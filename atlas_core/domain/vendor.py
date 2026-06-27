"""Vendor domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VendorStatus(str, Enum):
    """Lifecycle status for an Atlas vendor."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVIEW_REQUIRED = "review_required"
    AVOID = "avoid"


class VendorType(str, Enum):
    """Vendor type for an Atlas vendor."""

    MANUFACTURER_DIRECT = "manufacturer_direct"
    DISTRIBUTOR = "distributor"
    DEALER = "dealer"
    REP = "rep"
    SERVICE_PROVIDER = "service_provider"
    SUBCONTRACTOR = "subcontractor"
    UNKNOWN = "unknown"


@dataclass
class Vendor:
    vendor_id: str
    name: str
    vendor_type: VendorType = VendorType.UNKNOWN
    status: VendorStatus = VendorStatus.ACTIVE
    account_number: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    notes: list[str] = field(default_factory=list)
    active: bool = True

    def __post_init__(self) -> None:
        self.vendor_id = self._normalize_required_text("vendor_id", self.vendor_id)
        self.name = self._normalize_required_text("name", self.name)

        if not isinstance(self.vendor_type, VendorType):
            self.vendor_type = VendorType(self.vendor_type)

        if not isinstance(self.status, VendorStatus):
            self.status = VendorStatus(self.status)

        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def requires_review(self) -> bool:
        return (
            self.status
            in {
                VendorStatus.REVIEW_REQUIRED,
                VendorStatus.AVOID,
                VendorStatus.INACTIVE,
            }
            or not self.active
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "name": self.name,
            "vendor_type": self.vendor_type.value,
            "status": self.status.value,
            "account_number": self.account_number,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "phone": self.phone,
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
