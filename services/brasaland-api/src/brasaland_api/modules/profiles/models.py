"""Domain model for the `profiles` module (display name and contact data)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProfileRecord:
    id: str
    user_id: str
    name: str | None
    phone: str | None
    address: str | None

    @classmethod
    def from_doc(cls, doc: dict) -> "ProfileRecord":
        return cls(
            id=doc["id"],
            user_id=doc["user_id"],
            name=doc.get("name"),
            phone=doc.get("phone"),
            address=doc.get("address"),
        )

    def to_doc(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "address": self.address,
        }
