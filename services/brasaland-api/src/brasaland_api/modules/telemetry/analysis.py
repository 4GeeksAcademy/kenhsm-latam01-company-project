"""Technical telemetry analysis, separate from the business reporting pipeline."""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, Sequence

import httpx
import pandas as pd

from brasaland_api.core.config import Settings, get_settings
from brasaland_api.modules.telemetry.allowlists import EVENT_PROPERTY_CONTRACTS

CACHE_TTL = timedelta(seconds=60)
PAGE_SIZE = 1000
AUTH_EVENT_TYPES = ("auth_login_failed", "auth_login_succeeded")
FRAME_COLUMNS = ("timestamp", "event_type", "level", "value", "tags")


class TelemetryAnalysisError(RuntimeError):
    """Safe, user-facing telemetry analysis failure."""


class TelemetryReader(Protocol):
    def fetch_events(
        self,
        event_types: Sequence[str],
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]: ...


class SupabaseTelemetryReader:
    """Read-only PostgREST reader; all time and event-type predicates execute in SQL."""

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=10.0)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch_events(
        self,
        event_types: Sequence[str],
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise TelemetryAnalysisError("Telemetry storage is not configured")
        if not event_types:
            return []

        url = f"{self.settings.supabase_url.rstrip('/')}/rest/v1/telemetry_events"
        headers = {
            "apikey": self.settings.supabase_service_role_key.get_secret_value(),
            "Authorization": f"Bearer {self.settings.supabase_service_role_key.get_secret_value()}",
            "Range-Unit": "items",
            "Prefer": "count=none",
        }
        params = {
            "select": ",".join(FRAME_COLUMNS),
            "event_type": f"in.({','.join(event_types)})",
            "and": f"(timestamp.gte.{_utc_iso(start_date)},timestamp.lt.{_utc_iso(end_date)})",
            "order": "timestamp.asc",
        }
        rows: list[dict[str, Any]] = []
        offset = 0
        try:
            while True:
                page_headers = {**headers, "Range": f"{offset}-{offset + PAGE_SIZE - 1}"}
                response = self.client.get(
                    url,
                    params=params,
                    headers=page_headers,
                )
                response.raise_for_status()
                page = response.json()
                if not isinstance(page, list):
                    raise TelemetryAnalysisError("Telemetry query returned an invalid result")
                rows.extend(page)
                if len(page) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        except TelemetryAnalysisError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            raise TelemetryAnalysisError("Telemetry storage is temporarily unavailable") from error
        return rows


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_window(start_date: datetime, end_date: datetime) -> tuple[datetime, datetime]:
    start = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date.astimezone(timezone.utc)
    end = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date.astimezone(timezone.utc)
    if start >= end:
        raise ValueError("start_date must be earlier than end_date")
    return start, end


def _load_frame(
    event_types: Sequence[str],
    start_date: datetime,
    end_date: datetime,
    reader: TelemetryReader | None = None,
) -> pd.DataFrame:
    start, end = _normalize_window(start_date, end_date)
    owns_reader = reader is None
    telemetry_reader = reader or SupabaseTelemetryReader()
    try:
        rows = telemetry_reader.fetch_events(event_types, start, end)
    finally:
        if owns_reader and isinstance(telemetry_reader, SupabaseTelemetryReader):
            telemetry_reader.close()
    frame = pd.DataFrame.from_records(rows, columns=FRAME_COLUMNS)
    if frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp", "event_type"])
    frame["event_date"] = frame["timestamp"].dt.date
    return frame


def _records(grouped: pd.DataFrame) -> list[dict[str, Any]]:
    records = grouped.reset_index()
    if "event_date" in records.columns:
        records["event_date"] = records["event_date"].astype(str)
    return records.to_dict(orient="records")


def events_per_day(
    start_date: datetime,
    end_date: datetime,
    *,
    reader: TelemetryReader | None = None,
) -> list[dict[str, Any]]:
    """Event volume by UTC day and event type."""
    frame = _load_frame(tuple(EVENT_PROPERTY_CONTRACTS), start_date, end_date, reader)
    if frame.empty:
        return []
    grouped = frame.groupby(["event_date", "event_type"], dropna=True).size().rename("event_count")
    return _records(grouped)


def error_rate_by_type(
    start_date: datetime,
    end_date: datetime,
    *,
    reader: TelemetryReader | None = None,
) -> list[dict[str, Any]]:
    """Daily event/error counts and rate by event type."""
    frame = _load_frame(tuple(EVENT_PROPERTY_CONTRACTS), start_date, end_date, reader)
    if frame.empty:
        return []
    frame["is_error"] = frame["level"].eq("error")
    grouped = frame.groupby(["event_date", "event_type"], dropna=True).agg(
        total_events=("event_type", "size"),
        error_events=("is_error", "sum"),
    )
    grouped["error_rate"] = grouped["error_events"].div(grouped["total_events"])
    return _records(grouped)


def latency_by_day(
    start_date: datetime,
    end_date: datetime,
    *,
    reader: TelemetryReader | None = None,
) -> list[dict[str, Any]]:
    """Mean and p95 API latency by UTC day and route template."""
    frame = _load_frame(("api_latency_recorded",), start_date, end_date, reader)
    if frame.empty:
        return []
    frame["route_template"] = frame["tags"].str.get("route_template")
    frame["duration_ms"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["route_template", "duration_ms"])
    if frame.empty:
        return []
    grouped = frame.groupby(["event_date", "route_template"], dropna=True).agg(
        request_count=("duration_ms", "size"),
        mean_latency_ms=("duration_ms", "mean"),
        p95_latency_ms=("duration_ms", lambda values: values.quantile(0.95)),
    )
    return _records(grouped)


def auth_failure_rate(
    start_date: datetime,
    end_date: datetime,
    *,
    reader: TelemetryReader | None = None,
) -> list[dict[str, Any]]:
    """Daily failed login attempts divided by all succeeded/failed attempts."""
    frame = _load_frame(AUTH_EVENT_TYPES, start_date, end_date, reader)
    if frame.empty:
        return []
    frame["is_failure"] = frame["event_type"].eq("auth_login_failed")
    grouped = frame.groupby("event_date", dropna=True).agg(
        login_attempts=("event_type", "size"),
        failed_attempts=("is_failure", "sum"),
    )
    grouped["failure_rate"] = grouped["failed_attempts"].div(grouped["login_attempts"])
    return _records(grouped)


def _calculate_report(start_date: datetime, end_date: datetime) -> dict[str, Any]:
    reader = SupabaseTelemetryReader()
    try:
        return {
            "period": {"from": _utc_iso(start_date), "to": _utc_iso(end_date)},
            "metrics": {
                "events_per_day": events_per_day(start_date, end_date, reader=reader),
                "error_rate_by_type": error_rate_by_type(start_date, end_date, reader=reader),
                "latency_by_day": latency_by_day(start_date, end_date, reader=reader),
                "auth_failure_rate": auth_failure_rate(start_date, end_date, reader=reader),
            },
        }
    finally:
        reader.close()


_CACHE: dict[tuple[str, ...], tuple[datetime, dict[str, Any]]] = {}
_CACHE_LOCK = threading.RLock()


def clear_report_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def get_telemetry_report(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    now: datetime | None = None,
    cache_ttl: timedelta = CACHE_TTL,
) -> dict[str, Any]:
    use_default_window = start_date is None and end_date is None
    current = now or datetime.now(timezone.utc)
    current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)
    end = end_date or current
    start = start_date or (end - timedelta(days=7))
    start, end = _normalize_window(start, end)
    cache_key = ("default-last-7-days",) if use_default_window else (_utc_iso(start), _utc_iso(end))
    with _CACHE_LOCK:
        expired_keys = [key for key, (created_at, _) in _CACHE.items() if current - created_at >= cache_ttl]
        for key in expired_keys:
            _CACHE.pop(key, None)
        cached = _CACHE.get(cache_key)
        if cached and current - cached[0] < cache_ttl:
            return deepcopy(cached[1])
        report = _calculate_report(start, end)
        _CACHE[cache_key] = (current, report)
        return deepcopy(report)
