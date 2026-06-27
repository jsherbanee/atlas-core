"""Rule-based resolution suggestions for Atlas Core."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResolutionAction(str, Enum):
    """Action recommended by an Atlas resolver rule."""

    ADD_PLACEHOLDER = "add_placeholder"
    MARK_FOR_REVIEW = "mark_for_review"
    ADD_ASSUMPTION = "add_assumption"


@dataclass
class Resolution:
    rule_id: str
    action: ResolutionAction
    target_id: str
    message: str
    confidence: float = 0.75
    suggested_category: str | None = None
    suggested_description: str | None = None
    suggested_manufacturer: str | None = None
    suggested_model: str | None = None

    def __post_init__(self) -> None:
        self.rule_id = self._normalize_required_text("rule_id", self.rule_id)
        self.target_id = self._normalize_required_text("target_id", self.target_id)
        self.message = self._normalize_required_text("message", self.message)

        if not isinstance(self.action, ResolutionAction):
            self.action = ResolutionAction(self.action)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()


class Resolver:
    def resolve(
        self,
        equipment: list[Any],
        systems: list[Any] | None = None,
    ) -> list[Resolution]:
        del systems

        resolutions: list[Resolution] = []
        emitted: set[tuple[str, str]] = set()

        for index, item in enumerate(equipment):
            target_id = self._target_id(item, index)
            category = self._value(item, "category")
            system_id = self._value(item, "system_id")
            room_id = self._value(item, "room_id")

            if category == "speaker" and system_id and not self._has_category_in_scope(
                equipment, "amplifier", "system_id", system_id
            ):
                self._add_resolution(
                    resolutions,
                    emitted,
                    rule_id="RULE-001",
                    action=ResolutionAction.ADD_PLACEHOLDER,
                    target_id=target_id,
                    message=(
                        "Passive speakers require an amplifier. "
                        "No amplifier was detected in this system."
                    ),
                    suggested_category="amplifier",
                )

            if category == "display" and room_id and not self._has_category_in_scope(
                equipment, "mount", "room_id", room_id
            ):
                self._add_resolution(
                    resolutions,
                    emitted,
                    rule_id="RULE-002",
                    action=ResolutionAction.ADD_PLACEHOLDER,
                    target_id=target_id,
                    message=(
                        "Display requires a mount or mounting allowance. "
                        "No mount was detected in this room."
                    ),
                    suggested_category="mount",
                    suggested_manufacturer="Chief",
                )

            if category == "projector" and room_id and not self._has_category_in_scope(
                equipment, "mount", "room_id", room_id
            ):
                self._add_resolution(
                    resolutions,
                    emitted,
                    rule_id="RULE-003",
                    action=ResolutionAction.ADD_PLACEHOLDER,
                    target_id=target_id,
                    message=(
                        "Projector requires mounting hardware and review of throw, "
                        "lens, power, and structure."
                    ),
                    suggested_category="mount",
                    suggested_manufacturer="Chief",
                )

            if category == "drapery":
                self._add_resolution(
                    resolutions,
                    emitted,
                    rule_id="RULE-004",
                    action=ResolutionAction.MARK_FOR_REVIEW,
                    target_id=target_id,
                    message=(
                        "Drapery scope requires review of track, hardware, "
                        "infrastructure, support, and site conditions."
                    ),
                )

            confidence = self._numeric_value(item, "confidence")
            if confidence is not None and confidence < 0.6:
                self._add_resolution(
                    resolutions,
                    emitted,
                    rule_id="RULE-005",
                    action=ResolutionAction.MARK_FOR_REVIEW,
                    target_id=target_id,
                    message=(
                        "Equipment confidence is below threshold and requires "
                        "estimator review."
                    ),
                )

        return resolutions

    @classmethod
    def _add_resolution(
        cls,
        resolutions: list[Resolution],
        emitted: set[tuple[str, str]],
        *,
        rule_id: str,
        action: ResolutionAction,
        target_id: str,
        message: str,
        suggested_category: str | None = None,
        suggested_manufacturer: str | None = None,
    ) -> None:
        key = (rule_id, target_id)
        if key in emitted:
            return

        emitted.add(key)
        resolutions.append(
            Resolution(
                rule_id=rule_id,
                action=action,
                target_id=target_id,
                message=message,
                suggested_category=suggested_category,
                suggested_manufacturer=suggested_manufacturer,
            )
        )

    @classmethod
    def _has_category_in_scope(
        cls,
        equipment: list[Any],
        category: str,
        scope_field: str,
        scope_value: Any,
    ) -> bool:
        return any(
            cls._value(item, "category") == category
            and cls._value(item, scope_field) == scope_value
            for item in equipment
        )

    @staticmethod
    def _as_dict(item: Any) -> dict[str, Any]:
        if item is None or not hasattr(item, "to_dict"):
            return {}

        return item.to_dict()

    @classmethod
    def _value(cls, item: Any, field_name: str, default: Any = "") -> Any:
        if item is None:
            return default

        data = cls._as_dict(item)
        value = data.get(field_name, getattr(item, field_name, default))

        if value is None:
            return default

        if isinstance(value, Enum):
            return value.value

        return value

    @classmethod
    def _numeric_value(cls, item: Any, field_name: str) -> float | None:
        value = cls._value(item, field_name, None)
        if isinstance(value, (int, float)):
            return value

        return None

    @classmethod
    def _target_id(cls, item: Any, index: int) -> str:
        value = cls._value(item, "equipment_id")
        if isinstance(value, str) and value.strip():
            return value

        return f"equipment-{index + 1}"
