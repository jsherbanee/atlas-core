from atlas_core.parsers.schedule_parser import (
    detect_schedule_like_pages,
    extract_equipment_candidates,
)


def test_extract_equipment_candidates_filters_sentence_like_noise() -> None:
    pages = [
        {
            "source_file": "noise.pdf",
            "page_number": 1,
            "text": (
                "Provide speaker cabling in the lobby.\n"
                "SPK-1    Main loudspeaker    QSC\n"
            ),
        }
    ]

    candidates = extract_equipment_candidates(pages)

    assert [candidate["tag"] for candidate in candidates] == ["SPK-1"]
    assert candidates[0]["category_hint"] == "speaker"


def test_detect_schedule_like_pages_requires_tabular_rows() -> None:
    pages = [
        {
            "source_file": "schedule.pdf",
            "page_number": 2,
            "text": (
                "DEVICE SCHEDULE\n"
                "Coordinate speaker installation with architect.\n"
                "SPK-1    Main loudspeaker\n"
            ),
        }
    ]

    schedules = detect_schedule_like_pages(pages)

    assert len(schedules) == 1
    assert schedules[0]["rows"] == [{"tag": "SPK-1", "description": "Main loudspeaker"}]
