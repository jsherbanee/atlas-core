"""Scope gap detection helpers for Atlas Core."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.services.cross_reference_service import CrossReference


class ScopeGapSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ScopeGap:
    gap_id: str
    target_id: str
    message: str
    severity: ScopeGapSeverity = ScopeGapSeverity.MEDIUM
    confidence: float = 0.75
    suggested_action: str | None = None

    def __post_init__(self) -> None:
        self.gap_id = self._normalize_required_text("gap_id", self.gap_id)
        self.target_id = self._normalize_required_text("target_id", self.target_id)
        self.message = self._normalize_required_text("message", self.message)

        if not isinstance(self.severity, ScopeGapSeverity):
            self.severity = ScopeGapSeverity(self.severity)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class ScopeGapService:
    def detect_gaps(
        self,
        equipment: list[Equipment] | None = None,
        cross_references: list[CrossReference] | None = None,
    ) -> list[ScopeGap]:
        equipment_items = list(equipment or [])
        cross_reference_items = list(cross_references or [])
        gaps: list[ScopeGap] = []
        emitted: set[tuple[str, str]] = set()

        for item in equipment_items:
            category = self._value(item.category)
            if category == EquipmentCategory.PROJECTOR.value:
                if not self._has_mount_in_room(equipment_items, item.room_id):
                    self._add_gap(
                        gaps,
                        emitted,
                        ScopeGap(
                            gap_id="projector_missing_mount",
                            target_id=item.equipment_id,
                            message=(
                                "Projector is present, but no mount or "
                                "mounting allowance was detected in the same room."
                            ),
                            severity=ScopeGapSeverity.HIGH,
                            suggested_action=(
                                "Add projector mount, lens/throw review, power "
                                "coordination, and structural review allowance."
                            ),
                        ),
                    )

            if category == EquipmentCategory.DISPLAY.value:
                if not self._has_mount_in_room(equipment_items, item.room_id):
                    self._add_gap(
                        gaps,
                        emitted,
                        ScopeGap(
                            gap_id="display_missing_mount",
                            target_id=item.equipment_id,
                            message=(
                                "Display is present, but no display mount was "
                                "detected in the same room."
                            ),
                            severity=ScopeGapSeverity.MEDIUM,
                            suggested_action=(
                                "Add display mount and wall backing/PAC box review "
                                "allowance."
                            ),
                        ),
                    )

            if category == EquipmentCategory.SPEAKER.value:
                if not self._has_amplifier_in_system(
                    equipment_items,
                    item.system_id,
                ):
                    self._add_gap(
                        gaps,
                        emitted,
                        ScopeGap(
                            gap_id="speaker_missing_amplifier",
                            target_id=item.equipment_id,
                            message=(
                                "Speaker equipment is present, but no amplifier "
                                "was detected in the same system."
                            ),
                            severity=ScopeGapSeverity.HIGH,
                            suggested_action=(
                                "Add amplifier channel capacity review and "
                                "placeholder amplifier."
                            ),
                        ),
                    )

            if category == EquipmentCategory.DRAPERY.value:
                if not self._has_cross_reference(
                    item.equipment_id,
                    cross_reference_items,
                ):
                    self._add_gap(
                        gaps,
                        emitted,
                        ScopeGap(
                            gap_id="drapery_missing_cross_reference",
                            target_id=item.equipment_id,
                            message=(
                                "Drapery scope is present, but drawing/spec cross "
                                "references are incomplete."
                            ),
                            severity=ScopeGapSeverity.HIGH,
                            suggested_action=(
                                "Review drapery track, hardware, structural "
                                "support, fire rating, and site conditions."
                            ),
                        ),
                    )

        return gaps

    @classmethod
    def _add_gap(
        cls,
        gaps: list[ScopeGap],
        emitted: set[tuple[str, str]],
        gap: ScopeGap,
    ) -> None:
        key = (gap.gap_id, gap.target_id)
        if key in emitted:
            return

        emitted.add(key)
        gaps.append(gap)

    @classmethod
    def _has_mount_in_room(
        cls,
        equipment: list[Equipment],
        room_id: str | None,
    ) -> bool:
        if room_id is None:
            return False

        return any(
            item.room_id == room_id
            and cls._value(item.category) == EquipmentCategory.MOUNT.value
            for item in equipment
        )

    @classmethod
    def _has_amplifier_in_system(
        cls,
        equipment: list[Equipment],
        system_id: str | None,
    ) -> bool:
        if system_id is None:
            return False

        return any(
            item.system_id == system_id
            and cls._value(item.category) == EquipmentCategory.AMPLIFIER.value
            for item in equipment
        )

    @staticmethod
    def _has_cross_reference(
        equipment_id: str,
        cross_references: list[CrossReference],
    ) -> bool:
        return any(
            reference.source_id == equipment_id
            or reference.target_id == equipment_id
            for reference in cross_references
        )

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)
