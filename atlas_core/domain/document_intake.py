"""Domain models for deterministic local package intake snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from atlas_core.domain.document_relevance import DocumentRelevanceAssessment
from atlas_core.domain.source_fitness import SourceFitnessAssessment


@dataclass
class IntakeSourceReference:
    source_file: str
    page_number: int | None = None
    sheet_number: str | None = None
    section_number: str | None = None
    text_excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentIntakeSnapshot:
    snapshot_id: str
    package_path: str
    metadata: dict[str, Any]
    discovered_files: dict[str, list[str]]
    raw_pages: list[dict[str, Any]] = field(default_factory=list)
    raw_sheets: list[dict[str, Any]] = field(default_factory=list)
    raw_sections: list[dict[str, Any]] = field(default_factory=list)
    raw_device_schedules: list[dict[str, Any]] = field(default_factory=list)
    equipment_candidates: list[dict[str, Any]] = field(default_factory=list)
    source_references: list[dict[str, Any]] = field(default_factory=list)
    document_relevance_assessments: list[DocumentRelevanceAssessment] = field(
        default_factory=list
    )
    source_fitness_assessments: list[SourceFitnessAssessment] = field(
        default_factory=list
    )
    warnings: list[str] = field(default_factory=list)
    import_summary: dict[str, Any] = field(default_factory=dict)
    data_source: str = "real_package_intake"
    created_by_engine_version: str = "document-intake-service/1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentIntakeSnapshot":
        return cls(
            snapshot_id=str(payload.get("snapshot_id") or ""),
            package_path=str(payload.get("package_path") or ""),
            metadata=dict(payload.get("metadata") or {}),
            discovered_files={
                str(key): [str(item) for item in value]
                for key, value in dict(payload.get("discovered_files") or {}).items()
            },
            raw_pages=list(payload.get("raw_pages") or []),
            raw_sheets=list(payload.get("raw_sheets") or []),
            raw_sections=list(payload.get("raw_sections") or []),
            raw_device_schedules=list(payload.get("raw_device_schedules") or []),
            equipment_candidates=list(payload.get("equipment_candidates") or []),
            source_references=list(payload.get("source_references") or []),
            document_relevance_assessments=[
                (
                    item
                    if isinstance(item, DocumentRelevanceAssessment)
                    else DocumentRelevanceAssessment(**dict(item))
                )
                for item in list(payload.get("document_relevance_assessments") or [])
            ],
            source_fitness_assessments=[
                (
                    item
                    if isinstance(item, SourceFitnessAssessment)
                    else SourceFitnessAssessment.from_dict(dict(item))
                )
                for item in list(payload.get("source_fitness_assessments") or [])
            ],
            warnings=[str(item) for item in list(payload.get("warnings") or [])],
            import_summary=dict(payload.get("import_summary") or {}),
            data_source=str(payload.get("data_source") or "real_package_intake"),
            created_by_engine_version=str(
                payload.get("created_by_engine_version")
                or "document-intake-service/1.0.0"
            ),
        )
