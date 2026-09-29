from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class IncidentRecord:
    id: str
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: datetime
    updated_at: datetime
    source_key: str | None = None

    @classmethod
    def from_doc(cls, doc: dict) -> "IncidentRecord":
        return cls(**{**doc, "created_at": datetime.fromisoformat(doc["created_at"]), "updated_at": datetime.fromisoformat(doc["updated_at"])})

    def to_doc(self) -> dict:
        return {**self.__dict__, "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat()}