"""Request and response schemas for HR endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class EmployeeUpdate(BaseModel):
    location_id: str | None = None
    salary_usd: float | None = None


class EmployeeOut(BaseModel):
    id: str
    name: str
    location_id: str
    salary_usd: float