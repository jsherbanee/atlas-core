"""Deterministic assembly expansion and labor rollup service for D-03."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import hashlib
import json
from typing import Any
import uuid

from atlas_core.domain.assembly_labor import (
    AccessoryRule,
    AccessoryRuleKind,
    Assembly,
    AssemblyComponent,
    AssemblyComponentType,
    AssemblyDiagnostic,
    AssemblyExpansionRequest,
    AssemblyExpansionResult,
    AssemblyLifecycleState,
    AssemblyVersion,
    DiagnosticSeverity,
    LaborCategory,
    LaborRateRecord,
    LaborRateSet,
    LaborRollup,
    QuantityRule,
    QuantityRuleType,
)


class AssemblyExpansionService:
    ASSEMBLY_RULESET_VERSION = "atlas-assembly-rules:v1"
    LABOR_RULESET_VERSION = "atlas-labor-rules:v1"

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = self._normalized_state(state or self.empty_state())

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "assemblies": {},
            "versions": {},
            "components": {},
            "labor_activities": {},
            "labor_rate_sets": {},
            "labor_rate_records": {},
            "expansion_history": {},
        }

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.state, sort_keys=True))

    def create_assembly(
        self,
        *,
        canonical_name: str,
        display_name: str,
        created_by: str,
        assembly_id: str = "",
        description: str = "",
        category: str = "general",
        manufacturer_scope: str = "",
        system_applicability: list[str] | None = None,
        room_applicability: list[str] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        aid = assembly_id or f"assembly:{uuid.uuid4().hex[:12]}"
        if aid in self.state["assemblies"]:
            raise ValueError("Assembly already exists")
        assembly = Assembly(
            assembly_id=aid,
            canonical_name=canonical_name,
            display_name=display_name,
            description=description,
            category=category,
            manufacturer_scope=manufacturer_scope,
            system_applicability=list(system_applicability or []),
            room_applicability=list(room_applicability or []),
            notes=notes,
        )
        self.state["assemblies"][aid] = assembly.to_dict()
        version = self.create_assembly_version(
            assembly_id=aid,
            version_label="v1",
            created_by=created_by,
            revision_reason="Initial version",
        )
        return {
            "assembly": deepcopy(self.state["assemblies"][aid]),
            "version": deepcopy(version),
        }

    def create_assembly_version(
        self,
        *,
        assembly_id: str,
        version_label: str,
        created_by: str,
        revision_reason: str,
        parent_version_id: str = "",
        effective_date: str = "",
        expiration_date: str = "",
        assembly_version_id: str = "",
    ) -> dict[str, Any]:
        self._require_assembly(assembly_id)
        vid = (
            assembly_version_id
            or f"assembly_version:{assembly_id}:{uuid.uuid4().hex[:10]}"
        )
        if vid in self.state["versions"]:
            raise ValueError("Assembly version already exists")
        version = AssemblyVersion(
            assembly_version_id=vid,
            assembly_id=assembly_id,
            version_label=version_label,
            lifecycle_state=AssemblyLifecycleState.DRAFT,
            effective_date=effective_date or self._today_text(),
            expiration_date=expiration_date,
            parent_version_id=parent_version_id,
            revision_reason=revision_reason,
            created_by=created_by,
            ruleset_version=self.ASSEMBLY_RULESET_VERSION,
        )
        self.state["versions"][vid] = version.to_dict()
        self.state["components"][vid] = []
        return deepcopy(version.to_dict())

    def clone_assembly_version(
        self,
        *,
        source_assembly_version_id: str,
        created_by: str,
        version_label: str,
        revision_reason: str,
    ) -> dict[str, Any]:
        source = self._require_version(source_assembly_version_id)
        cloned = self.create_assembly_version(
            assembly_id=str(source.get("assembly_id")),
            version_label=version_label,
            created_by=created_by,
            revision_reason=revision_reason,
            parent_version_id=source_assembly_version_id,
        )
        self.state["components"][cloned["assembly_version_id"]] = [
            deepcopy(item)
            for item in list(
                self.state["components"].get(source_assembly_version_id) or []
            )
        ]
        return deepcopy(cloned)

    def add_component(
        self, *, assembly_version_id: str, component: dict[str, Any]
    ) -> dict[str, Any]:
        version = self._require_mutable_version(assembly_version_id)
        _ = version
        cid = str(component.get("component_id") or f"component:{uuid.uuid4().hex[:10]}")
        rule = component.get("quantity_rule") or {
            "rule_type": QuantityRuleType.FIXED.value,
            "value": 1,
        }
        accessory_rule = component.get("accessory_rule") or {
            "kind": AccessoryRuleKind.NONE.value,
        }
        comp = AssemblyComponent(
            component_id=cid,
            assembly_version_id=assembly_version_id,
            component_type=AssemblyComponentType(
                str(
                    component.get("component_type")
                    or AssemblyComponentType.PRODUCT.value
                )
            ),
            product_id=component.get("product_id") or "",
            nested_assembly_version_id=component.get("nested_assembly_version_id")
            or "",
            labor_activity_id=component.get("labor_activity_id") or "",
            quantity_rule=QuantityRule(**rule),
            accessory_rule=AccessoryRule(**accessory_rule),
            inclusion_state=component.get("inclusion_state") or "included",
            optional_selected_by_default=bool(
                component.get("optional_selected_by_default", False)
            ),
            sort_order=int(component.get("sort_order") or 0),
            notes=component.get("notes") or "",
            provenance_metadata=dict(component.get("provenance_metadata") or {}),
        )
        self._validate_component(comp)
        rows = list(self.state["components"].get(assembly_version_id) or [])
        if any(str(item.get("component_id")) == cid for item in rows):
            raise ValueError("Component already exists")
        rows.append(comp.to_dict())
        rows.sort(
            key=lambda item: (
                int(item.get("sort_order") or 0),
                str(item.get("component_id") or ""),
            )
        )
        self.state["components"][assembly_version_id] = rows
        return deepcopy(comp.to_dict())

    def update_draft_component(
        self,
        *,
        assembly_version_id: str,
        component_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_mutable_version(assembly_version_id)
        rows = list(self.state["components"].get(assembly_version_id) or [])
        for idx, row in enumerate(rows):
            if str(row.get("component_id")) != component_id:
                continue
            merged = dict(row)
            merged.update(dict(updates or {}))
            if "quantity_rule" not in merged:
                merged["quantity_rule"] = row.get("quantity_rule")
            if "accessory_rule" not in merged:
                merged["accessory_rule"] = row.get("accessory_rule")
            component = AssemblyComponent(
                component_id=component_id,
                assembly_version_id=assembly_version_id,
                component_type=AssemblyComponentType(
                    str(
                        merged.get("component_type")
                        or AssemblyComponentType.PRODUCT.value
                    )
                ),
                product_id=merged.get("product_id") or "",
                nested_assembly_version_id=merged.get("nested_assembly_version_id")
                or "",
                labor_activity_id=merged.get("labor_activity_id") or "",
                quantity_rule=QuantityRule(**dict(merged.get("quantity_rule") or {})),
                accessory_rule=AccessoryRule(
                    **dict(merged.get("accessory_rule") or {})
                ),
                inclusion_state=merged.get("inclusion_state") or "included",
                optional_selected_by_default=bool(
                    merged.get("optional_selected_by_default", False)
                ),
                sort_order=int(merged.get("sort_order") or 0),
                notes=merged.get("notes") or "",
                provenance_metadata=dict(merged.get("provenance_metadata") or {}),
            )
            self._validate_component(component)
            rows[idx] = component.to_dict()
            rows.sort(
                key=lambda item: (
                    int(item.get("sort_order") or 0),
                    str(item.get("component_id") or ""),
                )
            )
            self.state["components"][assembly_version_id] = rows
            return deepcopy(component.to_dict())
        raise ValueError("Component not found")

    def remove_draft_component(
        self, *, assembly_version_id: str, component_id: str
    ) -> None:
        self._require_mutable_version(assembly_version_id)
        rows = list(self.state["components"].get(assembly_version_id) or [])
        filtered = [
            item for item in rows if str(item.get("component_id")) != component_id
        ]
        if len(filtered) == len(rows):
            raise ValueError("Component not found")
        self.state["components"][assembly_version_id] = filtered

    def validate_assembly(self, *, assembly_version_id: str) -> dict[str, Any]:
        version = self._require_version(assembly_version_id)
        diagnostics: list[AssemblyDiagnostic] = []
        components = [
            AssemblyComponent(**item)
            for item in list(self.state["components"].get(assembly_version_id) or [])
        ]
        if not components:
            diagnostics.append(
                AssemblyDiagnostic(
                    code="assembly_empty",
                    severity=DiagnosticSeverity.ERROR,
                    message="Assembly version has no components.",
                    blocking=True,
                )
            )

        optional_groups: dict[str, int] = {}
        for item in components:
            try:
                self._validate_component(item)
            except ValueError as exc:
                diagnostics.append(
                    AssemblyDiagnostic(
                        code="invalid_component",
                        severity=DiagnosticSeverity.ERROR,
                        message=str(exc),
                        blocking=True,
                        component_id=item.component_id,
                    )
                )
            accessory = item.accessory_rule
            if (
                accessory.kind is AccessoryRuleKind.MUTEX_GROUP
                and not accessory.option_group
            ):
                diagnostics.append(
                    AssemblyDiagnostic(
                        code="invalid_optional_selection",
                        severity=DiagnosticSeverity.ERROR,
                        message="Mutually exclusive accessory group requires option_group.",
                        blocking=True,
                        component_id=item.component_id,
                    )
                )
            if accessory.kind in {
                AccessoryRuleKind.OPTIONAL,
                AccessoryRuleKind.MUTEX_GROUP,
            }:
                key = accessory.option_group or item.component_id
                optional_groups[key] = optional_groups.get(key, 0) + 1

        for group, count in optional_groups.items():
            if count > 1 and group.startswith("component:"):
                diagnostics.append(
                    AssemblyDiagnostic(
                        code="invalid_optional_selection",
                        severity=DiagnosticSeverity.WARNING,
                        message="Optional accessory component has no explicit option group.",
                        blocking=False,
                    )
                )

        cycle = self.detect_cycles(assembly_version_id=assembly_version_id)
        if cycle["has_cycle"]:
            diagnostics.append(
                AssemblyDiagnostic(
                    code="circular_assembly_reference",
                    severity=DiagnosticSeverity.ERROR,
                    message="Circular nested assembly reference detected.",
                    blocking=True,
                )
            )

        has_blocking = any(item.blocking for item in diagnostics)
        if (
            not has_blocking
            and version.get("lifecycle_state") == AssemblyLifecycleState.DRAFT.value
        ):
            version["lifecycle_state"] = AssemblyLifecycleState.VALIDATED.value
            version["validated_at"] = self._now_iso()
            self.state["versions"][assembly_version_id] = version

        return {
            "assembly_version_id": assembly_version_id,
            "valid": not has_blocking,
            "diagnostics": [item.to_dict() for item in diagnostics],
            "lifecycle_state": version.get("lifecycle_state"),
        }

    def activate_assembly_version(self, *, assembly_version_id: str) -> dict[str, Any]:
        version = self._require_version(assembly_version_id)
        if version.get("lifecycle_state") not in {
            AssemblyLifecycleState.VALIDATED.value,
            AssemblyLifecycleState.ACTIVE.value,
        }:
            raise ValueError("Only validated versions can be activated")
        assembly_id = str(version.get("assembly_id"))
        assembly = self._require_assembly(assembly_id)
        previous_active = str(assembly.get("current_active_version_id") or "")
        if previous_active and previous_active != assembly_version_id:
            previous = self._require_version(previous_active)
            previous["lifecycle_state"] = AssemblyLifecycleState.SUPERSEDED.value
            previous["superseded_at"] = self._now_iso()
            self.state["versions"][previous_active] = previous
        version["lifecycle_state"] = AssemblyLifecycleState.ACTIVE.value
        version["activated_at"] = self._now_iso()
        self.state["versions"][assembly_version_id] = version
        assembly["current_active_version_id"] = assembly_version_id
        assembly["updated_at"] = self._now_iso()
        self.state["assemblies"][assembly_id] = assembly
        return deepcopy(version)

    def supersede_assembly_version(self, *, assembly_version_id: str) -> dict[str, Any]:
        version = self._require_version(assembly_version_id)
        if version.get("lifecycle_state") != AssemblyLifecycleState.ACTIVE.value:
            raise ValueError("Only active versions can be superseded")
        version["lifecycle_state"] = AssemblyLifecycleState.SUPERSEDED.value
        version["superseded_at"] = self._now_iso()
        self.state["versions"][assembly_version_id] = version
        assembly = self._require_assembly(str(version.get("assembly_id")))
        if assembly.get("current_active_version_id") == assembly_version_id:
            assembly["current_active_version_id"] = ""
            assembly["updated_at"] = self._now_iso()
            self.state["assemblies"][str(version.get("assembly_id"))] = assembly
        return deepcopy(version)

    def archive_assembly_version(self, *, assembly_version_id: str) -> dict[str, Any]:
        version = self._require_version(assembly_version_id)
        if version.get("lifecycle_state") == AssemblyLifecycleState.ACTIVE.value:
            raise ValueError("Active versions cannot be archived")
        version["lifecycle_state"] = AssemblyLifecycleState.ARCHIVED.value
        self.state["versions"][assembly_version_id] = version
        return deepcopy(version)

    def detect_cycles(
        self, *, assembly_version_id: str, max_depth: int = 8
    ) -> dict[str, Any]:
        visited: set[str] = set()
        stack: list[str] = []
        cycle_path: list[str] = []

        def _visit(current: str, depth: int) -> bool:
            nonlocal cycle_path
            if depth > max_depth:
                return False
            if current in stack:
                cycle_path = stack[stack.index(current) :] + [current]
                return True
            if current in visited:
                return False
            visited.add(current)
            stack.append(current)
            rows = list(self.state["components"].get(current) or [])
            for row in rows:
                if (
                    str(row.get("component_type"))
                    != AssemblyComponentType.NESTED_ASSEMBLY.value
                ):
                    continue
                nested = str(row.get("nested_assembly_version_id") or "")
                if not nested:
                    continue
                if _visit(nested, depth + 1):
                    return True
            stack.pop()
            return False

        has_cycle = _visit(assembly_version_id, 0)
        return {
            "has_cycle": has_cycle,
            "cycle_path": cycle_path,
        }

    def create_labor_rate_set(
        self,
        *,
        labor_rate_set_id: str,
        version_label: str,
        effective_date: str,
        created_by: str,
        geography: str = "",
        prevailing_wage_applicable: bool = False,
    ) -> dict[str, Any]:
        if labor_rate_set_id in self.state["labor_rate_sets"]:
            raise ValueError("Labor rate set already exists")
        rate_set = LaborRateSet(
            labor_rate_set_id=labor_rate_set_id,
            version_label=version_label,
            lifecycle_state=AssemblyLifecycleState.DRAFT,
            effective_date=effective_date,
            geography=geography,
            prevailing_wage_applicable=prevailing_wage_applicable,
            created_by=created_by,
        )
        self.state["labor_rate_sets"][labor_rate_set_id] = rate_set.to_dict()
        self.state["labor_rate_records"][labor_rate_set_id] = []
        return deepcopy(rate_set.to_dict())

    def add_labor_rate_record(
        self, *, labor_rate_set_id: str, record: dict[str, Any]
    ) -> dict[str, Any]:
        rate_set = self._require_labor_rate_set(labor_rate_set_id)
        if rate_set.get("lifecycle_state") != AssemblyLifecycleState.DRAFT.value:
            raise ValueError("Only draft labor rate sets are editable")
        payload = LaborRateRecord(
            labor_rate_record_id=str(
                record.get("labor_rate_record_id")
                or f"labor_rate:{uuid.uuid4().hex[:10]}"
            ),
            labor_rate_set_id=labor_rate_set_id,
            labor_category=LaborCategory(
                str(record.get("labor_category") or LaborCategory.INSTALLATION.value)
            ),
            unit_basis=str(record.get("unit_basis") or "hours"),
            straight_time_rate=Decimal(str(record.get("straight_time_rate") or 0)),
            burden_rate=Decimal(str(record.get("burden_rate") or 0)),
            source_metadata=dict(record.get("source_metadata") or {}),
        )
        rows = list(self.state["labor_rate_records"].get(labor_rate_set_id) or [])
        if any(
            str(item.get("labor_rate_record_id")) == payload.labor_rate_record_id
            for item in rows
        ):
            raise ValueError("Labor rate record already exists")
        rows.append(payload.to_dict())
        self.state["labor_rate_records"][labor_rate_set_id] = rows
        return deepcopy(payload.to_dict())

    def activate_labor_rate_set(self, *, labor_rate_set_id: str) -> dict[str, Any]:
        rate_set = self._require_labor_rate_set(labor_rate_set_id)
        if rate_set.get("lifecycle_state") not in {
            AssemblyLifecycleState.DRAFT.value,
            AssemblyLifecycleState.VALIDATED.value,
        }:
            raise ValueError("Labor rate set cannot be activated")
        if not list(self.state["labor_rate_records"].get(labor_rate_set_id) or []):
            raise ValueError("Labor rate set requires at least one rate record")
        rate_set["lifecycle_state"] = AssemblyLifecycleState.ACTIVE.value
        rate_set["activated_at"] = self._now_iso()
        self.state["labor_rate_sets"][labor_rate_set_id] = rate_set
        return deepcopy(rate_set)

    def calculate_component_quantities(
        self,
        *,
        rule: QuantityRule,
        parent_quantity: Decimal,
        room_count: Decimal,
        system_count: Decimal,
        rack_count: Decimal,
        channel_count: Decimal,
        endpoint_count: Decimal,
    ) -> tuple[Decimal, str]:
        if parent_quantity < 0:
            raise ValueError("invalid negative quantities")
        driver = Decimal("0")
        explanation = ""
        if rule.rule_type is QuantityRuleType.FIXED:
            driver = rule.value
            explanation = f"fixed({rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_PARENT:
            driver = parent_quantity * rule.value
            explanation = f"per_parent({parent_quantity} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_ROOM:
            driver = room_count * rule.value
            explanation = f"per_room({room_count} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_SYSTEM:
            driver = system_count * rule.value
            explanation = f"per_system({system_count} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_RACK:
            driver = rack_count * rule.value
            explanation = f"per_rack({rack_count} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_CHANNEL:
            driver = channel_count * rule.value
            explanation = f"per_channel({channel_count} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PER_ENDPOINT:
            driver = endpoint_count * rule.value
            explanation = f"per_endpoint({endpoint_count} * {rule.value})"
        elif rule.rule_type is QuantityRuleType.PERCENTAGE:
            if rule.value < 0 or rule.value > Decimal("1"):
                raise ValueError("invalid percentages")
            driver = parent_quantity * rule.value
            explanation = f"percentage({parent_quantity} * {rule.value})"
        else:
            raise ValueError("unsupported combinations")

        adjusted = driver * (Decimal("1") + rule.waste_factor + rule.spare_factor)
        adjusted = max(adjusted, rule.minimum_quantity)
        if rule.round_up_to <= 0:
            raise ValueError("malformed rules")
        rounded = (adjusted / rule.round_up_to).to_integral_value(
            rounding=ROUND_CEILING
        ) * rule.round_up_to
        if rounded > Decimal("1000000"):
            raise ValueError("quantity overflow")
        return rounded.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), explanation

    def list_required_accessories(
        self, *, assembly_version_id: str
    ) -> list[dict[str, Any]]:
        self._require_version(assembly_version_id)
        return [
            deepcopy(item)
            for item in list(self.state["components"].get(assembly_version_id) or [])
            if str(dict(item.get("accessory_rule") or {}).get("kind"))
            == AccessoryRuleKind.REQUIRED.value
        ]

    def list_optional_accessories(
        self, *, assembly_version_id: str
    ) -> list[dict[str, Any]]:
        self._require_version(assembly_version_id)
        return [
            deepcopy(item)
            for item in list(self.state["components"].get(assembly_version_id) or [])
            if str(dict(item.get("accessory_rule") or {}).get("kind"))
            in {AccessoryRuleKind.OPTIONAL.value, AccessoryRuleKind.MUTEX_GROUP.value}
        ]

    def preview_expansion(
        self, *, request: AssemblyExpansionRequest | dict[str, Any], max_depth: int = 8
    ) -> dict[str, Any]:
        req = (
            request
            if isinstance(request, AssemblyExpansionRequest)
            else AssemblyExpansionRequest(**request)
        )
        if self.detect_cycles(
            assembly_version_id=req.assembly_version_id, max_depth=max_depth
        )["has_cycle"]:
            return AssemblyExpansionResult(
                assembly_version_id=req.assembly_version_id,
                diagnostics=[
                    AssemblyDiagnostic(
                        code="circular_assembly_reference",
                        severity=DiagnosticSeverity.ERROR,
                        message="Circular assembly reference detected during preview.",
                        blocking=True,
                    )
                ],
            ).to_dict()

        diagnostics: list[AssemblyDiagnostic] = []
        contributions = self._expand_version(
            assembly_version_id=req.assembly_version_id,
            parent_quantity=req.parent_quantity,
            room_count=req.room_count,
            system_count=req.system_count,
            rack_count=req.rack_count,
            channel_count=req.channel_count,
            endpoint_count=req.endpoint_count,
            selected_optional_component_ids=set(req.selected_optional_component_ids),
            diagnostics=diagnostics,
            parent_chain=[],
            depth=0,
            max_depth=max_depth,
        )
        consolidated = self.calculate_material_rollup(contributions=contributions)
        labor_rollup = self.calculate_labor_rollup(
            contributions=contributions, labor_rate_set_id=""
        )
        return AssemblyExpansionResult(
            assembly_version_id=req.assembly_version_id,
            contributions=contributions,
            diagnostics=diagnostics,
            consolidated_materials=consolidated,
            labor_rollup=labor_rollup,
        ).to_dict()

    def expand_assembly(
        self,
        *,
        request: AssemblyExpansionRequest | dict[str, Any],
        labor_rate_set_id: str = "",
        max_depth: int = 8,
    ) -> dict[str, Any]:
        payload = self.preview_expansion(request=request, max_depth=max_depth)
        payload["labor_rollup"] = self.calculate_labor_rollup(
            contributions=[
                c if isinstance(c, dict) else c.to_dict()
                for c in list(payload.get("contributions") or [])
            ],
            labor_rate_set_id=labor_rate_set_id,
        ).to_dict()
        run_id = self._digest_id(payload)
        self.state["expansion_history"][run_id] = deepcopy(payload)
        payload["expansion_run_id"] = run_id
        return payload

    def explain_expansion(self, *, expansion_run_id: str) -> dict[str, Any]:
        row = dict(self.state["expansion_history"].get(expansion_run_id) or {})
        if not row:
            raise ValueError("Expansion run not found")
        return deepcopy(row)

    def compare_assembly_versions(
        self,
        *,
        baseline_assembly_version_id: str,
        candidate_assembly_version_id: str,
    ) -> dict[str, Any]:
        baseline = {
            str(item.get("component_id")): dict(item)
            for item in list(
                self.state["components"].get(baseline_assembly_version_id) or []
            )
        }
        candidate = {
            str(item.get("component_id")): dict(item)
            for item in list(
                self.state["components"].get(candidate_assembly_version_id) or []
            )
        }
        added = sorted([key for key in candidate if key not in baseline])
        removed = sorted([key for key in baseline if key not in candidate])
        changed: list[str] = []
        for key in sorted(set(baseline) & set(candidate)):
            if baseline[key] != candidate[key]:
                changed.append(key)
        return {
            "baseline_assembly_version_id": baseline_assembly_version_id,
            "candidate_assembly_version_id": candidate_assembly_version_id,
            "added_components": added,
            "removed_components": removed,
            "changed_components": changed,
        }

    def calculate_material_rollup(
        self, *, contributions: list[dict[str, Any] | Any]
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for entry in contributions:
            row = entry if isinstance(entry, dict) else entry.to_dict()
            if str(row.get("component_type")) not in {
                AssemblyComponentType.PRODUCT.value,
                AssemblyComponentType.CONSUMABLE.value,
                AssemblyComponentType.INFRASTRUCTURE_MATERIAL.value,
            }:
                continue
            product_id = str(row.get("product_id") or "")
            if not product_id:
                continue
            key = (product_id, "ea", "")
            existing = grouped.get(key)
            quantity = Decimal(str(row.get("generated_quantity") or 0))
            if existing is None:
                grouped[key] = {
                    "product_id": product_id,
                    "unit_of_measure": "ea",
                    "generated_quantity": float(quantity),
                    "contribution_ids": [str(row.get("contribution_id") or "")],
                }
            else:
                existing["generated_quantity"] = float(
                    Decimal(str(existing.get("generated_quantity") or 0)) + quantity
                )
                existing["contribution_ids"].append(
                    str(row.get("contribution_id") or "")
                )
        return [
            grouped[key]
            for key in sorted(grouped, key=lambda item: (item[0], item[1], item[2]))
        ]

    def calculate_labor_rollup(
        self,
        *,
        contributions: list[dict[str, Any] | Any],
        labor_rate_set_id: str,
    ) -> LaborRollup:
        rows = [
            entry if isinstance(entry, dict) else entry.to_dict()
            for entry in contributions
        ]
        labor_rows = [
            row
            for row in rows
            if str(row.get("component_type"))
            == AssemblyComponentType.LABOR_ACTIVITY.value
        ]
        category_hours: dict[str, Decimal] = {}
        total_hours = Decimal("0")
        total_cost = Decimal("0")

        rate_records = [
            LaborRateRecord(**item)
            for item in list(
                self.state["labor_rate_records"].get(labor_rate_set_id) or []
            )
        ]
        by_category = {item.labor_category.value: item for item in rate_records}

        for row in labor_rows:
            hours = Decimal(str(row.get("generated_quantity") or 0))
            category_name = str(
                row.get("labor_category") or LaborCategory.INSTALLATION.value
            )
            category_hours[category_name] = (
                category_hours.get(category_name, Decimal("0")) + hours
            )
            total_hours += hours
            record = by_category.get(category_name)
            if record is None:
                continue
            unit_rate = record.straight_time_rate + record.burden_rate
            total_cost += unit_rate * hours

        return LaborRollup(
            labor_rollup_id=f"labor_rollup:{self._digest_id({'labor_rate_set_id': labor_rate_set_id, 'rows': rows})}",
            revision_id="preview",
            labor_rate_set_id=labor_rate_set_id or "none",
            total_hours=total_hours,
            total_labor_cost=total_cost,
            category_hours=category_hours,
        )

    def _expand_version(
        self,
        *,
        assembly_version_id: str,
        parent_quantity: Decimal,
        room_count: Decimal,
        system_count: Decimal,
        rack_count: Decimal,
        channel_count: Decimal,
        endpoint_count: Decimal,
        selected_optional_component_ids: set[str],
        diagnostics: list[AssemblyDiagnostic],
        parent_chain: list[str],
        depth: int,
        max_depth: int,
    ) -> list[Any]:
        if depth > max_depth:
            diagnostics.append(
                AssemblyDiagnostic(
                    code="recursion_limit_exceeded",
                    severity=DiagnosticSeverity.ERROR,
                    message="Nested assembly recursion limit exceeded.",
                    blocking=True,
                )
            )
            return []
        rows = [
            AssemblyComponent(**item)
            for item in list(self.state["components"].get(assembly_version_id) or [])
        ]
        contributions: list[Any] = []
        for row in rows:
            accessory_kind = row.accessory_rule.kind
            if accessory_kind is AccessoryRuleKind.OPTIONAL:
                is_selected = (
                    row.component_id in selected_optional_component_ids
                    or row.optional_selected_by_default
                )
                if not is_selected:
                    continue
            if accessory_kind is AccessoryRuleKind.MUTEX_GROUP:
                group = row.accessory_rule.option_group
                if not group:
                    diagnostics.append(
                        AssemblyDiagnostic(
                            code="invalid_optional_selection",
                            severity=DiagnosticSeverity.ERROR,
                            message="Mutually exclusive accessory group missing option_group.",
                            blocking=True,
                            component_id=row.component_id,
                        )
                    )
                    continue
                group_selected = [
                    item
                    for item in selected_optional_component_ids
                    if item.startswith(f"{group}:")
                ]
                if group_selected and row.component_id not in {
                    item.split(":", 1)[1] for item in group_selected if ":" in item
                }:
                    continue

            try:
                quantity, explanation = self.calculate_component_quantities(
                    rule=row.quantity_rule,
                    parent_quantity=parent_quantity,
                    room_count=room_count,
                    system_count=system_count,
                    rack_count=rack_count,
                    channel_count=channel_count,
                    endpoint_count=endpoint_count,
                )
            except ValueError as exc:
                diagnostics.append(
                    AssemblyDiagnostic(
                        code="invalid_quantity_rule",
                        severity=DiagnosticSeverity.ERROR,
                        message=str(exc),
                        blocking=True,
                        component_id=row.component_id,
                    )
                )
                continue

            if row.component_type is AssemblyComponentType.NESTED_ASSEMBLY:
                nested_version_id = row.nested_assembly_version_id
                if not nested_version_id:
                    diagnostics.append(
                        AssemblyDiagnostic(
                            code="missing_nested_assembly_version",
                            severity=DiagnosticSeverity.ERROR,
                            message="Nested assembly component requires nested assembly version.",
                            blocking=True,
                            component_id=row.component_id,
                        )
                    )
                    continue
                if nested_version_id in parent_chain:
                    diagnostics.append(
                        AssemblyDiagnostic(
                            code="circular_assembly_reference",
                            severity=DiagnosticSeverity.ERROR,
                            message="Circular nested assembly reference detected.",
                            blocking=True,
                            component_id=row.component_id,
                        )
                    )
                    continue
                contributions.extend(
                    self._expand_version(
                        assembly_version_id=nested_version_id,
                        parent_quantity=quantity,
                        room_count=room_count,
                        system_count=system_count,
                        rack_count=rack_count,
                        channel_count=channel_count,
                        endpoint_count=endpoint_count,
                        selected_optional_component_ids=selected_optional_component_ids,
                        diagnostics=diagnostics,
                        parent_chain=[*parent_chain, assembly_version_id],
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
                continue

            payload = {
                "contribution_id": f"contrib:{uuid.uuid4().hex[:12]}",
                "parent_component_id": row.component_id,
                "source_assembly_version_id": assembly_version_id,
                "component_type": row.component_type.value,
                "product_id": row.product_id,
                "labor_activity_id": row.labor_activity_id,
                "generated_quantity": float(quantity),
                "quantity_explanation": explanation,
                "parent_chain": [*parent_chain, assembly_version_id],
            }
            if row.component_type is AssemblyComponentType.LABOR_ACTIVITY:
                payload["labor_category"] = str(
                    row.provenance_metadata.get("labor_category")
                    or LaborCategory.INSTALLATION.value
                )
            contributions.append(payload)

        return contributions

    def _validate_component(self, component: AssemblyComponent) -> None:
        if (
            component.component_type is AssemblyComponentType.PRODUCT
            and not component.product_id
        ):
            raise ValueError("Product components require Product identity")
        if (
            component.component_type is AssemblyComponentType.NESTED_ASSEMBLY
            and not component.nested_assembly_version_id
        ):
            raise ValueError(
                "Nested Assembly components require exact Assembly Version"
            )
        if (
            component.component_type is AssemblyComponentType.LABOR_ACTIVITY
            and not component.labor_activity_id
        ):
            raise ValueError("Labor components require Labor Activity")
        if (
            component.component_type is AssemblyComponentType.ALLOWANCE
            and component.product_id
        ):
            raise ValueError("Allowance components must not fabricate Price Records")

    def _require_assembly(self, assembly_id: str) -> dict[str, Any]:
        item = self.state["assemblies"].get(assembly_id)
        if item is None:
            raise ValueError("Assembly not found")
        return dict(item)

    def _require_version(self, assembly_version_id: str) -> dict[str, Any]:
        item = self.state["versions"].get(assembly_version_id)
        if item is None:
            raise ValueError("Assembly version not found")
        return dict(item)

    def _require_mutable_version(self, assembly_version_id: str) -> dict[str, Any]:
        item = self._require_version(assembly_version_id)
        if item.get("lifecycle_state") in {
            AssemblyLifecycleState.ACTIVE.value,
            AssemblyLifecycleState.SUPERSEDED.value,
            AssemblyLifecycleState.ARCHIVED.value,
        }:
            raise ValueError("Assembly version is immutable")
        return item

    def _require_labor_rate_set(self, labor_rate_set_id: str) -> dict[str, Any]:
        item = self.state["labor_rate_sets"].get(labor_rate_set_id)
        if item is None:
            raise ValueError("Labor rate set not found")
        return dict(item)

    def _normalized_state(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = self.empty_state()
        for key in normalized:
            if isinstance(state.get(key), dict):
                normalized[key] = deepcopy(state[key])
        return normalized

    def _digest_id(self, payload: dict[str, Any]) -> str:
        digest = hashlib.sha1(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return digest[:16]

    def _now_iso(self) -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

    def _today_text(self) -> str:
        return self._now_iso()[:10]
