"""Service layer for user CRUD operations against TinyDB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from tinydb import Query

from brasaland_api.core.db import profiles_table, users_table
from brasaland_api.core.security import hash_password
from brasaland_api.modules.users.models import UserRecord, UserRole


def create_user(email: str, password: str, role: UserRole = UserRole.USER) -> UserRecord:
    table = users_table()
    if table.get(Query().email == email) is not None:
        raise ValueError("Ya existe un usuario con ese email.")

    record = UserRecord(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
        role=role,
        created_at=datetime.now(timezone.utc),
    )
    table.insert(record.to_doc())
    return record


def get_user_by_id(user_id: str) -> UserRecord | None:
    doc = users_table().get(Query().id == user_id)
    return UserRecord.from_doc(doc) if doc else None


def get_user_by_email(email: str) -> UserRecord | None:
    doc = users_table().get(Query().email == email)
    return UserRecord.from_doc(doc) if doc else None


def list_users() -> list[UserRecord]:
    return [UserRecord.from_doc(doc) for doc in users_table().all()]


def update_user(user_id: str, *, email: str | None = None, role: UserRole | None = None) -> UserRecord | None:
    table = users_table()
    query = Query().id == user_id
    if table.get(query) is None:
        return None

    updates: dict = {}
    if email is not None:
        existing = table.get(Query().email == email)
        if existing is not None and existing["id"] != user_id:
            raise ValueError("Ya existe un usuario con ese email.")
        updates["email"] = email
    if role is not None:
        updates["role"] = role.value

    if updates:
        table.update(updates, query)
    return get_user_by_id(user_id)


def delete_user(user_id: str) -> bool:
    table = users_table()
    query = Query().id == user_id
    if table.get(query) is None:
        return False
    table.remove(query)
    profiles_table().remove(Query().user_id == user_id)
    return True
