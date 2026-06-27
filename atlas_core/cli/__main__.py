import argparse
import json
import sys
from pathlib import Path
from typing import Any

from atlas_core import __version__


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"demo-estimate", "demo-maw", "demo-maw-plan-review"}

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

    return parser


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

        written_equipment_matrix_path = (
            csv_export_service.export_equipment_matrix(
                result.rows,
                equipment_matrix_path,
            )
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
        CsvExportService,
        EstimateWorkflowService,
        MarkdownExportService,
        PlanReviewWorkflowService,
    )

    seed = build_maw_seed_data()
    raw_sheets = _maw_plan_review_raw_sheets()
    raw_sections = _maw_plan_review_raw_sections()

    plan_review_result = PlanReviewWorkflowService().run_review(
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

    csv_export_service = CsvExportService()
    estimator_brief_path = output_dir / "maw_estimator_brief.csv"
    drawing_index_path = output_dir / "maw_drawing_index.csv"
    specification_index_path = output_dir / "maw_specification_index.csv"
    equipment_matrix_path = output_dir / "maw_equipment_matrix.csv"
    review_report_path = output_dir / "maw_review_report.csv"
    plan_review_summary_path = output_dir / "maw_plan_review_summary.md"

    written_estimator_brief_path = csv_export_service.export_estimator_brief(
        plan_review_result.brief,
        estimator_brief_path,
    )
    written_drawing_index_path = csv_export_service.export_drawing_index(
        plan_review_result.review.drawing_sheets,
        drawing_index_path,
    )
    written_specification_index_path = (
        csv_export_service.export_specification_index(
            plan_review_result.review.specification_sections,
            specification_index_path,
        )
    )
    written_equipment_matrix_path = csv_export_service.export_equipment_matrix(
        estimate_result.rows,
        equipment_matrix_path,
    )
    written_review_report_path = csv_export_service.export_review_report(
        plan_review_result.review.review_report,
        review_report_path,
    )
    written_plan_review_summary_path = (
        MarkdownExportService().export_plan_review_summary(
            plan_review_result,
            plan_review_summary_path,
        )
    )

    _print_estimator_brief_summary(plan_review_result.brief)
    print(f"estimator brief csv export: {written_estimator_brief_path}")
    print(f"drawing index csv export: {written_drawing_index_path}")
    print(f"specification index csv export: {written_specification_index_path}")
    print(f"equipment matrix csv export: {written_equipment_matrix_path}")
    print(f"review report csv export: {written_review_report_path}")
    print(f"plan review summary markdown export: {written_plan_review_summary_path}")
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
        f"drawings={brief.drawing_count} "
        f"specifications={brief.specification_count} "
        f"systems={brief.system_count} "
        f"equipment={brief.equipment_count} "
        f"issues={brief.issue_count} "
        f"placeholders={brief.placeholder_count} "
        f"review_required={brief.review_required_count} "
        f"confidence={brief.confidence}"
    )


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
