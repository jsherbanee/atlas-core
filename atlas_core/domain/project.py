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
    atlas_bid_id: str | None = None
    client_project_number: str | None = None
    internal_project_number: str | None = None
    consultant: str | None = None
    architect: str | None = None
    engineers: list[str] = field(default_factory=list)
    location: str | None = None
    issue_date: str | None = None
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
        self.atlas_bid_id = self._normalize_optional_text(self.atlas_bid_id)
        if self.atlas_bid_id is None:
            self.atlas_bid_id = self.project_id
        self.client_project_number = self._normalize_optional_text(
            self.client_project_number
        )
        self.internal_project_number = self._normalize_optional_text(
            self.internal_project_number
        )
        self.consultant = self._normalize_optional_text(self.consultant)
        self.architect = self._normalize_optional_text(self.architect)
        self.issue_date = self._normalize_optional_text(self.issue_date)
        self.location = self._normalize_optional_text(self.location)
        self.bid_date = self._normalize_optional_text(self.bid_date)
        self.engineers = [
            item.strip()
            for item in self.engineers
            if isinstance(item, str) and item.strip()
        ]

        if (
            not isinstance(self.target_margin, (int, float))
            or not 0 <= self.target_margin <= 1
        ):
            raise ValueError("target_margin must be between 0 and 1")

        if not isinstance(self.status, ProjectStatus):
            self.status = ProjectStatus(self.status)

        self.lifecycle_events = [
            self._normalize_lifecycle_event(event) for event in self.lifecycle_events
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
            "atlas_bid_id": self.atlas_bid_id,
            "client_project_number": self.client_project_number,
            "internal_project_number": self.internal_project_number,
            "consultant": self.consultant,
            "architect": self.architect,
            "engineers": list(self.engineers),
            "location": self.location,
            "issue_date": self.issue_date,
            "bid_date": self.bid_date,
            "status": self.status.value,
            "buildings": list(self.buildings),
            "google_drive_folder": self.google_drive_folder,
            "output_folder": self.output_folder,
            "target_margin": self.target_margin,
            "cslb_scope": self.cslb_scope,
            "notes": list(self.notes),
            "lifecycle_events": [event.to_dict() for event in self.lifecycle_events],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Project":
        target_margin_value = payload.get("target_margin")
        return cls(
            project_id=str(payload.get("project_id") or ""),
            name=str(payload.get("name") or ""),
            client=str(payload.get("client") or ""),
            atlas_bid_id=(str(payload.get("atlas_bid_id") or "") or None),
            client_project_number=(
                str(payload.get("client_project_number") or "") or None
            ),
            internal_project_number=(
                str(payload.get("internal_project_number") or "") or None
            ),
            consultant=(str(payload.get("consultant") or "") or None),
            architect=(str(payload.get("architect") or "") or None),
            engineers=[str(item) for item in list(payload.get("engineers") or [])],
            location=payload.get("location"),
            issue_date=(str(payload.get("issue_date") or "") or None),
            bid_date=payload.get("bid_date"),
            status=payload.get("status") or ProjectStatus.INTAKE,
            buildings=[str(item) for item in list(payload.get("buildings") or [])],
            google_drive_folder=payload.get("google_drive_folder"),
            output_folder=payload.get("output_folder"),
            target_margin=(
                0.28 if target_margin_value is None else float(target_margin_value)
            ),
            cslb_scope=str(payload.get("cslb_scope") or "C7"),
            notes=[str(item) for item in list(payload.get("notes") or [])],
            lifecycle_events=list(payload.get("lifecycle_events") or []),
        )

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
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    def __getattr__(self, name: str) -> Any:
        compatibility_defaults: dict[str, Any] = {
            "atlas_bid_id": self.project_id,
            "client_project_number": None,
            "internal_project_number": None,
            "consultant": None,
            "architect": None,
            "engineers": [],
            "issue_date": None,
        }
        if name in compatibility_defaults:
            return compatibility_defaults[name]
        raise AttributeError(name)

    @staticmethod
    def _normalize_lifecycle_event(
        event: ProjectLifecycleEvent | dict[str, Any],
    ) -> ProjectLifecycleEvent:
        from atlas_core.domain.project_lifecycle import ProjectLifecycleEvent

        if isinstance(event, ProjectLifecycleEvent):
            return event

        return ProjectLifecycleEvent.from_dict(event)
