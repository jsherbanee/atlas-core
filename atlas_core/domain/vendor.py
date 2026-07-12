"""Vendor domain model for Atlas Core."""

from datetime import UTC, datetime

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
    AUTHORIZED_DISTRIBUTOR = "authorized_distributor"
    REGIONAL_DISTRIBUTOR = "regional_distributor"
    BUYING_GROUP = "buying_group"
    MARKETPLACE = "marketplace"
    INTEGRATOR = "integrator"
    OTHER = "other"
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
    display_name: str | None = None
    normalized_name: str | None = None
    vendor_code: str | None = None
    website: str | None = None
    aliases: list[str] = field(default_factory=list)
    vendor_type: VendorType = VendorType.UNKNOWN
    status: VendorStatus = VendorStatus.ACTIVE
    account_number: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    notes: list[str] = field(default_factory=list)
    active: bool = True
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    def __post_init__(self) -> None:
        self.vendor_id = self._normalize_required_text("vendor_id", self.vendor_id)
        self.name = self._normalize_required_text("name", self.name)
        self.display_name = self._normalize_required_text(
            "display_name", self.display_name or self.name
        )
        self.normalized_name = self._normalize_name(
            self.normalized_name or self.display_name
        )
        self.vendor_code = self._normalize_optional_text(
            self.vendor_code or self.vendor_id.upper()
        )
        self.website = self._normalize_optional_text(self.website)
        self.aliases = [
            self._normalize_required_text("alias", item)
            for item in list(self.aliases)
            if self._normalize_optional_text(item)
        ]

        if not isinstance(self.vendor_type, VendorType):
            self.vendor_type = VendorType(self.vendor_type)

        if not isinstance(self.status, VendorStatus):
            self.status = VendorStatus(self.status)

        self.notes = [
            self._normalize_required_text("note", note) for note in self.notes
        ]
        self.created_at = self._normalize_required_text("created_at", self.created_at)
        self.updated_at = self._normalize_required_text("updated_at", self.updated_at)

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))
        self.updated_at = _now_iso()

    def add_alias(self, alias: str) -> None:
        normalized = self._normalize_required_text("alias", alias)
        if normalized not in self.aliases:
            self.aliases.append(normalized)
            self.updated_at = _now_iso()

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
            "display_name": self.display_name,
            "normalized_name": self.normalized_name,
            "vendor_code": self.vendor_code,
            "website": self.website,
            "aliases": list(self.aliases),
            "vendor_type": self.vendor_type.value,
            "status": self.status.value,
            "account_number": self.account_number,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "notes": list(self.notes),
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join(value.strip().upper().split())


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
