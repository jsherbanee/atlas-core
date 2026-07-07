"""Deterministic labor estimation engine for Atlas Core bid intelligence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview
from atlas_core.domain.labor_estimate import (
    LaborEstimate,
    LaborEstimateCategory,
    LaborEstimateSourceRef,
)


@dataclass(frozen=True)
class LaborFactorRule:
    equipment_categories: tuple[str, ...]
    hours_by_labor_category: dict[str, float]
    method: str


class LaborEstimationEngine:
    ENGINE_VERSION = "labor-estimation-engine/1.0.0"

    _DEFAULT_SYSTEM_AREA = "general"
    _CATEGORY_NAMES = {
        "engineering": "engineering",
        "project_management": "project_management",
        "shop_prefab": "shop_prefab",
        "field_installation": "field_installation",
        "cable_pull": "cable_pull",
        "device_mounting": "device_mounting",
        "rack_fabrication": "rack_fabrication",
        "termination": "termination",
        "programming": "programming",
        "testing_commissioning": "testing_commissioning",
        "documentation_closeout_support": "documentation_closeout_support",
    }
    _RFI_CONFIDENCE_PENALTY = {
        "critical": 0.07,
        "high": 0.05,
        "medium": 0.03,
        "low": 0.01,
    }
    _RISK_CONDITION_FACTORS = {
        "missing_model_number": "missing_model_number",
        "scope_responsibility_ambiguity": "scope_responsibility_ambiguity",
        "quantity_conflict": "quantity_conflict",
        "add_alternate_ambiguity": "add_alternate_ambiguity",
        "drawing_spec_cross_reference_gap": "drawing_spec_cross_reference_gap",
    }

    _RULES: tuple[LaborFactorRule, ...] = (
        LaborFactorRule(
            equipment_categories=("speaker", "microphone", "camera", "display"),
            hours_by_labor_category={
                "field_installation": 1.2,
                "cable_pull": 0.9,
                "device_mounting": 0.6,
                "termination": 0.45,
                "testing_commissioning": 0.35,
            },
            method="default_device_installation_factor",
        ),
        LaborFactorRule(
            equipment_categories=("projector", "projection_screen", "drapery"),
            hours_by_labor_category={
                "field_installation": 1.8,
                "device_mounting": 1.25,
                "cable_pull": 1.1,
                "termination": 0.55,
                "testing_commissioning": 0.45,
            },
            method="projection_and_specialty_installation_factor",
        ),
        LaborFactorRule(
            equipment_categories=("rack",),
            hours_by_labor_category={
                "rack_fabrication": 2.4,
                "shop_prefab": 1.6,
                "termination": 1.0,
                "field_installation": 1.2,
                "testing_commissioning": 0.5,
            },
            method="rack_fabrication_factor",
        ),
        LaborFactorRule(
            equipment_categories=("control_processor", "dsp", "intercom"),
            hours_by_labor_category={
                "programming": 1.4,
                "termination": 0.6,
                "testing_commissioning": 0.75,
                "field_installation": 0.8,
            },
            method="controls_programming_factor",
        ),
        LaborFactorRule(
            equipment_categories=("network", "infrastructure", "cable"),
            hours_by_labor_category={
                "cable_pull": 1.5,
                "termination": 0.9,
                "field_installation": 0.6,
                "testing_commissioning": 0.3,
            },
            method="infrastructure_factor",
        ),
    )

    def build(self, review: BidPackageReview) -> LaborEstimate:
        grouped_expected_hours: dict[tuple[str, str], float] = defaultdict(float)
        grouped_basis_quantity: dict[tuple[str, str], float] = defaultdict(float)
        grouped_source_refs: dict[
            tuple[str, str],
            dict[tuple[str, str], LaborEstimateSourceRef],
        ] = defaultdict(dict)
        grouped_methods: dict[tuple[str, str], set[str]] = defaultdict(set)
        grouped_assumptions: dict[tuple[str, str], set[str]] = defaultdict(set)

        systems_by_id = {
            getattr(system, "system_id", ""): system for system in review.systems
        }

        for equipment in review.equipment:
            quantity = float(getattr(equipment, "quantity", 1) or 1)
            category_value = self._enum_value(getattr(equipment, "category", None))
            rule = self._rule_for_category(category_value)
            if rule is None:
                rule = LaborFactorRule(
                    equipment_categories=("unknown",),
                    hours_by_labor_category={
                        "field_installation": 0.75,
                        "termination": 0.35,
                        "testing_commissioning": 0.25,
                    },
                    method="default_unknown_equipment_factor",
                )
                grouped_assumptions[
                    ("field_installation", self._DEFAULT_SYSTEM_AREA)
                ].add(
                    f"Used default labor factors for unknown equipment category on {getattr(equipment, 'equipment_id', 'unknown-equipment')}."
                )

            system_area = self._system_area_for_equipment(equipment, systems_by_id)
            equipment_id = str(getattr(equipment, "equipment_id", "unknown-equipment"))

            for labor_category, unit_hours in rule.hours_by_labor_category.items():
                key = (labor_category, system_area)
                grouped_expected_hours[key] += unit_hours * quantity
                grouped_basis_quantity[key] += quantity
                grouped_methods[key].add(rule.method)
                grouped_source_refs[key][("equipment", equipment_id)] = (
                    LaborEstimateSourceRef(
                        source_type="equipment",
                        source_id=equipment_id,
                        source_label=getattr(equipment, "description", None),
                        field="quantity",
                        excerpt=f"quantity={quantity:g} category={category_value or 'unknown'}",
                    )
                )
                if system_area != self._DEFAULT_SYSTEM_AREA:
                    grouped_source_refs[key][("system", system_area)] = (
                        LaborEstimateSourceRef(
                            source_type="system",
                            source_id=system_area,
                        )
                    )

                model_value = str(getattr(equipment, "model", "") or "").strip()
                manufacturer_value = str(
                    getattr(equipment, "manufacturer", "") or ""
                ).strip()
                if not model_value:
                    grouped_assumptions[key].add(
                        f"Estimated labor for {equipment_id} without explicit model number."
                    )
                if not manufacturer_value:
                    grouped_assumptions[key].add(
                        f"Estimated labor for {equipment_id} without named manufacturer."
                    )

        overhead_expected = sum(grouped_expected_hours.values())
        engineering_overhead = max(
            0.0,
            round(
                (overhead_expected * 0.12)
                + (len(review.engineering_assumptions) * 0.6),
                2,
            ),
        )
        pm_overhead = max(
            0.0,
            round((overhead_expected * 0.08) + (len(review.rfi_candidates) * 0.5), 2),
        )
        doc_overhead = max(0.0, round(overhead_expected * 0.04, 2))

        if engineering_overhead > 0:
            self._add_overhead_category(
                grouped_expected_hours,
                grouped_basis_quantity,
                grouped_source_refs,
                grouped_methods,
                grouped_assumptions,
                labor_category="engineering",
                system_area=self._DEFAULT_SYSTEM_AREA,
                hours=engineering_overhead,
                quantity_basis=float(len(review.equipment) or 1),
                method="engineering_overhead_factor",
                assumption=(
                    "Engineering labor includes review coordination and assumption "
                    "resolution effort."
                ),
            )

        if pm_overhead > 0:
            self._add_overhead_category(
                grouped_expected_hours,
                grouped_basis_quantity,
                grouped_source_refs,
                grouped_methods,
                grouped_assumptions,
                labor_category="project_management",
                system_area=self._DEFAULT_SYSTEM_AREA,
                hours=pm_overhead,
                quantity_basis=float(
                    len(review.rfi_candidates) or len(review.equipment) or 1
                ),
                method="project_management_overhead_factor",
                assumption=(
                    "Project management labor includes bid-phase coordination, scope "
                    "tracking, and clarifications."
                ),
            )

        if doc_overhead > 0:
            self._add_overhead_category(
                grouped_expected_hours,
                grouped_basis_quantity,
                grouped_source_refs,
                grouped_methods,
                grouped_assumptions,
                labor_category="documentation_closeout_support",
                system_area=self._DEFAULT_SYSTEM_AREA,
                hours=doc_overhead,
                quantity_basis=float(len(review.equipment) or 1),
                method="documentation_allowance_factor",
                assumption=(
                    "Documentation category is a bid allowance for manuals, as-builts, "
                    "and owner training support only."
                ),
            )

        risk_factors, warnings = self._risk_factors_from_review(review)
        global_confidence = self._confidence_from_review(review)

        category_outputs: list[LaborEstimateCategory] = []
        for (labor_category, system_area), expected_hours in sorted(
            grouped_expected_hours.items()
        ):
            expected_hours = round(expected_hours, 2)
            risk_multiplier = 1.0 + (0.05 * len(risk_factors))
            low_hours = round(max(0.0, expected_hours * 0.85), 2)
            high_hours = round(
                max(expected_hours, expected_hours * 1.2 * risk_multiplier), 2
            )

            refs = list(grouped_source_refs[(labor_category, system_area)].values())
            category_confidence = round(
                max(0.05, min(0.99, global_confidence - (0.01 * len(risk_factors)))), 2
            )
            methods = sorted(grouped_methods[(labor_category, system_area)])
            assumptions = sorted(grouped_assumptions[(labor_category, system_area)])
            quantity_basis = round(
                grouped_basis_quantity[(labor_category, system_area)],
                2,
            )

            category_outputs.append(
                LaborEstimateCategory(
                    category_id=f"{labor_category}:{system_area}",
                    category_name=self._CATEGORY_NAMES.get(
                        labor_category, labor_category
                    ),
                    system_area=system_area,
                    quantity_basis=f"quantity_sum={quantity_basis:g}",
                    hours_low=low_hours,
                    hours_expected=expected_hours,
                    hours_high=high_hours,
                    confidence=category_confidence,
                    calculation_method=", ".join(methods) or "deterministic_default",
                    source_refs=refs,
                    assumptions=assumptions,
                    risk_factors=sorted(risk_factors),
                )
            )

        total_low = round(sum(category.hours_low for category in category_outputs), 2)
        total_expected = round(
            sum(category.hours_expected for category in category_outputs), 2
        )
        total_high = round(sum(category.hours_high for category in category_outputs), 2)

        assumptions = self._build_global_assumptions(review, category_outputs)
        exclusions = [
            "Estimate excludes procurement, RFQ workflow, submittals, invoicing, and execution planning.",
            "Estimate excludes construction schedule sequencing and field supervision allocation.",
        ]

        all_source_refs = self._collect_global_source_refs(review, category_outputs)
        return LaborEstimate(
            project_id=review.project_id,
            total_labor_hours_low=total_low,
            total_labor_hours_expected=total_expected,
            total_labor_hours_high=total_high,
            labor_categories=category_outputs,
            assumptions=assumptions,
            exclusions=exclusions,
            confidence=global_confidence,
            source_refs=all_source_refs,
            warnings=warnings,
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _risk_factors_from_review(
        self, review: BidPackageReview
    ) -> tuple[set[str], list[str]]:
        risk_factors: set[str] = set()
        warnings: list[str] = []
        for candidate in review.rfi_candidates:
            detected_condition = str(
                getattr(candidate, "detected_condition", "") or ""
            ).strip()
            mapped_risk = self._RISK_CONDITION_FACTORS.get(detected_condition)
            if mapped_risk:
                risk_factors.add(mapped_risk)

        if "quantity_conflict" in risk_factors:
            warnings.append(
                "Quantity conflicts detected; labor range widened to reflect coordination uncertainty."
            )
        if "scope_responsibility_ambiguity" in risk_factors:
            warnings.append(
                "Scope responsibility ambiguity detected; labor range includes coordination contingency."
            )
        if "add_alternate_ambiguity" in risk_factors:
            warnings.append(
                "Add alternate language ambiguity detected; labor range may shift with clarifications."
            )
        if "drawing_spec_cross_reference_gap" in risk_factors:
            warnings.append(
                "Drawing/spec reference gaps detected; labor assumptions may change as cross-references are resolved."
            )

        if not review.equipment:
            warnings.append(
                "No resolved equipment detected; labor estimate may be understated until equipment is resolved."
            )

        return risk_factors, warnings

    def _confidence_from_review(self, review: BidPackageReview) -> float:
        confidence = float(getattr(review, "confidence", 0.75) or 0.75)

        for candidate in review.rfi_candidates:
            severity = str(
                getattr(
                    getattr(candidate, "severity", None),
                    "value",
                    getattr(candidate, "severity", ""),
                )
            )
            confidence -= self._RFI_CONFIDENCE_PENALTY.get(severity, 0.01)

        if not review.equipment:
            confidence -= 0.1
        if not review.systems:
            confidence -= 0.05
        if not review.specification_sections:
            confidence -= 0.05
        if not review.drawing_sheets:
            confidence -= 0.05

        return round(max(0.05, min(0.99, confidence)), 2)

    @staticmethod
    def _collect_global_source_refs(
        review: BidPackageReview,
        category_outputs: list[LaborEstimateCategory],
    ) -> list[LaborEstimateSourceRef]:
        refs: dict[tuple[str, str], LaborEstimateSourceRef] = {}
        for category in category_outputs:
            for source_ref in category.source_refs:
                refs[(source_ref.source_type, source_ref.source_id)] = source_ref

        refs[("review", review.review_id)] = LaborEstimateSourceRef(
            source_type="bid_package_review",
            source_id=review.review_id,
            source_label=review.name,
        )

        for candidate in review.rfi_candidates:
            candidate_id = str(getattr(candidate, "candidate_id", "") or "")
            if candidate_id:
                refs[("rfi_candidate", candidate_id)] = LaborEstimateSourceRef(
                    source_type="rfi_candidate",
                    source_id=candidate_id,
                    source_label=getattr(candidate, "detected_condition", None),
                )

        return sorted(refs.values(), key=lambda ref: (ref.source_type, ref.source_id))

    @staticmethod
    def _build_global_assumptions(
        review: BidPackageReview,
        categories: list[LaborEstimateCategory],
    ) -> list[str]:
        assumptions: set[str] = {
            "Labor factors are deterministic defaults and should be calibrated by estimator discipline norms.",
            "Hours represent bid-intelligence estimating ranges only, not project execution plans.",
        }

        if review.rfi_candidates:
            assumptions.add(
                "RFI candidate ambiguity reduced confidence and widened high-side labor range."
            )
        if not review.device_schedules:
            assumptions.add(
                "No device schedule input detected; quantity basis is derived from resolved equipment."
            )
        if any("unknown" in category.calculation_method for category in categories):
            assumptions.add(
                "At least one equipment item used unknown-category labor defaults."
            )

        return sorted(assumptions)

    @staticmethod
    def _add_overhead_category(
        grouped_expected_hours: dict[tuple[str, str], float],
        grouped_basis_quantity: dict[tuple[str, str], float],
        grouped_source_refs: dict[
            tuple[str, str],
            dict[tuple[str, str], LaborEstimateSourceRef],
        ],
        grouped_methods: dict[tuple[str, str], set[str]],
        grouped_assumptions: dict[tuple[str, str], set[str]],
        labor_category: str,
        system_area: str,
        hours: float,
        quantity_basis: float,
        method: str,
        assumption: str,
    ) -> None:
        key = (labor_category, system_area)
        grouped_expected_hours[key] += hours
        grouped_basis_quantity[key] += quantity_basis
        grouped_methods[key].add(method)
        grouped_assumptions[key].add(assumption)
        grouped_source_refs[key][("review", system_area)] = LaborEstimateSourceRef(
            source_type="review",
            source_id=system_area,
            source_label="bid_intelligence_overhead",
            excerpt=f"hours={hours:g}",
        )

    def _rule_for_category(self, category: str) -> LaborFactorRule | None:
        normalized = category.strip().casefold()
        for rule in self._RULES:
            if normalized in rule.equipment_categories:
                return rule

        return None

    @classmethod
    def _system_area_for_equipment(
        cls,
        equipment: Any,
        systems_by_id: dict[str, Any],
    ) -> str:
        system_id = str(getattr(equipment, "system_id", "") or "").strip()
        if not system_id:
            return cls._DEFAULT_SYSTEM_AREA

        matched_system = systems_by_id.get(system_id)
        if matched_system is None:
            return system_id

        name = str(getattr(matched_system, "name", "") or "").strip()
        return name or system_id

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(getattr(value, "value", value) or "")
