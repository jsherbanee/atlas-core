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
        excluded_total = Decimal("0")
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
            snapshot_id = str(line.get("selected_cost_snapshot_id") or "")
            section_key = str(line.get("section") or "unassigned")
            system_key = str(line.get("system") or "unassigned")
            room_key = str(line.get("room") or "unassigned")
            if not snapshot_id:
                unresolved_total += Decimal(str(line.get("requested_quantity") or 0))
                continue
            snapshot = dict(snapshots.get(snapshot_id) or {})
            line_total = Decimal(str(snapshot.get("extended_acquisition_cost") or 0))
            acquisition_total += line_total
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
            unresolved_cost_total=unresolved_total,
            excluded_line_total=excluded_total,
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
            snapshot_id = str(line_item.get("selected_cost_snapshot_id") or "")
            if not snapshot_id:
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
