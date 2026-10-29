"""SQLModel ORM models for inventory management (Supabase PostgreSQL).

Ingredient, IngredientEntry, and IngredientExit entities using SQLModel.
Stock is never stored directly — it's always calculated from entries and exits.
"""

from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class IngredientEntry(SQLModel, table=True):
    """Ingredient entry — inbound order from supplier.
    
    Represents a delivery of ingredients that increases stock.
    """
    __tablename__ = "ingredient_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id")
    quantity: float  # Amount received in the ingredient's unit
    supplier_name: str  # Name of the supplier
    location_id: int  # Location (1-14) where the delivery was received
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_uuid: str  # UUID of the user (from TinyDB) who registered the entry
    
    # Relationships
    ingredient: Optional["Ingredient"] = Relationship(back_populates="entries")


class IngredientExit(SQLModel, table=True):
    """Ingredient exit — consumption or waste record.
    
    Represents a reduction in stock due to consumption or waste.
    """
    __tablename__ = "ingredient_exits"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id")
    quantity: float  # Amount consumed or wasted in the ingredient's unit
    reason: str  # "consumption" or "waste"
    location_id: int  # Location (1-14) where the exit occurred
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_uuid: str  # UUID of the user (from TinyDB) who registered the exit
    
    # Relationships
    ingredient: Optional["Ingredient"] = Relationship(back_populates="exits")


class Ingredient(SQLModel, table=True):
    """Ingredient entity — represents a product in inventory.
    
    Stock is never stored as a column. It's always calculated as:
    current_stock = SUM(IngredientEntry.quantity) - SUM(IngredientExit.quantity)
    """
    __tablename__ = "ingredients"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g. "Falda de ternera", "Salsa de la casa"
    sku: str  # e.g. "BRS-BEEF-001"
    unit: str  # e.g. "kg", "litro", "unidad"
    category: str  # e.g. "meat", "produce", "sauce", "beverage", "packaging", "cleaning"
    country: str  # "CO" (Colombia) or "US" (United States)
    
    # Relationships
    entries: list[IngredientEntry] = Relationship(back_populates="ingredient")
    exits: list[IngredientExit] = Relationship(back_populates="ingredient")
