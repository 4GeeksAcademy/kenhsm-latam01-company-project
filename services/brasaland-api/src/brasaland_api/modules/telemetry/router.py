"""Partially validates and bulk-persists telemetry batches."""
"""Temporary telemetry receiver used to validate frontend batches."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import ValidationError

from brasaland_api.modules.telemetry.allowlists import properties_match_contract
from brasaland_api.modules.telemetry.schemas import TelemetryBatchStored, TelemetryEvent
from brasaland_api.modules.telemetry.storage import SupabaseStorageError, insert_events



from brasaland_api.modules.telemetry.schemas import TelemetryBatch, TelemetryBatchAccepted

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


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
  
  
# @router.post("/events", response_model=TelemetryBatchAccepted)
# def receive_events(batch: TelemetryBatch) -> TelemetryBatchAccepted:
#    event_types = [event.event_type for event in batch.events]
#    logger.info("Received telemetry batch count=%d event_types=%s", len(event_types), event_types)
#    return TelemetryBatchAccepted(received=len(batch.events))
