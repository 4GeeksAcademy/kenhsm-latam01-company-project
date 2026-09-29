"""Pydantic schemas for the `auth` module."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from brasaland_api.modules.profiles.schemas import ProfileOut
from brasaland_api.modules.users.models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserOut(BaseModel):
    email: str
    role: UserRole
    profile: ProfileOut | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class AuthMessage(BaseModel):
    message: str
