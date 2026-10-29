"""Routes for supplier endpoints."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
from tinydb import Query

try:
    from ..database import get_db
    from ..models import SupplierCreate, SupplierResponse, SupplierUpdate, VALID_CATEGORIES
except ImportError:
    from database import get_db
    from models import SupplierCreate, SupplierResponse, SupplierUpdate, VALID_CATEGORIES

router = APIRouter()

def supplier_to_response(doc: dict) -> SupplierResponse:
    """Convert database document to SupplierResponse."""
    return SupplierResponse(
        id=doc.doc_id,
        name=doc["name"],
        country=doc["country"],
        categories=doc["categories"],
        rate_per_unit=doc["rate_per_unit"],
        currency=doc["currency"],
        status=doc["status"],
        contact_email=doc.get("contact_email"),
        notes=doc.get("notes"),
        updated_at=datetime.fromisoformat(doc["updated_at"]) if isinstance(doc["updated_at"], str) else doc["updated_at"]
    )

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(supplier: SupplierCreate) -> SupplierResponse:
    """Create a new supplier."""
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    # Prepare supplier data
    supplier_data = {
        "name": supplier.name,
        "country": supplier.country,
        "categories": supplier.categories,
        "rate_per_unit": supplier.rate_per_unit,
        "currency": supplier.currency,
        "status": supplier.status,
        "contact_email": supplier.contact_email,
        "notes": supplier.notes,
        "updated_at": datetime.now().isoformat()
    }
    
    # Insert and get the document
    supplier_id = suppliers_table.insert(supplier_data)
    created_doc = suppliers_table.get(doc_id=supplier_id)
    
    return supplier_to_response(created_doc)

@router.get("", response_model=List[SupplierResponse])
async def get_suppliers(
    country: Optional[str] = None,
    category: Optional[str] = None
) -> List[SupplierResponse]:
    """Get all suppliers with optional filters."""
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    # Get all suppliers
    docs = suppliers_table.all()
    
    # Apply filters
    if country:
        docs = [doc for doc in docs if doc["country"] == country]
    
    if category:
        if category not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Valid categories: {', '.join(VALID_CATEGORIES)}"
            )
        docs = [doc for doc in docs if category in doc["categories"]]
    
    return [supplier_to_response(doc) for doc in docs]

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: int) -> SupplierResponse:
    """Get a specific supplier by ID."""
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    doc = suppliers_table.get(doc_id=supplier_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    return supplier_to_response(doc)

@router.patch("/{supplier_id}/rate", response_model=SupplierResponse)
async def update_supplier_rate(supplier_id: int, rate_per_unit: float) -> SupplierResponse:
    """Update supplier rate."""
    if rate_per_unit <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rate per unit must be greater than 0"
        )
    
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    doc = suppliers_table.get(doc_id=supplier_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    # Update rate and timestamp
    suppliers_table.update(
        {
            "rate_per_unit": rate_per_unit,
            "updated_at": datetime.now().isoformat()
        },
        doc_ids=[supplier_id]
    )
    
    updated_doc = suppliers_table.get(doc_id=supplier_id)
    return supplier_to_response(updated_doc)

@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
async def update_supplier_status(supplier_id: int, status_value: str) -> SupplierResponse:
    """Update supplier status."""
    if status_value not in ["active", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status must be 'active' or 'suspended'"
        )
    
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    doc = suppliers_table.get(doc_id=supplier_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    # Update status
    suppliers_table.update(
        {"status": status_value},
        doc_ids=[supplier_id]
    )
    
    updated_doc = suppliers_table.get(doc_id=supplier_id)
    return supplier_to_response(updated_doc)

@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(supplier_id: int):
    """Delete a supplier."""
    db = get_db()
    suppliers_table = db.table("suppliers")
    
    doc = suppliers_table.get(doc_id=supplier_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    
    suppliers_table.remove(doc_ids=[supplier_id])
    return None
