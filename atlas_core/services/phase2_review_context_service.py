"""Build deterministic review context for Atlas local GUI inspection."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from atlas_core.cli.__main__ import (
    _maw_plan_review_raw_sections,
    _maw_plan_review_raw_sheets,
)
from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.sample_data import build_maw_seed_data
from atlas_core.services import (
    EstimateWorkflowService,
    PlanReviewWorkflowService,
    RevisionComparisonService,
)
from atlas_core.services.document_intake_service import DocumentIntakeService
from atlas_core.services.document_intake_service import UploadedIntakeFile

DEFAULT_MAW_REFERENCE_PACKAGE = Path("examples/music_academy_of_the_west")
_EXPECTED_MAW_FOLDERS = [
    "drawings",
    "specifications",
    "schedules",
    "addenda",
    "images",
]


def get_sample_projects() -> list[dict[str, str]]:
    return [
        {
            "id": "maw",
            "label": "Music Academy of the West (MAW)",
            "description": "Canonical sample/reference project.",
        }
    ]


def build_reference_project_context(
    package_path: str | Path = DEFAULT_MAW_REFERENCE_PACKAGE,
) -> dict[str, Any]:
    root = Path(package_path)
    intake_service = DocumentIntakeService()
    missing_folders = _missing_expected_folders(root)
    if not root.exists() or not root.is_dir():
        return _build_seed_fallback_context(
            reason=(
                f"Reference package not found at {root}. "
                "Using curated seed fixture data instead of the full drawing/specification package."
            ),
            package_path=root,
        )

    try:
        discovery = intake_service.discover_package(root)
    except FileNotFoundError:
        return _build_seed_fallback_context(
            reason=(
                f"Reference package not found at {root}. "
                "Using curated seed fixture data instead of the full drawing/specification package."
            ),
            package_path=root,
        )

    supported_file_count = (
        len(discovery.drawing_files)
        + len(discovery.specification_files)
        + len(discovery.schedule_files)
        + len(discovery.addenda_files)
        + len(discovery.image_files)
    )
    if supported_file_count == 0:
        return _build_seed_fallback_context(
            reason=(
                f"No supported files were found in {root}. "
                "Using curated seed fixture data instead of the full drawing/specification package."
            ),
            package_path=root,
        )

    try:
        snapshot = intake_service.build_snapshot(root)
        workflow_result = intake_service.run_review_from_snapshot(snapshot)
    except Exception as exc:
        return _build_seed_fallback_context(
            reason=(
                f"Reference package intake failed ({exc}). "
                "Using curated seed fixture data instead of the full drawing/specification package."
            ),
            package_path=root,
        )

    warnings = list(snapshot.warnings)
    if missing_folders:
        warnings.insert(
            0,
            "Reference package is incomplete. Missing folders: "
            + ", ".join(missing_folders),
        )

    import_summary = dict(snapshot.import_summary)
    import_summary["extraction_warning_count"] = len(snapshot.warnings)

    return {
        "data_source_mode": "reference_project_real_intake",
        "data_source_label": "Real package intake",
        "sample_project_id": "maw",
        "sample_project_name": "Music Academy of the West",
        "review": workflow_result.review,
        "brief": workflow_result.brief,
        "final_review": workflow_result.final_review,
        "revision_comparison": None,
        "rows": workflow_result.rows,
        "warnings": warnings,
        "import_summary": import_summary,
        "package_location": str(root),
        "intake_snapshot": snapshot,
    }


def build_sample_review_context(sample_project_id: str = "maw") -> dict[str, Any]:
    if sample_project_id != "maw":
        raise ValueError("Unsupported sample project id")

    seed = build_maw_seed_data()
    baseline_result = PlanReviewWorkflowService().run_review(
        review_id="maw-plan-review",
        project_id="maw-demo",
        name="MAW Music Education Center Plan Review",
        raw_sheets=_maw_plan_review_raw_sheets(),
        raw_sections=_maw_plan_review_raw_sections(),
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )

    estimate_result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )
    baseline_result.rows = estimate_result.rows

    revision_comparison = _build_revision_comparison()

    return {
        "data_source_mode": "seed_fixture_fallback",
        "data_source_label": "Seed fixture fallback",
        "sample_project_id": sample_project_id,
        "sample_project_name": "Music Academy of the West",
        "review": baseline_result.review,
        "brief": baseline_result.brief,
        "final_review": baseline_result.final_review,
        "revision_comparison": revision_comparison,
        "rows": baseline_result.rows,
        "warnings": [],
        "import_summary": {},
        "package_location": None,
        "intake_snapshot": None,
    }


def discover_local_intake_snapshots(
    search_roots: list[str | Path] | None = None,
) -> list[dict[str, str]]:
    roots = (
        [Path("outputs"), Path("examples")]
        if search_roots is None
        else [Path(root) for root in search_roots]
    )
    snapshots: list[dict[str, str]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        for snapshot_path in sorted(root.rglob("intake_snapshot.json")):
            label = f"{snapshot_path.parent.name} ({snapshot_path})"
            snapshots.append({"label": label, "path": str(snapshot_path)})

    return snapshots


def build_intake_review_context(snapshot_path: str | Path) -> dict[str, Any]:
    intake_service = DocumentIntakeService()
    snapshot = intake_service.load_snapshot(snapshot_path)
    workflow_result = intake_service.run_review_from_snapshot(snapshot)
    return {
        "data_source_mode": "real_package_intake",
        "data_source_label": "Uploaded Project",
        "sample_project_id": "intake",
        "sample_project_name": str(
            snapshot.metadata.get("project_name")
            or snapshot.metadata.get("name")
            or Path(snapshot.package_path).name
        ),
        "review": workflow_result.review,
        "brief": workflow_result.brief,
        "final_review": workflow_result.final_review,
        "revision_comparison": None,
        "rows": workflow_result.rows,
        "warnings": list(snapshot.warnings),
        "import_summary": dict(snapshot.import_summary),
        "package_location": str(
            snapshot.import_summary.get("package_location") or snapshot.package_path
        ),
        "intake_snapshot": snapshot,
    }


def build_uploaded_review_context(
    uploaded_files: list[UploadedIntakeFile],
    uploads_root: str | Path = "outputs/uploads",
) -> dict[str, Any]:
    intake_service = DocumentIntakeService()
    upload_result = intake_service.build_session_package_from_uploads(
        uploaded_files=uploaded_files,
        uploads_root=uploads_root,
    )
    workflow_result = intake_service.run_review_from_snapshot(upload_result.snapshot)
    project_name = str(
        upload_result.snapshot.metadata.get("project_name")
        or upload_result.snapshot.metadata.get("name")
        or upload_result.package_path.name
    )
    return {
        "data_source_mode": "uploaded_project",
        "data_source_label": "Uploaded Project",
        "sample_project_id": "uploaded",
        "sample_project_name": project_name,
        "review": workflow_result.review,
        "brief": workflow_result.brief,
        "final_review": workflow_result.final_review,
        "revision_comparison": None,
        "rows": workflow_result.rows,
        "warnings": list(upload_result.warnings),
        "import_summary": dict(upload_result.import_summary),
        "package_location": str(upload_result.package_path),
        "intake_snapshot": upload_result.snapshot,
        "upload_session_id": upload_result.session_id,
    }


def _build_revision_comparison() -> Any:
    baseline_seed = build_maw_seed_data()
    baseline_review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-revision-baseline",
            project_id="maw-demo",
            name="MAW Revision Baseline",
            raw_sheets=_maw_plan_review_raw_sheets(),
            raw_sections=_maw_plan_review_raw_sections(),
            buildings=baseline_seed["buildings"],
            rooms=baseline_seed["rooms"],
            spaces=baseline_seed["spaces"],
            scenes=baseline_seed["scenes"],
            systems=baseline_seed["systems"],
            equipment=baseline_seed["equipment"],
        )
        .review
    )

    comparison_seed = build_maw_seed_data()
    comparison_equipment = deepcopy(comparison_seed["equipment"])
    for item in comparison_equipment:
        if item.equipment_id == "maw-recital-speakers":
            item.quantity = 6
            item.assumptions.append("OFCI speaker cabling by others.")
        elif item.equipment_id == "maw-control-processor":
            item.model = "Core Nano Plus"
            item.specification_reference = "27 41 26A"
        elif item.equipment_id == "maw-classroom-display":
            item.drawing_reference = "AV-602"

    comparison_equipment = [
        item
        for item in comparison_equipment
        if item.equipment_id != "maw-lobby-display"
    ]
    comparison_equipment.append(
        Equipment(
            equipment_id="maw-assistive-listening-pack",
            description="Assistive listening receivers add alternate",
            category=EquipmentCategory.ASSISTED_LISTENING,
            quantity=2,
            manufacturer="Listen Technologies",
            model="LT-84",
            system_id="maw-performance-audio",
            room_id="maw-recital-hall",
            drawing_reference="AV-403",
            specification_reference="27 41 16",
            assumptions=["Owner provided charging station by others."],
        )
    )

    comparison_review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-revision-comparison",
            project_id="maw-demo",
            name="MAW Revision Comparison",
            raw_sheets=_maw_plan_review_raw_sheets()
            + [{"sheet_number": "AV-602", "title": "Classroom AV Revision"}],
            raw_sections=_maw_plan_review_raw_sections()
            + [{"section_number": "27 41 26A", "title": "Control Addendum"}],
            buildings=comparison_seed["buildings"],
            rooms=comparison_seed["rooms"],
            spaces=comparison_seed["spaces"],
            scenes=comparison_seed["scenes"],
            systems=comparison_seed["systems"],
            equipment=comparison_equipment,
        )
        .review
    )

    return RevisionComparisonService().build(
        baseline_review=baseline_review,
        comparison_review=comparison_review,
        baseline_revision_id="maw-rev-0",
        comparison_revision_id="maw-rev-1",
    )


def _build_seed_fallback_context(reason: str, package_path: Path) -> dict[str, Any]:
    context = build_sample_review_context("maw")
    warnings = list(context.get("warnings") or [])
    warnings.extend(
        [
            reason,
            "This view is using curated seed fixture data, not the full drawing/specification package.",
        ]
    )
    context["warnings"] = warnings
    context["package_location"] = str(package_path)
    return context


def _missing_expected_folders(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return list(_EXPECTED_MAW_FOLDERS)

    missing: list[str] = []
    for folder_name in _EXPECTED_MAW_FOLDERS:
        folder_path = root / folder_name
        if not folder_path.exists() or not folder_path.is_dir():
            missing.append(folder_name)

    return missing
