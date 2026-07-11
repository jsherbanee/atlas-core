import json

from atlas_core.services.bom_review_service import (
    BomReviewService,
    COMPLETE,
    CONFLICTING_QUANTITY,
    DRAWING_ONLY,
    MISSING_MANUFACTURER,
    SPECIFICATION_ONLY,
    UNRESOLVED,
)


def test_build_items_assigns_completeness_and_preserves_conflicts():
    equipment_rows = [
        {
            "equipment_id": "eq-001",
            "manufacturer": "QSC",
            "model": "CX-Q 4K8",
            "description": "Network amplifier",
            "quantity": 2,
            "system_id": "Audio",
            "room": "Rack Room",
            "drawing_reference": "AV-501",
            "specification_reference": "27 41 16",
            "confidence": 0.91,
        },
        {
            "equipment_id": "eq-002",
            "manufacturer": "",
            "model": "AM-1",
            "description": "Amplifier",
            "quantity": 1,
            "system_id": "Audio",
            "room": "Rack Room",
            "drawing_reference": "AV-501",
            "confidence": 0.7,
        },
        {
            "equipment_id": "eq-003",
            "manufacturer": "Biamp",
            "model": "Tesira",
            "description": "DSP",
            "quantity": 1,
            "system_id": "Control",
            "room": "Control Room",
            "drawing_reference": "AV-601",
            "confidence": 0.8,
        },
    ]
    resolver_rows = [
        {
            "target_id": "equipment:eq-003",
            "field": "quantity",
            "observed_values": "1, 2",
            "message": "Quantity differs between drawing and schedule.",
        }
    ]

    items = BomReviewService().build_items(
        equipment_rows=equipment_rows,
        resolver_rows=resolver_rows,
    )

    statuses = {item.bom_item_id: item.completeness_status for item in items}
    assert statuses["eq-001"] == COMPLETE
    assert statuses["eq-002"] == MISSING_MANUFACTURER
    assert statuses["eq-003"] == CONFLICTING_QUANTITY
    assert any("Quantity conflict" in warning for warning in items[2].warnings)


def test_build_items_detects_source_coverage_modes_and_unresolved():
    equipment_rows = [
        {
            "equipment_id": "eq-drawing",
            "manufacturer": "Atlas",
            "model": "D-1",
            "description": "Loudspeaker",
            "quantity": 4,
            "drawing_reference": "AV-101",
        },
        {
            "equipment_id": "eq-spec",
            "manufacturer": "Atlas",
            "model": "S-1",
            "description": "Amplifier",
            "quantity": 2,
            "specification_reference": "27 41 16",
        },
        {
            "equipment_id": "eq-none",
            "manufacturer": "Atlas",
            "model": "U-1",
            "description": "Interface",
            "quantity": 1,
        },
    ]

    items = BomReviewService().build_items(equipment_rows=equipment_rows)

    statuses = {item.bom_item_id: item.completeness_status for item in items}
    assert statuses["eq-drawing"] == DRAWING_ONLY
    assert statuses["eq-spec"] == SPECIFICATION_ONLY
    assert statuses["eq-none"] == UNRESOLVED


def test_export_payloads_are_deterministic_and_traceable(tmp_path):
    items = BomReviewService().build_items(
        equipment_rows=[
            {
                "equipment_id": "eq-b",
                "manufacturer": "B",
                "model": "2",
                "description": "Display device",
                "quantity": 2,
                "drawing_reference": "AV-301",
                "source_file": "drawings/av-301.pdf",
                "page": 10,
            },
            {
                "equipment_id": "eq-a",
                "manufacturer": "A",
                "model": "1",
                "description": "Display device",
                "quantity": 1,
                "specification_reference": "27 41 16",
                "source_file": "specs/27-41-16.pdf",
                "page": 2,
            },
        ],
        source_references=[
            {
                "source_file": "drawings/av-301.pdf",
                "page": 10,
                "excerpt": "eq-b display device",
            },
            {
                "source_file": "specs/27-41-16.pdf",
                "page": 2,
                "excerpt": "eq-a display device",
            },
        ],
    )

    service = BomReviewService()
    csv_text = service.to_csv_text(items)
    json_text = service.to_json_text(items)

    assert csv_text.splitlines()[1].startswith("eq-a,")
    payload = json.loads(json_text)
    assert payload["bom_items"][0]["bom_item_id"] == "eq-a"
    assert payload["bom_items"][1]["bom_item_id"] == "eq-b"
    assert "drawings/av-301.pdf" in payload["bom_items"][1]["source_documents"]

    csv_path = tmp_path / "candidate_bom.csv"
    json_path = tmp_path / "candidate_bom.json"
    service.export_bom_items_csv(items, csv_path)
    service.export_bom_items_json(items, json_path)

    assert csv_path.exists()
    assert json_path.exists()
