"""Project lifecycle event domain model for Atlas Core."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from atlas_core.domain.project import ProjectStatus


@dataclass
class ProjectLifecycleEvent:
    from_status: ProjectStatus | None
    to_status: ProjectStatus
    note: str | None = None
    changed_by: str | None = None
    changed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        if self.from_status is not None and not isinstance(
            self.from_status,
            ProjectStatus,
        ):
            self.from_status = ProjectStatus(self.from_status)

        if not isinstance(self.to_status, ProjectStatus):
            self.to_status = ProjectStatus(self.to_status)

        self.note = self._normalize_optional_text(self.note)
        self.changed_by = self._normalize_optional_text(self.changed_by)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["from_status"] = (
            self.from_status.value
            if self.from_status is not None
            else None
        )
        data["to_status"] = self.to_status.value
        return data

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
