"""Router for inventory management endpoints.

All inventory endpoints are grouped under /inventory prefix.
Uses SQLModel for Supabase PostgreSQL queries.
Uses TinyDB for user authentication context.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import Annotated

from brasaland_api.core.db import get_inventory_session
from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.users.models import UserRecord
from brasaland_api.modules.inventory.models import (
    Ingredient,
    IngredientEntry,
    IngredientExit,
)
from brasaland_api.modules.inventory.schemas import (
    IngredientCreate,
    IngredientResponse,
    IngredientEntryCreate,
    IngredientEntryResponse,
    IngredientExitCreate,
    IngredientExitResponse,
    OrderListResponse,
    IngredientListResponse,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])
SessionDep = Annotated[Session, Depends(get_inventory_session)]
CurrentUserDep = Annotated[UserRecord, Depends(get_current_user)]


def calculate_current_stock(session: Session, ingredient_id: int) -> float:
    """Calculate current stock for an ingredient.
    
    current_stock = SUM(entries.quantity) - SUM(exits.quantity)
    """
    # Sum of all entries for this ingredient
    entries_sum = session.exec(
        select(func.sum(IngredientEntry.quantity))
        .where(IngredientEntry.ingredient_id == ingredient_id)
    ).first() or 0.0
    
    # Sum of all exits for this ingredient
    exits_sum = session.exec(
        select(func.sum(IngredientExit.quantity))
        .where(IngredientExit.ingredient_id == ingredient_id)
    ).first() or 0.0
    
    return float(entries_sum - exits_sum)


def enrich_ingredient_response(ingredient: Ingredient, session: Session) -> IngredientResponse:
    """Enrich an Ingredient with calculated current_stock."""
    current_stock = calculate_current_stock(session, ingredient.id)
    return IngredientResponse(
        id=ingredient.id,
        name=ingredient.name,
        sku=ingredient.sku,
        unit=ingredient.unit,
        category=ingredient.category,
        country=ingredient.country,
        current_stock=current_stock,
    )


# ===== Ingredient Endpoints =====

@router.get("/products", response_model=IngredientListResponse)
async def list_ingredients(session: SessionDep) -> IngredientListResponse:
    """List all ingredients with their calculated current stock.
    
    GET /inventory/products
    """
    ingredients = session.exec(select(Ingredient)).all()
    items = [enrich_ingredient_response(ing, session) for ing in ingredients]
    return IngredientListResponse(items=items, total=len(items))


@router.post("/products", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    data: IngredientCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> IngredientResponse:
    """Create a new ingredient.
    
    POST /inventory/products
    Requires authentication.
    Stock starts at 0 and is only modified through orders.
    """
    # Check if SKU already exists
    existing = session.exec(
        select(Ingredient).where(Ingredient.sku == data.sku)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ingredient with SKU '{data.sku}' already exists.",
        )
    
    ingredient = Ingredient(
        name=data.name,
        sku=data.sku,
        unit=data.unit,
        category=data.category,
        country=data.country,
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    
    return enrich_ingredient_response(ingredient, session)


@router.get("/products/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    session: SessionDep,
) -> IngredientResponse:
    """Get a single ingredient with its current stock.
    
    GET /inventory/products/{id}
    """
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {ingredient_id} not found.",
        )
    
    return enrich_ingredient_response(ingredient, session)


# ===== IngredientEntry Endpoints (Inbound Orders) =====

@router.post("/orders/inbound", response_model=IngredientEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_inbound_order(
    data: IngredientEntryCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> IngredientEntryResponse:
    """Register an inbound order (ingredient delivery from supplier).
    
    POST /inventory/orders/inbound
    Requires authentication. Increases stock.
    """
    # Verify ingredient exists
    ingredient = session.get(Ingredient, data.ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {data.ingredient_id} not found.",
        )
    
    # Create entry
    entry = IngredientEntry(
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        supplier_name=data.supplier_name,
        location_id=data.location_id,
        user_uuid=current_user.id,  # Store the UUID from TinyDB user
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    session.refresh(entry, ["ingredient"])
    
    return IngredientEntryResponse(
        id=entry.id,
        ingredient_id=entry.ingredient_id,
        quantity=entry.quantity,
        supplier_name=entry.supplier_name,
        location_id=entry.location_id,
        created_at=entry.created_at,
        user_uuid=entry.user_uuid,
        ingredient=enrich_ingredient_response(entry.ingredient, session),
    )


# ===== IngredientExit Endpoints (Outbound Orders) =====

@router.post("/orders/outbound", response_model=IngredientExitResponse, status_code=status.HTTP_201_CREATED)
async def create_outbound_order(
    data: IngredientExitCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> IngredientExitResponse:
    """Register an outbound order (consumption or waste).
    
    POST /inventory/orders/outbound
    Requires authentication. Decreases stock.
    
    RULE: A exit that would result in negative stock is rejected with HTTP 400.
    """
    # Validate reason
    if data.reason not in ("consumption", "waste"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="reason must be 'consumption' or 'waste'.",
        )
    
    # Verify ingredient exists
    ingredient = session.get(Ingredient, data.ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {data.ingredient_id} not found.",
        )
    
    # Calculate current stock
    current_stock = calculate_current_stock(session, data.ingredient_id)
    
    # CRITICAL: Check if exit would result in negative stock
    if current_stock - data.quantity < 0:
        available = max(0, current_stock)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for ingredient '{ingredient.name}'. Available: {available}, requested: {data.quantity}.",
        )
    
    # Create exit
    exit_record = IngredientExit(
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        reason=data.reason,
        location_id=data.location_id,
        user_uuid=current_user.id,  # Store the UUID from TinyDB user
    )
    session.add(exit_record)
    session.commit()
    session.refresh(exit_record)
    session.refresh(exit_record, ["ingredient"])
    
    return IngredientExitResponse(
        id=exit_record.id,
        ingredient_id=exit_record.ingredient_id,
        quantity=exit_record.quantity,
        reason=exit_record.reason,
        location_id=exit_record.location_id,
        created_at=exit_record.created_at,
        user_uuid=exit_record.user_uuid,
        ingredient=enrich_ingredient_response(exit_record.ingredient, session),
    )


# ===== Orders List Endpoint =====

@router.get("/orders", response_model=OrderListResponse)
async def list_orders(session: SessionDep) -> OrderListResponse:
    """List all entries and exits.
    
    GET /inventory/orders
    """
    entries = session.exec(select(IngredientEntry)).all()
    exits = session.exec(select(IngredientExit)).all()
    
    entry_responses = [
        IngredientEntryResponse(
            id=e.id,
            ingredient_id=e.ingredient_id,
            quantity=e.quantity,
            supplier_name=e.supplier_name,
            location_id=e.location_id,
            created_at=e.created_at,
            user_uuid=e.user_uuid,
            ingredient=enrich_ingredient_response(e.ingredient, session),
        )
        for e in entries
    ]
    
    exit_responses = [
        IngredientExitResponse(
            id=ex.id,
            ingredient_id=ex.ingredient_id,
            quantity=ex.quantity,
            reason=ex.reason,
            location_id=ex.location_id,
            created_at=ex.created_at,
            user_uuid=ex.user_uuid,
            ingredient=enrich_ingredient_response(ex.ingredient, session),
        )
        for ex in exits
    ]
    
    return OrderListResponse(entries=entry_responses, exits=exit_responses)
