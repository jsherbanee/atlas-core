import argparse
import json
import sys
from pathlib import Path
from typing import Any

from atlas_core import __version__


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    known_commands = {
        "demo-estimate",
        "demo-maw",
        "demo-maw-plan-review",
        "demo-maw-rfi-candidates",
        "demo-maw-labor-estimate",
        "demo-maw-revision-comparison",
        "package-intake",
        "phase2-review",
    }

    if argv and not argv[0].startswith("-") and argv[0] not in known_commands:
        parser.print_help()
        return 1

    args = parser.parse_args(argv)

    if args.version:
        print(f"atlas-core {__version__}")
        return 0

    if args.command == "demo-estimate":
        return _demo_estimate()

    if args.command == "demo-maw":
        return _demo_maw(args.csv, args.output_dir)

    if args.command == "demo-maw-plan-review":
        return _demo_maw_plan_review(args.output_dir)

    if args.command == "demo-maw-rfi-candidates":
        return _demo_maw_rfi_candidates()

    if args.command == "demo-maw-labor-estimate":
        return _demo_maw_labor_estimate()

    if args.command == "demo-maw-revision-comparison":
        return _demo_maw_revision_comparison()

    if args.command == "package-intake":
        return _package_intake(args.path, args.out)

    if args.command == "phase2-review":
        return _phase2_review(
            package_path=args.package,
            snapshot_path=args.snapshot,
            output_dir=args.out,
        )

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas-core", description="Atlas Core CLI")
    parser.add_argument("--version", action="store_true", help="Print package version")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "demo-estimate",
        help="Run a sample estimate workflow",
    )
    maw_parser = subparsers.add_parser(
        "demo-maw",
        help="Run the MAW seed estimate workflow",
    )
    maw_parser.add_argument(
        "--csv",
        "--export-csv",
        dest="csv",
        type=Path,
        help="Write the MAW equipment matrix rows to a CSV file",
    )
    maw_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Write MAW equipment matrix and review report CSV files",
    )
    maw_plan_review_parser = subparsers.add_parser(
        "demo-maw-plan-review",
        help="Run the MAW seed plan review workflow and export CSV files",
    )
    maw_plan_review_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Write MAW plan review CSV files",
    )
    subparsers.add_parser(
        "demo-maw-rfi-candidates",
        help="Run MAW plan review and print deterministic RFI candidates",
    )
    subparsers.add_parser(
        "demo-maw-labor-estimate",
        help="Run MAW plan review and print deterministic labor estimate",
    )
    subparsers.add_parser(
        "demo-maw-revision-comparison",
        help="Compare two deterministic MAW review snapshots and print revision changes",
    )
    package_intake_parser = subparsers.add_parser(
        "package-intake",
        help="Build deterministic intake snapshot from a local package folder",
    )
    package_intake_parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Path to package folder (drawings/specifications/schedules/addenda)",
    )
    package_intake_parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output folder for intake snapshot",
    )

    phase2_review_parser = subparsers.add_parser(
        "phase2-review",
        help="Run plan review from a package intake path or existing intake snapshot",
    )
    phase2_review_source_group = phase2_review_parser.add_mutually_exclusive_group(
        required=True
    )
    phase2_review_source_group.add_argument(
        "--package",
        type=Path,
        help="Path to package folder",
    )
    phase2_review_source_group.add_argument(
        "--snapshot",
        type=Path,
        help="Path to intake snapshot JSON",
    )
    phase2_review_parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output folder for phase2 review exports",
    )

    return parser


def _package_intake(package_path: Path, output_dir: Path) -> int:
    from atlas_core.services.document_intake_service import DocumentIntakeService

    intake_service = DocumentIntakeService()
    snapshot = intake_service.build_snapshot(package_path)
    snapshot_path = intake_service.write_snapshot(snapshot, output_dir)

    print("data source: real package intake")
    print(f"intake snapshot: {snapshot_path}")
    print(
        "intake summary: "
        f"pages={len(snapshot.raw_pages)} "
        f"sheets={len(snapshot.raw_sheets)} "
        f"sections={len(snapshot.raw_sections)} "
        f"schedules={len(snapshot.raw_device_schedules)} "
        f"equipment_candidates={len(snapshot.equipment_candidates)} "
        f"warnings={len(snapshot.warnings)}"
    )
    for warning in snapshot.warnings:
        print(f"warning: {warning}")

    return 0


def _phase2_review(
    package_path: Path | None,
    snapshot_path: Path | None,
    output_dir: Path,
) -> int:
    from atlas_core.services import PlanReviewExportService
    from atlas_core.services.document_intake_service import DocumentIntakeService

    intake_service = DocumentIntakeService()
    if snapshot_path is not None:
        snapshot = intake_service.load_snapshot(snapshot_path)
    elif package_path is not None:
        snapshot = intake_service.build_snapshot(package_path)
    else:
        raise ValueError("Either --package or --snapshot must be provided")

    output_dir.mkdir(parents=True, exist_ok=True)
    written_snapshot_path = intake_service.write_snapshot(snapshot, output_dir)
    workflow_result = intake_service.run_review_from_snapshot(snapshot)
    export_result = PlanReviewExportService().export_plan_review(
        workflow_result,
        output_dir=output_dir,
        prefix="phase2_review",
    )

    print("data source: real package intake")
    print(f"intake snapshot: {written_snapshot_path}")
    print(f"review exports: {json.dumps(export_result.to_dict(), sort_keys=True)}")
    print(
        "review summary: "
        f"review_id={workflow_result.review.review_id} "
        f"readiness_status={getattr(getattr(workflow_result.review.readiness, 'status', None), 'value', None)} "
        f"readiness_score={getattr(workflow_result.review.readiness, 'readiness_score', None)}"
    )

    return 0


def _demo_estimate() -> int:
    from atlas_core.domain import (
        Building,
        Equipment,
        EquipmentCategory,
        IntegratedSystem,
        Room,
        SystemCategory,
    )
    from atlas_core.services import EstimateWorkflowService

    building = Building(
        building_id="maw-music-education-center",
        name="MAW Music Education Center",
        project_id="demo-project",
    )
    room = Room(
        room_id="recital-hall",
        name="Recital Hall",
        building_id=building.building_id,
    )
    system = IntegratedSystem(
        system_id="performance-audio",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
        room_id=room.room_id,
    )
    speaker = Equipment(
        equipment_id="recital-hall-speaker",
        description="Main loudspeaker",
        category=EquipmentCategory.SPEAKER,
        system_id=system.system_id,
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=[building],
        rooms=[room],
        systems=[system],
        equipment=[speaker],
    )

    _print_workflow_result(result)
    return 0


def _demo_maw(
    csv_path: Path | None = None,
    output_dir: Path | None = None,
) -> int:
    from atlas_core.sample_data import build_maw_seed_data
    from atlas_core.services import CsvExportService, EstimateWorkflowService

    seed = build_maw_seed_data()
    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )

    csv_export_service = CsvExportService()

    if output_dir is not None:
        equipment_matrix_path = output_dir / "maw_equipment_matrix.csv"
        review_report_path = output_dir / "maw_review_report.csv"

        written_equipment_matrix_path = csv_export_service.export_equipment_matrix(
            result.rows,
            equipment_matrix_path,
        )
        written_review_report_path = csv_export_service.export_review_report(
            result.review_report,
            review_report_path,
        )

        print(f"equipment matrix csv export: {written_equipment_matrix_path}")
        print(f"review report csv export: {written_review_report_path}")
        return 0

    _print_workflow_result(result)

    if csv_path is not None:
        written_path = csv_export_service.export_equipment_matrix(
            result.rows,
            csv_path,
        )
        print(f"csv export: {written_path}")

    return 0


def _demo_maw_plan_review(output_dir: Path) -> int:
    from atlas_core.sample_data import build_maw_seed_data
    from atlas_core.services import (
        EstimateWorkflowService,
        PlanReviewExportService,
        PlanReviewWorkflowService,
    )

    seed = build_maw_seed_data()
    raw_sheets = _maw_plan_review_raw_sheets()
    raw_sections = _maw_plan_review_raw_sections()

    result = PlanReviewWorkflowService().run_review(
        review_id="maw-plan-review",
        project_id="maw-demo",
        name="MAW Music Education Center Plan Review",
        raw_sheets=raw_sheets,
        raw_sections=raw_sections,
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
    result.rows = estimate_result.rows

    export_result = PlanReviewExportService().export_plan_review(
        result,
        output_dir=output_dir,
        prefix="maw",
    )
    export_paths = export_result.to_dict()

    _print_estimator_brief_summary(result.brief)
    readiness = result.review.readiness
    if readiness is not None:
        print(
            "readiness summary: "
            f"score={readiness.readiness_score} "
            f"level={readiness.readiness_level.value} "
            f"blockers={len(readiness.blocking_issues)} "
            f"warnings={len(readiness.warnings)}"
        )
        print("readiness section scores:")
        for section_name, score in sorted(readiness.section_scores.items()):
            print(f"- {section_name}: {score}")
        print("recommended reviewer actions:")
        for action in readiness.recommended_reviewer_actions:
            print(f"- {action}")

    print(f"estimator brief csv export: {export_paths['estimator_brief_path']}")
    print(f"drawing index csv export: {export_paths['drawing_index_path']}")
    print(
        "specification index csv export: " f"{export_paths['specification_index_path']}"
    )
    print(f"equipment matrix csv export: {export_paths['equipment_matrix_path']}")
    print(f"review report csv export: {export_paths['review_report_path']}")
    print(f"recommendations csv export: {export_paths['recommendations_path']}")
    print(
        "plan review summary markdown export: "
        f"{export_paths['markdown_summary_path']}"
    )
    return 0


def _demo_maw_rfi_candidates() -> int:
    from atlas_core.sample_data import build_maw_seed_data
    from atlas_core.services import PlanReviewWorkflowService

    seed = build_maw_seed_data()
    raw_sheets = _maw_plan_review_raw_sheets()
    raw_sections = _maw_plan_review_raw_sections()

    review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-plan-review-rfi",
            project_id="maw-demo",
            name="MAW Music Education Center Plan Review RFI",
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
            buildings=seed["buildings"],
            rooms=seed["rooms"],
            spaces=seed["spaces"],
            scenes=seed["scenes"],
            systems=seed["systems"],
            equipment=seed["equipment"],
        )
        .review
    )

    print(f"rfi candidates: {len(review.rfi_candidates)}")
    for candidate in review.rfi_candidates:
        print(json.dumps(candidate.to_dict(), sort_keys=True))

    return 0


def _demo_maw_labor_estimate() -> int:
    from atlas_core.sample_data import build_maw_seed_data
    from atlas_core.services import PlanReviewWorkflowService

    seed = build_maw_seed_data()
    raw_sheets = _maw_plan_review_raw_sheets()
    raw_sections = _maw_plan_review_raw_sections()

    review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-plan-review-labor",
            project_id="maw-demo",
            name="MAW Music Education Center Plan Review Labor",
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
            buildings=seed["buildings"],
            rooms=seed["rooms"],
            spaces=seed["spaces"],
            scenes=seed["scenes"],
            systems=seed["systems"],
            equipment=seed["equipment"],
        )
        .review
    )

    labor_estimate = review.labor_estimate
    if labor_estimate is None:
        print("labor estimate: unavailable")
        return 1

    print(
        "labor estimate totals: "
        f"low={labor_estimate.total_labor_hours_low} "
        f"expected={labor_estimate.total_labor_hours_expected} "
        f"high={labor_estimate.total_labor_hours_high} "
        f"confidence={labor_estimate.confidence}"
    )
    print(f"labor categories: {len(labor_estimate.labor_categories)}")
    for category in labor_estimate.labor_categories:
        print(json.dumps(category.to_dict(), sort_keys=True))

    return 0


def _demo_maw_revision_comparison() -> int:
    from copy import deepcopy

    from atlas_core.domain import Equipment, EquipmentCategory
    from atlas_core.sample_data import build_maw_seed_data
    from atlas_core.services import PlanReviewWorkflowService, RevisionComparisonService

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

    comparison = RevisionComparisonService().build(
        baseline_review=baseline_review,
        comparison_review=comparison_review,
        baseline_revision_id="maw-rev-0",
        comparison_revision_id="maw-rev-1",
    )

    print(
        "revision comparison summary: "
        f"changes={len(comparison.changes)} "
        f"added={len(comparison.added_items)} "
        f"removed={len(comparison.removed_items)} "
        f"modified={len(comparison.modified_items)} "
        f"confidence={comparison.confidence}"
    )
    print(f"labor impact flags: {len(comparison.labor_impact_flags)}")
    print(f"rfi impacts: {len(comparison.rfi_impacts)}")
    for change in comparison.changes:
        print(json.dumps(change.to_dict(), sort_keys=True))

    return 0


def _maw_plan_review_raw_sheets() -> list[dict[str, str]]:
    return [
        {"sheet_number": "AV-101", "title": "Lobby Digital Signage"},
        {"sheet_number": "AV-401", "title": "Recital Hall Audio Plan"},
        {"sheet_number": "AV-402", "title": "Recital Hall Projection Plan"},
        {"sheet_number": "AV-501", "title": "AV Control Details"},
        {"sheet_number": "AV-601", "title": "Classroom AV Plan"},
        {"sheet_number": "A-701", "title": "Drapery and Interior Details"},
    ]


def _maw_plan_review_raw_sections() -> list[dict[str, str]]:
    return [
        {
            "section_number": "27 41 16",
            "title": "Integrated Audio Systems",
        },
        {
            "section_number": "27 41 19",
            "title": "Video Display and Projection Systems",
        },
        {
            "section_number": "27 41 26",
            "title": "AV Control Systems",
        },
        {
            "section_number": "11 61 33",
            "title": "Stage Curtains and Drapery",
        },
    ]


def _print_estimator_brief_summary(brief: Any) -> None:
    print(
        "estimator brief summary: "
        f"title={brief.brief_title} "
        f"drawings={brief.drawing_count} "
        f"specifications={brief.specification_count} "
        f"systems={brief.system_count} "
        f"equipment={brief.equipment_count} "
        f"issues={brief.issue_count} "
        f"placeholders={brief.placeholder_count} "
        f"review_required={brief.review_required_count} "
        f"confidence={brief.confidence}"
    )
    print(f"executive summary: {brief.executive_summary}")
    readiness_summary = brief.readiness_summary or {}
    print(
        "brief readiness: "
        f"score={readiness_summary.get('readiness_score')} "
        f"level={readiness_summary.get('readiness_level')}"
    )
    print(f"top blockers: {len(brief.top_blockers or [])}")
    print(f"top warnings: {len(brief.top_warnings or [])}")
    print(f"prioritized actions: {len(brief.prioritized_reviewer_actions or [])}")


def _print_workflow_result(result: Any) -> None:
    data = result.to_dict()

    print(f"equipment matrix rows: {len(data['rows'])}")
    print(f"resolver resolutions: {len(data['resolutions'])}")
    print(f"placeholder equipment items: {data['placeholder_equipment_count']}")

    for resolution in data["resolutions"]:
        print(json.dumps(resolution, sort_keys=True))

    for row in data["rows"]:
        print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
