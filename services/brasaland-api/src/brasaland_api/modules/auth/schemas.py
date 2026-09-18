"""Pydantic schemas for the `auth` module."""

from __future__ import annotations

from pydantic import BaseModel

from brasaland_api.modules.profiles.schemas import ProfileOut
from brasaland_api.modules.users.models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserOut(BaseModel):
    email: str
    role: UserRole
    profile: ProfileOut | None = None
