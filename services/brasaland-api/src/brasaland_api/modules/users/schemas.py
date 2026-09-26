"""Pydantic request/response schemas for the `users` module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from brasaland_api.modules.users.models import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    # Optional initial profile fields, used to create the linked Profile in the same operation.
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime
