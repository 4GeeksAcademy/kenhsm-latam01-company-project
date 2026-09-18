"""Service layer for profile operations against TinyDB."""

from __future__ import annotations

import uuid

from tinydb import Query

from brasaland_api.core.db import profiles_table
from brasaland_api.modules.profiles.models import ProfileRecord


def create_profile(
    user_id: str, *, name: str | None = None, phone: str | None = None, address: str | None = None
) -> ProfileRecord:
    record = ProfileRecord(id=str(uuid.uuid4()), user_id=user_id, name=name, phone=phone, address=address)
    profiles_table().insert(record.to_doc())
    return record


def get_profile_by_user_id(user_id: str) -> ProfileRecord | None:
    doc = profiles_table().get(Query().user_id == user_id)
    return ProfileRecord.from_doc(doc) if doc else None


def update_profile(
    user_id: str, *, name: str | None = None, phone: str | None = None, address: str | None = None
) -> ProfileRecord | None:
    table = profiles_table()
    query = Query().user_id == user_id
    if table.get(query) is None:
        return None

    updates = {}
    if name is not None:
        updates["name"] = name
    if phone is not None:
        updates["phone"] = phone
    if address is not None:
        updates["address"] = address
    if updates:
        table.update(updates, query)
    return get_profile_by_user_id(user_id)


def delete_profile_by_user_id(user_id: str) -> None:
    profiles_table().remove(Query().user_id == user_id)
