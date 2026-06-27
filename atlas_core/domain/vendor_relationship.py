"""Vendor relationship domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VendorRelationshipType(str, Enum):
    """Relationship type for an Atlas vendor relationship."""

    DIRECT = "direct"
    DISTRIBUTOR = "distributor"
    REP = "rep"
    DEALER = "dealer"
    UNKNOWN = "unknown"


@dataclass
class VendorRelationship:
    vendor_name: str
    relationship_type: VendorRelationshipType = VendorRelationshipType.UNKNOWN
    priority: int = 1
    account_number: str | None = None
    typical_lead_time_days: int | None = None
    notes: list[str] = field(default_factory=list)
    active: bool = True

    def __post_init__(self) -> None:
        self.vendor_name = self._normalize_required_text(
            "vendor_name", self.vendor_name
        )

        if not isinstance(self.relationship_type, VendorRelationshipType):
            self.relationship_type = VendorRelationshipType(
                self.relationship_type
            )

        if (
            not isinstance(self.priority, int)
            or isinstance(self.priority, bool)
            or self.priority <= 0
        ):
            raise ValueError("priority must be greater than 0")

        if (
            self.typical_lead_time_days is not None
            and (
                not isinstance(self.typical_lead_time_days, int)
                or isinstance(self.typical_lead_time_days, bool)
                or self.typical_lead_time_days < 0
            )
        ):
            raise ValueError("typical_lead_time_days cannot be negative")

        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_name": self.vendor_name,
            "relationship_type": self.relationship_type.value,
            "priority": self.priority,
            "account_number": self.account_number,
            "typical_lead_time_days": self.typical_lead_time_days,
            "notes": list(self.notes),
            "active": self.active,
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()
