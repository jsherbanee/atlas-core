import pytest

from atlas_core.services.master_library import CommercialProductService


def _seed_service() -> CommercialProductService:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-qsc",
        canonical_name="QSC",
        display_name="QSC",
        manufacturer_code="QSC",
    )
    service.create_vendor(
        vendor_id="vendor-avp",
        canonical_name="AV Partner",
        display_name="AV Partner",
        vendor_code="AVP",
    )
    return service


def test_create_customer_and_service_entities_and_search() -> None:
    service = CommercialProductService()
    customer = service.create_customer(
        customer_id="cust-maw",
        canonical_name="Music Academy of the West",
        aliases=["MAW"],
        attributes={"portfolio": "education"},
    )
    svc = service.create_service_entity(
        service_id="svc-system-design",
        canonical_name="System Design",
        aliases=["design"],
    )

    assert customer["entity_type"] == "customer"
    assert svc["entity_type"] == "service"

    rows = service.search_knowledge_entities("maw", entity_type="customer")
    assert len(rows) == 1
    assert rows[0]["entity_id"] == "customer:cust-maw"


def test_knowledge_duplicate_detection_is_deterministic() -> None:
    service = CommercialProductService()
    service.create_customer(customer_id="cust-1", canonical_name="Acme University")
    duplicates = service.detect_duplicate_knowledge_entities(
        entity_type="customer",
        canonical_name="acme   university",
    )
    assert len(duplicates) == 1

    with pytest.raises(ValueError, match="Duplicate knowledge entity"):
        service.create_customer(customer_id="cust-2", canonical_name="ACME UNIVERSITY")


def test_knowledge_relationship_id_is_deterministic_and_idempotent() -> None:
    service = CommercialProductService()
    source = service.create_customer(customer_id="cust-1", canonical_name="Client A")
    target = service.create_service_entity(
        service_id="svc-1",
        canonical_name="Maintenance",
    )

    first = service.create_knowledge_relationship(
        source_entity_id=source["entity_id"],
        target_entity_id=target["entity_id"],
        relationship_type="consumes",
        confidence=0.7,
    )
    second = service.create_knowledge_relationship(
        source_entity_id=source["entity_id"],
        target_entity_id=target["entity_id"],
        relationship_type="consumes",
        confidence=0.9,
    )

    assert first["relationship_id"] == second["relationship_id"]
    assert second["confidence"] == 0.9


def test_knowledge_bundle_export_import_roundtrip() -> None:
    source = CommercialProductService()
    customer = source.create_customer(
        customer_id="cust-1",
        canonical_name="Client A",
    )
    svc = source.create_service_entity(
        service_id="svc-1",
        canonical_name="Maintenance",
    )
    source.create_knowledge_relationship(
        source_entity_id=customer["entity_id"],
        target_entity_id=svc["entity_id"],
        relationship_type="consumes",
    )

    bundle = source.export_knowledge_entity_bundle()

    target = CommercialProductService()
    summary = target.import_knowledge_entity_bundle(bundle=bundle)
    assert summary["upserted_entities"] == 2
    assert summary["upserted_relationships"] == 1
    assert len(target.list_knowledge_entities()) == 2
    assert len(target.list_knowledge_relationships()) == 1


def test_existing_commercial_methods_sync_knowledge_entities() -> None:
    service = _seed_service()

    product = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="CORE-110F",
        product_name="Core 110f",
        product_description="DSP",
        category="dsp",
    )

    entities = service.list_knowledge_entities()
    entity_ids = {item["entity_id"] for item in entities}
    assert "manufacturer:mfr-qsc" in entity_ids
    assert "vendor:vendor-avp" in entity_ids
    assert f"product:{product['atlas_product_uuid']}" in entity_ids
