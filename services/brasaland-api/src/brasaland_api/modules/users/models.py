"""Domain model for the `users` module (credentials only, stored in TinyDB)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


@dataclass
class UserRecord:
    id: str
    email: str
    hashed_password: str
    is_active: bool
    role: UserRole
    created_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "UserRecord":
        return cls(
            id=doc["id"],
            email=doc["email"],
            hashed_password=doc["hashed_password"],
            is_active=doc["is_active"],
            role=UserRole(doc["role"]),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )

    def to_doc(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "is_active": self.is_active,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
        }
