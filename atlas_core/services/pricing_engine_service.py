"""Deterministic pricing engine for Atlas Core."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
from typing import Any

from atlas_core.domain.commercial_knowledge import (
    CommercialProductLifecycleStatus,
    KnowledgeFreshnessStatus,
)
from atlas_core.domain.deterministic_estimate import Estimate, ProductResolutionStatus
from atlas_core.domain.pricing_engine import (
    CommercialCoverageSummary,
    FreshnessStatus,
    PriceManualOverride,
    PriceSelection,
    PriceSelectionCandidate,
    PricedEstimateLine,
    PricingResult,
    PricingRule,
    PricingStatus,
    PricingSummary,
    PricingWarning,
)
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService


class DeterministicPricingEngine:
    POLICY_VERSION = "atlas-pricing-policy:v1"

    def __init__(
        self,
        *,
        freshness_thresholds: dict[str, int] | None = None,
        as_of: date | None = None,
    ) -> None:
        self.as_of = as_of or datetime.now(UTC).date()
        thresholds = freshness_thresholds or {}
        self.fresh_days = int(thresholds.get("fresh", 180))
        self.review_days = int(thresholds.get("review", 365))

    def run(
        self,
        *,
        estimate: Estimate,
        product_resolutions: list[ProductResolution | dict[str, Any]],
        commercial_state: dict[str, Any],
        project_id: str,
        preferred_vendor_policy: dict[str, Any] | None = None,
        project_quotes: list[dict[str, Any]] | None = None,
        manual_overrides: dict[str, dict[str, Any]] | None = None,
        generic_allowances: dict[str, float] | None = None,
    ) -> PricingResult:
        resolutions = [
            item if isinstance(item, ProductResolution) else ProductResolution(**item)
            for item in list(product_resolutions or [])
        ]
        resolution_by_source = {item.source_object_id: item for item in resolutions}
        policy = dict(preferred_vendor_policy or {})
        quote_rows = list(project_quotes or [])
        overrides = dict(manual_overrides or {})
        allowance_map = dict(generic_allowances or {})

        commercial_service = CommercialKnowledgeService(
            state=commercial_state,
            as_of=self.as_of,
        )
        commercial = commercial_service.to_dict()

        run_fingerprint = self._run_fingerprint(
            estimate=estimate,
            resolutions=resolutions,
            commercial_state=commercial,
            policy=policy,
            quotes=quote_rows,
            overrides=overrides,
            allowances=allowance_map,
        )

        priced_lines: list[PricedEstimateLine] = []
        warnings: list[PricingWarning] = []

        freshness_rows: dict[str, dict[str, Any]] = {}
        for item in commercial_service.freshness_rows():
            product_key = self._safe(item.get("product"), "")
            if product_key:
                freshness_rows[product_key] = dict(item)

        for line in estimate.all_lines():
            resolution = resolution_by_source.get(line.source_object)
            priced, line_warnings = self._price_line(
                line=line,
                resolution=resolution,
                commercial=commercial,
                freshness_rows=freshness_rows,
                policy=policy,
                quotes=quote_rows,
                manual_override=overrides.get(line.line_id),
                generic_allowances=allowance_map,
                project_id=project_id,
            )
            priced_lines.append(priced)
            warnings.extend(line_warnings)

        summary = self._summary(priced_lines)
        coverage = self._coverage(priced_lines)
        result = PricingResult(
            pricing_run_id=run_fingerprint,
            run_timestamp=self._now_iso(),
            pricing_policy_version=self.POLICY_VERSION,
            priced_lines=priced_lines,
            summary=summary,
            commercial_coverage=coverage,
            warnings=warnings,
        )
        return result

    def detect_price_update_impact(
        self,
        *,
        snapshot: PricingResult | dict[str, Any],
        latest: PricingResult | dict[str, Any],
    ) -> list[dict[str, Any]]:
        prior = (
            snapshot
            if isinstance(snapshot, PricingResult)
            else PricingResult(**snapshot)
        )
        current = (
            latest if isinstance(latest, PricingResult) else PricingResult(**latest)
        )

        current_by_line = {line.estimate_line_id: line for line in current.priced_lines}
        advisories: list[dict[str, Any]] = []

        for old_line in prior.priced_lines:
            new_line = current_by_line.get(old_line.estimate_line_id)
            if new_line is None:
                continue

            if (
                old_line.unit_cost is not None
                and new_line.unit_cost is not None
                and old_line.unit_cost != new_line.unit_cost
            ):
                if new_line.unit_cost > old_line.unit_cost:
                    advisories.append(
                        {
                            "estimate_line_id": old_line.estimate_line_id,
                            "signal": "Price Increase Available",
                            "old_unit_cost": old_line.unit_cost,
                            "new_unit_cost": new_line.unit_cost,
                        }
                    )
                else:
                    advisories.append(
                        {
                            "estimate_line_id": old_line.estimate_line_id,
                            "signal": "Price Decrease Available",
                            "old_unit_cost": old_line.unit_cost,
                            "new_unit_cost": new_line.unit_cost,
                        }
                    )

            if (
                old_line.freshness_status is not FreshnessStatus.STALE
                and new_line.freshness_status is FreshnessStatus.STALE
            ):
                advisories.append(
                    {
                        "estimate_line_id": old_line.estimate_line_id,
                        "signal": "Selected Price Became Stale",
                    }
                )

            if (
                old_line.freshness_status is not FreshnessStatus.MISSING_FROM_LATEST
                and new_line.freshness_status is FreshnessStatus.MISSING_FROM_LATEST
            ):
                advisories.append(
                    {
                        "estimate_line_id": old_line.estimate_line_id,
                        "signal": "Selected Product Missing From Latest Sheet",
                    }
                )

            if (
                old_line.selected_vendor_offering_id
                and new_line.selected_vendor_offering_id
                and old_line.selected_vendor_offering_id
                != new_line.selected_vendor_offering_id
            ):
                advisories.append(
                    {
                        "estimate_line_id": old_line.estimate_line_id,
                        "signal": "New Vendor Offering Available",
                        "old_vendor_offering_id": old_line.selected_vendor_offering_id,
                        "new_vendor_offering_id": new_line.selected_vendor_offering_id,
                    }
                )

        return advisories

    def export_pricing_summary_json(
        self, result: PricingResult | dict[str, Any]
    ) -> str:
        payload = (
            result if isinstance(result, PricingResult) else PricingResult(**result)
        )
        summary = payload.summary.to_dict() if payload.summary is not None else {}
        return json.dumps(
            {
                "pricing_run_id": payload.pricing_run_id,
                "run_timestamp": payload.run_timestamp,
                "pricing_policy_version": payload.pricing_policy_version,
                "summary": summary,
            },
            indent=2,
            sort_keys=True,
        )

    def export_priced_bom_csv(self, result: PricingResult | dict[str, Any]) -> str:
        payload = (
            result if isinstance(result, PricingResult) else PricingResult(**result)
        )
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "estimate_line_id",
                "source_equipment_id",
                "canonical_product_id",
                "quantity",
                "selected_vendor_offering_id",
                "unit_cost",
                "extended_cost",
                "currency",
                "pricing_status",
                "freshness_status",
                "pricing_confidence",
                "selection_reason",
            ],
        )
        writer.writeheader()
        for line in payload.priced_lines:
            writer.writerow(
                {
                    "estimate_line_id": line.estimate_line_id,
                    "source_equipment_id": line.source_equipment_id,
                    "canonical_product_id": line.canonical_product_id,
                    "quantity": line.quantity,
                    "selected_vendor_offering_id": line.selected_vendor_offering_id,
                    "unit_cost": line.unit_cost,
                    "extended_cost": line.extended_cost,
                    "currency": line.currency,
                    "pricing_status": line.pricing_status.value,
                    "freshness_status": line.freshness_status.value,
                    "pricing_confidence": line.pricing_confidence,
                    "selection_reason": line.selection_reason,
                }
            )
        return buffer.getvalue()

    def export_commercial_coverage_json(
        self, result: PricingResult | dict[str, Any]
    ) -> str:
        payload = (
            result if isinstance(result, PricingResult) else PricingResult(**result)
        )
        coverage = (
            payload.commercial_coverage.to_dict()
            if payload.commercial_coverage is not None
            else {}
        )
        return json.dumps(coverage, indent=2, sort_keys=True)

    def export_pricing_exceptions_csv(
        self, result: PricingResult | dict[str, Any]
    ) -> str:
        payload = (
            result if isinstance(result, PricingResult) else PricingResult(**result)
        )
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "estimate_line_id",
                "pricing_status",
                "warning_code",
                "warning_message",
                "selection_reason",
            ],
        )
        writer.writeheader()
        for line in payload.priced_lines:
            if (
                line.pricing_status
                in {
                    PricingStatus.NO_PRICING,
                    PricingStatus.STALE_PRICE,
                    PricingStatus.EXPIRED_PRICE,
                    PricingStatus.UNAVAILABLE,
                    PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET,
                    PricingStatus.ESTIMATED_ALLOWANCE,
                }
                or line.warnings
            ):
                if line.warnings:
                    for warning in line.warnings:
                        writer.writerow(
                            {
                                "estimate_line_id": line.estimate_line_id,
                                "pricing_status": line.pricing_status.value,
                                "warning_code": warning.code,
                                "warning_message": warning.message,
                                "selection_reason": line.selection_reason,
                            }
                        )
                else:
                    writer.writerow(
                        {
                            "estimate_line_id": line.estimate_line_id,
                            "pricing_status": line.pricing_status.value,
                            "warning_code": "pricing_exception",
                            "warning_message": line.selection_reason,
                            "selection_reason": line.selection_reason,
                        }
                    )
        return buffer.getvalue()

    def _price_line(
        self,
        *,
        line: Any,
        resolution: ProductResolution | None,
        commercial: dict[str, Any],
        freshness_rows: dict[str, dict[str, Any]],
        policy: dict[str, Any],
        quotes: list[dict[str, Any]],
        manual_override: dict[str, Any] | None,
        generic_allowances: dict[str, float],
        project_id: str,
    ) -> tuple[PricedEstimateLine, list[PricingWarning]]:
        warnings: list[PricingWarning] = []
        candidates: list[PriceSelectionCandidate] = []
        rules: list[PricingRule] = []

        quantity = float(line.quantity)
        canonical_product_id = None
        manufacturer_id = None
        resolution_status = ProductResolutionStatus.UNKNOWN_PRODUCT
        if resolution is not None:
            canonical_product_id = resolution.canonical_product_id
            manufacturer_id = resolution.manufacturer_id
            resolution_status = resolution.resolution_status

        source_equipment_id = str(line.source_object)

        if resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT:
            allowance = generic_allowances.get(source_equipment_id)
            if allowance is not None:
                priced = self._allowance_priced_line(
                    line=line,
                    source_equipment_id=source_equipment_id,
                    canonical_product_id=canonical_product_id,
                    manufacturer_id=manufacturer_id,
                    unit_cost=float(allowance),
                    reason="Generic allowance applied for unknown product by explicit allowance map.",
                    manual_override=manual_override,
                )
                warnings.append(
                    PricingWarning(
                        code="unknown_product_allowance",
                        message="Unknown product received explicit generic allowance.",
                        severity="warning",
                    )
                )
                return priced, warnings
            warnings.append(
                PricingWarning(
                    code="unknown_product_unpriced",
                    message="Unknown product remains unpriced without explicit allowance.",
                    severity="warning",
                )
            )
            return (
                self._no_pricing_line(
                    line=line,
                    source_equipment_id=source_equipment_id,
                    canonical_product_id=canonical_product_id,
                    manufacturer_id=manufacturer_id,
                    reason="Unknown product is ineligible for deterministic pricing.",
                    warnings=warnings,
                ),
                warnings,
            )

        if resolution_status is ProductResolutionStatus.GENERIC_ALLOWANCE:
            allowance = generic_allowances.get(source_equipment_id)
            if allowance is not None:
                return (
                    self._allowance_priced_line(
                        line=line,
                        source_equipment_id=source_equipment_id,
                        canonical_product_id=canonical_product_id,
                        manufacturer_id=manufacturer_id,
                        unit_cost=float(allowance),
                        reason="Generic allowance applied from approved allowance map.",
                        manual_override=manual_override,
                    ),
                    warnings,
                )
            return (
                self._no_pricing_line(
                    line=line,
                    source_equipment_id=source_equipment_id,
                    canonical_product_id=canonical_product_id,
                    manufacturer_id=manufacturer_id,
                    reason="Generic allowance product has no approved allowance entry.",
                    warnings=[
                        PricingWarning(
                            code="missing_allowance",
                            message="No allowance exists for generic-allowance line.",
                            severity="warning",
                        )
                    ],
                ),
                warnings,
            )

        product_key = self._product_key(
            canonical_product_id=canonical_product_id,
            manufacturer=line.manufacturer,
            model=line.model,
        )

        record_rows = self._commercial_records_for_product(
            commercial=commercial,
            product_key=product_key,
        )

        quote_candidates = self._quote_candidates(
            product_key=product_key,
            quotes=quotes,
            project_id=project_id,
        )

        for index, quote in enumerate(quote_candidates, start=1):
            candidate = PriceSelectionCandidate(
                candidate_id=f"quote:{source_equipment_id}:{index}",
                vendor=self._safe(quote.get("vendor"), "Quoted Vendor"),
                unit_cost=self._float_or_none(quote.get("unit_cost")),
                list_price=self._float_or_none(quote.get("list_price")),
                currency=self._safe(quote.get("currency"), "USD"),
                effective_date=self._safe(quote.get("effective_date"), ""),
                expiration_date=self._safe(quote.get("expiration_date"), ""),
                import_date=self._safe(quote.get("import_date"), ""),
                freshness_status=FreshnessStatus.FRESH,
                lead_time=self._safe(quote.get("lead_time"), ""),
                availability=self._safe(quote.get("availability"), "quoted"),
                source_price_sheet_id=self._safe(quote.get("price_sheet_id"), ""),
                source_price_sheet_version_id=self._safe(
                    quote.get("price_sheet_version_id"), ""
                ),
                source_price_record_id=self._safe(quote.get("price_record_id"), ""),
                source_vendor_offering_id=self._safe(
                    quote.get("vendor_offering_id"), ""
                ),
                confidence=0.99,
                rank=index,
                selection_reason="Active project-specific quote with exact product match.",
            )
            candidates.append(candidate)

        commercial_candidates = self._record_candidates(
            records=record_rows,
            commercial=commercial,
            freshness_rows=freshness_rows,
            product_key=product_key,
            policy=policy,
            manufacturer=line.manufacturer,
            model=line.model,
            source_equipment_id=source_equipment_id,
        )
        candidates.extend(commercial_candidates)

        candidates.sort(
            key=lambda item: (
                item.rank,
                float(item.unit_cost or 0.0),
                item.vendor.lower(),
                item.source_price_record_id,
            )
        )

        selected: PriceSelectionCandidate | None = candidates[0] if candidates else None
        selection_method = "deterministic"
        selection_reason = (
            selected.selection_reason
            if selected is not None
            else "No candidate matched deterministic pricing rules."
        )

        rules.append(
            PricingRule(
                rule_id="rule:quotes",
                name="Project quote priority",
                priority=1,
                matched=bool(quote_candidates),
                detail=(
                    "Project quote candidate(s) considered first."
                    if quote_candidates
                    else "No active project-specific quote candidates."
                ),
            )
        )
        rules.append(
            PricingRule(
                rule_id="rule:preferred_vendor",
                name="Preferred vendor policy",
                priority=2,
                matched=bool(policy),
                detail="Preferred vendor policy applied where possible.",
            )
        )

        if selected is None:
            warnings.append(
                PricingWarning(
                    code="no_pricing_candidate",
                    message="No deterministic pricing candidate available.",
                    severity="warning",
                )
            )
            return (
                self._no_pricing_line(
                    line=line,
                    source_equipment_id=source_equipment_id,
                    canonical_product_id=canonical_product_id,
                    manufacturer_id=manufacturer_id,
                    reason="No pricing candidates available after deterministic rule evaluation.",
                    warnings=warnings,
                    selection=PriceSelection(
                        selected_candidate_id=None,
                        selection_method=selection_method,
                        selection_reason=selection_reason,
                        candidates=candidates,
                        applied_rules=rules,
                    ),
                ),
                warnings,
            )

        pricing_status = self._candidate_status(selected)
        if pricing_status is PricingStatus.EXPIRED_PRICE:
            warnings.append(
                PricingWarning(
                    code="expired_price",
                    message="Selected candidate is expired; used because no valid current alternative exists.",
                    severity="warning",
                )
            )
        if pricing_status is PricingStatus.STALE_PRICE:
            warnings.append(
                PricingWarning(
                    code="stale_price",
                    message="Selected candidate is stale and should be reviewed.",
                    severity="warning",
                )
            )
        if pricing_status is PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET:
            warnings.append(
                PricingWarning(
                    code="missing_latest",
                    message="Product is missing from latest comparable sheet version.",
                    severity="warning",
                )
            )

        unit_cost = selected.unit_cost
        extended = round((unit_cost or 0.0) * quantity, 2)
        freshness, days_since = self._freshness_info(
            selected=selected,
            product_key=product_key,
            freshness_rows=freshness_rows,
        )

        selection = PriceSelection(
            selected_candidate_id=selected.candidate_id,
            selection_method=selection_method,
            selection_reason=selection_reason,
            candidates=candidates,
            applied_rules=rules,
        )

        manual = self._manual_override(
            line=line,
            manual_override=manual_override,
            automatic_candidate=selected,
        )
        if manual is not None:
            pricing_status = PricingStatus.MANUAL_OVERRIDE
            unit_cost = manual.manual_unit_cost
            extended = round(unit_cost * quantity, 2)
            selection_reason = "Manual override applied by estimator."
            selection_method = "manual_override"

        confidence, rationale = self._confidence(
            line=line,
            resolution=resolution,
            selected=selected,
            pricing_status=pricing_status,
            manual_override=manual,
        )

        source_ref = {
            "vendor": selected.vendor,
            "price_sheet_id": selected.source_price_sheet_id,
            "price_sheet_version_id": selected.source_price_sheet_version_id,
            "price_record_id": selected.source_price_record_id,
            "vendor_offering_id": selected.source_vendor_offering_id,
            "import_date": selected.import_date,
            "effective_date": selected.effective_date,
            "expiration_date": selected.expiration_date,
            "source_row": self._source_row_for_record(
                commercial,
                selected.source_price_record_id,
            ),
            "comparison_status": self._comparison_status(
                commercial,
                selected.source_price_sheet_version_id,
                product_key,
            ),
        }

        priced = PricedEstimateLine(
            estimate_line_id=line.line_id,
            source_equipment_id=source_equipment_id,
            canonical_product_id=canonical_product_id,
            manufacturer_id=manufacturer_id,
            quantity=quantity,
            selected_price_record_id=selected.source_price_record_id or None,
            selected_vendor_offering_id=selected.source_vendor_offering_id or None,
            selected_price_sheet_id=selected.source_price_sheet_id or None,
            selected_price_sheet_version_id=(
                selected.source_price_sheet_version_id or None
            ),
            unit_cost=unit_cost,
            extended_cost=extended,
            currency=selected.currency,
            pricing_status=pricing_status,
            pricing_confidence=confidence,
            selection_method=selection_method,
            selection_reason=selection_reason,
            effective_date=selected.effective_date,
            expiration_date=selected.expiration_date,
            import_date=selected.import_date,
            days_since_import=days_since,
            freshness_status=freshness,
            warnings=warnings,
            source_refs=[source_ref],
            manual_override=manual,
            selection=selection,
            confidence_rationale=rationale,
        )
        return priced, warnings

    def _allowance_priced_line(
        self,
        *,
        line: Any,
        source_equipment_id: str,
        canonical_product_id: str | None,
        manufacturer_id: str | None,
        unit_cost: float,
        reason: str,
        manual_override: dict[str, Any] | None,
    ) -> PricedEstimateLine:
        manual = self._manual_override(
            line=line, manual_override=manual_override, automatic_candidate=None
        )
        unit = manual.manual_unit_cost if manual is not None else unit_cost
        status = (
            PricingStatus.MANUAL_OVERRIDE
            if manual is not None
            else PricingStatus.ESTIMATED_ALLOWANCE
        )
        confidence = 0.55 if manual is None else 0.65
        rationale = [
            "Generic allowance pricing applied for deterministic placeholder coverage.",
            "Allowance pricing should be reviewed against current commercial records.",
        ]
        return PricedEstimateLine(
            estimate_line_id=line.line_id,
            source_equipment_id=source_equipment_id,
            canonical_product_id=canonical_product_id,
            manufacturer_id=manufacturer_id,
            quantity=float(line.quantity),
            selected_price_record_id=None,
            selected_vendor_offering_id=None,
            selected_price_sheet_id=None,
            selected_price_sheet_version_id=None,
            unit_cost=unit,
            extended_cost=round(unit * float(line.quantity), 2),
            currency="USD",
            pricing_status=status,
            pricing_confidence=confidence,
            selection_method="allowance" if manual is None else "manual_override",
            selection_reason=(
                reason
                if manual is None
                else "Manual override applied to allowance line."
            ),
            effective_date="",
            expiration_date="",
            import_date="",
            days_since_import=None,
            freshness_status=FreshnessStatus.UNKNOWN,
            warnings=[
                PricingWarning(
                    code="allowance_used",
                    message="Allowance pricing used in place of deterministic product pricing.",
                    severity="warning",
                )
            ],
            source_refs=[],
            manual_override=manual,
            selection=PriceSelection(
                selected_candidate_id=None,
                selection_method="allowance" if manual is None else "manual_override",
                selection_reason=reason,
                candidates=[],
                applied_rules=[],
            ),
            confidence_rationale=rationale,
        )

    def _no_pricing_line(
        self,
        *,
        line: Any,
        source_equipment_id: str,
        canonical_product_id: str | None,
        manufacturer_id: str | None,
        reason: str,
        warnings: list[PricingWarning],
        selection: PriceSelection | None = None,
    ) -> PricedEstimateLine:
        return PricedEstimateLine(
            estimate_line_id=line.line_id,
            source_equipment_id=source_equipment_id,
            canonical_product_id=canonical_product_id,
            manufacturer_id=manufacturer_id,
            quantity=float(line.quantity),
            selected_price_record_id=None,
            selected_vendor_offering_id=None,
            selected_price_sheet_id=None,
            selected_price_sheet_version_id=None,
            unit_cost=None,
            extended_cost=0.0,
            currency="USD",
            pricing_status=PricingStatus.NO_PRICING,
            pricing_confidence=0.2,
            selection_method="none",
            selection_reason=reason,
            effective_date="",
            expiration_date="",
            import_date="",
            days_since_import=None,
            freshness_status=FreshnessStatus.UNKNOWN,
            warnings=warnings,
            source_refs=[],
            manual_override=None,
            selection=selection,
            confidence_rationale=["No deterministic price record was selected."],
        )

    def _record_candidates(
        self,
        *,
        records: list[dict[str, Any]],
        commercial: dict[str, Any],
        freshness_rows: dict[str, dict[str, Any]],
        product_key: str,
        policy: dict[str, Any],
        manufacturer: str,
        model: str,
        source_equipment_id: str,
    ) -> list[PriceSelectionCandidate]:
        candidates: list[PriceSelectionCandidate] = []
        preferred_vendor = self._preferred_vendor(
            product_key=product_key,
            manufacturer=manufacturer,
            source_equipment_id=source_equipment_id,
            policy=policy,
        )

        for index, record in enumerate(records, start=1):
            version_id = self._safe(record.get("version_id"), "")
            version = dict(
                commercial.get("price_sheet_versions", {}).get(version_id) or {}
            )
            sheet_id = self._safe(version.get("price_sheet_id"), "")
            sheet = dict(commercial.get("price_sheets", {}).get(sheet_id) or {})
            vendor = self._safe(record.get("vendor"), "Unknown Vendor")

            lifecycle_status = self._safe(
                (commercial.get("product_lifecycle", {}).get(product_key) or {}).get(
                    "lifecycle_status"
                ),
                CommercialProductLifecycleStatus.UNKNOWN.value,
            )
            freshness_data = dict(freshness_rows.get(product_key) or {})
            freshness_status = self._candidate_freshness(
                record=record,
                freshness_data=freshness_data,
                lifecycle_status=lifecycle_status,
            )

            rank = self._rank_candidate(
                record=record,
                sheet=sheet,
                version=version,
                preferred_vendor=preferred_vendor,
                freshness_status=freshness_status,
            )
            confidence = self._candidate_confidence(
                record=record,
                sheet=sheet,
                version=version,
                freshness_status=freshness_status,
                preferred_vendor=preferred_vendor,
            )

            reason = self._candidate_reason(
                vendor=vendor,
                preferred_vendor=preferred_vendor,
                freshness=freshness_status,
                version_name=self._safe(version.get("version_name"), ""),
            )

            candidates.append(
                PriceSelectionCandidate(
                    candidate_id=f"record:{product_key}:{index}",
                    vendor=vendor,
                    unit_cost=self._float_or_none(record.get("cost")),
                    list_price=self._float_or_none(record.get("list_price")),
                    currency=self._safe(record.get("currency"), "USD"),
                    effective_date=self._safe(record.get("effective_date"), ""),
                    expiration_date=self._safe(record.get("expiration_date"), ""),
                    import_date=self._safe(version.get("import_date"), ""),
                    freshness_status=freshness_status,
                    lead_time=self._safe(record.get("lead_time"), ""),
                    availability=self._safe(record.get("availability"), "unknown"),
                    source_price_sheet_id=sheet_id,
                    source_price_sheet_version_id=version_id,
                    source_price_record_id=self._safe(
                        record.get("price_record_id"), ""
                    ),
                    source_vendor_offering_id=self._offering_id_for_record(
                        commercial,
                        record,
                    ),
                    confidence=confidence,
                    rank=rank,
                    selection_reason=reason,
                )
            )

        return candidates

    def _summary(self, priced_lines: list[PricedEstimateLine]) -> PricingSummary:
        material_subtotal = round(sum(item.extended_cost for item in priced_lines), 2)
        known_cost = round(
            sum(
                item.extended_cost
                for item in priced_lines
                if item.pricing_status
                not in {
                    PricingStatus.NO_PRICING,
                    PricingStatus.ESTIMATED_ALLOWANCE,
                }
            ),
            2,
        )
        allowance_cost = round(
            sum(
                item.extended_cost
                for item in priced_lines
                if item.pricing_status is PricingStatus.ESTIMATED_ALLOWANCE
            ),
            2,
        )
        unpriced_exposure = round(
            sum(
                item.extended_cost
                for item in priced_lines
                if item.pricing_status is PricingStatus.NO_PRICING
            ),
            2,
        )
        current_lines = sum(
            1
            for item in priced_lines
            if item.pricing_status
            in {PricingStatus.VERIFIED_CURRENT, PricingStatus.CURRENT_PRICE_SHEET}
        )
        current_coverage = (
            round((current_lines / len(priced_lines)) * 100, 4) if priced_lines else 0.0
        )
        confidence = (
            round(
                sum(item.pricing_confidence for item in priced_lines)
                / len(priced_lines),
                4,
            )
            if priced_lines
            else 0.0
        )
        return PricingSummary(
            material_subtotal=material_subtotal,
            known_cost=known_cost,
            allowance_cost=allowance_cost,
            unpriced_exposure=unpriced_exposure,
            current_pricing_coverage=current_coverage,
            commercial_confidence=confidence,
        )

    def _coverage(
        self, priced_lines: list[PricedEstimateLine]
    ) -> CommercialCoverageSummary:
        total = len(priced_lines)
        current = sum(
            1
            for item in priced_lines
            if item.pricing_status
            in {PricingStatus.VERIFIED_CURRENT, PricingStatus.CURRENT_PRICE_SHEET}
        )
        quoted = sum(
            1 for item in priced_lines if item.pricing_status is PricingStatus.QUOTED
        )
        historical = sum(
            1
            for item in priced_lines
            if item.pricing_status is PricingStatus.HISTORICAL_PRICE
        )
        stale = sum(
            1
            for item in priced_lines
            if item.pricing_status is PricingStatus.STALE_PRICE
        )
        allowances = sum(
            1
            for item in priced_lines
            if item.pricing_status is PricingStatus.ESTIMATED_ALLOWANCE
        )
        no_pricing = sum(
            1
            for item in priced_lines
            if item.pricing_status
            in {PricingStatus.NO_PRICING, PricingStatus.UNAVAILABLE}
        )

        priced_count = total - no_pricing
        total_value = sum(item.extended_cost for item in priced_lines)
        current_value = sum(
            item.extended_cost
            for item in priced_lines
            if item.pricing_status
            in {PricingStatus.VERIFIED_CURRENT, PricingStatus.CURRENT_PRICE_SHEET}
        )
        quoted_value = sum(
            item.extended_cost
            for item in priced_lines
            if item.pricing_status is PricingStatus.QUOTED
        )
        stale_estimated_value = sum(
            item.extended_cost
            for item in priced_lines
            if item.pricing_status
            in {
                PricingStatus.STALE_PRICE,
                PricingStatus.ESTIMATED_ALLOWANCE,
                PricingStatus.HISTORICAL_PRICE,
            }
        )

        return CommercialCoverageSummary(
            total_resolved_products=total,
            products_with_current_pricing=current,
            products_with_quoted_pricing=quoted,
            products_using_historical_pricing=historical,
            products_using_stale_pricing=stale,
            products_using_allowances=allowances,
            products_with_no_pricing=no_pricing,
            percentage_bom_lines_priced=(
                round((priced_count / total) * 100, 4) if total else 0.0
            ),
            percentage_material_value_current=(
                round((current_value / total_value) * 100, 4) if total_value else 0.0
            ),
            percentage_material_value_quoted=(
                round((quoted_value / total_value) * 100, 4) if total_value else 0.0
            ),
            percentage_material_value_stale_or_estimated=(
                round((stale_estimated_value / total_value) * 100, 4)
                if total_value
                else 0.0
            ),
            commercial_confidence=(
                round(
                    sum(item.pricing_confidence for item in priced_lines) / total,
                    4,
                )
                if total
                else 0.0
            ),
        )

    def _confidence(
        self,
        *,
        line: Any,
        resolution: ProductResolution | None,
        selected: PriceSelectionCandidate,
        pricing_status: PricingStatus,
        manual_override: PriceManualOverride | None,
    ) -> tuple[float, list[str]]:
        confidence = 0.65
        rationale = ["Base deterministic pricing confidence initialized."]

        resolution_confidence = (
            float(resolution.resolution_confidence)
            if resolution is not None
            else float(getattr(line, "confidence", 0.5) or 0.5)
        )
        confidence += (resolution_confidence - 0.5) * 0.3
        rationale.append(
            f"Resolution confidence contributed: {round(resolution_confidence, 4)}."
        )

        status_adjustments = {
            PricingStatus.QUOTED: 0.25,
            PricingStatus.VERIFIED_CURRENT: 0.2,
            PricingStatus.CURRENT_PRICE_SHEET: 0.15,
            PricingStatus.HISTORICAL_PRICE: -0.08,
            PricingStatus.STALE_PRICE: -0.2,
            PricingStatus.EXPIRED_PRICE: -0.3,
            PricingStatus.UNAVAILABLE: -0.4,
            PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET: -0.25,
            PricingStatus.ESTIMATED_ALLOWANCE: -0.22,
            PricingStatus.NO_PRICING: -0.5,
            PricingStatus.MANUAL_OVERRIDE: 0.0,
        }
        confidence += status_adjustments[pricing_status]
        rationale.append(f"Pricing status adjustment applied: {pricing_status.value}.")

        if selected.currency.upper() != "USD":
            confidence -= 0.08
            rationale.append("Currency mismatch from USD reduced confidence.")

        if selected.availability.lower() in {"out_of_stock", "unavailable"}:
            confidence -= 0.12
            rationale.append("Availability reduced confidence.")

        if manual_override is not None:
            confidence -= 0.05
            rationale.append(
                "Manual override applied; confidence reduced for review traceability."
            )

        final = round(max(0.0, min(confidence, 1.0)), 4)
        rationale.append(f"Final pricing confidence: {final}.")
        return final, rationale

    def _run_fingerprint(
        self,
        *,
        estimate: Estimate,
        resolutions: list[ProductResolution],
        commercial_state: dict[str, Any],
        policy: dict[str, Any],
        quotes: list[dict[str, Any]],
        overrides: dict[str, dict[str, Any]],
        allowances: dict[str, float],
    ) -> str:
        payload = {
            "estimate_lines": [item.to_dict() for item in estimate.all_lines()],
            "resolutions": [item.to_dict() for item in resolutions],
            "commercial_state": commercial_state,
            "policy": policy,
            "quotes": quotes,
            "overrides": overrides,
            "allowances": allowances,
            "policy_version": self.POLICY_VERSION,
            "as_of": self.as_of.isoformat(),
        }
        digest = hashlib.sha1(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return f"pricing-run:{digest}"

    def _commercial_records_for_product(
        self,
        *,
        commercial: dict[str, Any],
        product_key: str,
    ) -> list[dict[str, Any]]:
        records = []
        for item in commercial.get("price_records", {}).values():
            if self._safe(item.get("product"), "") == product_key:
                records.append(dict(item))
        return records

    def _quote_candidates(
        self,
        *,
        product_key: str,
        quotes: list[dict[str, Any]],
        project_id: str,
    ) -> list[dict[str, Any]]:
        rows = []
        for quote in quotes:
            if self._safe(quote.get("project_id"), "") != self._safe(project_id, ""):
                continue
            if self._safe(quote.get("product"), "") != product_key:
                continue
            if not bool(quote.get("active", True)):
                continue
            rows.append(dict(quote))
        rows.sort(
            key=lambda item: (
                0 if bool(item.get("exact_match", True)) else 1,
                self._safe(item.get("vendor"), "").lower(),
            )
        )
        return rows

    def _preferred_vendor(
        self,
        *,
        product_key: str,
        manufacturer: str,
        source_equipment_id: str,
        policy: dict[str, Any],
    ) -> str:
        by_project = dict(policy.get("project", {}))
        if source_equipment_id in by_project:
            return self._safe(by_project.get(source_equipment_id), "")

        by_product = dict(policy.get("product", {}))
        if product_key in by_product:
            return self._safe(by_product.get(product_key), "")

        by_manufacturer = dict(policy.get("manufacturer", {}))
        manufacturer_key = self._safe(manufacturer, "")
        if manufacturer_key in by_manufacturer:
            return self._safe(by_manufacturer.get(manufacturer_key), "")

        return self._safe(policy.get("organization"), "")

    def _rank_candidate(
        self,
        *,
        record: dict[str, Any],
        sheet: dict[str, Any],
        version: dict[str, Any],
        preferred_vendor: str,
        freshness_status: FreshnessStatus,
    ) -> int:
        vendor = self._safe(record.get("vendor"), "")
        availability = self._safe(record.get("availability"), "unknown").lower()
        version_id = self._safe(record.get("version_id"), "")
        is_latest = self._safe(sheet.get("active_version"), "") == version_id

        if availability in {"out_of_stock", "unavailable"}:
            return 8
        if freshness_status is FreshnessStatus.EXPIRED:
            return 7
        if freshness_status is FreshnessStatus.STALE:
            return 6
        if freshness_status is FreshnessStatus.MISSING_FROM_LATEST:
            return 5
        if (
            preferred_vendor
            and vendor.lower() == preferred_vendor.lower()
            and is_latest
        ):
            return 2
        if vendor.lower() in {"manufacturer catalog", "manufacturer"} and is_latest:
            return 4
        if is_latest:
            return 3
        return 5

    def _candidate_confidence(
        self,
        *,
        record: dict[str, Any],
        sheet: dict[str, Any],
        version: dict[str, Any],
        freshness_status: FreshnessStatus,
        preferred_vendor: str,
    ) -> float:
        confidence = 0.72
        vendor = self._safe(record.get("vendor"), "")
        if preferred_vendor and vendor.lower() == preferred_vendor.lower():
            confidence += 0.1
        if self._safe(sheet.get("active_version"), "") == self._safe(
            record.get("version_id"), ""
        ):
            confidence += 0.1
        if freshness_status is FreshnessStatus.REVIEW_RECOMMENDED:
            confidence -= 0.08
        elif freshness_status is FreshnessStatus.STALE:
            confidence -= 0.2
        elif freshness_status is FreshnessStatus.EXPIRED:
            confidence -= 0.28
        elif freshness_status is FreshnessStatus.MISSING_FROM_LATEST:
            confidence -= 0.12

        availability = self._safe(record.get("availability"), "unknown").lower()
        if availability in {"out_of_stock", "unavailable"}:
            confidence -= 0.2

        return round(max(0.0, min(confidence, 1.0)), 4)

    def _candidate_reason(
        self,
        *,
        vendor: str,
        preferred_vendor: str,
        freshness: FreshnessStatus,
        version_name: str,
    ) -> str:
        segments = [f"Candidate from {vendor}"]
        if preferred_vendor and vendor.lower() == preferred_vendor.lower():
            segments.append("preferred vendor policy matched")
        segments.append(f"freshness={freshness.value}")
        if version_name:
            segments.append(f"version={version_name}")
        return "; ".join(segments) + "."

    def _candidate_status(self, selected: PriceSelectionCandidate) -> PricingStatus:
        availability = selected.availability.lower()
        if availability in {"unavailable", "out_of_stock"}:
            return PricingStatus.UNAVAILABLE
        if selected.candidate_id.startswith("quote:"):
            return PricingStatus.QUOTED
        if selected.freshness_status is FreshnessStatus.EXPIRED:
            return PricingStatus.EXPIRED_PRICE
        if selected.freshness_status is FreshnessStatus.STALE:
            return PricingStatus.STALE_PRICE
        if selected.freshness_status is FreshnessStatus.MISSING_FROM_LATEST:
            return PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET
        if selected.rank <= 2:
            return PricingStatus.VERIFIED_CURRENT
        if selected.rank <= 4:
            return PricingStatus.CURRENT_PRICE_SHEET
        return PricingStatus.HISTORICAL_PRICE

    def _candidate_freshness(
        self,
        *,
        record: dict[str, Any],
        freshness_data: dict[str, Any],
        lifecycle_status: str,
    ) -> FreshnessStatus:
        expiration = self._date_from_text(self._safe(record.get("expiration_date"), ""))
        if expiration is not None and expiration < self.as_of:
            return FreshnessStatus.EXPIRED

        if (
            lifecycle_status
            == CommercialProductLifecycleStatus.MISSING_FROM_LATEST_PRICE_SHEET.value
        ):
            return FreshnessStatus.MISSING_FROM_LATEST

        mapped = self._safe(freshness_data.get("current_status"), "")
        if mapped == KnowledgeFreshnessStatus.FRESH.value:
            return FreshnessStatus.FRESH
        if mapped == KnowledgeFreshnessStatus.REVIEW_RECOMMENDED.value:
            return FreshnessStatus.REVIEW_RECOMMENDED
        if mapped == KnowledgeFreshnessStatus.STALE.value:
            return FreshnessStatus.STALE
        return FreshnessStatus.UNKNOWN

    def _manual_override(
        self,
        *,
        line: Any,
        manual_override: dict[str, Any] | None,
        automatic_candidate: PriceSelectionCandidate | None,
    ) -> PriceManualOverride | None:
        if not manual_override:
            return None
        if manual_override.get("manual_unit_cost") is None:
            return None

        return PriceManualOverride(
            original_automatic_selection=(
                automatic_candidate.to_dict()
                if automatic_candidate is not None
                else None
            ),
            manual_unit_cost=float(manual_override.get("manual_unit_cost", 0.0) or 0.0),
            selected_vendor=self._safe(
                manual_override.get("selected_vendor"),
                self._safe(getattr(line, "manufacturer", ""), ""),
            ),
            override_reason=self._safe(
                manual_override.get("override_reason"),
                "Estimator override",
            ),
            reviewer_placeholder=self._safe(
                manual_override.get("reviewer_placeholder"),
                "Estimator",
            ),
            timestamp=self._safe(manual_override.get("timestamp"), self._now_iso()),
            source_reference=self._safe(
                manual_override.get("source_reference"),
                "manual override",
            ),
        )

    def _freshness_info(
        self,
        *,
        selected: PriceSelectionCandidate,
        product_key: str,
        freshness_rows: dict[str, dict[str, Any]],
    ) -> tuple[FreshnessStatus, int | None]:
        freshness = selected.freshness_status
        row = dict(freshness_rows.get(product_key) or {})
        days_since = row.get("days_since_import")
        days = int(days_since) if isinstance(days_since, int) else None
        return freshness, days

    def _comparison_status(
        self,
        commercial: dict[str, Any],
        version_id: str,
        product_key: str,
    ) -> str:
        version = dict(commercial.get("price_sheet_versions", {}).get(version_id) or {})
        comparison = dict(version.get("comparison_summary") or {})

        if product_key in list(comparison.get("products_added") or []):
            return "Added in latest version"
        if product_key in list(comparison.get("products_removed") or []):
            return "Missing from latest version"

        updated = {
            item.get("product")
            for item in list(comparison.get("products_updated") or [])
        }
        unchanged = set(comparison.get("products_unchanged") or [])

        if product_key in updated:
            return "Updated in latest version"
        if product_key in unchanged:
            return "Unchanged"
        return "Historical only"

    def _source_row_for_record(
        self, commercial: dict[str, Any], record_id: str
    ) -> int | None:
        record = dict(commercial.get("price_records", {}).get(record_id) or {})
        source_row = record.get("source_row")
        return int(source_row) if isinstance(source_row, int) else None

    def _offering_id_for_record(
        self, commercial: dict[str, Any], record: dict[str, Any]
    ) -> str:
        product = self._safe(record.get("product"), "")
        vendor = self._safe(record.get("vendor"), "")
        sku = self._safe(record.get("vendor_sku"), "")
        for offering_id, offering in commercial.get("vendor_offerings", {}).items():
            if (
                self._safe(offering.get("product"), "") == product
                and self._safe(offering.get("vendor"), "") == vendor
                and self._safe(offering.get("vendor_sku"), "") == sku
            ):
                return str(offering_id)
        return ""

    @staticmethod
    def _product_key(
        *,
        canonical_product_id: str | None,
        manufacturer: str,
        model: str,
    ) -> str:
        if canonical_product_id:
            if "::" in canonical_product_id:
                return canonical_product_id
        return f"{manufacturer}::{model}"

    @staticmethod
    def _safe(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        text = str(value).strip().replace("$", "").replace(",", "")
        if not text:
            return None
        try:
            return round(float(text), 4)
        except ValueError:
            return None

    @staticmethod
    def _date_from_text(value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            for pattern in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"]:
                try:
                    return datetime.strptime(value, pattern).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
