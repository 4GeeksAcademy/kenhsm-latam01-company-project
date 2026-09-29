from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone

from tinydb import Query

from brasaland_api.core.db import incidents_table
from brasaland_api.modules.incidents.models import IncidentRecord
from brasaland_shared.incidents import MODEL_BRANCHES, MODEL_CATEGORIES, MODEL_ORIGINS, MODEL_STATUSES

TRANSITIONS = {"open": {"in_progress", "discarded"}, "in_progress": {"resolved", "discarded"}, "resolved": set(), "discarded": set()}


def create_incident(values: dict, *, source_key: str | None = None) -> IncidentRecord:
    now = datetime.now(timezone.utc)
    record = IncidentRecord(id=str(uuid.uuid4()), **values, created_at=now, updated_at=now, source_key=source_key)
    incidents_table().insert(record.to_doc())
    return record


def list_incidents(filters: dict[str, str | None]) -> list[IncidentRecord]:
    records = [IncidentRecord.from_doc(doc) for doc in incidents_table().all()]
    return [record for record in records if all(not value or getattr(record, key) == value for key, value in filters.items())]


def get_incident(incident_id: str) -> IncidentRecord | None:
    doc = incidents_table().get(Query().id == incident_id)
    return IncidentRecord.from_doc(doc) if doc else None


def update_status(incident_id: str, new_status: str) -> IncidentRecord | None:
    record = get_incident(incident_id)
    if record is None:
        return None
    if new_status not in TRANSITIONS.get(record.status, set()):
        raise ValueError(f"No se puede cambiar de {record.status} a {new_status}.")
    record.status = new_status
    record.updated_at = datetime.now(timezone.utc)
    incidents_table().update(record.to_doc(), Query().id == incident_id)
    return record


def find_source_key(source_key: str) -> IncidentRecord | None:
    doc = incidents_table().get(Query().source_key == source_key)
    return IncidentRecord.from_doc(doc) if doc else None


def summary() -> dict:
    records = [IncidentRecord.from_doc(doc) for doc in incidents_table().all()]
    return {"total": len(records), "by_status": _counts(records, "status", MODEL_STATUSES), "by_category": _counts(records, "category", MODEL_CATEGORIES), "by_origin": _counts(records, "origin", MODEL_ORIGINS), "by_branch": _counts(records, "branch", MODEL_BRANCHES)}


def _counts(records: list[IncidentRecord], field: str, keys: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(getattr(record, field) for record in records)
    return {key: counts[key] for key in keys}