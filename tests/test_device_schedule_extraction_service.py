from atlas_core.services.device_schedule_extraction_service import (
    DeviceScheduleExtractionService,
)


def test_extracts_valid_schedule_rows():
    rows = [
        {
            "tag": "SPK-1",
            "description": "Main loudspeaker",
        }
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.schedule_id == "sched-1"
    assert schedule.item_count() == 1
    assert schedule.items[0].tag == "SPK-1"
    assert schedule.items[0].description == "Main loudspeaker"
    assert schedule.items[0].item_id == "sched-1-spk-1"


def test_skips_incomplete_rows():
    rows = [
        {"tag": "SPK-1"},
        {"description": "Main loudspeaker"},
        {"tag": "SPK-2", "description": "Fill loudspeaker"},
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.item_count() == 1
    assert schedule.items[0].tag == "SPK-2"


def test_parses_qty():
    rows = [{"tag": "SPK-1", "description": "Main", "qty": "2.5"}]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].quantity == 2.5


def test_parses_quantity():
    rows = [{"tag": "SPK-1", "description": "Main", "quantity": "3"}]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].quantity == 3


def test_defaults_quantity_to_1():
    rows = [{"tag": "SPK-1", "description": "Main"}]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].quantity == 1


def test_uses_source_sheet_number_as_drawing_reference_fallback():
    rows = [{"tag": "SPK-1", "description": "Main"}]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
        source_sheet_number="AV1.01",
    )

    assert schedule.items[0].drawing_reference == "AV1.01"


def test_carries_manufacturer_and_model():
    rows = [
        {
            "tag": "SPK-1",
            "description": "Main",
            "manufacturer": "Acme",
            "model": "X100",
        }
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].manufacturer == "Acme"
    assert schedule.items[0].model == "X100"


def test_carries_room_and_system():
    rows = [
        {
            "tag": "SPK-1",
            "description": "Main",
            "room": "Main Lobby",
            "system": "Audio",
        }
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].room_name == "Main Lobby"
    assert schedule.items[0].system_name == "Audio"


def test_carries_notes_string():
    rows = [
        {
            "tag": "SPK-1",
            "description": "Main",
            "notes": "Install near stage",
        }
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].notes == ["Install near stage"]


def test_carries_notes_list():
    rows = [
        {
            "tag": "SPK-1",
            "description": "Main",
            "notes": ["Install near stage", "Coordinate with architect"],
        }
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert schedule.items[0].notes == [
        "Install near stage",
        "Coordinate with architect",
    ]


def test_preserves_row_order():
    rows = [
        {"tag": "SPK-1", "description": "Main"},
        {"tag": "MIC-1", "description": "Podium mic"},
        {"tag": "DSP-1", "description": "Processor"},
    ]

    schedule = DeviceScheduleExtractionService().extract_from_rows(
        schedule_id="sched-1",
        rows=rows,
    )

    assert [item.tag for item in schedule.items] == ["SPK-1", "MIC-1", "DSP-1"]
