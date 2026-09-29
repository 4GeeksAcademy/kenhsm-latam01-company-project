"""Temporary telemetry receiver used to validate frontend batches."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from brasaland_api.modules.telemetry.schemas import TelemetryBatch, TelemetryBatchAccepted

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryBatchAccepted)
def receive_events(batch: TelemetryBatch) -> TelemetryBatchAccepted:
    event_types = [event.event_type for event in batch.events]
    logger.info("Received telemetry batch count=%d event_types=%s", len(event_types), event_types)
    return TelemetryBatchAccepted(received=len(batch.events))