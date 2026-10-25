"""Minimal supply-chain endpoints (suppliers, purchase orders) protected by authentication."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from brasaland_api.core.deps import get_current_user, require_manager_or_admin
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
    payload: PurchaseOrderCreate, current_user: UserRecord = Depends(require_manager_or_admin)
) -> PurchaseOrderOut:
    order = PurchaseOrderOut(
        id=f"PO-{len(_PURCHASE_ORDERS) + 1:04d}",
        created_at=datetime.now(timezone.utc),
        created_by=str(current_user.id),
        status="pending_approval",
        approved_by=None,
        approved_at=None,
        **payload.model_dump(),
    )
    _PURCHASE_ORDERS.append(order.model_dump())
    return order


@router.post("/purchase-orders/{order_id}/approve", response_model=PurchaseOrderOut)
def approve_purchase_order(
    order_id: str, current_user: UserRecord = Depends(require_manager_or_admin)
) -> PurchaseOrderOut:
    order = next((item for item in _PURCHASE_ORDERS if item["id"] == order_id), None)
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada.")
    if order["created_by"] == str(current_user.id):
        raise HTTPException(status_code=403, detail="La persona solicitante no puede aprobar su propia orden.")
    if order["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="La orden ya no está pendiente de aprobación.")

    order["status"] = "approved"
    order["approved_by"] = str(current_user.id)
    order["approved_at"] = datetime.now(timezone.utc)
    return PurchaseOrderOut.model_validate(order)
