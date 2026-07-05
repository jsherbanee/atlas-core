import pytest

from atlas_core.domain import Legend, LegendItem


def test_creating_valid_legend_item() -> None:
    item = LegendItem(
        legend_item_id=" item-001 ",
        symbol=" S1 ",
        description=" Ceiling loudspeaker ",
        equipment_category=" speaker ",
        system_category=" audio ",
        source_sheet_number=" AV1.01 ",
        notes=[" Coordinate with architect. "],
        confidence=0.9,
    )

    assert item.legend_item_id == "item-001"
    assert item.symbol == "S1"
    assert item.description == "Ceiling loudspeaker"
    assert item.equipment_category == "speaker"
    assert item.system_category == "audio"
    assert item.source_sheet_number == "AV1.01"
    assert item.notes == ["Coordinate with architect."]
    assert item.confidence == 0.9


def test_rejecting_blank_symbol() -> None:
    with pytest.raises(ValueError, match="symbol cannot be blank"):
        LegendItem(
            legend_item_id="item-001",
            symbol=" ",
            description="Ceiling loudspeaker",
        )


def test_rejecting_blank_description() -> None:
    with pytest.raises(ValueError, match="description cannot be blank"):
        LegendItem(
            legend_item_id="item-001",
            symbol="S1",
            description=" ",
        )


def test_adding_item_to_legend() -> None:
    legend = Legend(legend_id="legend-001")
    item = LegendItem(
        legend_item_id="item-001",
        symbol="S1",
        description="Ceiling loudspeaker",
    )

    legend.add_item(item)

    assert legend.items == [item]


def test_item_count() -> None:
    legend = Legend(
        legend_id="legend-001",
        items=[
            LegendItem(
                legend_item_id="item-001",
                symbol="S1",
                description="Ceiling loudspeaker",
            ),
            LegendItem(
                legend_item_id="item-002",
                symbol="P1",
                description="Projector",
            ),
        ],
    )

    assert legend.item_count() == 2


def test_adding_notes() -> None:
    item = LegendItem(
        legend_item_id="item-001",
        symbol="S1",
        description="Ceiling loudspeaker",
    )

    item.add_note(" Coordinate with architect. ")

    assert item.notes == ["Coordinate with architect."]


def test_to_dict() -> None:
    item = LegendItem(
        legend_item_id="item-001",
        symbol="S1",
        description="Ceiling loudspeaker",
        notes=["Verify final mounting height."],
        confidence=0.88,
    )
    legend = Legend(
        legend_id="legend-001",
        source_sheet_number="AV1.01",
        items=[item],
        confidence=0.82,
    )

    assert legend.to_dict() == {
        "legend_id": "legend-001",
        "title": "Legend",
        "source_sheet_number": "AV1.01",
        "items": [
            {
                "legend_item_id": "item-001",
                "symbol": "S1",
                "description": "Ceiling loudspeaker",
                "equipment_category": None,
                "system_category": None,
                "source_sheet_number": None,
                "notes": ["Verify final mounting height."],
                "confidence": 0.88,
            }
        ],
        "confidence": 0.82,
    }
