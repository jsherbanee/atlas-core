"""RFI candidate generation helpers for Atlas Core."""

from __future__ import annotations

from typing import Any

from atlas_core.domain import BidPackageReview, RFICandidate, RFIPriority
from atlas_core.utils.refactoring import enum_value


class RFICandidateService:
    def build(self, review: BidPackageReview) -> list[RFICandidate]:
        candidates: list[RFICandidate] = []
        emitted: set[str] = set()

        scope_gaps = list(getattr(review, "scope_gaps", []) or [])
        equipment = list(getattr(review, "equipment", []) or [])
        detail_callouts = list(getattr(review, "detail_callouts", []) or [])
        engineering_assumptions = list(
            getattr(review, "engineering_assumptions", []) or []
        )

        has_mount_detail = self._has_mount_detail(detail_callouts)

        for gap in scope_gaps:
            if enum_value(getattr(gap, "severity", None)) == "high":
                gap_id = str(getattr(gap, "gap_id", "") or "unknown-gap")
                target_id = str(getattr(gap, "target_id", "") or "unknown-target")
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_scope_gap_{gap_id}_{target_id}",
                        title="Scope gap requires clarification",
                        question=(
                            "Please clarify the missing scope item identified by "
                            "Atlas."
                        ),
                        priority=RFIPriority.HIGH,
                        category="scope_gap",
                        related_equipment=getattr(gap, "target_id", None),
                    ),
                )

            if self._is_drapery_scope_gap(gap):
                gap_id = str(getattr(gap, "gap_id", "") or "unknown-gap")
                target_id = str(getattr(gap, "target_id", "") or "unknown-target")
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_drapery_gap_{gap_id}_{target_id}",
                        title="Drapery scope clarification",
                        question=(
                            "Please confirm drapery track, hardware, support "
                            "structure, fire rating, and installation responsibility."
                        ),
                        priority=RFIPriority.HIGH,
                        category="drapery",
                        related_equipment=getattr(gap, "target_id", None),
                    ),
                )

        for item in equipment:
            equipment_id = str(getattr(item, "equipment_id", "") or "unknown-equipment")
            category = enum_value(getattr(item, "category", None))

            if category == "projector" and not has_mount_detail:
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_projector_mounting_{equipment_id}",
                        title="Projector mounting requirements",
                        question=(
                            "Please confirm projector mount type, structural "
                            "attachment requirements, and responsibility for backing "
                            "or support."
                        ),
                        priority=RFIPriority.HIGH,
                        category="mounting",
                        related_equipment=getattr(item, "equipment_id", None),
                    ),
                )

            if category == "display" and not has_mount_detail:
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_display_mounting_{equipment_id}",
                        title="Display mounting requirements",
                        question=(
                            "Please confirm display mount type, wall backing, power "
                            "location, and any recessed box requirements."
                        ),
                        priority=RFIPriority.MEDIUM,
                        category="mounting",
                        related_equipment=getattr(item, "equipment_id", None),
                    ),
                )

            if category == "drapery":
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_drapery_equipment_{equipment_id}",
                        title="Drapery scope clarification",
                        question=(
                            "Please confirm drapery track, hardware, support "
                            "structure, fire rating, and installation responsibility."
                        ),
                        priority=RFIPriority.HIGH,
                        category="drapery",
                        related_equipment=getattr(item, "equipment_id", None),
                    ),
                )

            if not self._has_specification_reference(item):
                self._add_candidate(
                    candidates,
                    emitted,
                    RFICandidate(
                        rfi_id=f"rfi_specification_reference_{equipment_id}",
                        title="Equipment specification reference",
                        question=(
                            "Please confirm the applicable specification section for "
                            "this equipment."
                        ),
                        priority=RFIPriority.LOW,
                        category="specification",
                        related_equipment=getattr(item, "equipment_id", None),
                    ),
                )

        for assumption in engineering_assumptions:
            if enum_value(getattr(assumption, "severity", None)) != "risk":
                continue

            assumption_id = str(
                getattr(assumption, "assumption_id", "") or "unknown-assumption"
            )
            question = str(getattr(assumption, "description", "") or "").strip()
            if not question:
                continue

            self._add_candidate(
                candidates,
                emitted,
                RFICandidate(
                    rfi_id=f"rfi_assumption_{assumption_id}",
                    title="Engineering assumption requires clarification",
                    question=question,
                    priority=RFIPriority.HIGH,
                    category="assumption",
                    related_equipment=getattr(assumption, "related_equipment", None),
                    related_sheet=getattr(assumption, "related_sheet", None),
                    related_specification=getattr(
                        assumption,
                        "related_specification",
                        None,
                    ),
                ),
            )

        return candidates

    @staticmethod
    def _add_candidate(
        candidates: list[RFICandidate],
        emitted: set[str],
        candidate: RFICandidate,
    ) -> None:
        if candidate.rfi_id in emitted:
            return

        emitted.add(candidate.rfi_id)
        candidates.append(candidate)

    @staticmethod
    def _has_mount_detail(detail_callouts: list[Any]) -> bool:
        for callout in detail_callouts:
            text = " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                    " ".join(str(note) for note in getattr(callout, "notes", []) or []),
                ]
            ).casefold()
            if any(token in text for token in ("mount", "mounting", "bracket")):
                return True

        return False

    @staticmethod
    def _has_specification_reference(item: Any) -> bool:
        specification_reference = getattr(item, "specification_reference", None)
        return isinstance(specification_reference, str) and bool(
            specification_reference.strip()
        )

    @staticmethod
    def _is_drapery_scope_gap(gap: Any) -> bool:
        value = " ".join(
            [
                str(getattr(gap, "gap_id", "") or ""),
                str(getattr(gap, "message", "") or ""),
            ]
        ).casefold()
        return "drapery" in value
