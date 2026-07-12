from atlas_core.domain import (
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
    ProductResolutionStatus,
)
from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import MasterLibraryService, ProductResolutionService


def _row(
    *,
    equipment_id: str,
    manufacturer: str,
    model: str,
    description: str = "Audio DSP",
    completeness_status: str = "complete",
) -> dict[str, object]:
    return {
        "equipment_id": equipment_id,
        "manufacturer": manufacturer,
        "model": model,
        "description": description,
        "system": "Audio",
        "room": "Rack",
        "completeness_status": completeness_status,
        "drawing_references": ["AV-601"],
        "specification_references": ["27 41 16"],
        "source_documents": ["bid-set.pdf"],
    }


def _registry() -> ManufacturerRegistry:
    return ManufacturerRegistry(
        [
            Manufacturer(
                manufacturer_id="qsc",
                name="QSC",
                discipline=ManufacturerDiscipline.AUDIO,
                tier=ManufacturerTier.PREFERRED,
            ),
            Manufacturer(
                manufacturer_id="biamp",
                name="Biamp",
                discipline=ManufacturerDiscipline.AUDIO,
                tier=ManufacturerTier.APPROVED,
            ),
            Manufacturer(
                manufacturer_id="bose",
                name="Bose",
                discipline=ManufacturerDiscipline.AUDIO,
                tier=ManufacturerTier.PREFERRED,
            ),
        ]
    )


def test_exact_match_resolution() -> None:
    service = ProductResolutionService(
        master_library_service=MasterLibraryService(),
        manufacturer_registry=_registry(),
    )

    rows = [_row(equipment_id="EQ-1", manufacturer="QSC", model="Core 110f")]
    resolutions = service.resolve_equipment_rows(rows)

    resolution = resolutions[0]
    assert resolution.resolution_status is ProductResolutionStatus.EXACT_PRODUCT
    assert resolution.canonical_product is not None
    assert resolution.resolution_reason == "Exact manufacturer/model match."


def test_alias_match_resolution() -> None:
    library = MasterLibraryService()
    library.import_workspace_equipment(
        [_row(equipment_id="EQ-1", manufacturer="Shure", model="ULX-D4Q")]
    )

    service = ProductResolutionService(
        master_library_service=library,
        manufacturer_registry=_registry(),
    )
    resolutions = service.resolve_equipment_rows(
        [_row(equipment_id="EQ-2", manufacturer="Shure", model="ULXD4Q")]
    )

    resolution = resolutions[0]
    assert resolution.resolution_status is ProductResolutionStatus.EXACT_PRODUCT
    assert any(
        candidate.match_type in {"alias_match", "normalized_manufacturer_model"}
        for candidate in resolution.candidate_matches
    )


def test_approved_substitute_resolution() -> None:
    library = MasterLibraryService()
    library.import_workspace_equipment(
        [_row(equipment_id="EQ-1", manufacturer="Biamp", model="Tesira Forte")]
    )

    service = ProductResolutionService(
        master_library_service=library,
        manufacturer_registry=_registry(),
    )

    resolutions = service.resolve_equipment_rows(
        [_row(equipment_id="EQ-2", manufacturer="QSC", model="Unknown")]
    )
    resolution = resolutions[0]

    assert resolution.resolution_status in {
        ProductResolutionStatus.APPROVED_SUBSTITUTE,
        ProductResolutionStatus.UNKNOWN_PRODUCT,
    }


def test_unknown_resolution() -> None:
    service = ProductResolutionService(
        master_library_service=MasterLibraryService(),
        manufacturer_registry=_registry(),
    )

    resolutions = service.resolve_equipment_rows(
        [_row(equipment_id="EQ-UNK", manufacturer="Unknown", model="Unknown")]
    )

    resolution = resolutions[0]
    assert resolution.resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT
    assert "Unknown product" in resolution.resolution_reason


def test_manual_override_resolution() -> None:
    service = ProductResolutionService(
        master_library_service=MasterLibraryService(),
        manufacturer_registry=_registry(),
    )

    rows = [_row(equipment_id="EQ-1", manufacturer="QSC", model="Core 110f")]
    auto = service.resolve_equipment_rows(rows)[0]
    product_id = auto.canonical_product_id
    assert product_id is not None

    overridden = service.resolve_equipment_rows(
        rows,
        manual_overrides={
            "EQ-1": {
                "selected_product_id": product_id,
                "resolution_status": "preferred_alternate",
                "reviewer": "Estimator A",
                "timestamp": "2026-07-11T10:00:00+00:00",
                "reason": "Project standardization choice.",
            }
        },
    )[0]

    assert overridden.manual_override is not None
    assert overridden.manual_override.reviewer == "Estimator A"
    assert overridden.resolution_status is ProductResolutionStatus.PREFERRED_ALTERNATE


def test_resolution_confidence_and_traceability() -> None:
    service = ProductResolutionService(
        master_library_service=MasterLibraryService(),
        manufacturer_registry=_registry(),
    )

    resolution = service.resolve_equipment_rows(
        [_row(equipment_id="EQ-1", manufacturer="QSC", model="Core 110f")]
    )[0]

    assert 0.0 <= resolution.resolution_confidence <= 1.0
    assert resolution.source_evidence == ["27 41 16", "AV-601", "bid-set.pdf"]
    assert resolution.candidate_matches
