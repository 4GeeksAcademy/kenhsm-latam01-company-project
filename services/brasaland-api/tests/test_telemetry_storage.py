from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from brasaland_api.core.config import Settings
from brasaland_api.modules.telemetry import storage
from brasaland_api.modules.telemetry.schemas import TelemetryEvent
from brasaland_api.modules.telemetry.storage import SupabaseStorageError, event_to_row, insert_events


def make_event(event_type: str = "inbound_order_created", properties: dict[str, Any] | None = None) -> TelemetryEvent:
    if properties is None:
        properties = {
            "location_id": "COL-01",
            "country": "CO",
            "product_id": "PROD-01",
            "product_category": "protein",
            "quantity": 5.0,
            "unit": "kg",
            "currency": "COP",
            "supplier_id": "SUP-01",
            "inbound_order_id": "IN-1001",
            "unit_price": 42000,
        }
    return TelemetryEvent(
        eventId=UUID("6ba7b810-9dad-41d1-80b4-00c04fd430c8"),
        timestamp=datetime(2026, 9, 27, 14, 5, tzinfo=timezone.utc),
        sessionId="session-12345678",
        userId=None,
        event_type=event_type,
        schemaVersion="1.0.0",
        requestId=UUID("6ba7b811-9dad-41d1-80b4-00c04fd430c8"),
        properties=properties,
    )


def test_event_row_maps_context_to_tags_and_uses_safe_summary() -> None:
    event = make_event()

    row = event_to_row(event)

    assert row == {
        "timestamp": "2026-09-27T14:05:00+00:00",
        "service": "backoffice",
        "event_type": "inbound_order_created",
        "level": "info",
        "value": 5.0,
        "message": "inbound order created",
        "tags": event.properties,
    }


def test_insert_events_sends_all_rows_in_one_supabase_post(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, *, json: list[dict[str, Any]], headers: dict[str, str], timeout: float) -> Response:
        captured.append({"url": url, "rows": json, "headers": headers, "timeout": timeout})
        return Response()

    monkeypatch.setattr(storage.httpx, "post", fake_post)
    settings = Settings(
        supabase_url="https://brasaland.supabase.co",
        supabase_service_role_key=SecretStr("test-service-role-key"),
        _env_file=None,
    )

    stored = insert_events([make_event(), make_event()], settings=settings)

    assert stored == 2
    assert len(captured) == 1
    assert captured[0]["url"] == "https://brasaland.supabase.co/rest/v1/telemetry_events"
    assert len(captured[0]["rows"]) == 2
    assert captured[0]["headers"]["Prefer"] == "return=minimal"
    assert captured[0]["headers"]["Authorization"] == "Bearer test-service-role-key"


def test_insert_events_requires_supabase_configuration() -> None:
    with pytest.raises(SupabaseStorageError, match="not configured"):
        insert_events([make_event()], settings=Settings(_env_file=None))


def test_insert_events_wraps_postgrest_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_post(*args: Any, **kwargs: Any) -> None:
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr(storage.httpx, "post", fail_post)
    settings = Settings(
        supabase_url="https://brasaland.supabase.co",
        supabase_service_role_key=SecretStr("test-service-role-key"),
        _env_file=None,
    )

    with pytest.raises(SupabaseStorageError, match="rejected the telemetry batch"):
        insert_events([make_event()], settings=settings)