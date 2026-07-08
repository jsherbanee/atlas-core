from atlas_core.services.master_library import MasterLibraryService


def test_import_workspace_equipment_creates_canonical_products_with_aliases() -> None:
    service = MasterLibraryService()

    service.import_workspace_equipment(
        [
            {
                "equipment_id": "eq-1",
                "manufacturer": "QSC",
                "model": "Core 110f",
                "description": "Q-SYS network DSP core",
                "system": "Audio",
                "room": "Rack Room",
                "drawing_references": ["AV-101"],
                "specification_references": ["27 41 16"],
                "confidence": 0.84,
            },
            {
                "equipment_id": "eq-2",
                "manufacturer": "QSC",
                "model": "CORE-110F",
                "description": "QSYS Core Processor",
                "system": "Audio",
                "room": "Rack Room",
                "drawing_references": ["AV-201"],
                "specification_references": ["27 41 16"],
                "confidence": 0.82,
            },
        ]
    )

    rows = service.explorer_rows()
    assert len(rows) == 1
    row = rows[0]

    assert row["manufacturer"] == "QSC"
    assert row["normalized_model"] == "CORE110F"
    assert row["category"] == "dsp"
    assert len(row["aliases"]) >= 2


def test_alias_resolution_matches_model_alias_with_traceability() -> None:
    service = MasterLibraryService()
    service.import_workspace_equipment(
        [
            {
                "equipment_id": "eq-1",
                "manufacturer": "Shure",
                "model": "ULX-D4Q",
                "description": "Wireless Receiver",
                "system": "Audio",
                "room": "Booth",
                "drawing_references": ["AV-301"],
                "specification_references": ["27 51 23"],
                "confidence": 0.79,
            }
        ]
    )

    resolution = service.resolve_product(
        manufacturer="Shure",
        model="ULXD4Q",
        description="Wireless receiver rack unit",
    )

    matched = dict(resolution.get("matched") or {})
    assert matched["manufacturer"] == "Shure"
    assert matched["normalized_model"] == "ULXD4Q"
    assert float(resolution.get("confidence", 0.0)) > 0.5
    assert any("match_path=" in entry for entry in list(resolution.get("trace") or []))


def test_alias_resolution_falls_back_to_alias_path_when_manufacturer_alias_differs() -> (
    None
):
    service = MasterLibraryService()
    service.import_workspace_equipment(
        [
            {
                "equipment_id": "eq-1",
                "manufacturer": "QSC",
                "model": "Core 110f",
                "description": "Q-SYS DSP core",
                "system": "Audio",
                "room": "Rack",
                "drawing_references": [],
                "specification_references": [],
                "confidence": 0.85,
            }
        ]
    )

    resolution = service.resolve_product(
        manufacturer="Q-SYS",
        model="CORE-110F",
        description="DSP core",
    )

    trace = list(resolution.get("trace") or [])
    assert any(item == "match_path=alias" for item in trace)
    assert dict(resolution.get("matched") or {}).get("manufacturer") == "QSC"
