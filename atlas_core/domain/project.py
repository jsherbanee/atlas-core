"""Project domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProjectStatus(str, Enum):
    """Lifecycle status for an Atlas project."""

    INTAKE = "intake"
    ESTIMATING = "estimating"
    ENGINEERING = "engineering"
    PROCUREMENT = "procurement"
    ACTIVE = "active"
    CLOSEOUT = "closeout"
    ARCHIVED = "archived"


@dataclass
class Project:
    project_id: str
    name: str
    client: str
    location: str | None = None
    bid_date: str | None = None
    status: ProjectStatus = ProjectStatus.INTAKE
    buildings: list[str] = field(default_factory=list)
    google_drive_folder: str | None = None
    output_folder: str | None = None
    target_margin: float = 0.28
    cslb_scope: str = "C7"
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_required_text("project_id", self.project_id)
        self._validate_required_text("name", self.name)
        self._validate_required_text("client", self.client)

        if not isinstance(self.target_margin, (int, float)) or not 0 <= self.target_margin <= 1:
            raise ValueError("target_margin must be between 0 and 1")

        if not isinstance(self.status, ProjectStatus):
            self.status = ProjectStatus(self.status)

    def add_building(self, name: str) -> None:
        self._validate_required_text("building name", name)
        self.buildings.append(name.strip())

    def add_note(self, note: str) -> None:
        self._validate_required_text("note", note)
        self.notes.append(note.strip())

    def is_ready_for_estimate(self) -> bool:
        return all(
            isinstance(value, str) and value.strip()
            for value in (self.project_id, self.name, self.client)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "client": self.client,
            "location": self.location,
            "bid_date": self.bid_date,
            "status": self.status.value,
            "buildings": list(self.buildings),
            "google_drive_folder": self.google_drive_folder,
            "output_folder": self.output_folder,
            "target_margin": self.target_margin,
            "cslb_scope": self.cslb_scope,
            "notes": list(self.notes),
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")