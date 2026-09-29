"""Shared response schemas for infrastructure endpoints."""

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str