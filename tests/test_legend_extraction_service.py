from atlas_core.domain import DrawingSheet
from atlas_core.services import LegendExtractionService


def make_sheet(notes: list[str]) -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av-101",
        sheet_number="AV 1.01",
        title="Audio Plan",
        notes=notes,
        confidence=0.88,
    )


def test_extracts_symbol_legend_item() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["▲ Ceiling Speaker"])
    )

    assert legend is not None
    assert legend.item_count() == 1
    assert legend.legend_id == "av-1.01-legend"
    assert legend.items[0].legend_item_id == "av-1.01-legend-▲"
    assert legend.items[0].symbol == "▲"
    assert legend.items[0].description == "Ceiling Speaker"
    assert legend.items[0].source_sheet_number == "AV 1.01"
    assert legend.items[0].confidence == 0.88


def test_extracts_text_code_legend_item_with_dash() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["SPK - Ceiling Speaker"])
    )

    assert legend is not None
    assert legend.item_count() == 1
    assert legend.items[0].symbol == "SPK"
    assert legend.items[0].description == "Ceiling Speaker"
    assert legend.items[0].legend_item_id == "av-1.01-legend-spk"


def test_extracts_text_code_legend_item_with_colon() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["CAM: PTZ Camera"])
    )

    assert legend is not None
    assert legend.item_count() == 1
    assert legend.items[0].symbol == "CAM"
    assert legend.items[0].description == "PTZ Camera"
    assert legend.items[0].legend_item_id == "av-1.01-legend-cam"


def test_infers_speaker_category() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["▲ Ceiling Speaker"])
    )

    assert legend is not None
    assert legend.items[0].equipment_category == "speaker"


def test_infers_display_category() -> None:
    legend = LegendExtractionService().extract_from_sheet(make_sheet(["DSP: Display"]))

    assert legend is not None
    assert legend.items[0].equipment_category == "display"


def test_infers_camera_category() -> None:
    legend = LegendExtractionService().extract_from_sheet(make_sheet(["○ PTZ Camera"]))

    assert legend is not None
    assert legend.items[0].equipment_category == "camera"


def test_infers_system_category() -> None:
    legend = LegendExtractionService().extract_from_sheet(make_sheet(["DSP: Display"]))

    assert legend is not None
    assert legend.items[0].system_category == "display"


def test_avoids_duplicate_legend_entries() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["SPK - Ceiling Speaker", "SPK: Main Speaker"])
    )

    assert legend is not None
    assert legend.item_count() == 1


def test_returns_none_when_no_legend_exists() -> None:
    legend = LegendExtractionService().extract_from_sheet(
        make_sheet(["General coordination note", "Provide spare conduit"])
    )

    assert legend is None
