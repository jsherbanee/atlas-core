"""Scope reconciliation helpers for Atlas Core."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import DeviceSchedule, Equipment, Keynote, Legend


class ReconciliationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ReconciliationIssue:
    issue_id: str
    message: str
    severity: ReconciliationSeverity = ReconciliationSeverity.MEDIUM
    source: str = "scope_reconciliation"
    target_id: str | None = None
    suggested_action: str | None = None
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.issue_id = self._normalize_required_text("issue_id", self.issue_id)
        self.message = self._normalize_required_text("message", self.message)

        if not isinstance(self.severity, ReconciliationSeverity):
            self.severity = ReconciliationSeverity(str(self.severity).strip().lower())

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = enum_value(self.severity)
        return data

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class ScopeReconciliationService:
    def reconcile(
        self,
        equipment: list[Equipment] | None = None,
        device_schedules: list[DeviceSchedule] | None = None,
        keynotes: list[Keynote] | None = None,
        legends: list[Legend] | None = None,
    ) -> list[ReconciliationIssue]:
        equipment_items = list(equipment or [])
        schedule_items = list(device_schedules or [])
        keynote_items = list(keynotes or [])
        legend_items = list(legends or [])

        if (
            not equipment_items
            and not schedule_items
            and not keynote_items
            and not legend_items
        ):
            return []

        issues: list[ReconciliationIssue] = []
        emitted_issue_ids: set[str] = set()

        equipment_categories = {
            self._normalize_value(enum_value(item.category))
            for item in equipment_items
            if self._normalize_value(enum_value(item.category))
        }

        for keynote in keynote_items:
            category = self._normalize_value(keynote.equipment_category)
            if category and category not in equipment_categories:
                self._add_issue(
                    issues,
                    emitted_issue_ids,
                    ReconciliationIssue(
                        issue_id=f"keynote_missing_equipment_category:{category}",
                        message=(
                            "Keynote references equipment category not found in "
                            "equipment matrix."
                        ),
                        severity=ReconciliationSeverity.MEDIUM,
                        target_id=keynote.keynote_id,
                    ),
                )

        for legend in legend_items:
            for legend_item in legend.items:
                category = self._normalize_value(legend_item.equipment_category)
                if category and category not in equipment_categories:
                    self._add_issue(
                        issues,
                        emitted_issue_ids,
                        ReconciliationIssue(
                            issue_id=(
                                "legend_missing_equipment_category:" f"{category}"
                            ),
                            message=(
                                "Legend references equipment category not found "
                                "in equipment matrix."
                            ),
                            severity=ReconciliationSeverity.MEDIUM,
                            target_id=legend_item.legend_item_id,
                        ),
                    )

        for schedule in schedule_items:
            for schedule_item in schedule.items:
                manufacturer = self._normalize_value(schedule_item.manufacturer)
                model = self._normalize_value(schedule_item.model)
                if not manufacturer and not model:
                    continue

                if not self._has_matching_equipment(
                    manufacturer=manufacturer,
                    model=model,
                    equipment=equipment_items,
                ):
                    self._add_issue(
                        issues,
                        emitted_issue_ids,
                        ReconciliationIssue(
                            issue_id=(
                                "device_schedule_item_missing_equipment:"
                                f"{schedule_item.item_id}"
                            ),
                            message=(
                                "Device schedule item is not represented in "
                                "equipment matrix."
                            ),
                            severity=ReconciliationSeverity.HIGH,
                            target_id=schedule_item.item_id,
                        ),
                    )

        grouped_reference_gaps: dict[
            tuple[str, str | None, str | None], list[Equipment]
        ]
        grouped_reference_gaps = {}
        for equipment_item in equipment_items:
            drawing_reference = self._normalize_value(equipment_item.drawing_reference)
            specification_reference = self._normalize_value(
                equipment_item.specification_reference
            )
            if drawing_reference or specification_reference:
                continue

            group_key = (
                self._normalize_value(enum_value(equipment_item.category)) or "unknown",
                self._normalize_value(getattr(equipment_item, "room_id", None)),
                self._normalize_value(getattr(equipment_item, "system_id", None)),
            )
            grouped_reference_gaps.setdefault(group_key, []).append(equipment_item)

        for (
            category,
            room_id,
            system_id,
        ), grouped_items in grouped_reference_gaps.items():
            sample = grouped_items[0]
            sample_id = self._normalize_value(sample.equipment_id) or "equipment"
            context = [f"category={category}"]
            if room_id:
                context.append(f"room={room_id}")
            if system_id:
                context.append(f"system={system_id}")

            self._add_issue(
                issues,
                emitted_issue_ids,
                ReconciliationIssue(
                    issue_id=(
                        "equipment_missing_drawing_or_specification_reference:"
                        f"{category}:{room_id or 'no-room'}:{system_id or 'no-system'}"
                    ),
                    message=(
                        "Equipment has no drawing or specification reference for "
                        f"{len(grouped_items)} item(s) ({'; '.join(context)})."
                    ),
                    severity=ReconciliationSeverity.LOW,
                    target_id=sample_id,
                    suggested_action=(
                        "Link the grouped items to their governing drawing or "
                        "specification sources."
                    ),
                ),
            )

        return issues

    @classmethod
    def _add_issue(
        cls,
        issues: list[ReconciliationIssue],
        emitted_issue_ids: set[str],
        issue: ReconciliationIssue,
    ) -> None:
        if issue.issue_id in emitted_issue_ids:
            return

        emitted_issue_ids.add(issue.issue_id)
        issues.append(issue)

    @classmethod
    def _has_matching_equipment(
        cls,
        manufacturer: str | None,
        model: str | None,
        equipment: list[Equipment],
    ) -> bool:
        for item in equipment:
            equipment_manufacturer = cls._normalize_value(item.manufacturer)
            equipment_model = cls._normalize_value(item.model)

            if manufacturer and equipment_manufacturer != manufacturer:
                continue
            if model and equipment_model != model:
                continue

            return True

        return False

    @staticmethod
    def _normalize_value(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None
