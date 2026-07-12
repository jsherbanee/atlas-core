"""Deterministic estimate engine domain models for D-02."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class EstimateRevisionState(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    LOCKED = "locked"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class EstimateDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATIONAL = "informational"


@dataclass
class ManualSelectionMetadata:
    reason: str
    actor: str
    timestamp: str
    prior_automatic_price_record_id: str = ""

    def __post_init__(self) -> None:
        self.reason = _required("reason", self.reason)
        self.actor = _required("actor", self.actor)
        self.timestamp = _required("timestamp", self.timestamp)
        self.prior_automatic_price_record_id = _safe(
            self.prior_automatic_price_record_id
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "prior_automatic_price_record_id": self.prior_automatic_price_record_id,
        }


@dataclass
class SnapshotReference:
    vendor_id: str
    vendor_offering_id: str
    price_sheet_id: str
    price_sheet_version_id: str
    price_record_id: str

    def __post_init__(self) -> None:
        self.vendor_id = _safe(self.vendor_id)
        self.vendor_offering_id = _safe(self.vendor_offering_id)
        self.price_sheet_id = _safe(self.price_sheet_id)
        self.price_sheet_version_id = _safe(self.price_sheet_version_id)
        self.price_record_id = _safe(self.price_record_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "vendor_offering_id": self.vendor_offering_id,
            "price_sheet_id": self.price_sheet_id,
            "price_sheet_version_id": self.price_sheet_version_id,
            "price_record_id": self.price_record_id,
        }


@dataclass
class CostSnapshot:
    cost_snapshot_id: str
    estimate_id: str
    revision_id: str
    line_item_id: str
    product_id: str
    source_currency: str
    source_unit_cost: Decimal | None
    effective_unit_cost: Decimal | None
    requested_quantity: Decimal
    purchasable_quantity: Decimal
    package_count: int
    excess_quantity: Decimal
    extended_acquisition_cost: Decimal
    selection_rule: str
    selection_timestamp: str
    tie_break_sequence: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    confidence_breakdown: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    source_filename: str = ""
    source_file_hash: str = ""
    source_reference: str = ""
    import_timestamp: str = ""
    effective_date: str = ""
    expiration_date: str = ""
    purchasing_channel: str = ""
    cost_engine_ruleset_version: str = ""
    estimate_ruleset_version: str = ""
    snapshot_schema_version: str = ""
    reference: SnapshotReference = field(
        default_factory=lambda: SnapshotReference("", "", "", "", "")
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )

    def __post_init__(self) -> None:
        self.cost_snapshot_id = _required("cost_snapshot_id", self.cost_snapshot_id)
        self.estimate_id = _required("estimate_id", self.estimate_id)
        self.revision_id = _required("revision_id", self.revision_id)
        self.line_item_id = _required("line_item_id", self.line_item_id)
        self.product_id = _required("product_id", self.product_id)
        self.source_currency = _safe(self.source_currency, "USD")
        self.source_unit_cost = _decimal_or_none(self.source_unit_cost)
        self.effective_unit_cost = _decimal_or_none(self.effective_unit_cost)
        self.requested_quantity = _decimal(self.requested_quantity)
        self.purchasable_quantity = _decimal(self.purchasable_quantity)
        self.package_count = int(self.package_count)
        self.excess_quantity = _decimal(self.excess_quantity)
        self.extended_acquisition_cost = _decimal(self.extended_acquisition_cost)
        self.selection_rule = _safe(self.selection_rule)
        self.selection_timestamp = _safe(self.selection_timestamp)
        self.tie_break_sequence = [
            _safe(item) for item in list(self.tie_break_sequence)
        ]
        self.source_filename = _safe(self.source_filename)
        self.source_file_hash = _safe(self.source_file_hash)
        self.source_reference = _safe(self.source_reference)
        self.import_timestamp = _safe(self.import_timestamp)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.purchasing_channel = _safe(self.purchasing_channel)
        self.cost_engine_ruleset_version = _safe(self.cost_engine_ruleset_version)
        self.estimate_ruleset_version = _safe(self.estimate_ruleset_version)
        self.snapshot_schema_version = _safe(self.snapshot_schema_version)
        if not isinstance(self.reference, SnapshotReference):
            self.reference = SnapshotReference(**self.reference)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_snapshot_id": self.cost_snapshot_id,
            "estimate_id": self.estimate_id,
            "revision_id": self.revision_id,
            "line_item_id": self.line_item_id,
            "product_id": self.product_id,
            "source_currency": self.source_currency,
            "source_unit_cost": _to_number(self.source_unit_cost),
            "effective_unit_cost": _to_number(self.effective_unit_cost),
            "requested_quantity": _to_number(self.requested_quantity),
            "purchasable_quantity": _to_number(self.purchasable_quantity),
            "package_count": self.package_count,
            "excess_quantity": _to_number(self.excess_quantity),
            "extended_acquisition_cost": _to_number(self.extended_acquisition_cost),
            "selection_rule": self.selection_rule,
            "selection_timestamp": self.selection_timestamp,
            "tie_break_sequence": list(self.tie_break_sequence),
            "confidence_score": self.confidence_score,
            "confidence_breakdown": dict(self.confidence_breakdown),
            "diagnostics": list(self.diagnostics),
            "source_filename": self.source_filename,
            "source_file_hash": self.source_file_hash,
            "source_reference": self.source_reference,
            "import_timestamp": self.import_timestamp,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "purchasing_channel": self.purchasing_channel,
            "cost_engine_ruleset_version": self.cost_engine_ruleset_version,
            "estimate_ruleset_version": self.estimate_ruleset_version,
            "snapshot_schema_version": self.snapshot_schema_version,
            "reference": self.reference.to_dict(),
            "created_at": self.created_at,
        }


@dataclass
class EstimateLineItem:
    line_item_id: str
    product_id: str
    manufacturer: str
    model: str
    description: str
    requested_quantity: Decimal
    engineering_quantity: Decimal
    procurement_quantity: Decimal
    unit_of_measure: str
    section: str = ""
    system: str = ""
    room: str = ""
    source_object_id: str = ""
    source_selection_status: str = "no_eligible_cost"
    selected_cost_snapshot_id: str = ""
    manual_selection_metadata: ManualSelectionMetadata | None = None
    line_role: str = "standard_product"
    parent_line_item_id: str = ""
    assembly_id: str = ""
    assembly_version_id: str = ""
    assembly_component_id: str = ""
    source_contribution_chain: list[str] = field(default_factory=list)
    generated_quantity: Decimal = Decimal("0")
    quantity_rule: dict[str, Any] = field(default_factory=dict)
    optional_accessory_decision: str = "not_applicable"
    manual_adjustment_metadata: list[dict[str, Any]] = field(default_factory=list)
    expansion_run_id: str = ""
    assembly_ruleset_version: str = ""
    labor_snapshot_id: str = ""
    excluded: bool = False
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )

    def __post_init__(self) -> None:
        self.line_item_id = _required("line_item_id", self.line_item_id)
        self.product_id = _safe(self.product_id)
        self.manufacturer = _safe(self.manufacturer)
        self.model = _safe(self.model)
        self.description = _safe(self.description)
        self.requested_quantity = _decimal(self.requested_quantity)
        self.engineering_quantity = _decimal(self.engineering_quantity)
        self.procurement_quantity = _decimal(self.procurement_quantity)
        self.unit_of_measure = _safe(self.unit_of_measure, "ea")
        self.section = _safe(self.section)
        self.system = _safe(self.system)
        self.room = _safe(self.room)
        self.source_object_id = _safe(self.source_object_id)
        self.source_selection_status = _safe(self.source_selection_status)
        self.selected_cost_snapshot_id = _safe(self.selected_cost_snapshot_id)
        if self.manual_selection_metadata is not None and not isinstance(
            self.manual_selection_metadata, ManualSelectionMetadata
        ):
            self.manual_selection_metadata = ManualSelectionMetadata(
                **self.manual_selection_metadata
            )
        self.line_role = _safe(self.line_role, "standard_product")
        self.parent_line_item_id = _safe(self.parent_line_item_id)
        self.assembly_id = _safe(self.assembly_id)
        self.assembly_version_id = _safe(self.assembly_version_id)
        self.assembly_component_id = _safe(self.assembly_component_id)
        self.source_contribution_chain = [
            _safe(item) for item in list(self.source_contribution_chain) if _safe(item)
        ]
        self.generated_quantity = _decimal(self.generated_quantity)
        self.quantity_rule = dict(self.quantity_rule)
        self.optional_accessory_decision = _safe(
            self.optional_accessory_decision, "not_applicable"
        )
        self.manual_adjustment_metadata = [
            dict(item) for item in list(self.manual_adjustment_metadata)
        ]
        self.expansion_run_id = _safe(self.expansion_run_id)
        self.assembly_ruleset_version = _safe(self.assembly_ruleset_version)
        self.labor_snapshot_id = _safe(self.labor_snapshot_id)
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_item_id": self.line_item_id,
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "description": self.description,
            "requested_quantity": _to_number(self.requested_quantity),
            "engineering_quantity": _to_number(self.engineering_quantity),
            "procurement_quantity": _to_number(self.procurement_quantity),
            "unit_of_measure": self.unit_of_measure,
            "section": self.section,
            "system": self.system,
            "room": self.room,
            "source_object_id": self.source_object_id,
            "source_selection_status": self.source_selection_status,
            "selected_cost_snapshot_id": self.selected_cost_snapshot_id,
            "manual_selection_metadata": (
                self.manual_selection_metadata.to_dict()
                if self.manual_selection_metadata is not None
                else None
            ),
            "line_role": self.line_role,
            "parent_line_item_id": self.parent_line_item_id,
            "assembly_id": self.assembly_id,
            "assembly_version_id": self.assembly_version_id,
            "assembly_component_id": self.assembly_component_id,
            "source_contribution_chain": list(self.source_contribution_chain),
            "generated_quantity": _to_number(self.generated_quantity),
            "quantity_rule": dict(self.quantity_rule),
            "optional_accessory_decision": self.optional_accessory_decision,
            "manual_adjustment_metadata": list(self.manual_adjustment_metadata),
            "expansion_run_id": self.expansion_run_id,
            "assembly_ruleset_version": self.assembly_ruleset_version,
            "labor_snapshot_id": self.labor_snapshot_id,
            "excluded": self.excluded,
            "diagnostics": list(self.diagnostics),
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EstimateDiagnostic:
    code: str
    severity: EstimateDiagnosticSeverity
    message: str
    scope: str
    blocking: bool = False
    line_item_id: str = ""

    def __post_init__(self) -> None:
        self.code = _required("code", self.code)
        if not isinstance(self.severity, EstimateDiagnosticSeverity):
            self.severity = EstimateDiagnosticSeverity(self.severity)
        self.message = _required("message", self.message)
        self.scope = _required("scope", self.scope)
        self.line_item_id = _safe(self.line_item_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "scope": self.scope,
            "blocking": self.blocking,
            "line_item_id": self.line_item_id,
        }


@dataclass
class EstimateTotals:
    acquisition_cost_total: Decimal = Decimal("0")
    generated_material_acquisition_cost: Decimal = Decimal("0")
    generated_labor_cost: Decimal = Decimal("0")
    allowance_cost_total: Decimal = Decimal("0")
    unresolved_cost_total: Decimal = Decimal("0")
    unresolved_material_total: Decimal = Decimal("0")
    unresolved_labor_total: Decimal = Decimal("0")
    material_subtotal: Decimal = Decimal("0")
    labor_subtotal: Decimal = Decimal("0")
    excluded_line_total: Decimal = Decimal("0")
    assembly_count: int = 0
    generated_product_line_count: int = 0
    generated_labor_line_count: int = 0
    diagnostic_counts: dict[str, int] = field(default_factory=dict)
    readiness_summary: dict[str, Any] = field(default_factory=dict)
    section_subtotals: dict[str, Decimal] = field(default_factory=dict)
    system_subtotals: dict[str, Decimal] = field(default_factory=dict)
    room_subtotals: dict[str, Decimal] = field(default_factory=dict)
    warning_counts: dict[str, int] = field(default_factory=dict)
    confidence_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.acquisition_cost_total = _decimal(self.acquisition_cost_total)
        self.generated_material_acquisition_cost = _decimal(
            self.generated_material_acquisition_cost
        )
        self.generated_labor_cost = _decimal(self.generated_labor_cost)
        self.allowance_cost_total = _decimal(self.allowance_cost_total)
        self.unresolved_cost_total = _decimal(self.unresolved_cost_total)
        self.unresolved_material_total = _decimal(self.unresolved_material_total)
        self.unresolved_labor_total = _decimal(self.unresolved_labor_total)
        self.material_subtotal = _decimal(self.material_subtotal)
        self.labor_subtotal = _decimal(self.labor_subtotal)
        self.excluded_line_total = _decimal(self.excluded_line_total)
        self.assembly_count = int(self.assembly_count)
        self.generated_product_line_count = int(self.generated_product_line_count)
        self.generated_labor_line_count = int(self.generated_labor_line_count)
        self.diagnostic_counts = {
            str(key): int(value) for key, value in dict(self.diagnostic_counts).items()
        }
        self.readiness_summary = dict(self.readiness_summary)
        self.section_subtotals = {
            _safe(key, "unassigned"): _decimal(value)
            for key, value in dict(self.section_subtotals).items()
        }
        self.system_subtotals = {
            _safe(key, "unassigned"): _decimal(value)
            for key, value in dict(self.system_subtotals).items()
        }
        self.room_subtotals = {
            _safe(key, "unassigned"): _decimal(value)
            for key, value in dict(self.room_subtotals).items()
        }
        self.warning_counts = {
            str(key): int(value) for key, value in dict(self.warning_counts).items()
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "acquisition_cost_total": _to_number(self.acquisition_cost_total),
            "generated_material_acquisition_cost": _to_number(
                self.generated_material_acquisition_cost
            ),
            "generated_labor_cost": _to_number(self.generated_labor_cost),
            "allowance_cost_total": _to_number(self.allowance_cost_total),
            "unresolved_cost_total": _to_number(self.unresolved_cost_total),
            "unresolved_material_total": _to_number(self.unresolved_material_total),
            "unresolved_labor_total": _to_number(self.unresolved_labor_total),
            "material_subtotal": _to_number(self.material_subtotal),
            "labor_subtotal": _to_number(self.labor_subtotal),
            "excluded_line_total": _to_number(self.excluded_line_total),
            "assembly_count": self.assembly_count,
            "generated_product_line_count": self.generated_product_line_count,
            "generated_labor_line_count": self.generated_labor_line_count,
            "diagnostic_counts": dict(self.diagnostic_counts),
            "readiness_summary": dict(self.readiness_summary),
            "section_subtotals": {
                key: _to_number(value) for key, value in self.section_subtotals.items()
            },
            "system_subtotals": {
                key: _to_number(value) for key, value in self.system_subtotals.items()
            },
            "room_subtotals": {
                key: _to_number(value) for key, value in self.room_subtotals.items()
            },
            "warning_counts": dict(self.warning_counts),
            "confidence_summary": dict(self.confidence_summary),
        }


@dataclass
class CostRefreshResult:
    line_item_id: str
    prior_snapshot_id: str
    candidate_snapshot_id: str
    accepted: bool
    comparison: dict[str, Any]

    def __post_init__(self) -> None:
        self.line_item_id = _required("line_item_id", self.line_item_id)
        self.prior_snapshot_id = _safe(self.prior_snapshot_id)
        self.candidate_snapshot_id = _safe(self.candidate_snapshot_id)
        self.comparison = dict(self.comparison)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_item_id": self.line_item_id,
            "prior_snapshot_id": self.prior_snapshot_id,
            "candidate_snapshot_id": self.candidate_snapshot_id,
            "accepted": self.accepted,
            "comparison": dict(self.comparison),
        }


@dataclass
class RevisionComparison:
    baseline_revision_id: str
    comparison_revision_id: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    changed_lines: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_revision_id": self.baseline_revision_id,
            "comparison_revision_id": self.comparison_revision_id,
            "added_lines": list(self.added_lines),
            "removed_lines": list(self.removed_lines),
            "changed_lines": list(self.changed_lines),
        }


@dataclass
class EstimateRevision:
    revision_id: str
    estimate_id: str
    revision_number: int
    state: EstimateRevisionState
    parent_revision_id: str = ""
    revision_reason: str = ""
    line_items: list[EstimateLineItem] = field(default_factory=list)
    diagnostics: list[EstimateDiagnostic] = field(default_factory=list)
    totals: EstimateTotals | None = None
    locked_by: str = ""
    locked_at: str = ""
    superseded_by_revision_id: str = ""
    superseded_at: str = ""
    created_by: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    updated_by: str = ""
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    cost_engine_ruleset_version: str = ""
    estimate_calculation_ruleset_version: str = ""
    snapshot_schema_version: str = ""

    def __post_init__(self) -> None:
        self.revision_id = _required("revision_id", self.revision_id)
        self.estimate_id = _required("estimate_id", self.estimate_id)
        self.revision_number = int(self.revision_number)
        if not isinstance(self.state, EstimateRevisionState):
            self.state = EstimateRevisionState(self.state)
        self.parent_revision_id = _safe(self.parent_revision_id)
        self.revision_reason = _safe(self.revision_reason)
        self.line_items = [
            item if isinstance(item, EstimateLineItem) else EstimateLineItem(**item)
            for item in list(self.line_items)
        ]
        self.diagnostics = [
            item if isinstance(item, EstimateDiagnostic) else EstimateDiagnostic(**item)
            for item in list(self.diagnostics)
        ]
        if self.totals is not None and not isinstance(self.totals, EstimateTotals):
            self.totals = EstimateTotals(**self.totals)
        self.locked_by = _safe(self.locked_by)
        self.locked_at = _safe(self.locked_at)
        self.superseded_by_revision_id = _safe(self.superseded_by_revision_id)
        self.superseded_at = _safe(self.superseded_at)
        self.created_by = _safe(self.created_by)
        self.updated_by = _safe(self.updated_by)
        self.cost_engine_ruleset_version = _safe(self.cost_engine_ruleset_version)
        self.estimate_calculation_ruleset_version = _safe(
            self.estimate_calculation_ruleset_version
        )
        self.snapshot_schema_version = _safe(self.snapshot_schema_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "estimate_id": self.estimate_id,
            "revision_number": self.revision_number,
            "state": self.state.value,
            "parent_revision_id": self.parent_revision_id,
            "revision_reason": self.revision_reason,
            "line_items": [item.to_dict() for item in self.line_items],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "totals": self.totals.to_dict() if self.totals is not None else None,
            "locked_by": self.locked_by,
            "locked_at": self.locked_at,
            "superseded_by_revision_id": self.superseded_by_revision_id,
            "superseded_at": self.superseded_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
            "cost_engine_ruleset_version": self.cost_engine_ruleset_version,
            "estimate_calculation_ruleset_version": self.estimate_calculation_ruleset_version,
            "snapshot_schema_version": self.snapshot_schema_version,
        }


@dataclass
class Estimate:
    estimate_id: str
    project_id: str
    name: str
    active_draft_revision_id: str = ""
    revision_ids: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    updated_by: str = ""
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )

    def __post_init__(self) -> None:
        self.estimate_id = _required("estimate_id", self.estimate_id)
        self.project_id = _required("project_id", self.project_id)
        self.name = _required("name", self.name)
        self.active_draft_revision_id = _safe(self.active_draft_revision_id)
        self.revision_ids = [
            _safe(item) for item in list(self.revision_ids) if _safe(item)
        ]
        self.created_by = _safe(self.created_by)
        self.updated_by = _safe(self.updated_by)

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimate_id": self.estimate_id,
            "project_id": self.project_id,
            "name": self.name,
            "active_draft_revision_id": self.active_draft_revision_id,
            "revision_ids": list(self.revision_ids),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
        }


def _safe(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _required(field_name: str, value: Any) -> str:
    text = _safe(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank")
    return text


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


def _to_number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
