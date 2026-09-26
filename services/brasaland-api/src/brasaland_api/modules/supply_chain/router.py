"""Minimal supply-chain endpoints (suppliers, purchase orders) protected by authentication."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends, status

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])

_SUPPLIERS = [
    {"id": "SUP-001", "name": "Carnes del Valle", "country": "CO"},
    {"id": "SUP-014", "name": "Florida Produce Co.", "country": "US"},
]

_PURCHASE_ORDERS: list[dict] = []


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    location_id: str
    items: dict[str, float]


@router.get("/suppliers")
def list_suppliers(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
    return _SUPPLIERS


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate, current_user: UserRecord = Depends(get_current_user)
) -> dict:
    order = {"id": f"PO-{len(_PURCHASE_ORDERS) + 1:04d}", "created_by": current_user.id, **payload.model_dump()}
    _PURCHASE_ORDERS.append(order)
    return order
