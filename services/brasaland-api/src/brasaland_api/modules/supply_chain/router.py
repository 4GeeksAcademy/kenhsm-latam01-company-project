"""Minimal supply-chain endpoints (suppliers, purchase orders) protected by authentication."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.supply_chain.schemas import PurchaseOrderCreate, PurchaseOrderOut, SupplierOut
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])

_SUPPLIERS = [
    {"id": "SUP-001", "name": "Carnes del Valle", "country": "CO"},
    {"id": "SUP-014", "name": "Florida Produce Co.", "country": "US"},
]

_PURCHASE_ORDERS: list[dict] = []


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(current_user: UserRecord = Depends(get_current_user)) -> list[SupplierOut]:
    return _SUPPLIERS


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate, current_user: UserRecord = Depends(get_current_user)
) -> PurchaseOrderOut:
    order = PurchaseOrderOut(
        id=f"PO-{len(_PURCHASE_ORDERS) + 1:04d}",
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    _PURCHASE_ORDERS.append(order.model_dump())
    return order
