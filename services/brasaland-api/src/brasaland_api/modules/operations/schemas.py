"""Explicit response projections for operations endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class SalesSummary(BaseModel):
    location_id: str
    date: date
    total_usd: float


class InventoryItem(BaseModel):
    location_id: str
    ingredient: str
    quantity: float