import argparse
import json
import sys

from atlas_core import __version__


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"demo-estimate"}

    if argv and not argv[0].startswith("-") and argv[0] not in known_commands:
        parser.print_help()
        return 1

    args = parser.parse_args(argv)

    if args.version:
        print(f"atlas-core {__version__}")
        return 0

    if args.command == "demo-estimate":
        return _demo_estimate()

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
    from atlas_core.services import EstimateWorkflowResult, EstimateWorkflowService

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

    print(f"equipment matrix rows: {len(result.rows)}")
    print(f"resolver resolutions: {len(result.resolutions)}")
    print(f"placeholder equipment items: {result.placeholder_equipment_count}")

    for resolution in result.resolutions:
        print(
            json.dumps(
                EstimateWorkflowResult._resolution_to_dict(resolution),
                sort_keys=True,
            )
        )

    for row in result.rows:
        print(json.dumps(row.to_dict(), sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
