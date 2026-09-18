"""Pydantic request/response schemas for the `profiles` module."""

from __future__ import annotations

from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class ProfileOut(BaseModel):
    id: str
    user_id: str
    name: str | None = None
    phone: str | None = None
    address: str | None = None
