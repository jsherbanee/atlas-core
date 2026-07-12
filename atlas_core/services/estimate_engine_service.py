"""Deterministic estimate engine service for D-02 revision and snapshot workflows."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, date
from decimal import Decimal
import hashlib
import json
from typing import Any
import uuid

from atlas_core.domain.cost_engine import CostSelectionResult
from atlas_core.domain.assembly_labor import AssemblyExpansionRequest
from atlas_core.domain.estimate_engine import (
    CostRefreshResult,
    CostSnapshot,
    Estimate,
    EstimateDiagnostic,
    EstimateDiagnosticSeverity,
    EstimateLineItem,
    EstimateRevision,
    EstimateRevisionState,
    EstimateTotals,
    ManualSelectionMetadata,
    RevisionComparison,
    SnapshotReference,
)
from atlas_core.services.assembly_expansion_service import AssemblyExpansionService
from atlas_core.services.cost_engine_service import DeterministicCostEngine


class EstimateEngineService:
    ESTIMATE_RULESET_VERSION = "atlas-estimate-rules:v1"
    SNAPSHOT_SCHEMA_VERSION = "atlas-cost-snapshot:v1"

    def __init__(
        self,
        state: dict[str, Any] | None = None,
        *,
        as_of: date | None = None,
    ) -> None:
        self._as_of = as_of
        self.state = self._normalized_state(state or self.empty_state())

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "estimates": {},
            "revisions": {},
            "cost_snapshots": {},
            "labor_snapshots": {},
            "assembly_expansions": {},
            "assembly_refresh_previews": {},
            "assembly_overrides": {},
            "assembly_state": AssemblyExpansionService.empty_state(),
            "refresh_results": {},
            "revision_comparisons": {},
        }

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.state, sort_keys=True))

    def create_estimate(
        self,
        *,
        project_id: str,
        name: str,
        created_by: str,
        estimate_id: str | None = None,
    ) -> dict[str, Any]:
        now = self._now_iso()
        eid = estimate_id or f"estimate:{project_id}:{uuid.uuid4().hex[:8]}"
        if eid in self.state["estimates"]:
            raise ValueError("Estimate already exists")
        estimate = Estimate(
            estimate_id=eid,
            project_id=project_id,
            name=name,
            created_by=created_by,
            updated_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.state["estimates"][eid] = estimate.to_dict()
        revision = self.create_revision(
            estimate_id=eid,
            created_by=created_by,
            reason="Initial revision",
            clone_from_revision_id="",
        )
        estimate_row = dict(self.state["estimates"][eid])
        estimate_row["active_draft_revision_id"] = revision["revision_id"]
        estimate_row["revision_ids"] = [revision["revision_id"]]
        self.state["estimates"][eid] = estimate_row
        return {
            "estimate": deepcopy(estimate_row),
            "revision": deepcopy(revision),
        }

    def create_revision(
        self,
        *,
        estimate_id: str,
        created_by: str,
        reason: str,
        clone_from_revision_id: str = "",
    ) -> dict[str, Any]:
        estimate = self._require_estimate(estimate_id)
        next_number = len(list(estimate.get("revision_ids") or [])) + 1
        revision_id = f"revision:{estimate_id}:{next_number}"
        if revision_id in self.state["revisions"]:
            raise ValueError("Revision already exists")

        line_items: list[EstimateLineItem] = []
        if clone_from_revision_id:
            source = self._require_revision(clone_from_revision_id)
            line_items = [
                EstimateLineItem(**dict(item))
                for item in list(source.get("line_items") or [])
            ]

        revision = EstimateRevision(
            revision_id=revision_id,
            estimate_id=estimate_id,
            revision_number=next_number,
            state=EstimateRevisionState.DRAFT,
            parent_revision_id=clone_from_revision_id,
            revision_reason=reason,
            line_items=line_items,
            created_by=created_by,
            updated_by=created_by,
            created_at=self._now_iso(),
            updated_at=self._now_iso(),
            cost_engine_ruleset_version=DeterministicCostEngine.POLICY_VERSION,
            estimate_calculation_ruleset_version=self.ESTIMATE_RULESET_VERSION,
            snapshot_schema_version=self.SNAPSHOT_SCHEMA_VERSION,
        )
        self.state["revisions"][revision_id] = revision.to_dict()

        estimate["revision_ids"] = list(estimate.get("revision_ids") or []) + [
            revision_id
        ]
        estimate["active_draft_revision_id"] = revision_id
        estimate["updated_by"] = created_by
        estimate["updated_at"] = self._now_iso()
        self.state["estimates"][estimate_id] = estimate

        if clone_from_revision_id:
            cloned = self._require_revision(clone_from_revision_id)
            if cloned.get("state") == EstimateRevisionState.LOCKED.value:
                cloned["state"] = EstimateRevisionState.SUPERSEDED.value
                cloned["superseded_by_revision_id"] = revision_id
                cloned["superseded_at"] = self._now_iso()
                self.state["revisions"][clone_from_revision_id] = cloned

        return deepcopy(self.state["revisions"][revision_id])

    def clone_revision(
        self,
        *,
        source_revision_id: str,
        created_by: str,
        reason: str = "Clone revision",
    ) -> dict[str, Any]:
        source = self._require_revision(source_revision_id)
        return self.create_revision(
            estimate_id=str(source.get("estimate_id")),
            created_by=created_by,
            reason=reason,
            clone_from_revision_id=source_revision_id,
        )

    def add_line_item(
        self,
        *,
        revision_id: str,
        actor: str,
        line: dict[str, Any],
    ) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        line_item_id = str(line.get("line_item_id") or f"line:{uuid.uuid4().hex[:10]}")
        new_line = EstimateLineItem(
            line_item_id=line_item_id,
            product_id=str(line.get("product_id") or ""),
            manufacturer=str(line.get("manufacturer") or ""),
            model=str(line.get("model") or ""),
            description=str(line.get("description") or ""),
            requested_quantity=Decimal(str(line.get("requested_quantity") or 0)),
            engineering_quantity=Decimal(
                str(
                    line.get("engineering_quantity")
                    or line.get("requested_quantity")
                    or 0
                )
            ),
            procurement_quantity=Decimal(
                str(
                    line.get("procurement_quantity")
                    or line.get("requested_quantity")
                    or 0
                )
            ),
            unit_of_measure=str(line.get("unit_of_measure") or "ea"),
            section=str(line.get("section") or ""),
            system=str(line.get("system") or ""),
            room=str(line.get("room") or ""),
            source_object_id=str(line.get("source_object_id") or ""),
            source_selection_status=str(
                line.get("source_selection_status") or "no_eligible_cost"
            ),
            line_role=str(line.get("line_role") or "standard_product"),
            parent_line_item_id=str(line.get("parent_line_item_id") or ""),
            assembly_id=str(line.get("assembly_id") or ""),
            assembly_version_id=str(line.get("assembly_version_id") or ""),
            assembly_component_id=str(line.get("assembly_component_id") or ""),
            source_contribution_chain=list(line.get("source_contribution_chain") or []),
            generated_quantity=Decimal(str(line.get("generated_quantity") or 0)),
            quantity_rule=dict(line.get("quantity_rule") or {}),
            optional_accessory_decision=str(
                line.get("optional_accessory_decision") or "not_applicable"
            ),
            manual_adjustment_metadata=list(
                line.get("manual_adjustment_metadata") or []
            ),
            expansion_run_id=str(line.get("expansion_run_id") or ""),
            assembly_ruleset_version=str(line.get("assembly_ruleset_version") or ""),
            labor_snapshot_id=str(line.get("labor_snapshot_id") or ""),
            excluded=bool(line.get("excluded", False)),
            notes=str(line.get("notes") or ""),
            created_at=self._now_iso(),
            updated_at=self._now_iso(),
        )
        items = [dict(item) for item in list(revision.get("line_items") or [])]
        if any(str(item.get("line_item_id")) == line_item_id for item in items):
            raise ValueError("Line item already exists")
        items.append(new_line.to_dict())
        revision["line_items"] = items
        revision["updated_by"] = actor
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        return deepcopy(new_line.to_dict())

    def update_draft_line_item(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        items = [dict(item) for item in list(revision.get("line_items") or [])]
        for idx, item in enumerate(items):
            if str(item.get("line_item_id")) != line_item_id:
                continue
            next_item = dict(item)
            for key in [
                "product_id",
                "manufacturer",
                "model",
                "description",
                "unit_of_measure",
                "section",
                "system",
                "room",
                "source_object_id",
                "notes",
            ]:
                if key in updates:
                    next_item[key] = updates[key]
            for key in [
                "requested_quantity",
                "engineering_quantity",
                "procurement_quantity",
            ]:
                if key in updates:
                    next_item[key] = float(Decimal(str(updates[key])))
            if "source_selection_status" in updates:
                next_item["source_selection_status"] = str(
                    updates["source_selection_status"]
                )
            next_item["updated_at"] = self._now_iso()
            items[idx] = EstimateLineItem(**next_item).to_dict()
            revision["line_items"] = items
            revision["updated_by"] = actor
            revision["updated_at"] = self._now_iso()
            self.state["revisions"][revision_id] = revision
            return deepcopy(items[idx])
        raise ValueError("Line item not found")

    def remove_draft_line_item(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
    ) -> None:
        revision = self._require_mutable_revision(revision_id)
        items = [
            dict(item)
            for item in list(revision.get("line_items") or [])
            if str(item.get("line_item_id")) != line_item_id
        ]
        if len(items) == len(list(revision.get("line_items") or [])):
            raise ValueError("Line item not found")
        revision["line_items"] = items
        revision["updated_by"] = actor
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision

    def preview_assembly_insertion(
        self,
        *,
        revision_id: str,
        assembly_version_id: str,
        parent_quantity: float,
        labor_rate_set_id: str,
        actor: str,
        room_count: float = 1.0,
        system_count: float = 1.0,
        rack_count: float = 1.0,
        channel_count: float = 1.0,
        endpoint_count: float = 1.0,
        optional_component_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        request = AssemblyExpansionRequest(
            estimate_id=str(revision.get("estimate_id") or ""),
            revision_id=revision_id,
            assembly_version_id=assembly_version_id,
            parent_quantity=Decimal(str(parent_quantity)),
            room_count=Decimal(str(room_count)),
            system_count=Decimal(str(system_count)),
            rack_count=Decimal(str(rack_count)),
            channel_count=Decimal(str(channel_count)),
            endpoint_count=Decimal(str(endpoint_count)),
            selected_optional_component_ids=list(optional_component_ids or []),
        )
        preview = self._assembly_service().expand_assembly(
            request=request,
            labor_rate_set_id=labor_rate_set_id,
        )
        preview["actor"] = actor
        return preview

    def add_assembly_to_revision(
        self,
        *,
        revision_id: str,
        assembly_version_id: str,
        parent_quantity: float,
        labor_rate_set_id: str,
        commercial_state: dict[str, Any],
        actor: str,
        parent_description: str = "Assembly",
        room_count: float = 1.0,
        system_count: float = 1.0,
        rack_count: float = 1.0,
        channel_count: float = 1.0,
        endpoint_count: float = 1.0,
        optional_component_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        working_revision_id = revision_id
        revision = self._require_revision(revision_id)
        if revision.get("state") == EstimateRevisionState.LOCKED.value:
            cloned = self.clone_revision(
                source_revision_id=revision_id,
                created_by=actor,
                reason="Assembly insertion from locked revision",
            )
            working_revision_id = str(cloned.get("revision_id"))

        working = self._require_mutable_revision(working_revision_id)
        preview = self.preview_assembly_insertion(
            revision_id=working_revision_id,
            assembly_version_id=assembly_version_id,
            parent_quantity=parent_quantity,
            labor_rate_set_id=labor_rate_set_id,
            actor=actor,
            room_count=room_count,
            system_count=system_count,
            rack_count=rack_count,
            channel_count=channel_count,
            endpoint_count=endpoint_count,
            optional_component_ids=optional_component_ids,
        )
        diagnostics = list(preview.get("diagnostics") or [])
        if any(bool(item.get("blocking")) for item in diagnostics):
            return {
                "working_revision_id": working_revision_id,
                "accepted": False,
                "diagnostics": diagnostics,
            }

        before_revision = deepcopy(working)
        before_snapshots = deepcopy(dict(self.state.get("cost_snapshots") or {}))
        before_labor = deepcopy(dict(self.state.get("labor_snapshots") or {}))
        before_expansions = deepcopy(dict(self.state.get("assembly_expansions") or {}))
        try:
            assembly = self._assembly_service()._require_version(assembly_version_id)
            assembly_id = str(assembly.get("assembly_id") or "")
            parent_line_id = f"assembly_parent:{uuid.uuid4().hex[:10]}"
            parent_line = self.add_line_item(
                revision_id=working_revision_id,
                actor=actor,
                line={
                    "line_item_id": parent_line_id,
                    "product_id": "",
                    "manufacturer": "",
                    "model": "",
                    "description": parent_description,
                    "requested_quantity": parent_quantity,
                    "engineering_quantity": parent_quantity,
                    "procurement_quantity": parent_quantity,
                    "unit_of_measure": "ea",
                    "section": "Assemblies",
                    "system": "Assembly",
                    "room": "Unassigned",
                    "source_object_id": parent_line_id,
                    "source_selection_status": "not_priced",
                    "line_role": "assembly_parent",
                    "assembly_id": assembly_id,
                    "assembly_version_id": assembly_version_id,
                    "generated_quantity": parent_quantity,
                    "expansion_run_id": str(preview.get("expansion_run_id") or ""),
                    "assembly_ruleset_version": AssemblyExpansionService.ASSEMBLY_RULESET_VERSION,
                },
            )

            created_lines: list[dict[str, Any]] = []
            for contribution in list(preview.get("contributions") or []):
                row = dict(contribution)
                line_role = "generated_product_child"
                product_id = str(row.get("product_id") or "")
                labor_activity_id = str(row.get("labor_activity_id") or "")
                description = product_id or labor_activity_id or "Generated component"
                source_status = "no_eligible_cost"
                if str(row.get("component_type") or "") == "labor_activity":
                    line_role = "generated_labor_child"
                    source_status = "labor_snapshot_created"
                line_item_id = f"assembly_child:{uuid.uuid4().hex[:10]}"
                child = self.add_line_item(
                    revision_id=working_revision_id,
                    actor=actor,
                    line={
                        "line_item_id": line_item_id,
                        "product_id": product_id,
                        "manufacturer": (
                            product_id.split("::", 1)[0] if "::" in product_id else ""
                        ),
                        "model": (
                            product_id.split("::", 1)[1] if "::" in product_id else ""
                        ),
                        "description": description,
                        "requested_quantity": row.get("generated_quantity") or 0,
                        "engineering_quantity": row.get("generated_quantity") or 0,
                        "procurement_quantity": row.get("generated_quantity") or 0,
                        "unit_of_measure": (
                            "hours" if line_role == "generated_labor_child" else "ea"
                        ),
                        "section": "Assemblies",
                        "system": "Assembly",
                        "room": "Unassigned",
                        "source_object_id": str(
                            row.get("contribution_id") or line_item_id
                        ),
                        "source_selection_status": source_status,
                        "line_role": line_role,
                        "parent_line_item_id": parent_line_id,
                        "assembly_id": assembly_id,
                        "assembly_version_id": assembly_version_id,
                        "assembly_component_id": str(
                            row.get("parent_component_id") or ""
                        ),
                        "source_contribution_chain": list(
                            row.get("parent_chain") or []
                        ),
                        "generated_quantity": row.get("generated_quantity") or 0,
                        "quantity_rule": {
                            "explanation": str(row.get("quantity_explanation") or "")
                        },
                        "optional_accessory_decision": "included",
                        "expansion_run_id": str(preview.get("expansion_run_id") or ""),
                        "assembly_ruleset_version": AssemblyExpansionService.ASSEMBLY_RULESET_VERSION,
                    },
                )

                if line_role == "generated_product_child" and product_id:
                    selection = self.select_line_cost(
                        revision_id=working_revision_id,
                        line_item_id=str(child.get("line_item_id") or ""),
                        commercial_state=commercial_state,
                        actor=actor,
                    )
                    if not str(
                        dict(selection.get("snapshot") or {})
                        .get("reference", {})
                        .get("price_record_id", "")
                    ):
                        raise ValueError(
                            "Missing required product cost selection during assembly insertion"
                        )
                if line_role == "generated_labor_child":
                    snapshot_id = self._create_labor_snapshot(
                        revision_id=working_revision_id,
                        parent_line_item_id=parent_line_id,
                        line_item_id=str(child.get("line_item_id") or ""),
                        contribution=row,
                        labor_rate_set_id=labor_rate_set_id,
                        expansion_run_id=str(preview.get("expansion_run_id") or ""),
                        assembly_id=assembly_id,
                        assembly_version_id=assembly_version_id,
                    )
                    labor_snapshot = dict(
                        self.state.get("labor_snapshots", {}).get(snapshot_id) or {}
                    )
                    if not str(labor_snapshot.get("labor_rate_record_id") or ""):
                        raise ValueError(
                            "Missing required labor rate selection during assembly insertion"
                        )
                    self._set_line_field(
                        revision_id=working_revision_id,
                        line_item_id=str(child.get("line_item_id") or ""),
                        field_name="labor_snapshot_id",
                        value=snapshot_id,
                    )
                created_lines.append(child)

            expansion_run_id = str(
                preview.get("expansion_run_id") or uuid.uuid4().hex[:16]
            )
            self.state["assembly_expansions"][expansion_run_id] = {
                "expansion_run_id": expansion_run_id,
                "revision_id": working_revision_id,
                "assembly_id": assembly_id,
                "assembly_version_id": assembly_version_id,
                "parent_line_item_id": parent_line_id,
                "labor_rate_set_id": labor_rate_set_id,
                "context": {
                    "parent_quantity": parent_quantity,
                    "room_count": room_count,
                    "system_count": system_count,
                    "rack_count": rack_count,
                    "channel_count": channel_count,
                    "endpoint_count": endpoint_count,
                    "optional_component_ids": list(optional_component_ids or []),
                },
                "preview": deepcopy(preview),
                "created_by": actor,
                "created_at": self._now_iso(),
                "manual_overrides": [],
                "refresh_pending": False,
            }
            self.calculate_revision_totals(revision_id=working_revision_id)
            self.validate_revision(revision_id=working_revision_id)
            return {
                "working_revision_id": working_revision_id,
                "accepted": True,
                "expansion_run_id": expansion_run_id,
                "parent_line": parent_line,
                "created_lines": created_lines,
                "diagnostics": diagnostics,
            }
        except Exception:
            self.state["revisions"][working_revision_id] = before_revision
            self.state["cost_snapshots"] = before_snapshots
            self.state["labor_snapshots"] = before_labor
            self.state["assembly_expansions"] = before_expansions
            raise

    def remove_draft_assembly(
        self,
        *,
        revision_id: str,
        parent_line_item_id: str,
        actor: str,
    ) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        items = [dict(item) for item in list(revision.get("line_items") or [])]
        removed_ids = {
            str(item.get("line_item_id") or "")
            for item in items
            if str(item.get("line_item_id") or "") == parent_line_item_id
            or str(item.get("parent_line_item_id") or "") == parent_line_item_id
        }
        if not removed_ids:
            raise ValueError("Assembly parent line not found")
        revision["line_items"] = [
            item
            for item in items
            if str(item.get("line_item_id") or "") not in removed_ids
        ]
        revision["updated_by"] = actor
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        for snapshot_id, payload in list(
            dict(self.state.get("labor_snapshots") or {}).items()
        ):
            if str(payload.get("line_item_id") or "") in removed_ids:
                self.state["labor_snapshots"].pop(snapshot_id, None)
        self.calculate_revision_totals(revision_id=revision_id)
        return {"removed_line_ids": sorted(removed_ids)}

    def recalculate_draft_assembly(
        self,
        *,
        revision_id: str,
        expansion_run_id: str,
        labor_rate_set_id: str,
        actor: str,
    ) -> dict[str, Any]:
        row = self._require_expansion_run(expansion_run_id)
        if str(row.get("revision_id") or "") != revision_id:
            raise ValueError("Expansion run does not belong to revision")
        preview = self.preview_assembly_insertion(
            revision_id=revision_id,
            assembly_version_id=str(row.get("assembly_version_id") or ""),
            parent_quantity=float(
                dict(row.get("context") or {}).get("parent_quantity") or 1
            ),
            labor_rate_set_id=labor_rate_set_id,
            actor=actor,
            room_count=float(dict(row.get("context") or {}).get("room_count") or 1),
            system_count=float(dict(row.get("context") or {}).get("system_count") or 1),
            rack_count=float(dict(row.get("context") or {}).get("rack_count") or 1),
            channel_count=float(
                dict(row.get("context") or {}).get("channel_count") or 1
            ),
            endpoint_count=float(
                dict(row.get("context") or {}).get("endpoint_count") or 1
            ),
            optional_component_ids=list(
                dict(row.get("context") or {}).get("optional_component_ids") or []
            ),
        )
        comparison = self.compare_assembly_expansion(
            baseline_expansion_run_id=expansion_run_id,
            candidate_preview=preview,
        )
        refresh_id = f"assembly_refresh:{uuid.uuid4().hex[:12]}"
        self.state["assembly_refresh_previews"][refresh_id] = {
            "refresh_id": refresh_id,
            "revision_id": revision_id,
            "baseline_expansion_run_id": expansion_run_id,
            "candidate_preview": preview,
            "comparison": comparison,
            "created_by": actor,
            "created_at": self._now_iso(),
            "kind": "recalculate",
        }
        return deepcopy(self.state["assembly_refresh_previews"][refresh_id])

    def compare_assembly_expansion(
        self,
        *,
        baseline_expansion_run_id: str,
        candidate_preview: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_row = self._require_expansion_run(baseline_expansion_run_id)
        baseline_preview = dict(baseline_row.get("preview") or {})

        def _index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
            return {
                f"{str(item.get('parent_component_id') or '')}:{str(item.get('product_id') or item.get('labor_activity_id') or '')}": dict(
                    item
                )
                for item in list(items or [])
            }

        base = _index(list(baseline_preview.get("contributions") or []))
        cand = _index(list(candidate_preview.get("contributions") or []))
        added = sorted([key for key in cand if key not in base])
        removed = sorted([key for key in base if key not in cand])
        changed: list[dict[str, Any]] = []
        for key in sorted(set(base) & set(cand)):
            old_qty = Decimal(str(base[key].get("generated_quantity") or 0))
            new_qty = Decimal(str(cand[key].get("generated_quantity") or 0))
            if old_qty != new_qty:
                changed.append(
                    {
                        "component_key": key,
                        "old_quantity": float(old_qty),
                        "new_quantity": float(new_qty),
                        "delta": float(new_qty - old_qty),
                    }
                )
        return {
            "baseline_expansion_run_id": baseline_expansion_run_id,
            "candidate_expansion_run_id": str(
                candidate_preview.get("expansion_run_id") or "preview"
            ),
            "added_components": added,
            "removed_components": removed,
            "changed_components": changed,
            "material_delta_count": len(added) + len(removed) + len(changed),
            "labor_delta": self._labor_rollup_delta(
                dict(baseline_preview.get("labor_rollup") or {}),
                dict(candidate_preview.get("labor_rollup") or {}),
            ),
        }

    def upgrade_assembly_version(
        self,
        *,
        revision_id: str,
        expansion_run_id: str,
        target_assembly_version_id: str,
        labor_rate_set_id: str,
        actor: str,
    ) -> dict[str, Any]:
        row = self._require_expansion_run(expansion_run_id)
        preview = self.preview_assembly_insertion(
            revision_id=revision_id,
            assembly_version_id=target_assembly_version_id,
            parent_quantity=float(
                dict(row.get("context") or {}).get("parent_quantity") or 1
            ),
            labor_rate_set_id=labor_rate_set_id,
            actor=actor,
            room_count=float(dict(row.get("context") or {}).get("room_count") or 1),
            system_count=float(dict(row.get("context") or {}).get("system_count") or 1),
            rack_count=float(dict(row.get("context") or {}).get("rack_count") or 1),
            channel_count=float(
                dict(row.get("context") or {}).get("channel_count") or 1
            ),
            endpoint_count=float(
                dict(row.get("context") or {}).get("endpoint_count") or 1
            ),
            optional_component_ids=list(
                dict(row.get("context") or {}).get("optional_component_ids") or []
            ),
        )
        comparison = self.compare_assembly_expansion(
            baseline_expansion_run_id=expansion_run_id,
            candidate_preview=preview,
        )
        refresh_id = f"assembly_refresh:{uuid.uuid4().hex[:12]}"
        self.state["assembly_refresh_previews"][refresh_id] = {
            "refresh_id": refresh_id,
            "revision_id": revision_id,
            "baseline_expansion_run_id": expansion_run_id,
            "candidate_preview": preview,
            "comparison": comparison,
            "created_by": actor,
            "created_at": self._now_iso(),
            "kind": "upgrade_version",
            "target_assembly_version_id": target_assembly_version_id,
        }
        return deepcopy(self.state["assembly_refresh_previews"][refresh_id])

    def refresh_assembly_product_costs(
        self,
        *,
        revision_id: str,
        expansion_run_id: str,
        commercial_state: dict[str, Any],
        actor: str,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        expansion = self._require_expansion_run(expansion_run_id)
        parent_id = str(expansion.get("parent_line_item_id") or "")
        rows: list[dict[str, Any]] = []
        for line in list(revision.get("line_items") or []):
            item = dict(line)
            if str(item.get("parent_line_item_id") or "") != parent_id:
                continue
            if str(item.get("line_role") or "") != "generated_product_child":
                continue
            line_id = str(item.get("line_item_id") or "")
            preview = self.refresh_line_cost(
                revision_id=revision_id,
                line_item_id=line_id,
                commercial_state=commercial_state,
                actor=actor,
                accept=False,
            )
            rows.append(preview)
        refresh_id = f"assembly_refresh:{uuid.uuid4().hex[:12]}"
        self.state["assembly_refresh_previews"][refresh_id] = {
            "refresh_id": refresh_id,
            "revision_id": revision_id,
            "baseline_expansion_run_id": expansion_run_id,
            "created_by": actor,
            "created_at": self._now_iso(),
            "kind": "product_cost_refresh",
            "line_previews": rows,
        }
        return deepcopy(self.state["assembly_refresh_previews"][refresh_id])

    def refresh_assembly_labor_rates(
        self,
        *,
        revision_id: str,
        expansion_run_id: str,
        labor_rate_set_id: str,
        actor: str,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        expansion = self._require_expansion_run(expansion_run_id)
        parent_id = str(expansion.get("parent_line_item_id") or "")
        before = Decimal("0")
        after = Decimal("0")
        updates: list[dict[str, Any]] = []
        for line in list(revision.get("line_items") or []):
            item = dict(line)
            if str(item.get("parent_line_item_id") or "") != parent_id:
                continue
            if str(item.get("line_role") or "") != "generated_labor_child":
                continue
            labor_snapshot_id = str(item.get("labor_snapshot_id") or "")
            current = dict(
                self.state.get("labor_snapshots", {}).get(labor_snapshot_id) or {}
            )
            hours = Decimal(str(current.get("calculated_hours") or 0))
            unit_rate_before = Decimal(str(current.get("unit_rate") or 0))
            extended_before = Decimal(str(current.get("extended_labor_cost") or 0))
            before += extended_before
            refreshed = self._build_labor_snapshot_payload(
                revision_id=revision_id,
                parent_line_item_id=parent_id,
                line_item_id=str(item.get("line_item_id") or ""),
                labor_activity_id=str(current.get("labor_activity_id") or ""),
                labor_category=str(current.get("labor_category") or "installation"),
                assembly_id=str(item.get("assembly_id") or ""),
                assembly_version_id=str(item.get("assembly_version_id") or ""),
                assembly_component_id=str(item.get("assembly_component_id") or ""),
                driver_value=Decimal(str(current.get("driver_value") or 0)),
                calculated_hours=hours,
                labor_rate_set_id=labor_rate_set_id,
                expansion_run_id=str(item.get("expansion_run_id") or ""),
            )
            updates.append(
                {
                    "line_item_id": str(item.get("line_item_id") or ""),
                    "prior_snapshot_id": labor_snapshot_id,
                    "candidate_snapshot": refreshed,
                    "cost_delta": float(
                        Decimal(str(refreshed.get("extended_labor_cost") or 0))
                        - extended_before
                    ),
                    "unit_rate_delta": float(
                        Decimal(str(refreshed.get("unit_rate") or 0)) - unit_rate_before
                    ),
                }
            )
            after += Decimal(str(refreshed.get("extended_labor_cost") or 0))
        refresh_id = f"assembly_refresh:{uuid.uuid4().hex[:12]}"
        self.state["assembly_refresh_previews"][refresh_id] = {
            "refresh_id": refresh_id,
            "revision_id": revision_id,
            "baseline_expansion_run_id": expansion_run_id,
            "created_by": actor,
            "created_at": self._now_iso(),
            "kind": "labor_rate_refresh",
            "labor_rate_set_id": labor_rate_set_id,
            "updates": updates,
            "old_extended_labor_cost": float(before),
            "new_extended_labor_cost": float(after),
        }
        return deepcopy(self.state["assembly_refresh_previews"][refresh_id])

    def apply_assembly_refresh(
        self,
        *,
        refresh_id: str,
        actor: str,
        accept: bool,
        commercial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        preview = dict(
            self.state.get("assembly_refresh_previews", {}).get(refresh_id) or {}
        )
        if not preview:
            raise ValueError("Assembly refresh preview not found")
        if not accept:
            preview["accepted"] = False
            preview["resolved_at"] = self._now_iso()
            preview["resolved_by"] = actor
            self.state["assembly_refresh_previews"][refresh_id] = preview
            return deepcopy(preview)

        kind = str(preview.get("kind") or "")
        revision_id = str(preview.get("revision_id") or "")
        if kind == "product_cost_refresh":
            for line_preview in list(preview.get("line_previews") or []):
                result = dict(line_preview)
                line_id = str(
                    dict(result.get("refresh_result") or {}).get("line_item_id") or ""
                )
                if not line_id:
                    continue
                self.refresh_line_cost(
                    revision_id=revision_id,
                    line_item_id=line_id,
                    commercial_state=dict(commercial_state or {}),
                    actor=actor,
                    accept=True,
                )
        elif kind == "labor_rate_refresh":
            for update in list(preview.get("updates") or []):
                item = dict(update)
                candidate = dict(item.get("candidate_snapshot") or {})
                snapshot_id = str(candidate.get("labor_snapshot_id") or "")
                if snapshot_id:
                    self.state["labor_snapshots"][snapshot_id] = candidate
                line_id = str(item.get("line_item_id") or "")
                if line_id:
                    self._set_line_field(
                        revision_id=revision_id,
                        line_item_id=line_id,
                        field_name="labor_snapshot_id",
                        value=snapshot_id,
                    )
        elif kind in {"recalculate", "upgrade_version"}:
            baseline_run = str(preview.get("baseline_expansion_run_id") or "")
            baseline = self._require_expansion_run(baseline_run)
            self.remove_draft_assembly(
                revision_id=revision_id,
                parent_line_item_id=str(baseline.get("parent_line_item_id") or ""),
                actor=actor,
            )
            candidate = dict(preview.get("candidate_preview") or {})
            context = dict(
                self._require_expansion_run(baseline_run).get("context") or {}
            )
            self.add_assembly_to_revision(
                revision_id=revision_id,
                assembly_version_id=str(
                    candidate.get("assembly_version_id")
                    or str(baseline.get("assembly_version_id") or "")
                ),
                parent_quantity=float(context.get("parent_quantity") or 1),
                labor_rate_set_id=str(
                    preview.get("labor_rate_set_id")
                    or self._require_expansion_run(baseline_run).get(
                        "labor_rate_set_id"
                    )
                    or ""
                ),
                commercial_state=dict(commercial_state or {}),
                actor=actor,
                room_count=float(context.get("room_count") or 1),
                system_count=float(context.get("system_count") or 1),
                rack_count=float(context.get("rack_count") or 1),
                channel_count=float(context.get("channel_count") or 1),
                endpoint_count=float(context.get("endpoint_count") or 1),
                optional_component_ids=list(
                    context.get("optional_component_ids") or []
                ),
            )

        preview["accepted"] = True
        preview["resolved_at"] = self._now_iso()
        preview["resolved_by"] = actor
        self.state["assembly_refresh_previews"][refresh_id] = preview
        self.calculate_revision_totals(revision_id=revision_id)
        self.validate_revision(revision_id=revision_id)
        return deepcopy(preview)

    def override_assembly_component(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
        adjusted_quantity: float,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Override reason is required")
        revision = self._require_mutable_revision(revision_id)
        _ = revision
        line = self._require_line_item(
            self._require_revision(revision_id), line_item_id
        )
        original_value = float(line.get("requested_quantity") or 0)
        updated = self.update_draft_line_item(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            updates={
                "requested_quantity": adjusted_quantity,
                "engineering_quantity": adjusted_quantity,
                "procurement_quantity": adjusted_quantity,
            },
        )
        self._append_adjustment(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            reason=reason,
            original_value=original_value,
            adjusted_value=adjusted_quantity,
            kind="component_quantity_override",
        )
        self.calculate_revision_totals(revision_id=revision_id)
        return updated

    def exclude_assembly_component(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Override reason is required")
        self._set_line_field(
            revision_id=revision_id,
            line_item_id=line_item_id,
            field_name="excluded",
            value=True,
        )
        self._append_adjustment(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            reason=reason,
            original_value=False,
            adjusted_value=True,
            kind="component_exclusion",
        )
        self.calculate_revision_totals(revision_id=revision_id)
        return self._require_line_item(
            self._require_revision(revision_id), line_item_id
        )

    def include_optional_accessory(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Override reason is required")
        self._set_line_field(
            revision_id=revision_id,
            line_item_id=line_item_id,
            field_name="optional_accessory_decision",
            value="included",
        )
        self._append_adjustment(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            reason=reason,
            original_value="excluded",
            adjusted_value="included",
            kind="optional_accessory_inclusion",
        )
        return self._require_line_item(
            self._require_revision(revision_id), line_item_id
        )

    def exclude_optional_accessory(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Override reason is required")
        self._set_line_field(
            revision_id=revision_id,
            line_item_id=line_item_id,
            field_name="optional_accessory_decision",
            value="excluded",
        )
        self._append_adjustment(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            reason=reason,
            original_value="included",
            adjusted_value="excluded",
            kind="optional_accessory_exclusion",
        )
        return self._require_line_item(
            self._require_revision(revision_id), line_item_id
        )

    def override_labor_hours(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
        adjusted_hours: float,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Override reason is required")
        line = self._require_line_item(
            self._require_revision(revision_id), line_item_id
        )
        labor_snapshot_id = str(line.get("labor_snapshot_id") or "")
        if not labor_snapshot_id:
            raise ValueError("Labor snapshot not found for line")
        snapshot = dict(
            self.state.get("labor_snapshots", {}).get(labor_snapshot_id) or {}
        )
        if not snapshot:
            raise ValueError("Labor snapshot payload not found")
        unit_rate = Decimal(str(snapshot.get("unit_rate") or 0))
        snapshot["calculated_hours"] = float(Decimal(str(adjusted_hours)))
        snapshot["extended_labor_cost"] = float(
            unit_rate * Decimal(str(adjusted_hours))
        )
        snapshot["updated_at"] = self._now_iso()
        self.state["labor_snapshots"][labor_snapshot_id] = snapshot
        self.update_draft_line_item(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            updates={
                "requested_quantity": adjusted_hours,
                "engineering_quantity": adjusted_hours,
                "procurement_quantity": adjusted_hours,
            },
        )
        self._append_adjustment(
            revision_id=revision_id,
            line_item_id=line_item_id,
            actor=actor,
            reason=reason,
            original_value=float(line.get("requested_quantity") or 0),
            adjusted_value=adjusted_hours,
            kind="labor_hours_override",
        )
        self.calculate_revision_totals(revision_id=revision_id)
        return deepcopy(snapshot)

    def replay_assembly_expansion(self, *, expansion_run_id: str) -> dict[str, Any]:
        return deepcopy(self._require_expansion_run(expansion_run_id))

    def inspect_assembly_provenance(
        self,
        *,
        revision_id: str,
        parent_line_item_id: str,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        lines = [
            dict(item)
            for item in list(revision.get("line_items") or [])
            if str(item.get("line_item_id") or "") == parent_line_item_id
            or str(item.get("parent_line_item_id") or "") == parent_line_item_id
        ]
        run_ids = {
            str(item.get("expansion_run_id") or "")
            for item in lines
            if str(item.get("expansion_run_id") or "")
        }
        expansions = [
            deepcopy(dict(self.state.get("assembly_expansions", {}).get(run_id) or {}))
            for run_id in sorted(run_ids)
        ]
        labor_snapshots = [
            deepcopy(
                dict(
                    self.state.get("labor_snapshots", {}).get(
                        str(item.get("labor_snapshot_id") or ""),
                        {},
                    )
                    or {}
                )
            )
            for item in lines
            if str(item.get("labor_snapshot_id") or "")
        ]
        return {
            "revision_id": revision_id,
            "parent_line_item_id": parent_line_item_id,
            "lines": lines,
            "expansions": expansions,
            "labor_snapshots": labor_snapshots,
        }

    def create_cost_snapshot(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        selection: CostSelectionResult,
    ) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        line = self._require_line_item(revision, line_item_id)
        selected = selection.selected_candidate
        provenance = selection.provenance
        product_id = str(line.get("product_id") or selection.request.product_id)
        source_currency = str(selection.request.currency)
        source_unit_cost = selection.selected_source_unit_cost
        effective_unit_cost = selection.effective_per_unit_cost
        requested_quantity = selection.normalized_requested_quantity
        purchasable_quantity = selection.purchasable_quantity
        package_count = int(selection.package_count)
        excess_quantity = max(
            0.0,
            float(
                selection.purchasable_quantity - selection.normalized_requested_quantity
            ),
        )
        extended_acquisition_cost = selection.extended_acquisition_cost
        selection_rule = selection.selection_rule
        selection_timestamp = selection.selection_timestamp or self._now_iso()
        tie_break_sequence = list(selection.tie_break_sequence)
        confidence_score = float(selection.deterministic_confidence)
        confidence_breakdown = dict(selection.confidence_breakdown)
        diagnostics = [item.to_dict() for item in list(selection.diagnostics)]
        source_filename = "" if provenance is None else provenance.source_filename
        source_file_hash = "" if provenance is None else provenance.source_file_hash
        source_reference = "" if provenance is None else provenance.source_reference
        import_timestamp = "" if provenance is None else provenance.import_timestamp
        effective_date = "" if provenance is None else provenance.effective_date
        expiration_date = "" if provenance is None else provenance.expiration_date
        purchasing_channel = str(selection.request.preferred_purchasing_channel)
        reference_obj = SnapshotReference(
            vendor_id="" if selected is None else str(selected.vendor),
            vendor_offering_id=(
                "" if selected is None else str(selected.vendor_offering_id)
            ),
            price_sheet_id="" if selected is None else str(selected.price_sheet_id),
            price_sheet_version_id=(
                "" if selected is None else str(selected.price_sheet_version_id)
            ),
            price_record_id="" if selected is None else str(selected.price_record_id),
        )

        snapshot_input = {
            "revision_id": revision_id,
            "line_item_id": line_item_id,
            "product_id": product_id,
            "source_currency": source_currency,
            "source_unit_cost": source_unit_cost,
            "effective_unit_cost": effective_unit_cost,
            "requested_quantity": requested_quantity,
            "purchasable_quantity": purchasable_quantity,
            "package_count": package_count,
            "excess_quantity": excess_quantity,
            "extended_acquisition_cost": extended_acquisition_cost,
            "selection_rule": selection_rule,
            "selection_timestamp": selection_timestamp,
            "tie_break_sequence": tie_break_sequence,
            "confidence_score": confidence_score,
            "confidence_breakdown": confidence_breakdown,
            "diagnostics": diagnostics,
            "source_filename": source_filename,
            "source_file_hash": source_file_hash,
            "source_reference": source_reference,
            "import_timestamp": import_timestamp,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "purchasing_channel": purchasing_channel,
            "cost_engine_ruleset_version": DeterministicCostEngine.POLICY_VERSION,
            "estimate_ruleset_version": self.ESTIMATE_RULESET_VERSION,
            "snapshot_schema_version": self.SNAPSHOT_SCHEMA_VERSION,
            "reference": reference_obj.to_dict(),
        }
        digest = hashlib.sha1(
            json.dumps(snapshot_input, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        snapshot = CostSnapshot(
            cost_snapshot_id=f"snapshot:{line_item_id}:{digest}",
            estimate_id=str(revision.get("estimate_id")),
            revision_id=revision_id,
            line_item_id=line_item_id,
            product_id=product_id,
            source_currency=source_currency,
            source_unit_cost=(
                None if source_unit_cost is None else Decimal(str(source_unit_cost))
            ),
            effective_unit_cost=(
                None
                if effective_unit_cost is None
                else Decimal(str(effective_unit_cost))
            ),
            requested_quantity=Decimal(str(requested_quantity)),
            purchasable_quantity=Decimal(str(purchasable_quantity)),
            package_count=package_count,
            excess_quantity=Decimal(str(excess_quantity)),
            extended_acquisition_cost=Decimal(str(extended_acquisition_cost)),
            selection_rule=selection_rule,
            selection_timestamp=selection_timestamp,
            tie_break_sequence=tie_break_sequence,
            confidence_score=confidence_score,
            confidence_breakdown=confidence_breakdown,
            diagnostics=diagnostics,
            source_filename=source_filename,
            source_file_hash=source_file_hash,
            source_reference=source_reference,
            import_timestamp=import_timestamp,
            effective_date=effective_date,
            expiration_date=expiration_date,
            purchasing_channel=purchasing_channel,
            cost_engine_ruleset_version=DeterministicCostEngine.POLICY_VERSION,
            estimate_ruleset_version=self.ESTIMATE_RULESET_VERSION,
            snapshot_schema_version=self.SNAPSHOT_SCHEMA_VERSION,
            reference=reference_obj,
            created_at=self._now_iso(),
        )
        self.state["cost_snapshots"][snapshot.cost_snapshot_id] = snapshot.to_dict()
        return deepcopy(snapshot.to_dict())

    def select_line_cost(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        commercial_state: dict[str, Any],
        actor: str,
        manual_price_record_id: str = "",
        manual_reason: str = "",
        as_of_date: str = "",
    ) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        line = self._require_line_item(revision, line_item_id)
        product_id = self._line_product_id(line)
        if not as_of_date:
            as_of_date = self._now_iso()[:10]
        request = {
            "product_id": product_id,
            "requested_quantity": float(line.get("requested_quantity") or 0.0),
            "as_of_date": as_of_date,
            "currency": "USD",
            "manual_price_record_id": manual_price_record_id,
        }
        result = DeterministicCostEngine().select_cost(
            request,
            commercial_state=commercial_state,
        )
        snapshot = self.create_cost_snapshot(
            revision_id=revision_id,
            line_item_id=line_item_id,
            selection=result,
        )

        items = [dict(item) for item in list(revision.get("line_items") or [])]
        for idx, item in enumerate(items):
            if str(item.get("line_item_id")) != line_item_id:
                continue
            item["selected_cost_snapshot_id"] = snapshot["cost_snapshot_id"]
            item["source_selection_status"] = result.status.value
            if manual_price_record_id:
                if not manual_reason.strip():
                    raise ValueError("Manual selection requires reason")
                metadata = ManualSelectionMetadata(
                    reason=manual_reason,
                    actor=actor,
                    timestamp=self._now_iso(),
                    prior_automatic_price_record_id=str(
                        (
                            result.selected_candidate.price_record_id
                            if result.selected_candidate
                            else ""
                        )
                    ),
                )
                item["manual_selection_metadata"] = metadata.to_dict()
            item["updated_at"] = self._now_iso()
            items[idx] = item
            break
        revision["line_items"] = items
        revision["updated_by"] = actor
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        return {
            "selection": result.to_dict(),
            "snapshot": snapshot,
        }

    def refresh_line_cost(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        commercial_state: dict[str, Any],
        actor: str,
        accept: bool,
        as_of_date: str = "",
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        working_revision_id = revision_id
        if revision.get("state") == EstimateRevisionState.LOCKED.value:
            cloned = self.clone_revision(
                source_revision_id=revision_id,
                created_by=actor,
                reason="Refresh from locked revision",
            )
            working_revision_id = str(cloned.get("revision_id"))

        working_revision = self._require_mutable_revision(working_revision_id)
        line = self._require_line_item(working_revision, line_item_id)
        prior_snapshot_id = str(line.get("selected_cost_snapshot_id") or "")

        selection_payload = self.select_line_cost(
            revision_id=working_revision_id,
            line_item_id=line_item_id,
            commercial_state=commercial_state,
            actor=actor,
            as_of_date=as_of_date,
        )
        candidate_snapshot = dict(selection_payload["snapshot"])

        if not accept:
            # Roll back line snapshot pointer while retaining immutable snapshot history.
            items = [
                dict(item) for item in list(working_revision.get("line_items") or [])
            ]
            for idx, item in enumerate(items):
                if str(item.get("line_item_id")) == line_item_id:
                    item["selected_cost_snapshot_id"] = prior_snapshot_id
                    items[idx] = item
                    break
            working_revision["line_items"] = items
            self.state["revisions"][working_revision_id] = working_revision

        old_snapshot = self.state["cost_snapshots"].get(prior_snapshot_id, {})
        comparison = self.compare_cost_snapshots(
            baseline_snapshot_id=prior_snapshot_id,
            candidate_snapshot_id=str(candidate_snapshot.get("cost_snapshot_id")),
        )
        refresh = CostRefreshResult(
            line_item_id=line_item_id,
            prior_snapshot_id=prior_snapshot_id,
            candidate_snapshot_id=str(candidate_snapshot.get("cost_snapshot_id")),
            accepted=accept,
            comparison=comparison,
        )
        self.state["refresh_results"].setdefault(working_revision_id, []).append(
            refresh.to_dict()
        )

        return {
            "working_revision_id": working_revision_id,
            "accepted": accept,
            "previous_snapshot": deepcopy(old_snapshot),
            "candidate_snapshot": deepcopy(candidate_snapshot),
            "refresh_result": refresh.to_dict(),
        }

    def refresh_revision_costs(
        self,
        *,
        revision_id: str,
        commercial_state: dict[str, Any],
        actor: str,
        accept: bool,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        line_ids = [
            str(item.get("line_item_id"))
            for item in list(revision.get("line_items") or [])
        ]
        results: list[dict[str, Any]] = []
        working_revision_id = revision_id
        for line_id in line_ids:
            output = self.refresh_line_cost(
                revision_id=working_revision_id,
                line_item_id=line_id,
                commercial_state=commercial_state,
                actor=actor,
                accept=accept,
            )
            working_revision_id = str(output.get("working_revision_id"))
            results.append(output)
        return {
            "working_revision_id": working_revision_id,
            "line_results": results,
        }

    def compare_cost_snapshots(
        self,
        *,
        baseline_snapshot_id: str,
        candidate_snapshot_id: str,
    ) -> dict[str, Any]:
        baseline = dict(self.state["cost_snapshots"].get(baseline_snapshot_id) or {})
        candidate = dict(self.state["cost_snapshots"].get(candidate_snapshot_id) or {})
        return {
            "unit_cost_delta": float(
                Decimal(str(candidate.get("effective_unit_cost") or 0))
                - Decimal(str(baseline.get("effective_unit_cost") or 0))
            ),
            "extended_cost_delta": float(
                Decimal(str(candidate.get("extended_acquisition_cost") or 0))
                - Decimal(str(baseline.get("extended_acquisition_cost") or 0))
            ),
            "vendor_changed": (
                str(dict(candidate.get("reference") or {}).get("vendor_id") or "")
                != str(dict(baseline.get("reference") or {}).get("vendor_id") or "")
            ),
            "vendor_offering_changed": (
                str(
                    dict(candidate.get("reference") or {}).get("vendor_offering_id")
                    or ""
                )
                != str(
                    dict(baseline.get("reference") or {}).get("vendor_offering_id")
                    or ""
                )
            ),
            "price_record_changed": (
                str(dict(candidate.get("reference") or {}).get("price_record_id") or "")
                != str(
                    dict(baseline.get("reference") or {}).get("price_record_id") or ""
                )
            ),
            "confidence_delta": float(
                Decimal(str(candidate.get("confidence_score") or 0))
                - Decimal(str(baseline.get("confidence_score") or 0))
            ),
        }

    def calculate_revision_totals(self, *, revision_id: str) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        snapshots = self.state["cost_snapshots"]
        acquisition_total = Decimal("0")
        unresolved_total = Decimal("0")
        unresolved_material_total = Decimal("0")
        unresolved_labor_total = Decimal("0")
        generated_material_total = Decimal("0")
        generated_labor_total = Decimal("0")
        allowance_total = Decimal("0")
        excluded_total = Decimal("0")
        assembly_count = 0
        generated_product_line_count = 0
        generated_labor_line_count = 0
        section_subtotals: dict[str, Decimal] = {}
        system_subtotals: dict[str, Decimal] = {}
        room_subtotals: dict[str, Decimal] = {}
        warning_counts: dict[str, int] = {
            EstimateDiagnosticSeverity.ERROR.value: 0,
            EstimateDiagnosticSeverity.WARNING.value: 0,
            EstimateDiagnosticSeverity.INFORMATIONAL.value: 0,
        }

        for item in list(revision.get("line_items") or []):
            line = dict(item)
            line_role = str(line.get("line_role") or "standard_product")
            if bool(line.get("excluded", False)):
                excluded_total += Decimal(str(line.get("requested_quantity") or 0))
                continue
            if line_role == "assembly_parent":
                assembly_count += 1
            snapshot_id = str(line.get("selected_cost_snapshot_id") or "")
            section_key = str(line.get("section") or "unassigned")
            system_key = str(line.get("system") or "unassigned")
            room_key = str(line.get("room") or "unassigned")

            if line_role == "generated_labor_child":
                generated_labor_line_count += 1
                labor_snapshot_id = str(line.get("labor_snapshot_id") or "")
                labor_snapshot = dict(
                    self.state.get("labor_snapshots", {}).get(labor_snapshot_id) or {}
                )
                if not labor_snapshot_id or not labor_snapshot:
                    unresolved_total += Decimal(
                        str(line.get("requested_quantity") or 0)
                    )
                    unresolved_labor_total += Decimal(
                        str(line.get("requested_quantity") or 0)
                    )
                    continue
                labor_cost = Decimal(
                    str(labor_snapshot.get("extended_labor_cost") or 0)
                )
                generated_labor_total += labor_cost
                acquisition_total += labor_cost
                section_subtotals[section_key] = (
                    section_subtotals.get(section_key, Decimal("0")) + labor_cost
                )
                system_subtotals[system_key] = (
                    system_subtotals.get(system_key, Decimal("0")) + labor_cost
                )
                room_subtotals[room_key] = (
                    room_subtotals.get(room_key, Decimal("0")) + labor_cost
                )
                continue

            if not snapshot_id:
                unresolved_total += Decimal(str(line.get("requested_quantity") or 0))
                unresolved_material_total += Decimal(
                    str(line.get("requested_quantity") or 0)
                )
                continue
            snapshot = dict(snapshots.get(snapshot_id) or {})
            line_total = Decimal(str(snapshot.get("extended_acquisition_cost") or 0))
            acquisition_total += line_total
            if line_role == "generated_product_child":
                generated_product_line_count += 1
                generated_material_total += line_total
            if line_role == "generated_allowance_child":
                allowance_total += line_total
            section_subtotals[section_key] = (
                section_subtotals.get(section_key, Decimal("0")) + line_total
            )
            system_subtotals[system_key] = (
                system_subtotals.get(system_key, Decimal("0")) + line_total
            )
            room_subtotals[room_key] = (
                room_subtotals.get(room_key, Decimal("0")) + line_total
            )

        diagnostics = [dict(item) for item in list(revision.get("diagnostics") or [])]
        for diag in diagnostics:
            severity = str(
                diag.get("severity") or EstimateDiagnosticSeverity.INFORMATIONAL.value
            )
            warning_counts[severity] = int(warning_counts.get(severity, 0)) + 1

        line_count = len(list(revision.get("line_items") or []))
        resolved_count = sum(
            1
            for item in list(revision.get("line_items") or [])
            if str(item.get("selected_cost_snapshot_id") or "")
        )
        confidence = 0.0 if line_count == 0 else round(resolved_count / line_count, 4)

        totals = EstimateTotals(
            acquisition_cost_total=acquisition_total,
            generated_material_acquisition_cost=generated_material_total,
            generated_labor_cost=generated_labor_total,
            allowance_cost_total=allowance_total,
            unresolved_cost_total=unresolved_total,
            unresolved_material_total=unresolved_material_total,
            unresolved_labor_total=unresolved_labor_total,
            material_subtotal=generated_material_total
            + (acquisition_total - generated_labor_total - generated_material_total),
            labor_subtotal=generated_labor_total,
            excluded_line_total=excluded_total,
            assembly_count=assembly_count,
            generated_product_line_count=generated_product_line_count,
            generated_labor_line_count=generated_labor_line_count,
            diagnostic_counts=warning_counts,
            readiness_summary={
                "has_unresolved_material": unresolved_material_total > 0,
                "has_unresolved_labor": unresolved_labor_total > 0,
                "diagnostic_blocking_count": sum(
                    1 for item in diagnostics if bool(item.get("blocking"))
                ),
            },
            section_subtotals=section_subtotals,
            system_subtotals=system_subtotals,
            room_subtotals=room_subtotals,
            warning_counts=warning_counts,
            confidence_summary={
                "line_count": line_count,
                "resolved_line_count": resolved_count,
                "coverage": confidence,
            },
        )
        revision["totals"] = totals.to_dict()
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        return deepcopy(totals.to_dict())

    def validate_revision(self, *, revision_id: str) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        diagnostics: list[EstimateDiagnostic] = []
        for line in list(revision.get("line_items") or []):
            line_item = dict(line)
            line_id = str(line_item.get("line_item_id") or "")
            quantity = Decimal(str(line_item.get("requested_quantity") or 0))
            if quantity <= 0:
                diagnostics.append(
                    EstimateDiagnostic(
                        code="invalid_quantity",
                        severity=EstimateDiagnosticSeverity.ERROR,
                        message="Requested quantity must be greater than zero.",
                        scope="line",
                        blocking=True,
                        line_item_id=line_id,
                    )
                )
            product_id = str(line_item.get("product_id") or "")
            if not product_id:
                diagnostics.append(
                    EstimateDiagnostic(
                        code="missing_product_reference",
                        severity=EstimateDiagnosticSeverity.ERROR,
                        message="Missing product reference.",
                        scope="line",
                        blocking=True,
                        line_item_id=line_id,
                    )
                )
            line_role = str(line_item.get("line_role") or "standard_product")
            snapshot_id = str(line_item.get("selected_cost_snapshot_id") or "")
            if line_role in {
                "generated_labor_child",
                "assembly_parent",
                "informational_child",
            }:
                snapshot_id = snapshot_id
            elif not snapshot_id:
                diagnostics.append(
                    EstimateDiagnostic(
                        code="missing_snapshot",
                        severity=EstimateDiagnosticSeverity.ERROR,
                        message="Missing cost snapshot on priced-required line.",
                        scope="line",
                        blocking=True,
                        line_item_id=line_id,
                    )
                )
            else:
                snapshot = dict(self.state["cost_snapshots"].get(snapshot_id) or {})
                reference = dict(snapshot.get("reference") or {})
                required_ref = [
                    "price_sheet_version_id",
                    "price_record_id",
                    "vendor_offering_id",
                ]
                if any(not str(reference.get(key) or "") for key in required_ref):
                    diagnostics.append(
                        EstimateDiagnostic(
                            code="missing_required_provenance",
                            severity=EstimateDiagnosticSeverity.ERROR,
                            message="Snapshot provenance missing required immutable references.",
                            scope="line",
                            blocking=True,
                            line_item_id=line_id,
                        )
                    )
            if line_role == "generated_labor_child":
                labor_snapshot_id = str(line_item.get("labor_snapshot_id") or "")
                if not labor_snapshot_id:
                    diagnostics.append(
                        EstimateDiagnostic(
                            code="missing_labor_snapshot",
                            severity=EstimateDiagnosticSeverity.ERROR,
                            message="Missing immutable labor snapshot for generated labor line.",
                            scope="line",
                            blocking=True,
                            line_item_id=line_id,
                        )
                    )
                else:
                    labor_snapshot = dict(
                        self.state.get("labor_snapshots", {}).get(labor_snapshot_id)
                        or {}
                    )
                    if not labor_snapshot:
                        diagnostics.append(
                            EstimateDiagnostic(
                                code="missing_labor_snapshot",
                                severity=EstimateDiagnosticSeverity.ERROR,
                                message="Labor snapshot reference is not resolvable.",
                                scope="line",
                                blocking=True,
                                line_item_id=line_id,
                            )
                        )
                    if not str(labor_snapshot.get("labor_rate_record_id") or ""):
                        diagnostics.append(
                            EstimateDiagnostic(
                                code="missing_labor_rate",
                                severity=EstimateDiagnosticSeverity.ERROR,
                                message="Labor snapshot is missing labor rate selection.",
                                scope="line",
                                blocking=True,
                                line_item_id=line_id,
                            )
                        )

            if line_role in {"generated_product_child", "generated_labor_child"}:
                if not str(line_item.get("assembly_version_id") or "") or not str(
                    line_item.get("assembly_component_id") or ""
                ):
                    diagnostics.append(
                        EstimateDiagnostic(
                            code="incomplete_assembly_provenance",
                            severity=EstimateDiagnosticSeverity.ERROR,
                            message="Generated line is missing assembly provenance fields.",
                            scope="line",
                            blocking=True,
                            line_item_id=line_id,
                        )
                    )
            metadata = line_item.get("manual_selection_metadata")
            if metadata:
                reason = str(dict(metadata).get("reason") or "").strip()
                if not reason:
                    diagnostics.append(
                        EstimateDiagnostic(
                            code="manual_selection_missing_reason",
                            severity=EstimateDiagnosticSeverity.ERROR,
                            message="Manual source selection requires reason.",
                            scope="line",
                            blocking=True,
                            line_item_id=line_id,
                        )
                    )

        totals = self.calculate_revision_totals(revision_id=revision_id)
        has_blocking = any(item.blocking for item in diagnostics)
        revision["diagnostics"] = [item.to_dict() for item in diagnostics]
        revision["totals"] = totals
        if revision.get("state") in {
            EstimateRevisionState.LOCKED.value,
            EstimateRevisionState.SUPERSEDED.value,
            EstimateRevisionState.ARCHIVED.value,
        }:
            pass
        else:
            revision["state"] = (
                EstimateRevisionState.DRAFT.value
                if has_blocking
                else EstimateRevisionState.READY.value
            )
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        return {
            "diagnostics": deepcopy(revision["diagnostics"]),
            "ready": not has_blocking,
            "state": revision.get("state"),
        }

    def lock_revision(self, *, revision_id: str, actor: str) -> dict[str, Any]:
        revision = self._require_mutable_revision(revision_id)
        validation = self.validate_revision(revision_id=revision_id)
        if not bool(validation.get("ready")):
            raise ValueError("Revision is not lock-ready")
        revision = self._require_revision(revision_id)
        revision["state"] = EstimateRevisionState.LOCKED.value
        revision["locked_by"] = actor
        revision["locked_at"] = self._now_iso()
        revision["updated_by"] = actor
        revision["updated_at"] = self._now_iso()
        self.state["revisions"][revision_id] = revision
        return deepcopy(revision)

    def replay_revision(self, *, revision_id: str) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        line_snapshots: list[dict[str, Any]] = []
        for line in list(revision.get("line_items") or []):
            snapshot_id = str(line.get("selected_cost_snapshot_id") or "")
            if not snapshot_id:
                continue
            line_snapshots.append(
                deepcopy(dict(self.state["cost_snapshots"].get(snapshot_id) or {}))
            )
        return {
            "revision": deepcopy(revision),
            "snapshots": line_snapshots,
            "totals": deepcopy(revision.get("totals")),
            "diagnostics": deepcopy(revision.get("diagnostics")),
        }

    def reselection_preview(
        self,
        *,
        revision_id: str,
        commercial_state: dict[str, Any],
        as_of_date: str,
    ) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        preview: list[dict[str, Any]] = []
        for line in list(revision.get("line_items") or []):
            line_id = str(line.get("line_item_id") or "")
            prior_snapshot_id = str(line.get("selected_cost_snapshot_id") or "")
            product_id = self._line_product_id(line)
            request = {
                "product_id": product_id,
                "requested_quantity": float(line.get("requested_quantity") or 0.0),
                "as_of_date": as_of_date,
                "currency": "USD",
                "manual_price_record_id": "",
            }
            result = DeterministicCostEngine().select_cost(
                request,
                commercial_state=commercial_state,
            )
            selected = result.selected_candidate
            candidate_snapshot_ref = SnapshotReference(
                vendor_id="" if selected is None else str(selected.vendor),
                vendor_offering_id=(
                    "" if selected is None else str(selected.vendor_offering_id)
                ),
                price_sheet_id="" if selected is None else str(selected.price_sheet_id),
                price_sheet_version_id=(
                    "" if selected is None else str(selected.price_sheet_version_id)
                ),
                price_record_id=(
                    "" if selected is None else str(selected.price_record_id)
                ),
            ).to_dict()
            baseline_snapshot = dict(
                self.state["cost_snapshots"].get(prior_snapshot_id) or {}
            )
            baseline_ref = dict(baseline_snapshot.get("reference") or {})
            comparison = {
                "unit_cost_delta": float(
                    Decimal(str(result.effective_per_unit_cost or 0))
                    - Decimal(str(baseline_snapshot.get("effective_unit_cost") or 0))
                ),
                "extended_cost_delta": float(
                    Decimal(str(result.extended_acquisition_cost or 0))
                    - Decimal(
                        str(baseline_snapshot.get("extended_acquisition_cost") or 0)
                    )
                ),
                "vendor_changed": (
                    str(candidate_snapshot_ref.get("vendor_id") or "")
                    != str(baseline_ref.get("vendor_id") or "")
                ),
                "vendor_offering_changed": (
                    str(candidate_snapshot_ref.get("vendor_offering_id") or "")
                    != str(baseline_ref.get("vendor_offering_id") or "")
                ),
                "price_record_changed": (
                    str(candidate_snapshot_ref.get("price_record_id") or "")
                    != str(baseline_ref.get("price_record_id") or "")
                ),
                "confidence_delta": float(
                    Decimal(str(result.deterministic_confidence or 0))
                    - Decimal(str(baseline_snapshot.get("confidence_score") or 0))
                ),
            }
            preview.append(
                {
                    "line_item_id": line_id,
                    "refresh_result": {
                        "line_item_id": line_id,
                        "prior_snapshot_id": prior_snapshot_id,
                        "candidate_snapshot_id": "preview-only",
                        "accepted": False,
                        "comparison": comparison,
                    },
                }
            )
        return {
            "revision_id": revision_id,
            "as_of_date": as_of_date,
            "line_previews": preview,
        }

    def compare_revisions(
        self,
        *,
        baseline_revision_id: str,
        comparison_revision_id: str,
    ) -> dict[str, Any]:
        baseline = self._require_revision(baseline_revision_id)
        comparison = self._require_revision(comparison_revision_id)
        base_lines = {
            str(item.get("line_item_id")): dict(item)
            for item in list(baseline.get("line_items") or [])
        }
        cmp_lines = {
            str(item.get("line_item_id")): dict(item)
            for item in list(comparison.get("line_items") or [])
        }
        added = sorted([key for key in cmp_lines if key not in base_lines])
        removed = sorted([key for key in base_lines if key not in cmp_lines])
        changed: list[dict[str, Any]] = []
        for line_id in sorted(set(base_lines) & set(cmp_lines)):
            base_snapshot = str(
                base_lines[line_id].get("selected_cost_snapshot_id") or ""
            )
            cmp_snapshot = str(
                cmp_lines[line_id].get("selected_cost_snapshot_id") or ""
            )
            if base_snapshot != cmp_snapshot:
                changed.append(
                    {
                        "line_item_id": line_id,
                        "baseline_snapshot_id": base_snapshot,
                        "comparison_snapshot_id": cmp_snapshot,
                        "snapshot_delta": (
                            self.compare_cost_snapshots(
                                baseline_snapshot_id=base_snapshot,
                                candidate_snapshot_id=cmp_snapshot,
                            )
                            if base_snapshot and cmp_snapshot
                            else {}
                        ),
                    }
                )
        payload = RevisionComparison(
            baseline_revision_id=baseline_revision_id,
            comparison_revision_id=comparison_revision_id,
            added_lines=added,
            removed_lines=removed,
            changed_lines=changed,
        ).to_dict()
        key = f"{baseline_revision_id}::{comparison_revision_id}"
        self.state["revision_comparisons"][key] = payload
        return deepcopy(payload)

    def list_revision_history(self, *, estimate_id: str) -> list[dict[str, Any]]:
        estimate = self._require_estimate(estimate_id)
        rows = [
            deepcopy(dict(self.state["revisions"].get(revision_id) or {}))
            for revision_id in list(estimate.get("revision_ids") or [])
        ]
        rows.sort(key=lambda item: int(item.get("revision_number") or 0))
        return rows

    def mission_control_readiness(self, *, estimate_id: str) -> dict[str, Any]:
        history = self.list_revision_history(estimate_id=estimate_id)
        recommendations: list[str] = []
        if not history:
            recommendations.append("No estimate revisions exist.")
            return {"ready": False, "recommendations": recommendations}
        latest = history[-1]
        state = str(latest.get("state") or "")
        diagnostics = list(latest.get("diagnostics") or [])
        has_blocking = any(bool(item.get("blocking")) for item in diagnostics)
        if has_blocking:
            recommendations.append("Estimate has blocking diagnostics.")
        if state == EstimateRevisionState.DRAFT.value:
            recommendations.append("Draft revision should be validated.")
        if state == EstimateRevisionState.READY.value:
            recommendations.append("Revision is ready to lock.")
        if state == EstimateRevisionState.LOCKED.value:
            recommendations.append("Locked revision is replay-ready.")

        for line in list(latest.get("line_items") or []):
            status = str(line.get("source_selection_status") or "")
            if status in {"expired_cost_only", "future_cost_only", "no_eligible_cost"}:
                recommendations.append(
                    f"Line {line.get('line_item_id')} requires cost refresh."
                )

        diagnostics_by_code = {
            str(item.get("code") or ""): dict(item)
            for item in list(latest.get("diagnostics") or [])
        }
        code_to_text = {
            "missing_labor_rate": "Generated labor line has no eligible labor rate.",
            "missing_labor_snapshot": "Generated labor line is missing immutable labor snapshot.",
            "incomplete_assembly_provenance": "Generated assembly lines are missing provenance fields.",
            "circular_assembly_reference": "Circular assembly reference detected.",
            "invalid_optional_selection": "Optional accessory decision requires review.",
        }
        for code, text in code_to_text.items():
            if code in diagnostics_by_code:
                recommendations.append(text)

        if any(
            bool(item.get("refresh_pending"))
            for item in list(self.state.get("assembly_expansions", {}).values())
            if str(item.get("revision_id") or "")
            == str(latest.get("revision_id") or "")
        ):
            recommendations.append("Estimate revision has stale assembly expansion.")

        return {
            "ready": not has_blocking
            and state
            in {
                EstimateRevisionState.READY.value,
                EstimateRevisionState.LOCKED.value,
            },
            "state": state,
            "recommendations": sorted(set(recommendations)),
        }

    def _assembly_service(self) -> AssemblyExpansionService:
        return AssemblyExpansionService(
            state=dict(self.state.get("assembly_state") or {})
        )

    def _persist_assembly_service(self, service: AssemblyExpansionService) -> None:
        self.state["assembly_state"] = service.to_dict()

    def _require_expansion_run(self, expansion_run_id: str) -> dict[str, Any]:
        row = dict(
            self.state.get("assembly_expansions", {}).get(expansion_run_id) or {}
        )
        if not row:
            raise ValueError("Assembly expansion run not found")
        return row

    def _set_line_field(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        field_name: str,
        value: Any,
    ) -> None:
        revision = self._require_mutable_revision(revision_id)
        rows = [dict(item) for item in list(revision.get("line_items") or [])]
        for idx, item in enumerate(rows):
            if str(item.get("line_item_id") or "") != line_item_id:
                continue
            item[field_name] = value
            item["updated_at"] = self._now_iso()
            rows[idx] = item
            revision["line_items"] = rows
            revision["updated_at"] = self._now_iso()
            self.state["revisions"][revision_id] = revision
            return
        raise ValueError("Line item not found")

    def _append_adjustment(
        self,
        *,
        revision_id: str,
        line_item_id: str,
        actor: str,
        reason: str,
        original_value: Any,
        adjusted_value: Any,
        kind: str,
    ) -> None:
        revision = self._require_mutable_revision(revision_id)
        rows = [dict(item) for item in list(revision.get("line_items") or [])]
        for idx, item in enumerate(rows):
            if str(item.get("line_item_id") or "") != line_item_id:
                continue
            adjustments = [
                dict(entry)
                for entry in list(item.get("manual_adjustment_metadata") or [])
            ]
            adjustment = {
                "kind": kind,
                "reason": reason,
                "created_by": actor,
                "created_at": self._now_iso(),
                "original_value": original_value,
                "adjusted_value": adjusted_value,
                "assembly_id": str(item.get("assembly_id") or ""),
                "assembly_version_id": str(item.get("assembly_version_id") or ""),
                "assembly_component_id": str(item.get("assembly_component_id") or ""),
                "estimate_revision_id": revision_id,
                "diagnostic_impact": "pending_review",
            }
            adjustments.append(adjustment)
            item["manual_adjustment_metadata"] = adjustments
            rows[idx] = item
            revision["line_items"] = rows
            self.state["revisions"][revision_id] = revision
            run_id = str(item.get("expansion_run_id") or "")
            if run_id and run_id in self.state.get("assembly_expansions", {}):
                row = dict(self.state["assembly_expansions"][run_id])
                row.setdefault("manual_overrides", []).append(adjustment)
                self.state["assembly_expansions"][run_id] = row
            return
        raise ValueError("Line item not found")

    def _labor_rollup_delta(
        self,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_hours = Decimal(str(baseline.get("total_hours") or 0))
        candidate_hours = Decimal(str(candidate.get("total_hours") or 0))
        baseline_cost = Decimal(str(baseline.get("total_labor_cost") or 0))
        candidate_cost = Decimal(str(candidate.get("total_labor_cost") or 0))
        return {
            "hours_delta": float(candidate_hours - baseline_hours),
            "cost_delta": float(candidate_cost - baseline_cost),
        }

    def _create_labor_snapshot(
        self,
        *,
        revision_id: str,
        parent_line_item_id: str,
        line_item_id: str,
        contribution: dict[str, Any],
        labor_rate_set_id: str,
        expansion_run_id: str,
        assembly_id: str,
        assembly_version_id: str,
    ) -> str:
        payload = self._build_labor_snapshot_payload(
            revision_id=revision_id,
            parent_line_item_id=parent_line_item_id,
            line_item_id=line_item_id,
            labor_activity_id=str(contribution.get("labor_activity_id") or ""),
            labor_category=str(contribution.get("labor_category") or "installation"),
            assembly_id=assembly_id,
            assembly_version_id=assembly_version_id,
            assembly_component_id=str(contribution.get("parent_component_id") or ""),
            driver_value=Decimal(str(contribution.get("generated_quantity") or 0)),
            calculated_hours=Decimal(str(contribution.get("generated_quantity") or 0)),
            labor_rate_set_id=labor_rate_set_id,
            expansion_run_id=expansion_run_id,
        )
        snapshot_id = str(payload.get("labor_snapshot_id") or "")
        self.state["labor_snapshots"][snapshot_id] = payload
        return snapshot_id

    def _build_labor_snapshot_payload(
        self,
        *,
        revision_id: str,
        parent_line_item_id: str,
        line_item_id: str,
        labor_activity_id: str,
        labor_category: str,
        assembly_id: str,
        assembly_version_id: str,
        assembly_component_id: str,
        driver_value: Decimal,
        calculated_hours: Decimal,
        labor_rate_set_id: str,
        expansion_run_id: str,
    ) -> dict[str, Any]:
        service = self._assembly_service()
        records = list(
            service.state.get("labor_rate_records", {}).get(labor_rate_set_id) or []
        )
        match = next(
            (
                dict(item)
                for item in records
                if str(item.get("labor_category") or "") == labor_category
            ),
            {},
        )
        straight = Decimal(str(match.get("straight_time_rate") or 0))
        burden = Decimal(str(match.get("burden_rate") or 0))
        unit_rate = straight + burden
        snapshot_id = f"labor_snapshot:{line_item_id}:{uuid.uuid4().hex[:10]}"
        return {
            "labor_snapshot_id": snapshot_id,
            "revision_id": revision_id,
            "line_item_id": line_item_id,
            "parent_line_item_id": parent_line_item_id,
            "labor_activity_id": labor_activity_id,
            "labor_category": labor_category,
            "assembly_id": assembly_id,
            "assembly_version_id": assembly_version_id,
            "assembly_component_id": assembly_component_id,
            "quantity_driver": "generated_quantity",
            "driver_value": float(driver_value),
            "base_hours": float(calculated_hours),
            "applied_factors": {},
            "calculated_hours": float(calculated_hours),
            "labor_rate_set_id": labor_rate_set_id,
            "labor_rate_record_id": str(match.get("labor_rate_record_id") or ""),
            "unit_rate": float(unit_rate),
            "extended_labor_cost": float(unit_rate * calculated_hours),
            "geography": str(
                service.state.get("labor_rate_sets", {})
                .get(labor_rate_set_id, {})
                .get("geography")
                or ""
            ),
            "prevailing_wage_applicable": bool(
                service.state.get("labor_rate_sets", {})
                .get(labor_rate_set_id, {})
                .get("prevailing_wage_applicable", False)
            ),
            "source_metadata": dict(match.get("source_metadata") or {}),
            "calculation_rule": "hours * (straight_time_rate + burden_rate)",
            "calculation_timestamp": self._now_iso(),
            "ruleset_version": AssemblyExpansionService.LABOR_RULESET_VERSION,
            "expansion_run_id": expansion_run_id,
            "created_at": self._now_iso(),
        }

    def _line_product_id(self, line_item: dict[str, Any]) -> str:
        explicit = str(line_item.get("product_id") or "").strip()
        if explicit:
            return explicit
        manufacturer = (
            str(line_item.get("manufacturer") or "Unknown").strip() or "Unknown"
        )
        model = str(line_item.get("model") or "Unknown").strip() or "Unknown"
        return f"{manufacturer}::{model}"

    def _require_line_item(
        self, revision: dict[str, Any], line_item_id: str
    ) -> dict[str, Any]:
        for item in list(revision.get("line_items") or []):
            if str(item.get("line_item_id")) == line_item_id:
                return dict(item)
        raise ValueError("Line item not found")

    def _require_estimate(self, estimate_id: str) -> dict[str, Any]:
        estimate = self.state["estimates"].get(estimate_id)
        if estimate is None:
            raise ValueError("Estimate not found")
        return dict(estimate)

    def _require_revision(self, revision_id: str) -> dict[str, Any]:
        revision = self.state["revisions"].get(revision_id)
        if revision is None:
            raise ValueError("Revision not found")
        return dict(revision)

    def _require_mutable_revision(self, revision_id: str) -> dict[str, Any]:
        revision = self._require_revision(revision_id)
        if revision.get("state") in {
            EstimateRevisionState.LOCKED.value,
            EstimateRevisionState.SUPERSEDED.value,
            EstimateRevisionState.ARCHIVED.value,
        }:
            raise ValueError("Revision is immutable")
        return revision

    def _normalized_state(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = self.empty_state()
        for key in normalized:
            candidate = state.get(key)
            if isinstance(candidate, dict):
                normalized[key] = deepcopy(candidate)
            elif isinstance(candidate, list):
                normalized[key] = list(candidate)
        return normalized

    def _now_iso(self) -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
