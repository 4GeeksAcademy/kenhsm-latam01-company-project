"""Shared TinyDB instance and table accessors.

User and Profile data live exclusively in TinyDB, now and after any future
Supabase/PostgreSQL integration for other modules.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from tinydb import TinyDB
from sqlalchemy.engine import create_engine
from sqlmodel import Session, SQLModel

from brasaland_api.core.config import get_settings


@lru_cache
def get_db() -> TinyDB:
    settings = get_settings()
    db_path = Path(settings.tinydb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(db_path)


def users_table():
    return get_db().table("users")


def profiles_table():
    return get_db().table("profiles")


def incidents_table():
    return get_db().table("incidents")

def password_reset_tokens_table():
    return get_db().table("password_reset_tokens")


# ===== SQLModel / Supabase PostgreSQL =====

_sqlmodel_engine = None


def get_sqlmodel_engine():
    """Get or create SQLModel engine for Supabase PostgreSQL."""
    global _sqlmodel_engine
    if _sqlmodel_engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL not configured in .env. "
                "Cannot initialize inventory database connection."
            )
        _sqlmodel_engine = create_engine(
            settings.database_url,
            echo=False,
            future=True,
        )
    return _sqlmodel_engine


def init_inventory_db():
    """Initialize inventory database schema on startup."""
    engine = get_sqlmodel_engine()
    SQLModel.metadata.create_all(engine)


def get_inventory_session():
    """Dependency to inject a SQLModel session into endpoints."""
    engine = get_sqlmodel_engine()
    with Session(engine) as session:
        yield session

