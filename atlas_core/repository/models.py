"""Repository domain models for manifests and health reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProjectManifest:
    project_id: str
    project_name: str
    owner: str
    status: str
    lifecycle_stage: str
    created_at: str
    updated_at: str
    last_opened_at: str | None
    atlas_version: str
    schema_version: str
    storage_version: str
    document_counts: dict[str, int] = field(default_factory=dict)
    review_artifact_counts: dict[str, int] = field(default_factory=dict)
    intelligence_artifact_counts: dict[str, int] = field(default_factory=dict)
    history_event_count: int = 0
    checksum_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryHealthReport:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    orphaned_files: list[str] = field(default_factory=list)
    repair_recommendations: list[str] = field(default_factory=list)
    validated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
