"""Pydantic schemas for inventory API requests and responses.

Separate from ORM models — these are for API contracts only.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# ===== Ingredient Schemas =====

class IngredientCreate(BaseModel):
    """Request schema for creating a new ingredient."""
    name: str
    sku: str
    unit: str
    category: str  # "meat", "produce", "sauce", "beverage", "packaging", "cleaning"
    country: str  # "CO" or "US"


class IngredientResponse(BaseModel):
    """Response schema for ingredient with calculated current_stock."""
    id: int
    name: str
    sku: str
    unit: str
    category: str
    country: str
    current_stock: float  # Calculated: SUM(entries) - SUM(exits)
    
    class Config:
        from_attributes = True


# ===== IngredientEntry Schemas =====

class IngredientEntryCreate(BaseModel):
    """Request schema for registering an inbound order (ingredient entry)."""
    ingredient_id: int
    quantity: float = Field(gt=0, description="Quantity must be positive")
    supplier_name: str
    location_id: int = Field(ge=1, le=14, description="Location ID must be between 1 and 14")


class IngredientEntryResponse(BaseModel):
    """Response schema for ingredient entry."""
    id: int
    ingredient_id: int
    quantity: float
    supplier_name: str
    location_id: int
    created_at: datetime
    user_uuid: str
    ingredient: IngredientResponse  # Include ingredient details
    
    class Config:
        from_attributes = True


# ===== IngredientExit Schemas =====

class IngredientExitCreate(BaseModel):
    """Request schema for registering an outbound order (ingredient exit)."""
    ingredient_id: int
    quantity: float = Field(gt=0, description="Quantity must be positive")
    reason: str = Field(..., description="'consumption' or 'waste'")
    location_id: int = Field(ge=1, le=14, description="Location ID must be between 1 and 14")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.reason not in ("consumption", "waste"):
            raise ValueError("reason must be 'consumption' or 'waste'")


class IngredientExitResponse(BaseModel):
    """Response schema for ingredient exit."""
    id: int
    ingredient_id: int
    quantity: float
    reason: str
    location_id: int
    created_at: datetime
    user_uuid: str
    ingredient: IngredientResponse  # Include ingredient details
    
    class Config:
        from_attributes = True


# ===== Combined Responses =====

class OrderListResponse(BaseModel):
    """Response for listing both entries and exits."""
    entries: list[IngredientEntryResponse]
    exits: list[IngredientExitResponse]


class IngredientListResponse(BaseModel):
    """Response for listing all ingredients with current stock."""
    items: list[IngredientResponse]
    total: int
