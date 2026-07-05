"""Validation helpers for Atlas Core utilities."""


def validate_data(data: object) -> bool:
    """Return True for non-empty collections and mappings, otherwise False."""
    if data is None:
        return False
    if isinstance(data, (str, bytes)):
        return bool(data.strip())
    if isinstance(data, (list, tuple, set, dict)):
        return bool(data)
    return True
