"""Minimal operations endpoints (sales, inventory) protected by authentication.

Full persistence for this domain is out of scope for AUTH-01; these routes
exist to demonstrate that sensitive, pre-existing endpoints are now guarded
by `get_current_user`, per the architecture proposal in docs/ARCHITECTURE_PROPOSAL.md.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/operations", tags=["operations"])

_SALES = [
    {"location_id": "COL-01", "date": "2026-09-17", "total_usd": 1820.50},
    {"location_id": "FLA-02", "date": "2026-09-17", "total_usd": 2140.00},
]

_INVENTORY = [
    {"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 42.5},
    {"location_id": "FLA-02", "ingredient": "carne_res_kg", "quantity": 11.0},
]


@router.get("/sales")
def list_sales(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
    return _SALES


@router.get("/inventory")
def list_inventory(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
    return _INVENTORY
