from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from brasaland_api.core.deps import get_current_user
from brasaland_api.main import app
from brasaland_api.modules.operations import router as operations_router
from brasaland_api.modules.supply_chain import router as supply_chain_router
from brasaland_api.modules.supply_chain.router import PurchaseOrderCreate
from brasaland_api.modules.users.models import UserRole


def user(role: UserRole = UserRole.USER, user_id: str = "user-1"):
    return type("User", (), {"id": user_id, "role": role})()


def test_operations_returns_sales_and_inventory():
    assert operations_router.list_sales(user())[0]["location_id"] == "COL-01"
    assert operations_router.list_inventory(user())[0]["quantity"] > 0


def test_operations_handles_empty_inventory(monkeypatch):
    monkeypatch.setattr(operations_router, "_INVENTORY", [])
    assert operations_router.list_inventory(user()) == []


def test_operations_requires_authenticated_user_dependency():
    with pytest.raises(HTTPException) as error:
        from brasaland_api.core.deps import get_current_user
        get_current_user("invalid")
    assert error.value.status_code == 401


def test_supply_chain_lists_suppliers():
    suppliers = supply_chain_router.list_suppliers(user())
    assert len(suppliers) == 2
    assert suppliers[0]["id"] == "SUP-001"


def test_purchase_order_requires_all_fields():
    with pytest.raises(ValidationError):
        PurchaseOrderCreate(supplier_id="SUP-001", location_id="COL-01")


def test_purchase_order_is_created_with_requesting_user():
    order = supply_chain_router.create_purchase_order(
        PurchaseOrderCreate(supplier_id="SUP-001", location_id="COL-01", items={"carne": 5}),
        user(UserRole.MANAGER, "requester-1"),
    )
    assert order.created_by == "requester-1"
    assert order.status == "pending_approval"
    assert order.items == {"carne": 5}


def test_purchase_order_requires_role_and_a_separate_human_approver(monkeypatch):
    monkeypatch.setattr(supply_chain_router, "_PURCHASE_ORDERS", [])
    client = TestClient(app)
    payload = {"supplier_id": "SUP-001", "location_id": "COL-01", "items": {"carne": 5}}

    try:
        app.dependency_overrides[get_current_user] = lambda: user(UserRole.USER)
        denied = client.post("/supply-chain/purchase-orders", json=payload)
        assert denied.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: user(UserRole.MANAGER, "requester-1")
        created = client.post("/supply-chain/purchase-orders", json=payload)
        assert created.status_code == 201
        order_id = created.json()["id"]
        assert created.json()["status"] == "pending_approval"

        self_approval = client.post(f"/supply-chain/purchase-orders/{order_id}/approve")
        assert self_approval.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: user(UserRole.ADMIN, "approver-1")
        approved = client.post(f"/supply-chain/purchase-orders/{order_id}/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["approved_by"] == "approver-1"
    finally:
        app.dependency_overrides.pop(get_current_user, None)