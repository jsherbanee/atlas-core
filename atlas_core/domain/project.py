"""Project domain model for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_core.domain.project_lifecycle import ProjectLifecycleEvent


class ProjectStatus(str, Enum):
    """Lifecycle status for an Atlas project."""

    OPPORTUNITY = "opportunity"
    INTAKE = "intake"
    ESTIMATING = "estimating"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
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
    lifecycle_events: list[ProjectLifecycleEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_required_text("project_id", self.project_id)
        self._validate_required_text("name", self.name)
        self._validate_required_text("client", self.client)

        if (
            not isinstance(self.target_margin, (int, float))
            or not 0 <= self.target_margin <= 1
        ):
            raise ValueError("target_margin must be between 0 and 1")

        if not isinstance(self.status, ProjectStatus):
            self.status = ProjectStatus(self.status)

        self.lifecycle_events = [
            self._normalize_lifecycle_event(event)
            for event in self.lifecycle_events
        ]

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

    def mark_opportunity(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.OPPORTUNITY, note, changed_by)

    def mark_intake(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.INTAKE, note, changed_by)

    def mark_estimating(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.ESTIMATING, note, changed_by)

    def mark_submitted(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.SUBMITTED, note, changed_by)

    def mark_awarded(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.AWARDED, note, changed_by)

    def mark_engineering(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.ENGINEERING, note, changed_by)

    def mark_procurement(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.PROCUREMENT, note, changed_by)

    def mark_active(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.ACTIVE, note, changed_by)

    def mark_closeout(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.CLOSEOUT, note, changed_by)

    def mark_archived(
        self,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        self._set_status(ProjectStatus.ARCHIVED, note, changed_by)

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
            "lifecycle_events": [
                event.to_dict()
                for event in self.lifecycle_events
            ],
        }

    def _set_status(
        self,
        new_status: ProjectStatus,
        note: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        from atlas_core.domain.project_lifecycle import ProjectLifecycleEvent

        if not isinstance(new_status, ProjectStatus):
            new_status = ProjectStatus(new_status)

        event = ProjectLifecycleEvent(
            from_status=self.status,
            to_status=new_status,
            note=note,
            changed_by=changed_by,
        )
        self.status = new_status
        self.lifecycle_events.append(event)

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @staticmethod
    def _normalize_lifecycle_event(
        event: ProjectLifecycleEvent | dict[str, Any],
    ) -> ProjectLifecycleEvent:
        from atlas_core.domain.project_lifecycle import ProjectLifecycleEvent

        if isinstance(event, ProjectLifecycleEvent):
            return event

        return ProjectLifecycleEvent(**event)
