"""Pydantic models for Supplier."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional, List

# Valid categories
VALID_CATEGORIES = [
    "carne",
    "verduras_y_hortalizas",
    "salsas_y_condimentos",
    "bebidas",
    "packaging",
    "productos_limpieza",
    "lacteos",
    "carbon_y_combustible"
]

# Valid statuses
VALID_STATUSES = ["active", "suspended"]

# Countries mapping
COUNTRY_CURRENCY_MAP = {
    "Colombia": "COP",
    "USA": "USD"
}

class StatusEnum(str, Enum):
    """Status enum."""
    ACTIVE = "active"
    SUSPENDED = "suspended"

class SupplierBase(BaseModel):
    """Base supplier model with common fields."""
    name: str = Field(..., min_length=1, description="Commercial name of the supplier")
    country: str = Field(..., description="Country of operation: 'Colombia' or 'USA'")
    categories: List[str] = Field(..., min_length=1, description="Product categories supplied")
    rate_per_unit: float = Field(..., gt=0, description="Current rate per unit")
    currency: str = Field(..., description="Currency: 'COP' for Colombia, 'USD' for USA")
    status: str = Field(default="active", description="Status: 'active' or 'suspended'")
    contact_email: Optional[str] = Field(None, description="Contact email")
    notes: Optional[str] = Field(None, description="Internal notes")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country value."""
        if v not in ["Colombia", "USA"]:
            raise ValueError("Country must be 'Colombia' or 'USA'")
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: List[str]) -> List[str]:
        """Validate that all categories are valid."""
        for category in v:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category: {category}. Valid categories: {', '.join(VALID_CATEGORIES)}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency value."""
        if v not in ["COP", "USD"]:
            raise ValueError("Currency must be 'COP' or 'USD'")
        return v

    @field_validator("rate_per_unit")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """Validate rate is positive."""
        if v <= 0:
            raise ValueError("Rate per unit must be greater than 0")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        if v not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_country_currency_match(cls, v: str, info) -> str:
        """Validate that country and currency match."""
        if "country" in info.data:
            country = info.data["country"]
            expected_currency = COUNTRY_CURRENCY_MAP.get(country)
            if expected_currency and v != expected_currency:
                raise ValueError(f"Country '{country}' requires currency '{expected_currency}', got '{v}'")
        return v

class SupplierCreate(SupplierBase):
    """Model for creating a supplier (no updated_at)."""
    pass

class SupplierUpdate(BaseModel):
    """Model for updating supplier fields."""
    name: Optional[str] = None
    country: Optional[str] = None
    categories: Optional[List[str]] = None
    rate_per_unit: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country value."""
        if v is not None and v not in ["Colombia", "USA"]:
            raise ValueError("Country must be 'Colombia' or 'USA'")
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all categories are valid."""
        if v is not None:
            for category in v:
                if category not in VALID_CATEGORIES:
                    raise ValueError(f"Invalid category: {category}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        return v

class SupplierResponse(SupplierBase):
    """Model for supplier response (includes auto-generated fields)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Supplier ID")
    updated_at: datetime = Field(..., description="Last update timestamp")

