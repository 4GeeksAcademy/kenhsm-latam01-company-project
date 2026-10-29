"""Seed script for inventory data — Brasaland.

Runs seed functions to populate inventory tables with initial data.
To be executed as: python -m brasaland_api.modules.inventory.seed
"""

from __future__ import annotations

from sqlmodel import Session
from datetime import datetime

from brasaland_api.core.db import get_sqlmodel_engine
from brasaland_api.modules.inventory.models import (
    Ingredient,
    IngredientEntry,
    IngredientExit,
)


def seed_inventory():
    """Populate inventory tables with initial data."""
    engine = get_sqlmodel_engine()
    
    with Session(engine) as session:
        # Check if data already seeded
        existing_ingredients = session.query(Ingredient).count()
        if existing_ingredients > 0:
            print("✓ Inventory already seeded. Skipping.")
            return
        
        # ===== Seed Ingredients =====
        ingredients_data = [
            {
                "name": "Falda de ternera",
                "sku": "BRS-BEEF-001",
                "unit": "kg",
                "category": "meat",
                "country": "CO",
            },
            {
                "name": "Costilla de cerdo",
                "sku": "BRS-PORK-001",
                "unit": "kg",
                "category": "meat",
                "country": "US",
            },
            {
                "name": "Chimichurri",
                "sku": "BRS-SAUCE-001",
                "unit": "litro",
                "category": "sauce",
                "country": "CO",
            },
            {
                "name": "Salsa BBQ de la casa",
                "sku": "BRS-SAUCE-002",
                "unit": "litro",
                "category": "sauce",
                "country": "US",
            },
            {
                "name": "Yuca",
                "sku": "BRS-PROD-001",
                "unit": "kg",
                "category": "produce",
                "country": "CO",
            },
            {
                "name": "Caja para llevar (M)",
                "sku": "BRS-PKG-001",
                "unit": "unidad",
                "category": "packaging",
                "country": "CO",
            },
        ]
        
        ingredients = []
        for data in ingredients_data:
            ing = Ingredient(**data)
            session.add(ing)
            ingredients.append(ing)
        
        session.commit()
        print(f"✓ Seeded {len(ingredients)} ingredients.")
        
        # Refresh to get IDs
        for ing in ingredients:
            session.refresh(ing)
        
        # ===== Seed IngredientEntries (Inbound Orders) =====
        entries_data = [
            {
                "ingredient_id": ingredients[0].id,  # BRS-BEEF-001 (Falda de ternera)
                "quantity": 50.0,
                "supplier_name": "Carnes del Valle S.A.",
                "location_id": 1,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440000",  # Example UUID
                "created_at": datetime(2026, 10, 15, 8, 0, 0),
            },
            {
                "ingredient_id": ingredients[0].id,  # BRS-BEEF-001 (Falda de ternera)
                "quantity": 30.0,
                "supplier_name": "MiamiMeat Co.",
                "location_id": 7,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440001",
                "created_at": datetime(2026, 10, 16, 9, 30, 0),
            },
            {
                "ingredient_id": ingredients[1].id,  # BRS-PORK-001 (Costilla de cerdo)
                "quantity": 40.0,
                "supplier_name": "MiamiMeat Co.",
                "location_id": 7,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440001",
                "created_at": datetime(2026, 10, 16, 10, 0, 0),
            },
            {
                "ingredient_id": ingredients[2].id,  # BRS-SAUCE-001 (Chimichurri)
                "quantity": 20.0,
                "supplier_name": "Salsas Artesanales Ltda.",
                "location_id": 3,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": datetime(2026, 10, 17, 7, 0, 0),
            },
        ]
        
        entries = []
        for data in entries_data:
            entry = IngredientEntry(**data)
            session.add(entry)
            entries.append(entry)
        
        session.commit()
        print(f"✓ Seeded {len(entries)} ingredient entries.")
        
        # Refresh to get IDs
        for entry in entries:
            session.refresh(entry)
        
        # ===== Seed IngredientExits (Outbound Orders) =====
        exits_data = [
            {
                "ingredient_id": ingredients[0].id,  # BRS-BEEF-001 (Falda de ternera)
                "quantity": 15.0,
                "reason": "consumption",
                "location_id": 1,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440002",
                "created_at": datetime(2026, 10, 18, 12, 0, 0),
            },
            {
                "ingredient_id": ingredients[0].id,  # BRS-BEEF-001 (Falda de ternera)
                "quantity": 5.0,
                "reason": "waste",
                "location_id": 1,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440003",
                "created_at": datetime(2026, 10, 18, 14, 30, 0),
            },
            {
                "ingredient_id": ingredients[2].id,  # BRS-SAUCE-001 (Chimichurri)
                "quantity": 8.0,
                "reason": "consumption",
                "location_id": 3,
                "user_uuid": "550e8400-e29b-41d4-a716-446655440002",
                "created_at": datetime(2026, 10, 19, 11, 0, 0),
            },
        ]
        
        exits = []
        for data in exits_data:
            exit_rec = IngredientExit(**data)
            session.add(exit_rec)
            exits.append(exit_rec)
        
        session.commit()
        print(f"✓ Seeded {len(exits)} ingredient exits.")
        
        # ===== Verify Stock Calculations =====
        print("\n✓ Stock Summary (Entries - Exits):")
        for ing in ingredients:
            # Recalculate from database
            from sqlalchemy import func
            from sqlmodel import select
            
            entries_sum = session.exec(
                select(func.sum(IngredientEntry.quantity))
                .where(IngredientEntry.ingredient_id == ing.id)
            ).first() or 0.0
            
            exits_sum = session.exec(
                select(func.sum(IngredientExit.quantity))
                .where(IngredientExit.ingredient_id == ing.id)
            ).first() or 0.0
            
            current = float(entries_sum - exits_sum)
            print(f"  {ing.sku} ({ing.name}): {entries_sum} - {exits_sum} = {current} {ing.unit}")


if __name__ == "__main__":
    seed_inventory()
    print("\n✅ Inventory seeding completed successfully!")
