"""Request and response models for telemetry batch ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    timestamp: datetime
    sessionId: str | None
    userId: str | None
    event_type: str = Field(pattern=r"^[a-z]+(?:_[a-z]+)+$")
    schemaVersion: Literal["1.0.0"]
    requestId: UUID
    properties: dict[str, Any]

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("timestamp must include a UTC timezone")
        return value


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent]
    received: int

class TelemetryBatchAccepted(BaseModel):
    received: int


class TelemetryBatchStored(BaseModel):
    received: int
    stored: int
    rejected: int
