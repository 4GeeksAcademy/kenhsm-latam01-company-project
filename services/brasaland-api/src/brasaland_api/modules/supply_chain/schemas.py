"""Request and response schemas for supply-chain endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SupplierOut(BaseModel):
    id: str
    name: str
    country: str


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    location_id: str
    items: dict[str, float]


class PurchaseOrderOut(PurchaseOrderCreate):
    id: str
    created_at: datetime
    created_by: str
    status: Literal["pending_approval", "approved"]
    approved_by: str | None
    approved_at: datetime | None