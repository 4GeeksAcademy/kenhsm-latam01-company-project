"""Pure transformation helpers for the weekly Brasaland business report."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


LOCATION_METADATA = {
    **{f"COL-{number:02d}": ("CO", "COP") for number in range(1, 11)},
    **{f"FLA-{number:02d}": ("US", "USD") for number in range(1, 5)},
}

BUSINESS_EVENT_TYPES = {
    "inbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
}


def iso_week_bounds(week_start: date) -> tuple[datetime, datetime]:
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    start = datetime.combine(week_start, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def _decimal(value: Any, field: str, *, allow_zero: bool = True) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a non-negative number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{field} must be a non-negative number") from error
    if not number.is_finite() or number < 0 or (not allow_zero and number == 0):
        raise ValueError(f"{field} must be a non-negative number")
    return number


def _json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def transform_weekly_location_metrics(
    events: list[dict[str, Any]], week_start: date | str
) -> list[dict[str, Any]]:
    """Validate source events and return one KPI row for each canonical location."""
    if isinstance(week_start, str):
        week_start = date.fromisoformat(week_start)
    lower_bound, upper_bound = iso_week_bounds(week_start)
    totals = {
        location_id: {
            "total_purchase_cost": Decimal(0),
            "total_waste_cost": Decimal(0),
            "stockout_events_count": 0,
            "price_alert_events_count": 0,
        }
        for location_id in LOCATION_METADATA
    }
    seen: dict[str, dict[str, Any]] = {}

    for event in events:
        event_type = event.get("event_type")
        if event_type not in BUSINESS_EVENT_TYPES:
            continue

        event_timestamp = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
        if event_timestamp.tzinfo is None:
            raise ValueError("telemetry event timestamp must include a timezone")
        event_timestamp = event_timestamp.astimezone(timezone.utc)
        if not lower_bound <= event_timestamp < upper_bound:
            continue

        event_id = str(event.get("event_id") or event.get("id") or "")
        if not event_id:
            raise ValueError("telemetry event is missing its persisted id")
        prior = seen.get(event_id)
        if prior is not None:
            if prior != event:
                raise ValueError(f"conflicting telemetry rows share id {event_id}")
            continue
        seen[event_id] = event

        properties = event.get("tags") or {}
        location_id = properties.get("location_id")
        if location_id not in LOCATION_METADATA:
            raise ValueError(f"unknown location_id in telemetry row {event_id}")
        expected_country, expected_currency = LOCATION_METADATA[location_id]
        if properties.get("country") != expected_country or properties.get("currency") != expected_currency:
            raise ValueError(f"country/currency mismatch for location {location_id}")

        row = totals[location_id]
        if event_type == "inbound_order_created":
            quantity = _decimal(properties.get("quantity"), "quantity", allow_zero=False)
            unit_price = _decimal(properties.get("unit_price"), "unit_price")
            row["total_purchase_cost"] += quantity * unit_price
        elif event_type == "stock_waste_registered":
            quantity = _decimal(properties.get("quantity"), "quantity", allow_zero=False)
            unit_cost = _decimal(properties.get("unit_cost"), "unit_cost")
            row["total_waste_cost"] += quantity * unit_cost
        elif event_type == "stock_threshold_triggered":
            row["stockout_events_count"] += 1
        elif event_type == "ingredient_price_variance_detected":
            row["price_alert_events_count"] += 1

    output = []
    for location_id, (country, currency) in LOCATION_METADATA.items():
        totals_for_location = totals[location_id]
        purchase_cost = totals_for_location["total_purchase_cost"]
        waste_cost = totals_for_location["total_waste_cost"]
        output.append(
            {
                "location_id": location_id,
                "country": country,
                "week_start": week_start.isoformat(),
                "total_purchase_cost": _json_number(purchase_cost),
                "total_waste_cost": _json_number(waste_cost),
                "waste_ratio": _json_number(waste_cost / purchase_cost if purchase_cost else Decimal(0)),
                "stockout_events_count": totals_for_location["stockout_events_count"],
                "price_alert_events_count": totals_for_location["price_alert_events_count"],
                "currency": currency,
            }
        )
    return output