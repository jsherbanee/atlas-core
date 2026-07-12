"""Deterministic product resolution domain models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from atlas_core.domain.deterministic_estimate import ProductResolutionStatus


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class ProductResolutionCandidate:
    product_id: str
    manufacturer: str
    model: str
    match_type: str
    confidence: float
    reason: str

    def __post_init__(self) -> None:
        self.product_id = _required("product_id", self.product_id)
        self.manufacturer = _required("manufacturer", self.manufacturer)
        self.model = _required("model", self.model)
        self.match_type = _required("match_type", self.match_type)
        self.reason = _required("reason", self.reason)
        self.confidence = _rate("confidence", self.confidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class ProductResolutionManualOverride:
    original_match: dict[str, Any] | None
    manual_selection: dict[str, Any]
    reviewer: str
    timestamp: str
    reason: str

    def __post_init__(self) -> None:
        self.original_match = dict(self.original_match or {}) or None
        self.manual_selection = dict(self.manual_selection or {})
        if not self.manual_selection:
            raise ValueError("manual_selection cannot be blank")
        self.reviewer = _required("reviewer", self.reviewer)
        self.timestamp = _required("timestamp", self.timestamp)
        self.reason = _required("reason", self.reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_match": dict(self.original_match or {}),
            "manual_selection": dict(self.manual_selection),
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


@dataclass
class ProductResolution:
    resolution_id: str
    source_object_id: str
    resolution_status: ProductResolutionStatus
    canonical_product: dict[str, Any] | None
    manufacturer: str
    model: str
    resolution_confidence: float
    resolution_reason: str
    candidate_matches: list[ProductResolutionCandidate] = field(default_factory=list)
    manual_override: ProductResolutionManualOverride | None = None
    source_evidence: list[str] = field(default_factory=list)
    canonical_product_id: str | None = None
    manufacturer_id: str | None = None
    future_price_records: list[str] = field(default_factory=list)
    future_vendor_records: list[str] = field(default_factory=list)
    future_labor_templates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.resolution_id = _required("resolution_id", self.resolution_id)
        self.source_object_id = _required("source_object_id", self.source_object_id)
        self.manufacturer = _normalize(self.manufacturer) or "Unknown"
        self.model = _normalize(self.model) or "Unknown"
        self.resolution_reason = _required("resolution_reason", self.resolution_reason)
        self.resolution_confidence = _rate(
            "resolution_confidence", self.resolution_confidence
        )

        if not isinstance(self.resolution_status, ProductResolutionStatus):
            self.resolution_status = ProductResolutionStatus(self.resolution_status)

        self.canonical_product = dict(self.canonical_product or {}) or None
        self.candidate_matches = [
            (
                item
                if isinstance(item, ProductResolutionCandidate)
                else ProductResolutionCandidate(**item)
            )
            for item in self.candidate_matches
        ]
        if self.manual_override is not None and not isinstance(
            self.manual_override, ProductResolutionManualOverride
        ):
            self.manual_override = ProductResolutionManualOverride(
                **self.manual_override
            )

        self.source_evidence = [
            _required("source_evidence", str(item))
            for item in list(self.source_evidence)
            if _normalize(str(item))
        ]
        self.canonical_product_id = _normalize(self.canonical_product_id)
        self.manufacturer_id = _normalize(self.manufacturer_id)
        self.future_price_records = list(self.future_price_records)
        self.future_vendor_records = list(self.future_vendor_records)
        self.future_labor_templates = list(self.future_labor_templates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_id": self.resolution_id,
            "source_object_id": self.source_object_id,
            "resolution_status": self.resolution_status.value,
            "canonical_product": dict(self.canonical_product or {}),
            "manufacturer": self.manufacturer,
            "model": self.model,
            "resolution_confidence": self.resolution_confidence,
            "resolution_reason": self.resolution_reason,
            "candidate_matches": [item.to_dict() for item in self.candidate_matches],
            "manual_override": (
                self.manual_override.to_dict()
                if self.manual_override is not None
                else None
            ),
            "source_evidence": list(self.source_evidence),
            "canonical_product_id": self.canonical_product_id,
            "manufacturer_id": self.manufacturer_id,
            "future_price_records": list(self.future_price_records),
            "future_vendor_records": list(self.future_vendor_records),
            "future_labor_templates": list(self.future_labor_templates),
        }


def _required(field_name: str, value: str) -> str:
    normalized = _normalize(value)
    if not normalized:
        raise ValueError(f"{field_name} cannot be blank")
    return normalized


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _rate(field_name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if not 0 <= normalized <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return normalized
