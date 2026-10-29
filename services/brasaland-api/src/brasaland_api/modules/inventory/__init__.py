"""Inventory management module.

Handles ingredient management, inbound orders (entries), and outbound orders (exits).
Uses SQLModel ORM for Supabase PostgreSQL persistence.
"""

from .router import router

__all__ = [
    "router",
]

