"""MAW Music Education Center sample seed data."""

from atlas_core.domain import (
    Building,
    BuildingType,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Room,
    RoomType,
    SystemCategory,
)


def build_maw_seed_data() -> dict[str, list]:
    building = Building(
        building_id="maw-music-education-center",
        name="MAW Music Education Center",
        project_id="maw-demo",
        building_type=BuildingType.EDUCATION,
        address="1000 Music Center Way",
        confidence=0.95,
    )

    recital_hall = Room(
        room_id="maw-recital-hall",
        name="Recital Hall",
        building_id=building.building_id,
        room_number="101",
        room_type=RoomType.PERFORMANCE,
        confidence=0.95,
    )
    control_booth = Room(
        room_id="maw-control-booth",
        name="Control Booth",
        building_id=building.building_id,
        room_number="101B",
        room_type=RoomType.CONTROL_ROOM,
        confidence=0.9,
    )
    classroom = Room(
        room_id="maw-classroom",
        name="Classroom",
        building_id=building.building_id,
        room_number="204",
        room_type=RoomType.CLASSROOM,
        confidence=0.9,
    )
    lobby = Room(
        room_id="maw-lobby",
        name="Lobby",
        building_id=building.building_id,
        room_number="100",
        room_type=RoomType.LOBBY,
        confidence=0.9,
    )

    performance_audio = IntegratedSystem(
        system_id="maw-performance-audio",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
        room_id=recital_hall.room_id,
        building_id=building.building_id,
        description="Main recital hall reinforcement and playback system.",
        manufacturers=["Meyer Sound", "QSC"],
        confidence=0.9,
    )
    projection = IntegratedSystem(
        system_id="maw-projection",
        name="Projection",
        category=SystemCategory.PROJECTION,
        room_id=recital_hall.room_id,
        building_id=building.building_id,
        description="Laser projection system for recital hall presentations.",
        manufacturers=["Epson"],
        confidence=0.86,
    )
    av_control = IntegratedSystem(
        system_id="maw-av-control",
        name="AV Control",
        category=SystemCategory.CONTROL,
        room_id=control_booth.room_id,
        building_id=building.building_id,
        description="Central control processor and user interface logic.",
        manufacturers=["QSC"],
        confidence=0.88,
    )
    classroom_av = IntegratedSystem(
        system_id="maw-classroom-av",
        name="Classroom AV",
        category=SystemCategory.VIDEO,
        room_id=classroom.room_id,
        building_id=building.building_id,
        description="Instructional display and source routing.",
        manufacturers=["Sony", "QSC"],
        confidence=0.84,
    )
    lobby_digital_signage = IntegratedSystem(
        system_id="maw-lobby-digital-signage",
        name="Lobby Digital Signage",
        category=SystemCategory.DISPLAY,
        room_id=lobby.room_id,
        building_id=building.building_id,
        description="Public-facing event and wayfinding display.",
        manufacturers=["Sony"],
        confidence=0.82,
    )

    equipment = [
        Equipment(
            equipment_id="maw-recital-speakers",
            description="Meyer Sound recital hall loudspeakers",
            category=EquipmentCategory.SPEAKER,
            quantity=4,
            manufacturer="Meyer Sound",
            model="ULTRA-X40",
            system_id=performance_audio.system_id,
            room_id=recital_hall.room_id,
            confidence=0.92,
            drawing_reference="AV-401",
            specification_reference="27 41 16",
        ),
        Equipment(
            equipment_id="maw-recital-projector",
            description="Recital hall laser projector",
            category=EquipmentCategory.PROJECTOR,
            quantity=1,
            manufacturer="Epson",
            model="PowerLite L735U",
            system_id=projection.system_id,
            room_id=recital_hall.room_id,
            confidence=0.86,
            drawing_reference="AV-402",
            specification_reference="27 41 19",
        ),
        Equipment(
            equipment_id="maw-control-processor",
            description="Q-SYS control processor",
            category=EquipmentCategory.CONTROL_PROCESSOR,
            quantity=1,
            manufacturer="QSC",
            model="Core Nano",
            system_id=av_control.system_id,
            room_id=control_booth.room_id,
            confidence=0.9,
            drawing_reference="AV-501",
            specification_reference="27 41 26",
        ),
        Equipment(
            equipment_id="maw-classroom-display",
            description="Classroom instructional display",
            category=EquipmentCategory.DISPLAY,
            quantity=1,
            manufacturer="Sony",
            model="FW-65BZ40L",
            system_id=classroom_av.system_id,
            room_id=classroom.room_id,
            confidence=0.83,
            drawing_reference="AV-601",
            specification_reference="27 41 19",
        ),
        Equipment(
            equipment_id="maw-lobby-display",
            description="Lobby digital signage display",
            category=EquipmentCategory.DISPLAY,
            quantity=1,
            manufacturer="Sony",
            model="FW-55BZ40L",
            system_id=lobby_digital_signage.system_id,
            room_id=lobby.room_id,
            confidence=0.82,
            drawing_reference="AV-101",
            specification_reference="27 41 19",
        ),
        Equipment(
            equipment_id="maw-recital-drapery",
            description="Recital hall acoustic drapery allowance",
            category=EquipmentCategory.DRAPERY,
            quantity=1,
            manufacturer="Rose Brand",
            model="FR Velour Traveler",
            room_id=recital_hall.room_id,
            confidence=0.68,
            drawing_reference="A-701",
            specification_reference="11 61 33",
        ),
    ]

    return {
        "buildings": [building],
        "rooms": [recital_hall, control_booth, classroom, lobby],
        "spaces": [],
        "scenes": [],
        "systems": [
            performance_audio,
            projection,
            av_control,
            classroom_av,
            lobby_digital_signage,
        ],
        "equipment": equipment,
    }
