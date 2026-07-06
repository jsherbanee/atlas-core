from atlas_core.domain import DrawingSheet
from atlas_core.services.detail_callout_extraction_service import (
    DetailCalloutExtractionService,
)


def make_sheet(
    title: str = "Audio Plan", notes: list[str] | None = None
) -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av-101",
        sheet_number="AV 1.01",
        title=title,
        notes=notes or [],
        confidence=0.88,
    )


def test_extracts_detail_5_av_701() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Detail 5/AV-701"])
    )

    assert len(callouts) == 1
    assert callouts[0].detail_number == "5"
    assert callouts[0].target_sheet_number == "AV-701"
    assert callouts[0].source_sheet_number == "AV 1.01"
    assert callouts[0].callout_id == "av-1.01-detail-5-av-701"


def test_extracts_bare_5_av_701() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["5/AV-701"])
    )

    assert len(callouts) == 1
    assert callouts[0].detail_number == "5"
    assert callouts[0].target_sheet_number == "AV-701"


def test_extracts_see_3_a_501() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["See 3/A-501 for section"])
    )

    assert len(callouts) == 1
    assert callouts[0].detail_number == "3"
    assert callouts[0].target_sheet_number == "A-501"


def test_extracts_ref_2_e_601() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Ref: 2/E-601"])
    )

    assert len(callouts) == 1
    assert callouts[0].detail_number == "2"
    assert callouts[0].target_sheet_number == "E-601"


def test_normalizes_target_sheet_number() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Mounting Detail 7/av503"])
    )

    assert len(callouts) == 1
    assert callouts[0].target_sheet_number == "AV-503"


def test_infers_projector_category() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Projector mount detail 4/AV-701"])
    )

    assert len(callouts) == 1
    assert callouts[0].equipment_category == "projector"
    assert callouts[0].system_category == "projection"


def test_infers_rack_category() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Rack Detail 1/AV-801"])
    )

    assert len(callouts) == 1
    assert callouts[0].equipment_category == "rack"
    assert callouts[0].system_category == "infrastructure"


def test_infers_mount_category() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["Mounting Detail 7/AV-503"])
    )

    assert len(callouts) == 1
    assert callouts[0].equipment_category == "mount"
    assert callouts[0].system_category == "infrastructure"


def test_avoids_duplicate_callouts() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(
            title="Detail 5/AV-701",
            notes=["See 5/AV-701 for mounting"],
        )
    )

    assert len(callouts) == 1
    assert callouts[0].callout_id == "av-1.01-detail-5-av-701"


def test_returns_empty_list_when_no_callouts_exist() -> None:
    callouts = DetailCalloutExtractionService().extract_from_sheet(
        make_sheet(notes=["General coordination note", "Confirm cable pathways"])
    )

    assert callouts == []
