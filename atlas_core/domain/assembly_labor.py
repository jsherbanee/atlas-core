"""Deterministic assembly and labor domain models for D-03."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class AssemblyLifecycleState(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class AssemblyComponentType(str, Enum):
    PRODUCT = "product"
    NESTED_ASSEMBLY = "nested_assembly"
    LABOR_ACTIVITY = "labor_activity"
    CONSUMABLE = "consumable"
    INFRASTRUCTURE_MATERIAL = "infrastructure_material"
    ALLOWANCE = "allowance"
    INFORMATIONAL = "informational"


class AccessoryRuleKind(str, Enum):
    NONE = "none"
    REQUIRED = "required"
    OPTIONAL = "optional"
    MUTEX_GROUP = "mutex_group"


class QuantityRuleType(str, Enum):
    FIXED = "fixed"
    PER_PARENT = "per_parent"
    PER_ROOM = "per_room"
    PER_SYSTEM = "per_system"
    PER_RACK = "per_rack"
    PER_CHANNEL = "per_channel"
    PER_ENDPOINT = "per_endpoint"
    PERCENTAGE = "percentage"


class LaborCategory(str, Enum):
    ENGINEERING = "engineering"
    PROJECT_MANAGEMENT = "project_management"
    FABRICATION = "fabrication"
    INSTALLATION = "installation"
    CABLE_PULL = "cable_pull"
    TERMINATION = "termination"
    RACK_BUILD = "rack_build"
    PROGRAMMING = "programming"
    COMMISSIONING = "commissioning"
    TESTING = "testing"
    TRAINING = "training"
    DOCUMENTATION = "documentation"
    MOBILIZATION_PLACEHOLDER = "mobilization_placeholder"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATIONAL = "informational"


@dataclass
class QuantityRule:
    rule_type: QuantityRuleType
    value: Decimal
    minimum_quantity: Decimal = Decimal("0")
    round_up_to: Decimal = Decimal("1")
    waste_factor: Decimal = Decimal("0")
    spare_factor: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not isinstance(self.rule_type, QuantityRuleType):
            self.rule_type = QuantityRuleType(self.rule_type)
        self.value = _decimal(self.value)
        self.minimum_quantity = _decimal(self.minimum_quantity)
        self.round_up_to = _decimal(self.round_up_to)
        self.waste_factor = _decimal(self.waste_factor)
        self.spare_factor = _decimal(self.spare_factor)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_type": self.rule_type.value,
            "value": _float(self.value),
            "minimum_quantity": _float(self.minimum_quantity),
            "round_up_to": _float(self.round_up_to),
            "waste_factor": _float(self.waste_factor),
            "spare_factor": _float(self.spare_factor),
        }


@dataclass
class AccessoryRule:
    kind: AccessoryRuleKind = AccessoryRuleKind.NONE
    option_group: str = ""
    conditional_field: str = ""
    conditional_value: str = ""
    replacement_component_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AccessoryRuleKind):
            self.kind = AccessoryRuleKind(self.kind)
        self.option_group = _safe(self.option_group)
        self.conditional_field = _safe(self.conditional_field)
        self.conditional_value = _safe(self.conditional_value)
        self.replacement_component_id = _safe(self.replacement_component_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "option_group": self.option_group,
            "conditional_field": self.conditional_field,
            "conditional_value": self.conditional_value,
            "replacement_component_id": self.replacement_component_id,
        }


@dataclass
class Assembly:
    assembly_id: str
    canonical_name: str
    display_name: str
    description: str = ""
    category: str = "general"
    manufacturer_scope: str = ""
    system_applicability: list[str] = field(default_factory=list)
    room_applicability: list[str] = field(default_factory=list)
    active: bool = True
    current_active_version_id: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    def __post_init__(self) -> None:
        self.assembly_id = _required("assembly_id", self.assembly_id)
        self.canonical_name = _required("canonical_name", self.canonical_name)
        self.display_name = _required("display_name", self.display_name)
        self.description = _safe(self.description)
        self.category = _safe(self.category, "general")
        self.manufacturer_scope = _safe(self.manufacturer_scope)
        self.system_applicability = [
            _safe(item) for item in self.system_applicability if _safe(item)
        ]
        self.room_applicability = [
            _safe(item) for item in self.room_applicability if _safe(item)
        ]
        self.current_active_version_id = _safe(self.current_active_version_id)
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_id": self.assembly_id,
            "canonical_name": self.canonical_name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "manufacturer_scope": self.manufacturer_scope,
            "system_applicability": list(self.system_applicability),
            "room_applicability": list(self.room_applicability),
            "active": self.active,
            "current_active_version_id": self.current_active_version_id,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AssemblyVersion:
    assembly_version_id: str
    assembly_id: str
    version_label: str
    lifecycle_state: AssemblyLifecycleState = AssemblyLifecycleState.DRAFT
    effective_date: str = ""
    expiration_date: str = ""
    parent_version_id: str = ""
    revision_reason: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: _now_iso())
    validated_at: str = ""
    activated_at: str = ""
    superseded_at: str = ""
    ruleset_version: str = "atlas-assembly-rules:v1"
    schema_version: str = "atlas-assembly-schema:v1"

    def __post_init__(self) -> None:
        self.assembly_version_id = _required(
            "assembly_version_id", self.assembly_version_id
        )
        self.assembly_id = _required("assembly_id", self.assembly_id)
        self.version_label = _required("version_label", self.version_label)
        if not isinstance(self.lifecycle_state, AssemblyLifecycleState):
            self.lifecycle_state = AssemblyLifecycleState(self.lifecycle_state)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.parent_version_id = _safe(self.parent_version_id)
        self.revision_reason = _safe(self.revision_reason)
        self.created_by = _safe(self.created_by)
        self.validated_at = _safe(self.validated_at)
        self.activated_at = _safe(self.activated_at)
        self.superseded_at = _safe(self.superseded_at)
        self.ruleset_version = _safe(self.ruleset_version)
        self.schema_version = _safe(self.schema_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_version_id": self.assembly_version_id,
            "assembly_id": self.assembly_id,
            "version_label": self.version_label,
            "lifecycle_state": self.lifecycle_state.value,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "parent_version_id": self.parent_version_id,
            "revision_reason": self.revision_reason,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "validated_at": self.validated_at,
            "activated_at": self.activated_at,
            "superseded_at": self.superseded_at,
            "ruleset_version": self.ruleset_version,
            "schema_version": self.schema_version,
        }


@dataclass
class LaborActivity:
    labor_activity_id: str
    name: str
    labor_category: LaborCategory
    unit_basis: str = "hours"
    notes: str = ""

    def __post_init__(self) -> None:
        self.labor_activity_id = _required("labor_activity_id", self.labor_activity_id)
        self.name = _required("name", self.name)
        if not isinstance(self.labor_category, LaborCategory):
            self.labor_category = LaborCategory(self.labor_category)
        self.unit_basis = _safe(self.unit_basis, "hours")
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labor_activity_id": self.labor_activity_id,
            "name": self.name,
            "labor_category": self.labor_category.value,
            "unit_basis": self.unit_basis,
            "notes": self.notes,
        }


@dataclass
class AssemblyComponent:
    component_id: str
    assembly_version_id: str
    component_type: AssemblyComponentType
    product_id: str = ""
    nested_assembly_version_id: str = ""
    labor_activity_id: str = ""
    quantity_rule: QuantityRule = field(
        default_factory=lambda: QuantityRule(
            rule_type=QuantityRuleType.FIXED,
            value=Decimal("1"),
        )
    )
    accessory_rule: AccessoryRule = field(default_factory=AccessoryRule)
    inclusion_state: str = "included"
    optional_selected_by_default: bool = False
    sort_order: int = 0
    notes: str = ""
    provenance_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.component_id = _required("component_id", self.component_id)
        self.assembly_version_id = _required(
            "assembly_version_id", self.assembly_version_id
        )
        if not isinstance(self.component_type, AssemblyComponentType):
            self.component_type = AssemblyComponentType(self.component_type)
        self.product_id = _safe(self.product_id)
        self.nested_assembly_version_id = _safe(self.nested_assembly_version_id)
        self.labor_activity_id = _safe(self.labor_activity_id)
        if not isinstance(self.quantity_rule, QuantityRule):
            self.quantity_rule = QuantityRule(**self.quantity_rule)
        if not isinstance(self.accessory_rule, AccessoryRule):
            self.accessory_rule = AccessoryRule(**self.accessory_rule)
        self.inclusion_state = _safe(self.inclusion_state, "included")
        self.sort_order = int(self.sort_order)
        self.notes = _safe(self.notes)
        self.provenance_metadata = dict(self.provenance_metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "assembly_version_id": self.assembly_version_id,
            "component_type": self.component_type.value,
            "product_id": self.product_id,
            "nested_assembly_version_id": self.nested_assembly_version_id,
            "labor_activity_id": self.labor_activity_id,
            "quantity_rule": self.quantity_rule.to_dict(),
            "accessory_rule": self.accessory_rule.to_dict(),
            "inclusion_state": self.inclusion_state,
            "optional_selected_by_default": self.optional_selected_by_default,
            "sort_order": self.sort_order,
            "notes": self.notes,
            "provenance_metadata": dict(self.provenance_metadata),
        }


@dataclass
class AssemblyDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    blocking: bool = False
    component_id: str = ""

    def __post_init__(self) -> None:
        self.code = _required("code", self.code)
        if not isinstance(self.severity, DiagnosticSeverity):
            self.severity = DiagnosticSeverity(self.severity)
        self.message = _required("message", self.message)
        self.component_id = _safe(self.component_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "blocking": self.blocking,
            "component_id": self.component_id,
        }


@dataclass
class AssemblyExpansionRequest:
    estimate_id: str
    revision_id: str
    assembly_version_id: str
    parent_quantity: Decimal
    room_count: Decimal = Decimal("1")
    system_count: Decimal = Decimal("1")
    rack_count: Decimal = Decimal("1")
    channel_count: Decimal = Decimal("1")
    endpoint_count: Decimal = Decimal("1")
    selected_optional_component_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.estimate_id = _required("estimate_id", self.estimate_id)
        self.revision_id = _required("revision_id", self.revision_id)
        self.assembly_version_id = _required(
            "assembly_version_id", self.assembly_version_id
        )
        self.parent_quantity = _decimal(self.parent_quantity)
        self.room_count = _decimal(self.room_count)
        self.system_count = _decimal(self.system_count)
        self.rack_count = _decimal(self.rack_count)
        self.channel_count = _decimal(self.channel_count)
        self.endpoint_count = _decimal(self.endpoint_count)
        self.selected_optional_component_ids = [
            _safe(item) for item in self.selected_optional_component_ids if _safe(item)
        ]


@dataclass
class AssemblyContribution:
    contribution_id: str
    parent_component_id: str
    source_assembly_version_id: str
    component_type: AssemblyComponentType
    product_id: str = ""
    labor_activity_id: str = ""
    generated_quantity: Decimal = Decimal("0")
    quantity_explanation: str = ""
    parent_chain: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.contribution_id = _required("contribution_id", self.contribution_id)
        self.parent_component_id = _required(
            "parent_component_id", self.parent_component_id
        )
        self.source_assembly_version_id = _required(
            "source_assembly_version_id", self.source_assembly_version_id
        )
        if not isinstance(self.component_type, AssemblyComponentType):
            self.component_type = AssemblyComponentType(self.component_type)
        self.product_id = _safe(self.product_id)
        self.labor_activity_id = _safe(self.labor_activity_id)
        self.generated_quantity = _decimal(self.generated_quantity)
        self.quantity_explanation = _safe(self.quantity_explanation)
        self.parent_chain = [_safe(item) for item in self.parent_chain if _safe(item)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contribution_id": self.contribution_id,
            "parent_component_id": self.parent_component_id,
            "source_assembly_version_id": self.source_assembly_version_id,
            "component_type": self.component_type.value,
            "product_id": self.product_id,
            "labor_activity_id": self.labor_activity_id,
            "generated_quantity": _float(self.generated_quantity),
            "quantity_explanation": self.quantity_explanation,
            "parent_chain": list(self.parent_chain),
        }


@dataclass
class LaborRateSet:
    labor_rate_set_id: str
    version_label: str
    lifecycle_state: AssemblyLifecycleState
    effective_date: str
    expiration_date: str = ""
    geography: str = ""
    prevailing_wage_applicable: bool = False
    created_by: str = ""
    created_at: str = field(default_factory=lambda: _now_iso())
    activated_at: str = ""
    superseded_at: str = ""

    def __post_init__(self) -> None:
        self.labor_rate_set_id = _required("labor_rate_set_id", self.labor_rate_set_id)
        self.version_label = _required("version_label", self.version_label)
        if not isinstance(self.lifecycle_state, AssemblyLifecycleState):
            self.lifecycle_state = AssemblyLifecycleState(self.lifecycle_state)
        self.effective_date = _required("effective_date", self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.geography = _safe(self.geography)
        self.created_by = _safe(self.created_by)
        self.activated_at = _safe(self.activated_at)
        self.superseded_at = _safe(self.superseded_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labor_rate_set_id": self.labor_rate_set_id,
            "version_label": self.version_label,
            "lifecycle_state": self.lifecycle_state.value,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "geography": self.geography,
            "prevailing_wage_applicable": self.prevailing_wage_applicable,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "superseded_at": self.superseded_at,
        }


@dataclass
class LaborRateRecord:
    labor_rate_record_id: str
    labor_rate_set_id: str
    labor_category: LaborCategory
    unit_basis: str
    straight_time_rate: Decimal
    burden_rate: Decimal = Decimal("0")
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.labor_rate_record_id = _required(
            "labor_rate_record_id", self.labor_rate_record_id
        )
        self.labor_rate_set_id = _required("labor_rate_set_id", self.labor_rate_set_id)
        if not isinstance(self.labor_category, LaborCategory):
            self.labor_category = LaborCategory(self.labor_category)
        self.unit_basis = _safe(self.unit_basis, "hours")
        self.straight_time_rate = _decimal(self.straight_time_rate)
        self.burden_rate = _decimal(self.burden_rate)
        self.source_metadata = dict(self.source_metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labor_rate_record_id": self.labor_rate_record_id,
            "labor_rate_set_id": self.labor_rate_set_id,
            "labor_category": self.labor_category.value,
            "unit_basis": self.unit_basis,
            "straight_time_rate": _float(self.straight_time_rate),
            "burden_rate": _float(self.burden_rate),
            "source_metadata": dict(self.source_metadata),
        }


@dataclass
class LaborSnapshot:
    labor_snapshot_id: str
    revision_id: str
    parent_line_item_id: str
    labor_activity_id: str
    labor_category: LaborCategory
    quantity_driver: str
    driver_value: Decimal
    base_hours: Decimal
    applied_factors: dict[str, Decimal]
    calculated_hours: Decimal
    labor_rate_set_id: str
    labor_rate_record_id: str
    unit_rate: Decimal
    extended_labor_cost: Decimal
    ruleset_version: str
    provenance: dict[str, Any]
    created_at: str = field(default_factory=lambda: _now_iso())

    def __post_init__(self) -> None:
        self.labor_snapshot_id = _required("labor_snapshot_id", self.labor_snapshot_id)
        self.revision_id = _required("revision_id", self.revision_id)
        self.parent_line_item_id = _required(
            "parent_line_item_id", self.parent_line_item_id
        )
        self.labor_activity_id = _required("labor_activity_id", self.labor_activity_id)
        if not isinstance(self.labor_category, LaborCategory):
            self.labor_category = LaborCategory(self.labor_category)
        self.quantity_driver = _required("quantity_driver", self.quantity_driver)
        self.driver_value = _decimal(self.driver_value)
        self.base_hours = _decimal(self.base_hours)
        self.applied_factors = {
            _safe(key): _decimal(value)
            for key, value in dict(self.applied_factors).items()
            if _safe(key)
        }
        self.calculated_hours = _decimal(self.calculated_hours)
        self.labor_rate_set_id = _required("labor_rate_set_id", self.labor_rate_set_id)
        self.labor_rate_record_id = _required(
            "labor_rate_record_id", self.labor_rate_record_id
        )
        self.unit_rate = _decimal(self.unit_rate)
        self.extended_labor_cost = _decimal(self.extended_labor_cost)
        self.ruleset_version = _safe(self.ruleset_version, "atlas-labor-rules:v1")
        self.provenance = dict(self.provenance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labor_snapshot_id": self.labor_snapshot_id,
            "revision_id": self.revision_id,
            "parent_line_item_id": self.parent_line_item_id,
            "labor_activity_id": self.labor_activity_id,
            "labor_category": self.labor_category.value,
            "quantity_driver": self.quantity_driver,
            "driver_value": _float(self.driver_value),
            "base_hours": _float(self.base_hours),
            "applied_factors": {
                key: _float(value) for key, value in self.applied_factors.items()
            },
            "calculated_hours": _float(self.calculated_hours),
            "labor_rate_set_id": self.labor_rate_set_id,
            "labor_rate_record_id": self.labor_rate_record_id,
            "unit_rate": _float(self.unit_rate),
            "extended_labor_cost": _float(self.extended_labor_cost),
            "ruleset_version": self.ruleset_version,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


@dataclass
class LaborRollup:
    labor_rollup_id: str
    revision_id: str
    labor_rate_set_id: str
    total_hours: Decimal
    total_labor_cost: Decimal
    category_hours: dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.labor_rollup_id = _required("labor_rollup_id", self.labor_rollup_id)
        self.revision_id = _required("revision_id", self.revision_id)
        self.labor_rate_set_id = _required("labor_rate_set_id", self.labor_rate_set_id)
        self.total_hours = _decimal(self.total_hours)
        self.total_labor_cost = _decimal(self.total_labor_cost)
        self.category_hours = {
            _safe(key): _decimal(value)
            for key, value in dict(self.category_hours).items()
            if _safe(key)
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "labor_rollup_id": self.labor_rollup_id,
            "revision_id": self.revision_id,
            "labor_rate_set_id": self.labor_rate_set_id,
            "total_hours": _float(self.total_hours),
            "total_labor_cost": _float(self.total_labor_cost),
            "category_hours": {
                key: _float(value) for key, value in self.category_hours.items()
            },
        }


@dataclass
class AssemblyExpansionResult:
    assembly_version_id: str
    contributions: list[AssemblyContribution | dict[str, Any]] = field(
        default_factory=list
    )
    diagnostics: list[AssemblyDiagnostic] = field(default_factory=list)
    consolidated_materials: list[dict[str, Any]] = field(default_factory=list)
    labor_rollup: LaborRollup | dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.labor_rollup, LaborRollup):
            labor_rollup_payload: dict[str, Any] | None = self.labor_rollup.to_dict()
        elif isinstance(self.labor_rollup, dict):
            labor_rollup_payload = dict(self.labor_rollup)
        else:
            labor_rollup_payload = None

        return {
            "assembly_version_id": self.assembly_version_id,
            "contributions": [
                item.to_dict() if hasattr(item, "to_dict") else dict(item)
                for item in self.contributions
            ],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "consolidated_materials": list(self.consolidated_materials),
            "labor_rollup": labor_rollup_payload,
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


def _float(value: Decimal) -> float:
    return float(value)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
