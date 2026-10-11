from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr

from brasaland_api.core.config import Settings
from brasaland_api.main import app
from brasaland_api.modules.telemetry import analysis
from brasaland_api.modules.telemetry.analysis import (
    SupabaseTelemetryReader,
    auth_failure_rate,
    clear_report_cache,
    error_rate_by_type,
    events_per_day,
    get_telemetry_report,
    latency_by_day,
)


class MemoryReader:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.calls = []

    def fetch_events(self, event_types, start_date, end_date):
        self.calls.append((tuple(event_types), start_date, end_date))
        return [row for row in self.rows if row["event_type"] in event_types]


def row(
    timestamp: str,
    event_type: str,
    *,
    level: str = "info",
    value: float | None = None,
    tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "level": level,
        "value": value,
        "tags": tags or {},
    }


def test_events_per_day_groups_by_utc_date_and_type_and_passes_window():
    reader = MemoryReader([
        row("2026-10-08T12:00:00Z", "section_viewed"),
        row("2026-10-08T13:00:00Z", "section_viewed"),
        row("2026-10-09T01:00:00Z", "section_viewed"),
        row("2026-10-08T14:00:00Z", "api_request_failed", level="error"),
    ])
    start = datetime(2026, 10, 8, tzinfo=timezone.utc)
    end = datetime(2026, 10, 10, tzinfo=timezone.utc)

    result = events_per_day(start, end, reader=reader)

    assert result == [
        {"event_date": "2026-10-08", "event_type": "api_request_failed", "event_count": 1},
        {"event_date": "2026-10-08", "event_type": "section_viewed", "event_count": 2},
        {"event_date": "2026-10-09", "event_type": "section_viewed", "event_count": 1},
    ]
    assert reader.calls[0][1:] == (start, end)


def test_error_rate_by_type_computes_daily_error_ratio():
    reader = MemoryReader([
        row("2026-10-08T09:00:00Z", "api_request_failed", level="error"),
        row("2026-10-08T09:01:00Z", "api_request_failed", level="warn"),
        row("2026-10-08T09:02:00Z", "api_request_failed", level="error"),
        row("2026-10-08T09:03:00Z", "section_viewed"),
    ])

    result = error_rate_by_type(
        datetime(2026, 10, 8, tzinfo=timezone.utc),
        datetime(2026, 10, 9, tzinfo=timezone.utc),
        reader=reader,
    )

    api_errors = next(item for item in result if item["event_type"] == "api_request_failed")
    assert api_errors["total_events"] == 3
    assert api_errors["error_events"] == 2
    assert api_errors["error_rate"] == 2 / 3


def test_latency_groups_only_rows_with_route_and_numeric_duration():
    reader = MemoryReader([
        row("2026-10-08T09:00:00Z", "api_latency_recorded", value=100, tags={"route_template": "/users"}),
        row("2026-10-08T09:01:00Z", "api_latency_recorded", value=300, tags={"route_template": "/users"}),
        row("2026-10-08T09:02:00Z", "api_latency_recorded", value=None, tags={"route_template": "/users"}),
        row("2026-10-08T09:03:00Z", "api_latency_recorded", value=200, tags={}),
    ])

    result = latency_by_day(
        datetime(2026, 10, 8, tzinfo=timezone.utc),
        datetime(2026, 10, 9, tzinfo=timezone.utc),
        reader=reader,
    )

    assert result == [{
        "event_date": "2026-10-08",
        "route_template": "/users",
        "request_count": 2,
        "mean_latency_ms": 200.0,
        "p95_latency_ms": 290.0,
    }]
    assert reader.calls[0][0] == ("api_latency_recorded",)


def test_auth_failure_rate_uses_both_attempt_types_in_source_filter():
    reader = MemoryReader([
        row("2026-10-08T09:00:00Z", "auth_login_failed", level="warn"),
        row("2026-10-08T09:01:00Z", "auth_login_failed", level="warn"),
        row("2026-10-08T09:02:00Z", "auth_login_succeeded"),
    ])

    result = auth_failure_rate(
        datetime(2026, 10, 8, tzinfo=timezone.utc),
        datetime(2026, 10, 9, tzinfo=timezone.utc),
        reader=reader,
    )

    assert result == [{
        "event_date": "2026-10-08",
        "login_attempts": 3,
        "failed_attempts": 2,
        "failure_rate": 2 / 3,
    }]
    assert set(reader.calls[0][0]) == {"auth_login_failed", "auth_login_succeeded"}


def test_supabase_reader_filters_event_type_and_utc_half_open_window():
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[row("2026-10-08T12:00:00Z", "section_viewed")])

    client = httpx.Client(transport=httpx.MockTransport(respond))
    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_service_role_key=SecretStr("test-only-key"),
        _env_file=None,
    )
    reader = SupabaseTelemetryReader(settings, client)
    try:
        records = reader.fetch_events(
            ["auth_login_failed", "auth_login_succeeded"],
            datetime(2026, 10, 8, tzinfo=timezone.utc),
            datetime(2026, 10, 9, tzinfo=timezone.utc),
        )
    finally:
        reader.close()
        client.close()

    query = parse_qs(urlparse(str(requests[0].url)).query)
    assert len(records) == 1
    assert "timestamp.gte.2026-10-08T00:00:00Z" in query["and"][0]
    assert "timestamp.lt.2026-10-09T00:00:00Z" in query["and"][0]
    assert query["event_type"][0] == "in.(auth_login_failed,auth_login_succeeded)"
    assert query["select"][0] == "timestamp,event_type,level,value,tags"
    assert requests[0].headers["authorization"] == "Bearer test-only-key"


def test_report_cache_reuses_same_window_for_sixty_seconds(monkeypatch):
    clear_report_cache()
    calls = []

    def calculate(start, end):
        calls.append((start, end))
        return {"period": {"from": start.isoformat(), "to": end.isoformat()}, "metrics": {}}

    monkeypatch.setattr(analysis, "_calculate_report", calculate)
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 8, tzinfo=timezone.utc)
    now = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)

    first = get_telemetry_report(start, end, now=now)
    second = get_telemetry_report(start, end, now=now + timedelta(seconds=59))
    third = get_telemetry_report(start, end, now=now + timedelta(seconds=61))

    assert first == second == third
    assert len(calls) == 2
    assert len(analysis._CACHE) == 1
    clear_report_cache()


def test_default_last_seven_days_uses_a_stable_cache_key(monkeypatch):
    clear_report_cache()
    calls = []

    def calculate(start, end):
        calls.append((start, end))
        return {"period": {"from": start.isoformat(), "to": end.isoformat()}, "metrics": {}}

    monkeypatch.setattr(analysis, "_calculate_report", calculate)
    get_telemetry_report(now=datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
    get_telemetry_report(now=datetime(2026, 10, 11, 12, 0, 10, tzinfo=timezone.utc))

    assert len(calls) == 1
    clear_report_cache()


def test_empty_windows_are_serializable_and_reversed_period_is_rejected(monkeypatch):
    empty = MemoryReader([])
    start = datetime(2026, 10, 8, tzinfo=timezone.utc)
    end = datetime(2026, 10, 9, tzinfo=timezone.utc)
    assert events_per_day(start, end, reader=empty) == []
    assert error_rate_by_type(start, end, reader=empty) == []
    assert latency_by_day(start, end, reader=empty) == []
    assert auth_failure_rate(start, end, reader=empty) == []
    try:
        events_per_day(end, start, reader=empty)
    except ValueError as error:
        assert "earlier" in str(error)
    else:
        raise AssertionError("reversed range was accepted")


def test_endpoint_uses_seven_day_default_and_returns_period_metrics(monkeypatch):
    captured = []

    def fake_report(start_date, end_date, *, now):
        captured.append((start_date, end_date, now))
        return {"period": {"from": start_date.isoformat(), "to": end_date.isoformat()}, "metrics": {"events_per_day": []}}

    monkeypatch.setattr("brasaland_api.modules.telemetry.router.get_telemetry_report", fake_report)
    response = TestClient(app).get("/telemetry/report")

    assert response.status_code == 200
    assert set(response.json()) == {"period", "metrics"}
    start, end, now = captured[0]
    assert end == now
    assert end - start == timedelta(days=7)


def test_endpoint_rejects_naive_or_reversed_dates():
    client = TestClient(app)
    naive = client.get("/telemetry/report?start_date=2026-10-01T00:00:00&end_date=2026-10-02T00:00:00Z")
    reversed_window = client.get("/telemetry/report?start_date=2026-10-03T00:00:00Z&end_date=2026-10-02T00:00:00Z")
    assert naive.status_code == 400
    assert reversed_window.status_code == 400


def test_endpoint_returns_safe_503_when_supabase_is_unconfigured():
    clear_report_cache()
    response = TestClient(app).get("/telemetry/report")
    assert response.status_code == 503
    assert response.json() == {"detail": "Telemetry report is temporarily unavailable"}
