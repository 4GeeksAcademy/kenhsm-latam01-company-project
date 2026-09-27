"""Append-only bulk persistence for telemetry batches in Supabase."""

from __future__ import annotations

from typing import Any

import httpx

from brasaland_api.core.config import Settings, get_settings
from brasaland_api.modules.telemetry.schemas import TelemetryEvent

VALUE_PROPERTIES = {
    "inbound_order_created": "quantity",
    "outbound_order_created": "quantity",
    "stock_waste_registered": "quantity",
    "stock_threshold_triggered": "quantity",
    "direct_stock_edit_rejected": "quantity",
    "ingredient_price_variance_detected": "variance_percent",
    "inventory_order_validation_failed": "item_count",
    "purchase_order_created": "line_count",
    "workflow_completed": "elapsed_seconds",
    "workflow_abandoned": "elapsed_seconds",
    "api_latency_recorded": "duration_ms",
    "incident_analysis_completed": "duration_ms",
    "incident_analysis_failed": "duration_ms",
    "background_job_failed": "duration_ms",
}


class SupabaseStorageError(RuntimeError):
    """Supabase is not configured or rejected a telemetry batch."""


def event_to_row(event: TelemetryEvent) -> dict[str, Any]:
    value_property = VALUE_PROPERTIES.get(event.event_type)
    candidate = event.properties.get(value_property) if value_property else None
    value = candidate if isinstance(candidate, (int, float)) and not isinstance(candidate, bool) else None

    return {
        "timestamp": event.timestamp.isoformat(),
        "service": "backoffice",
        "event_type": event.event_type,
        "level": event_level(event),
        "value": value,
        "message": event.event_type.replace("_", " "),
        "tags": event.properties,
    }


def event_level(event: TelemetryEvent) -> str:
    if event.event_type == "api_request_failed":
        status_code = event.properties.get("status_code")
        return "error" if isinstance(status_code, int) and not isinstance(status_code, bool) and status_code >= 500 else "warn"
    if event.event_type == "incident_analysis_failed":
        return "error" if event.properties.get("failure_stage") == "dependency" else "warn"
    if event.event_type == "frontend_error_captured":
        return "error"
    if event.event_type == "background_job_failed":
        return "error"
    if event.event_type in {"auth_login_failed", "access_denied", "inventory_order_validation_failed"}:
        return "warn"
    return "info"


def insert_events(events: list[TelemetryEvent], *, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseStorageError("Supabase storage is not configured")

    rows = [event_to_row(event) for event in events]
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/telemetry_events"
    headers = {
        "apikey": settings.supabase_service_role_key.get_secret_value(),
        "Authorization": f"Bearer {settings.supabase_service_role_key.get_secret_value()}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        response = httpx.post(url, json=rows, headers=headers, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise SupabaseStorageError("Supabase rejected the telemetry batch") from error

    return len(rows)