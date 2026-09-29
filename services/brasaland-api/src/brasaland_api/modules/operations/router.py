"""Minimal operations endpoints (sales, inventory) protected by authentication.

Full persistence for this domain is out of scope for AUTH-01; these routes
exist to demonstrate that sensitive, pre-existing endpoints are now guarded
by `get_current_user`, per the architecture proposal in docs/ARCHITECTURE_PROPOSAL.md.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from brasaland_api.core.cache import response_cache
from brasaland_api.core.deps import get_current_user
<<<<<<< HEAD
from brasaland_api.modules.operations.schemas import InventoryItem, SalesSummary
=======
>>>>>>> origin/main
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/operations", tags=["operations"])
SALES_CACHE_TTL_SECONDS = 30

_SALES = [
    {"location_id": "COL-01", "date": "2026-09-17", "total_usd": 1820.50},
    {"location_id": "FLA-02", "date": "2026-09-17", "total_usd": 2140.00},
]

_INVENTORY = [
    {"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 42.5},
    {"location_id": "FLA-02", "ingredient": "carne_res_kg", "quantity": 11.0},
]


<<<<<<< HEAD
@router.get("/sales", response_model=list[SalesSummary])
def list_sales(current_user: UserRecord = Depends(get_current_user)) -> list[SalesSummary]:
    return _SALES


@router.get("/inventory", response_model=list[InventoryItem])
def list_inventory(current_user: UserRecord = Depends(get_current_user)) -> list[InventoryItem]:
=======
@router.get("/sales")
def list_sales(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
    return response_cache.get_or_set(
        f"operations:sales:{current_user.id}",
        lambda: _SALES,
        ttl_seconds=SALES_CACHE_TTL_SECONDS,
    )


@router.get("/inventory")
def list_inventory(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
>>>>>>> origin/main
    return _INVENTORY
