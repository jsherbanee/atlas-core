"""Base domain models for Atlas Core."""


class BaseModel:
    """A minimal domain model base class."""

    def __init__(self, **data):
        self._data = data

    def to_dict(self):
        return dict(self._data)
