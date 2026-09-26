"""Shared TinyDB instance and table accessors.

User and Profile data live exclusively in TinyDB, now and after any future
Supabase/PostgreSQL integration for other modules.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from tinydb import TinyDB

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
