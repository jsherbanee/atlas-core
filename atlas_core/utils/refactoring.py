"""Small shared helpers for behavior-preserving refactors."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar, cast

TEnum = TypeVar("TEnum", bound=Enum)


def coerce_enum(value: Any, enum_type: type[TEnum]) -> TEnum:
    """Return an enum member from either an enum instance or a matching value."""
    if isinstance(value, enum_type):
        return cast(TEnum, value)

    return cast(TEnum, enum_type(value))


def normalize_required_text(field_name: str, value: str) -> str:
    """Trim and validate required text values."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")

    return value.strip()


def normalize_optional_text(value: str | None) -> str | None:
    """Trim optional text values and collapse blanks to None."""
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None


def enum_value(value: Any) -> Any:
    """Return the underlying enum value when present, otherwise the original value."""
    return getattr(value, "value", value)


def serialize_value(value: Any) -> Any:
    """Serialize enum values for dict output while preserving other values."""
    if isinstance(value, Enum):
        return value.value

    return value


def serialize_item(item: Any) -> Any:
    """Serialize a value or nested object to a JSON-friendly form."""
    if isinstance(item, Enum):
        return item.value

    if isinstance(item, (list, tuple, set)):
        return [serialize_item(entry) for entry in item]

    if isinstance(item, dict):
        return {str(key): serialize_item(value) for key, value in item.items()}

    if hasattr(item, "to_dict"):
        return item.to_dict()

    if hasattr(item, "__dict__"):
        return {
            key: serialize_item(value)
            for key, value in item.__dict__.items()
            if not key.startswith("_")
        }

    return item


def serialize_items(items: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """Serialize a list of items to a JSON-friendly form."""
    return [serialize_item(item) for item in items or []]
