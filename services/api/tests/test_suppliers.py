"""Tests for supplier endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from database import get_db

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def clean_db():
    """Clean database before and after each test."""
    db = get_db()
    # Clear all tables
    if "suppliers" in db.tables():
        db.table("suppliers").truncate()
    yield db
    # Cleanup after test
    if "suppliers" in db.tables():
        db.table("suppliers").truncate()

def test_create_supplier(client, clean_db):
    """Test creating a new supplier."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Test Supplier",
            "country": "Colombia",
            "categories": ["carne"],
            "rate_per_unit": 25000.0,
            "currency": "COP",
            "status": "active",
            "contact_email": "test@supplier.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Supplier"
    assert data["country"] == "Colombia"
    assert data["rate_per_unit"] == 25000.0
    assert data["status"] == "active"
    assert "id" in data
    assert "updated_at" in data

def test_create_supplier_invalid_rate(client, clean_db):
    """Test that negative rates are rejected."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Bad Supplier",
            "country": "Colombia",
            "categories": ["carne"],
            "rate_per_unit": -100.0,
            "currency": "COP",
            "status": "active"
        }
    )
    assert response.status_code == 422

def test_create_supplier_invalid_status(client, clean_db):
    """Test that invalid status is rejected."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Bad Supplier",
            "country": "Colombia",
            "categories": ["carne"],
            "rate_per_unit": 25000.0,
            "currency": "COP",
            "status": "invalid_status"
        }
    )
    assert response.status_code == 422

def test_create_supplier_invalid_category(client, clean_db):
    """Test that invalid category is rejected."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Bad Supplier",
            "country": "Colombia",
            "categories": ["invalid_category"],
            "rate_per_unit": 25000.0,
            "currency": "COP",
            "status": "active"
        }
    )
    assert response.status_code == 422

def test_create_supplier_wrong_currency(client, clean_db):
    """Test that wrong currency for country is rejected."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Bad Supplier",
            "country": "Colombia",
            "categories": ["carne"],
            "rate_per_unit": 25000.0,
            "currency": "USD",  # Should be COP for Colombia
            "status": "active"
        }
    )
    assert response.status_code == 422

def test_get_all_suppliers(client, clean_db):
    """Test getting all suppliers."""
    # Create two suppliers
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    suppliers_table.insert({
        "name": "Supplier 1",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "test1@supplier.com",
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    suppliers_table.insert({
        "name": "Supplier 2",
        "country": "USA",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 2.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "test2@supplier.com",
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.get("/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Supplier 1"
    assert data[1]["name"] == "Supplier 2"

def test_get_suppliers_filter_by_country(client, clean_db):
    """Test filtering suppliers by country."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    suppliers_table.insert({
        "name": "Colombian Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    suppliers_table.insert({
        "name": "USA Supplier",
        "country": "USA",
        "categories": ["carne"],
        "rate_per_unit": 6.50,
        "currency": "USD",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.get("/suppliers?country=Colombia")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["country"] == "Colombia"

def test_get_suppliers_filter_by_category(client, clean_db):
    """Test filtering suppliers by category."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    suppliers_table.insert({
        "name": "Meat Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    suppliers_table.insert({
        "name": "Veggie Supplier",
        "country": "Colombia",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 3200.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.get("/suppliers?category=carne")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "carne" in data[0]["categories"]

def test_get_supplier_by_id(client, clean_db):
    """Test getting a specific supplier."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "test@supplier.com",
        "notes": "Test notes",
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.get(f"/suppliers/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["name"] == "Test Supplier"

def test_get_supplier_not_found(client, clean_db):
    """Test getting a non-existent supplier."""
    response = client.get("/suppliers/999")
    assert response.status_code == 404

def test_update_supplier_rate(client, clean_db):
    """Test updating supplier rate."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    old_time = datetime.now().isoformat()
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": old_time
    })
    
    response = client.patch(f"/suppliers/{doc_id}/rate?rate_per_unit=26000.0")
    assert response.status_code == 200
    data = response.json()
    assert data["rate_per_unit"] == 26000.0
    # Check that updated_at changed
    assert data["updated_at"] != old_time

def test_update_supplier_rate_invalid(client, clean_db):
    """Test that invalid rate update is rejected."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.patch(f"/suppliers/{doc_id}/rate?rate_per_unit=-100")
    assert response.status_code == 422

def test_update_supplier_status(client, clean_db):
    """Test updating supplier status."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.patch(f"/suppliers/{doc_id}/status?status_value=suspended")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "suspended"

def test_update_supplier_status_invalid(client, clean_db):
    """Test that invalid status update is rejected."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.patch(f"/suppliers/{doc_id}/status?status_value=invalid_status")
    assert response.status_code == 422

def test_delete_supplier(client, clean_db):
    """Test deleting a supplier."""
    db = clean_db
    suppliers_table = db.table("suppliers")
    
    doc_id = suppliers_table.insert({
        "name": "Test Supplier",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 25000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": None,
        "notes": None,
        "updated_at": datetime.now().isoformat()
    })
    
    response = client.delete(f"/suppliers/{doc_id}")
    assert response.status_code == 204
    
    # Verify supplier is deleted
    response = client.get(f"/suppliers/{doc_id}")
    assert response.status_code == 404

def test_delete_supplier_not_found(client, clean_db):
    """Test deleting a non-existent supplier."""
    response = client.delete("/suppliers/999")
    assert response.status_code == 404

def test_supplier_with_multiple_categories(client, clean_db):
    """Test supplier with multiple categories."""
    response = client.post(
        "/suppliers",
        json={
            "name": "Multi-category Supplier",
            "country": "Colombia",
            "categories": ["carne", "bebidas", "packaging"],
            "rate_per_unit": 20000.0,
            "currency": "COP",
            "status": "active"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["categories"]) == 3
    assert "carne" in data["categories"]
    assert "bebidas" in data["categories"]
    assert "packaging" in data["categories"]
