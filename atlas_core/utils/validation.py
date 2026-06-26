"""Validation helpers for Atlas Core."""


def validate_data(data: dict) -> bool:
    return isinstance(data, dict)
