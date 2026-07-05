from atlas_core.domain import (
    DeviceSchedule,
    DeviceScheduleItem,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    RoomType,
)
from atlas_core.services import DrawingMetadata
from atlas_core.services.room_detection_service import RoomDetectionService


def test_detects_rooms_from_drawing_metadata() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawing_metadata=[
            DrawingMetadata(
                sheet_number="AV1.01",
                title="AV Plan",
                room_names=["Main Lobby"],
            )
        ],
    )

    assert len(rooms) == 1
    assert rooms[0].name == "Main Lobby"


def test_detects_rooms_from_drawing_sheet_title() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Recital Hall Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )

    assert [room.name for room in rooms] == ["Recital Hall"]


def test_detects_rooms_from_drawing_notes() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="AV Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
                notes=["Provide coverage for the Black Box Theater."],
            )
        ],
    )

    assert [room.name for room in rooms] == ["Black Box Theater"]


def test_detects_rooms_from_device_schedule_item_room_name() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        device_schedules=[
            DeviceSchedule(
                schedule_id="sched-1",
                items=[
                    DeviceScheduleItem(
                        item_id="item-1",
                        tag="SPK-1",
                        description="Speaker",
                        room_name="Conference Room 101",
                    )
                ],
            )
        ],
    )

    assert [room.name for room in rooms] == ["Conference Room 101"]


def test_detects_rooms_from_equipment_description() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        equipment=[
            Equipment(
                equipment_id="eq-1",
                description="Installed in the Control Booth",
                category=EquipmentCategory.SPEAKER,
            )
        ],
    )

    assert [room.name for room in rooms] == ["Control Booth"]


def test_avoids_duplicate_room_names_case_insensitively() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawing_metadata=[
            DrawingMetadata(
                sheet_number="AV1.01",
                title="AV Plan",
                room_names=["Main Lobby"],
            )
        ],
        drawings=[
            DrawingSheet(
                sheet_id="av1.02",
                sheet_number="AV1.02",
                title="Main Lobby Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )

    assert len(rooms) == 1
    assert rooms[0].name == "Main Lobby"


def test_infers_performance_room_type() -> None:
    room = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Black Box Theater Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )[0]

    assert room.room_type is RoomType.PERFORMANCE


def test_infers_classroom_room_type() -> None:
    room = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Classroom 204",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )[0]

    assert room.room_type is RoomType.CLASSROOM


def test_infers_lobby_room_type() -> None:
    room = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Main Lobby",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )[0]

    assert room.room_type is RoomType.LOBBY


def test_infers_control_room_type() -> None:
    room = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Control Room",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )[0]

    assert room.room_type is RoomType.CONTROL_ROOM


def test_infers_equipment_room_type() -> None:
    room = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Rack Room",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
    )[0]

    assert room.room_type is RoomType.EQUIPMENT_ROOM


def test_returns_rooms_sorted_by_name() -> None:
    rooms = RoomDetectionService().detect_rooms(
        building_id="building-1",
        drawings=[
            DrawingSheet(
                sheet_id="av1.01",
                sheet_number="AV1.01",
                title="Control Booth",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            ),
            DrawingSheet(
                sheet_id="av1.02",
                sheet_number="AV1.02",
                title="Main Lobby",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            ),
        ],
    )

    assert [room.name for room in rooms] == ["Control Booth", "Main Lobby"]


def test_rejects_blank_building_id() -> None:
    try:
        RoomDetectionService().detect_rooms(building_id="   ")
    except ValueError as exc:
        assert str(exc) == "building_id cannot be blank"
    else:
        assert False, "Expected ValueError"


def test_empty_inputs_return_empty_list() -> None:
    assert RoomDetectionService().detect_rooms(building_id="building-1") == []
