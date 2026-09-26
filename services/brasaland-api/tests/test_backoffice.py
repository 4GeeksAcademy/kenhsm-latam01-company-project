from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from brasaland_api.modules.operations import router as operations_router
from brasaland_api.modules.supply_chain import router as supply_chain_router
from brasaland_api.modules.supply_chain.router import PurchaseOrderCreate
from brasaland_api.modules.users.models import UserRole


def user(role: UserRole = UserRole.USER):
    return type("User", (), {"id": "manager-1", "role": role})()


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
        PurchaseOrderCreate(supplier_id="SUP-001", location_id="COL-01", items={"carne": 5}), user()
    )
    assert order["created_by"] == "manager-1"
    assert order["items"] == {"carne": 5}