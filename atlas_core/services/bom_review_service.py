"""Canonical BOM review workflow helpers for estimator-facing analysis output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import io
import json
from pathlib import Path
from typing import Any

BOM_HEADERS = [
    "bom_item_id",
    "manufacturer",
    "model",
    "description",
    "quantity",
    "system",
    "room_or_area",
    "source_documents",
    "source_pages",
    "drawing_references",
    "specification_references",
    "confidence",
    "quantity_confidence",
    "scope_status",
    "responsibility",
    "completeness_status",
    "warnings",
    "related_rfi_candidates",
]

COMPLETE = "complete"
MISSING_MANUFACTURER = "missing_manufacturer"
MISSING_MODEL = "missing_model"
MISSING_QUANTITY = "missing_quantity"
GENERIC_DESCRIPTION = "generic_description"
CONFLICTING_QUANTITY = "conflicting_quantity"
DRAWING_ONLY = "drawing_only"
SPECIFICATION_ONLY = "specification_only"
SCHEDULE_ONLY = "schedule_only"
UNRESOLVED = "unresolved"


@dataclass
class CanonicalBomItem:
    bom_item_id: str
    manufacturer: str
    model: str
    description: str
    quantity: str
    system: str
    room_or_area: str
    source_documents: list[str]
    source_pages: list[str]
    drawing_references: list[str]
    specification_references: list[str]
    confidence: float
    quantity_confidence: float
    scope_status: str
    responsibility: str
    completeness_status: str
    warnings: list[str]
    related_rfi_candidates: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BomReviewService:
    def build_items(
        self,
        equipment_rows: list[dict[str, Any]] | None,
        resolver_rows: list[dict[str, Any]] | None = None,
        source_references: list[dict[str, Any]] | None = None,
        rfi_rows: list[dict[str, Any]] | None = None,
    ) -> list[CanonicalBomItem]:
        rows = list(equipment_rows or [])
        resolver = list(resolver_rows or [])
        refs = list(source_references or [])
        rfis = list(rfi_rows or [])
        quantity_conflicts = self._quantity_conflicts_by_target(resolver)

        seen_ids: set[str] = set()
        items: list[CanonicalBomItem] = []
        for index, row in enumerate(rows, start=1):
            bom_item_id = self._normalize_bom_item_id(
                row.get("equipment_id") or row.get("bom_item_id") or f"bom-{index}",
                seen_ids,
            )

            drawing_refs = self._split_refs(row.get("drawing_references"))
            if not drawing_refs:
                drawing_refs = self._split_refs(row.get("drawing_reference"))

            specification_refs = self._split_refs(row.get("specification_references"))
            if not specification_refs:
                specification_refs = self._split_refs(
                    row.get("specification_reference")
                )

            schedule_refs = self._split_refs(
                row.get("schedule_references") or row.get("schedule_reference")
            )

            quantity_value = row.get("quantity")
            quantity_text = self._quantity_text(quantity_value)

            conflict = quantity_conflicts.get(
                bom_item_id,
                quantity_conflicts.get(str(row.get("equipment_id") or ""), None),
            )

            manufacturer = self._normalized_text(row.get("manufacturer"))
            model = self._normalized_text(row.get("model"))
            description = self._normalized_text(row.get("description"), "n/a")
            confidence = self._normalized_confidence(row.get("confidence"))
            status = self._normalized_text(
                row.get("current_status") or row.get("status"),
                "needs_review",
            )
            responsibility = self._normalized_text(row.get("responsibility"), "unknown")

            related_rfis = self._related_rfi_candidates(
                row=row,
                rfi_rows=rfis,
                explicit_refs=self._split_refs(row.get("potential_rfis")),
            )

            source_documents, source_pages = self._source_evidence(
                row=row,
                source_references=refs,
                drawing_refs=drawing_refs,
                specification_refs=specification_refs,
                schedule_refs=schedule_refs,
            )

            warnings = self._split_refs(row.get("warnings"))
            if conflict:
                warnings.append(
                    "Quantity conflict remains visible; observed values: "
                    + self._normalized_text(conflict.get("observed_values"), "unknown")
                )

            completeness_status = self._completeness_status(
                manufacturer=manufacturer,
                model=model,
                quantity_text=quantity_text,
                description=description,
                drawing_refs=drawing_refs,
                specification_refs=specification_refs,
                schedule_refs=schedule_refs,
                has_quantity_conflict=bool(conflict),
            )

            if completeness_status == GENERIC_DESCRIPTION:
                warnings.append("Description appears generic and requires review.")

            if completeness_status == UNRESOLVED:
                warnings.append(
                    "Insufficient traceable source references for this line."
                )

            quantity_confidence = self._quantity_confidence(
                quantity_text=quantity_text,
                has_quantity_conflict=bool(conflict),
                confidence=confidence,
            )

            items.append(
                CanonicalBomItem(
                    bom_item_id=bom_item_id,
                    manufacturer=manufacturer,
                    model=model,
                    description=description,
                    quantity=quantity_text,
                    system=self._normalized_text(
                        row.get("system") or row.get("system_id"),
                        "Unknown",
                    ),
                    room_or_area=self._normalized_text(
                        row.get("room_or_area")
                        or row.get("room")
                        or row.get("room_id"),
                        "Unknown",
                    ),
                    source_documents=source_documents,
                    source_pages=source_pages,
                    drawing_references=sorted(drawing_refs),
                    specification_references=sorted(specification_refs),
                    confidence=confidence,
                    quantity_confidence=quantity_confidence,
                    scope_status=status,
                    responsibility=responsibility,
                    completeness_status=completeness_status,
                    warnings=sorted({item for item in warnings if item}),
                    related_rfi_candidates=related_rfis,
                )
            )

        return sorted(items, key=lambda item: item.bom_item_id)

    @staticmethod
    def completeness_metrics(items: list[CanonicalBomItem]) -> dict[str, int]:
        total = len(items)
        complete_lines = sum(
            1 for item in items if item.completeness_status == COMPLETE
        )
        conflicting_lines = sum(
            1 for item in items if item.completeness_status == CONFLICTING_QUANTITY
        )
        incomplete_lines = sum(
            1
            for item in items
            if item.completeness_status not in {COMPLETE, CONFLICTING_QUANTITY}
        )
        return {
            "total_candidate_bom_lines": total,
            "complete_lines": complete_lines,
            "incomplete_lines": incomplete_lines,
            "conflicting_lines": conflicting_lines,
            "drawing_only_items": sum(
                1 for item in items if item.completeness_status == DRAWING_ONLY
            ),
            "specification_only_items": sum(
                1 for item in items if item.completeness_status == SPECIFICATION_ONLY
            ),
            "unresolved_items": sum(
                1 for item in items if item.completeness_status == UNRESOLVED
            ),
        }

    def to_csv_text(self, items: list[CanonicalBomItem]) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=BOM_HEADERS)
        writer.writeheader()
        for row in self._deterministic_rows(items):
            writer.writerow(row)
        return buffer.getvalue()

    def to_json_text(self, items: list[CanonicalBomItem]) -> str:
        payload = {
            "bom_items": self._deterministic_rows(items),
            "metrics": self.completeness_metrics(items),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def export_bom_items_csv(
        self,
        items: list[CanonicalBomItem],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv_text(items), encoding="utf-8")
        return path

    def export_bom_items_json(
        self,
        items: list[CanonicalBomItem],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json_text(items), encoding="utf-8")
        return path

    @classmethod
    def _deterministic_rows(
        cls,
        items: list[CanonicalBomItem],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in sorted(items, key=lambda value: value.bom_item_id):
            payload = item.to_dict()
            rows.append(
                {
                    "bom_item_id": payload["bom_item_id"],
                    "manufacturer": payload["manufacturer"],
                    "model": payload["model"],
                    "description": payload["description"],
                    "quantity": payload["quantity"],
                    "system": payload["system"],
                    "room_or_area": payload["room_or_area"],
                    "source_documents": "|".join(payload["source_documents"]),
                    "source_pages": "|".join(payload["source_pages"]),
                    "drawing_references": "|".join(payload["drawing_references"]),
                    "specification_references": "|".join(
                        payload["specification_references"]
                    ),
                    "confidence": payload["confidence"],
                    "quantity_confidence": payload["quantity_confidence"],
                    "scope_status": payload["scope_status"],
                    "responsibility": payload["responsibility"],
                    "completeness_status": payload["completeness_status"],
                    "warnings": "|".join(payload["warnings"]),
                    "related_rfi_candidates": "|".join(
                        payload["related_rfi_candidates"]
                    ),
                }
            )
        return rows

    @classmethod
    def _normalize_bom_item_id(cls, raw_value: Any, seen_ids: set[str]) -> str:
        base = cls._normalized_text(raw_value, "bom-item")
        if base not in seen_ids:
            seen_ids.add(base)
            return base
        suffix = 2
        while f"{base}-{suffix}" in seen_ids:
            suffix += 1
        unique = f"{base}-{suffix}"
        seen_ids.add(unique)
        return unique

    @classmethod
    def _quantity_conflicts_by_target(
        cls,
        resolver_rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        conflicts: dict[str, dict[str, Any]] = {}
        for row in resolver_rows:
            field_name = cls._normalized_text(row.get("field"), "")
            if "quantity" not in field_name.lower():
                continue
            target_id = cls._normalized_text(row.get("target_id"), "")
            if not target_id:
                continue
            conflicts[target_id] = row
            if ":" in target_id:
                _, object_id = target_id.split(":", 1)
                conflicts[object_id] = row
        return conflicts

    @classmethod
    def _source_evidence(
        cls,
        row: dict[str, Any],
        source_references: list[dict[str, Any]],
        drawing_refs: list[str],
        specification_refs: list[str],
        schedule_refs: list[str],
    ) -> tuple[list[str], list[str]]:
        tokens = {
            cls._normalized_text(row.get("equipment_id"), "").lower(),
            cls._normalized_text(row.get("manufacturer"), "").lower(),
            cls._normalized_text(row.get("model"), "").lower(),
            cls._normalized_text(row.get("description"), "").lower(),
            *[item.lower() for item in drawing_refs],
            *[item.lower() for item in specification_refs],
            *[item.lower() for item in schedule_refs],
        }
        tokens = {item for item in tokens if item and len(item) > 2}

        documents: set[str] = set(
            cls._split_refs(row.get("source_documents") or row.get("source_file"))
        )
        pages: set[str] = set(
            cls._split_refs(row.get("source_pages") or row.get("page"))
        )

        for ref in source_references:
            source_file = cls._normalized_text(ref.get("source_file"), "")
            page = cls._normalized_text(ref.get("page") or ref.get("page_number"), "")
            excerpt = cls._normalized_text(ref.get("excerpt"), "").lower()
            haystacks = [source_file.lower(), excerpt]
            if not tokens or any(
                any(token in hay for token in tokens) for hay in haystacks
            ):
                if source_file:
                    documents.add(source_file)
                if page:
                    pages.add(page)

        return sorted(documents), sorted(pages)

    @classmethod
    def _related_rfi_candidates(
        cls,
        row: dict[str, Any],
        rfi_rows: list[dict[str, Any]],
        explicit_refs: list[str],
    ) -> list[str]:
        candidates = set(explicit_refs)
        tokens = {
            cls._normalized_text(row.get("equipment_id"), "").lower(),
            cls._normalized_text(row.get("manufacturer"), "").lower(),
            cls._normalized_text(row.get("model"), "").lower(),
        }
        tokens = {item for item in tokens if item}
        for rfi in rfi_rows:
            rfi_id = cls._normalized_text(rfi.get("rfi_id") or rfi.get("title"), "")
            if not rfi_id:
                continue
            text = str(rfi).lower()
            if tokens and any(token in text for token in tokens):
                candidates.add(rfi_id)
        return sorted(candidates)

    @classmethod
    def _completeness_status(
        cls,
        manufacturer: str,
        model: str,
        quantity_text: str,
        description: str,
        drawing_refs: list[str],
        specification_refs: list[str],
        schedule_refs: list[str],
        has_quantity_conflict: bool,
    ) -> str:
        if has_quantity_conflict:
            return CONFLICTING_QUANTITY
        if cls._is_missing(manufacturer):
            return MISSING_MANUFACTURER
        if cls._is_missing(model):
            return MISSING_MODEL
        if cls._is_missing(quantity_text):
            return MISSING_QUANTITY
        if cls._is_generic_description(description):
            return GENERIC_DESCRIPTION

        has_drawing = bool(drawing_refs)
        has_specification = bool(specification_refs)
        has_schedule = bool(schedule_refs)

        if has_drawing and not has_specification and not has_schedule:
            return DRAWING_ONLY
        if has_specification and not has_drawing and not has_schedule:
            return SPECIFICATION_ONLY
        if has_schedule and not has_drawing and not has_specification:
            return SCHEDULE_ONLY
        if not has_drawing and not has_specification and not has_schedule:
            return UNRESOLVED
        return COMPLETE

    @classmethod
    def _quantity_confidence(
        cls,
        quantity_text: str,
        has_quantity_conflict: bool,
        confidence: float,
    ) -> float:
        if has_quantity_conflict:
            return 0.3
        if cls._is_missing(quantity_text):
            return 0.0
        return round(max(0.1, min(confidence, 1.0)), 2)

    @staticmethod
    def _is_generic_description(description: str) -> bool:
        normalized = description.strip().lower()
        if normalized in {"n/a", "unknown", "equipment", "device", "item"}:
            return True
        return len(normalized) < 8

    @staticmethod
    def _is_missing(value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in {"", "n/a", "unknown", "none", "null"}

    @classmethod
    def _normalized_confidence(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            numeric = float(value)
        else:
            text = cls._normalized_text(value, "")
            numeric = 0.0
            if text:
                try:
                    numeric = float(text)
                except ValueError:
                    numeric = 0.0
        numeric = max(0.0, min(numeric, 1.0))
        return round(numeric, 2)

    @classmethod
    def _quantity_text(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return cls._normalized_text(value, "")

    @staticmethod
    def _normalized_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _split_refs(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            refs = [str(item).strip() for item in value if str(item).strip()]
            return sorted(set(refs))
        text = str(value).replace("|", ",").replace(";", ",")
        refs = [item.strip() for item in text.split(",") if item.strip()]
        return sorted(set(refs))
