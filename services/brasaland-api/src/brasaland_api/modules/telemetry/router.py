"""Temporary telemetry receiver used to validate frontend batches."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import ValidationError

from brasaland_api.modules.telemetry.allowlists import properties_match_contract
from brasaland_api.modules.telemetry.analysis import TelemetryAnalysisError, get_telemetry_report
from brasaland_api.modules.telemetry.schemas import TelemetryBatchStored, TelemetryEvent
from brasaland_api.modules.telemetry.storage import SupabaseStorageError, insert_events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/report")
def telemetry_report(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    period_end = end_date or now
    period_start = start_date or (period_end - timedelta(days=7))
    if period_start.tzinfo is None or period_end.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date and end_date must include a timezone",
        )
    if period_start >= period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be earlier than end_date",
        )
    try:
        return get_telemetry_report(period_start, period_end, now=now)
    except TelemetryAnalysisError as error:
        logger.exception("Telemetry report query failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry report is temporarily unavailable",
        ) from error


@router.post("/events", response_model=TelemetryBatchStored)
def receive_events(payload: dict[str, Any] = Body(...)) -> TelemetryBatchStored:
    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="events must be an array")

    valid_events: list[TelemetryEvent] = []
    rejected = 0
    for raw_event in raw_events:
        try:
            event = TelemetryEvent.model_validate(raw_event)
        except ValidationError:
            rejected += 1
            continue

        if not properties_match_contract(event.event_type, event.properties):
            rejected += 1
            continue
        valid_events.append(event)

    if valid_events:
        try:
            stored = insert_events(valid_events)
        except SupabaseStorageError as error:
            logger.exception("Telemetry batch persistence failed; received=%d valid=%d", len(raw_events), len(valid_events))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry storage is temporarily unavailable",
            ) from error
    else:
        stored = 0

    logger.info(
        "Telemetry batch processed received=%d stored=%d rejected=%d",
        len(raw_events),
        stored,
        rejected,
    )
    return TelemetryBatchStored(received=len(raw_events), stored=stored, rejected=rejected)
