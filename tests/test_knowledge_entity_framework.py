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


def test_create_contact_location_and_project_entities_and_search() -> None:
    service = CommercialProductService()
    customer = service.create_customer(
        customer_id="cust-1",
        canonical_name="Client One",
    )
    contact = service.create_contact(
        contact_id="contact-1",
        canonical_name="Jordan Lee",
        display_name="Jordan Lee",
        email="jordan@example.com",
        phone="555-0101",
        title="Project Manager",
        organization="Client One",
    )
    location = service.create_location(
        location_id="loc-1",
        canonical_name="Main Office",
        display_name="Main Office",
        address_line1="100 Main St",
        city="Los Angeles",
        state="CA",
        postal_code="90001",
        country="US",
        external_identifier="LOC-EXT-1",
    )
    project = service.create_project_entity(
        project_id="proj-1",
        canonical_name="Project One",
        display_name="Project One",
        customer="Client One",
        location="Main Office",
        client_project_number="C-1001",
        internal_project_number="I-1001",
        status="active",
        relationships=[
            {
                "source_entity_id": customer["entity_id"],
                "target_entity_id": contact["entity_id"],
                "relationship_type": "has_contact",
            },
            {
                "source_entity_id": "project:proj-1",
                "target_entity_id": location["entity_id"],
                "relationship_type": "located_at",
            },
        ],
    )

    assert contact["entity_type"] == "contact"
    assert location["entity_type"] == "location"
    assert project["entity_type"] == "project"

    assert (
        service.search_contacts("jordan@example.com")[0]["entity_id"]
        == contact["entity_id"]
    )
    assert (
        service.search_locations("loc-ext-1")[0]["entity_id"] == location["entity_id"]
    )
    assert (
        service.search_project_entities("c-1001")[0]["entity_id"]
        == project["entity_id"]
    )
    assert len(service.list_knowledge_relationships()) == 2


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


def test_customer_and_service_operational_workflows() -> None:
    service = CommercialProductService()
    service.create_customer(customer_id="cust-1", canonical_name="Client A")
    service.create_service_entity(service_id="svc-1", canonical_name="Maintenance")

    updated_customer = service.update_customer(
        "cust-1",
        updates={
            "display_name": "Client A (Updated)",
            "aliases": ["client-a"],
            "attributes": {"segment": "education"},
        },
    )
    assert updated_customer["display_name"] == "Client A (Updated)"
    assert updated_customer["attributes"]["segment"] == "education"

    service.set_customer_active("cust-1", False)
    assert service.get_customer("cust-1") is not None
    assert bool(dict(service.get_customer("cust-1") or {}).get("active")) is False
    assert service.search_customers("client", include_inactive=False) == []
    assert len(service.search_customers("client", include_inactive=True)) == 1

    updated_service = service.update_service_entity(
        "svc-1",
        updates={"notes": "Standard support", "attributes": {"tier": "gold"}},
    )
    assert updated_service["notes"] == "Standard support"
    assert updated_service["attributes"]["tier"] == "gold"

    service.set_service_entity_active("svc-1", False)
    assert bool(dict(service.get_service_entity("svc-1") or {}).get("active")) is False
    service.set_service_entity_active("svc-1", True)
    assert bool(dict(service.get_service_entity("svc-1") or {}).get("active")) is True


def test_knowledge_entity_summary_and_product_lifecycle_sync() -> None:
    service = _seed_service()
    customer = service.create_customer(customer_id="cust-1", canonical_name="Client A")
    support = service.create_service_entity(
        service_id="svc-1", canonical_name="Support"
    )
    service.create_knowledge_relationship(
        source_entity_id=customer["entity_id"],
        target_entity_id=support["entity_id"],
        relationship_type="consumes",
    )

    product = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="CORE-8",
        product_name="Core 8",
        product_description="DSP",
        category="dsp",
    )
    product_entity_id = f"product:{product['atlas_product_uuid']}"

    service.mark_product_discontinued(product["atlas_product_uuid"])
    inactive_product_entity = service.get_knowledge_entity(product_entity_id)
    assert inactive_product_entity is not None
    assert bool(dict(inactive_product_entity).get("active")) is False
    assert (
        dict(inactive_product_entity).get("attributes", {}).get("lifecycle_status")
        == "discontinued"
    )

    service.reactivate_product(product["atlas_product_uuid"])
    active_product_entity = service.get_knowledge_entity(product_entity_id)
    assert active_product_entity is not None
    assert bool(dict(active_product_entity).get("active")) is True
    assert (
        dict(active_product_entity).get("attributes", {}).get("lifecycle_status")
        == "active"
    )

    summary = service.knowledge_entity_summary()
    assert summary["total_entities"] >= 5
    assert summary["total_relationships"] == 1
    assert summary["by_type"]["customer"]["total"] == 1
    assert summary["by_type"]["service"]["total"] == 1


@pytest.mark.parametrize(
    ("entity_type", "id_header", "id_value", "canonical_name"),
    [
        ("customer", "customer_id", "cust-100", "Customer 100"),
        ("service", "service_id", "svc-100", "Service 100"),
        ("manufacturer", "manufacturer_id", "mfr-100", "Manufacturer 100"),
        ("vendor", "vendor_id", "vendor-100", "Vendor 100"),
        ("contact", "contact_id", "contact-100", "Contact 100"),
        ("location", "location_id", "location-100", "Location 100"),
        ("project", "project_id", "project-100", "Project 100"),
    ],
)
def test_csv_template_and_partial_success_import_for_core_entities(
    entity_type: str,
    id_header: str,
    id_value: str,
    canonical_name: str,
) -> None:
    service = CommercialProductService()
    template = service.knowledge_entity_csv_template(entity_type=entity_type)
    assert id_header in template

    csv_text = (
        f"{id_header},canonical_name,display_name,aliases,notes,active\n"
        f"{id_value},{canonical_name},{canonical_name},alias-one,ok,true\n"
        f",Broken Row,,alias-two,missing id,true\n"
    ).encode("utf-8")
    preview = service.preview_knowledge_entity_import_csv(
        entity_type=entity_type,
        file_bytes=csv_text,
    )
    assert preview["record_count"] == 2
    assert preview["accepted_count"] == 1
    assert preview["rejected_count"] == 1

    imported = service.import_knowledge_entities_from_csv(
        entity_type=entity_type,
        file_bytes=csv_text,
        allow_partial_success=True,
    )
    assert imported["imported_rows"] == 1
    assert imported["rejected_rows"] == 1
    assert "row_number" in imported["rejected_rows_csv"]

    exported_csv = service.export_knowledge_entities_csv(entity_type=entity_type)
    assert canonical_name in exported_csv
    exported_json = service.export_knowledge_entities_json(entity_type=entity_type)
    assert canonical_name in exported_json


def test_contact_location_and_project_csv_import_roundtrip() -> None:
    service = CommercialProductService()
    contact_csv = (
        "contact_id,canonical_name,display_name,email,phone,title,organization,external_identifier,aliases,notes,active\n"
        "contact-200,Contact 200,Contact 200,contact200@example.com,555-0200,Coordinator,Client One,EXT-200,Alias One,ok,true\n"
        ",Broken Contact,,,,,,,,missing id,true\n"
    ).encode("utf-8")
    location_csv = (
        "location_id,canonical_name,display_name,address_line1,address_line2,city,state,postal_code,country,external_identifier,aliases,notes,active\n"
        "location-200,Location 200,Location 200,200 Main St,,Los Angeles,CA,90002,US,EXT-200,Alias Two,ok,true\n"
        ",Broken Location,,,,,,,,,,missing id,true\n"
    ).encode("utf-8")
    project_csv = (
        "project_id,canonical_name,display_name,customer,location,client_project_number,internal_project_number,status,external_identifier,aliases,notes,active\n"
        "project-200,Project 200,Project 200,Client One,Location 200,C-200,I-200,active,EXT-PROJ-200,Alias Three,ok,true\n"
        ",Broken Project,,,,,,,,,,missing id,true\n"
    ).encode("utf-8")

    for entity_type, payload, expected in [
        ("contact", contact_csv, "contact-200"),
        ("location", location_csv, "location-200"),
        ("project", project_csv, "project-200"),
    ]:
        preview = service.preview_knowledge_entity_import_csv(
            entity_type=entity_type,
            file_bytes=payload,
        )
        assert preview["record_count"] == 2
        assert preview["accepted_count"] == 1
        assert preview["rejected_count"] == 1

        imported = service.import_knowledge_entities_from_csv(
            entity_type=entity_type,
            file_bytes=payload,
            allow_partial_success=True,
        )
        assert imported["imported_rows"] == 1
        assert imported["rejected_rows"] == 1
        assert expected in service.export_knowledge_entities_csv(
            entity_type=entity_type
        )


def test_product_csv_import_requires_manufacturer_identity_and_part_number() -> None:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-200",
        canonical_name="Manufacturer 200",
    )
    template = service.knowledge_entity_csv_template(entity_type="product")
    assert "manufacturer_id" in template
    assert "manufacturer_part_number" in template

    csv_text = (
        "manufacturer_id,manufacturer_part_number,product_name,product_description,category,lifecycle_status,active,notes\n"
        "mfr-200,PART-200,Product 200,Description,dsp,active,true,ok\n"
        "mfr-unknown,PART-201,Product 201,Description,dsp,active,true,bad-manufacturer\n"
        "mfr-200,,Product 202,Description,dsp,active,true,missing-part\n"
    ).encode("utf-8")

    preview = service.preview_knowledge_entity_import_csv(
        entity_type="product",
        file_bytes=csv_text,
    )
    assert preview["record_count"] == 3
    assert preview["accepted_count"] == 1
    assert preview["rejected_count"] == 2

    imported = service.import_knowledge_entities_from_csv(
        entity_type="product",
        file_bytes=csv_text,
        allow_partial_success=True,
    )
    assert imported["imported_rows"] == 1
    assert imported["rejected_rows"] == 2

    entities = service.list_knowledge_entities(entity_type="product")
    assert len(entities) == 1
    assert entities[0]["attributes"]["manufacturer_part_number"] == "PART-200"


def test_knowledge_import_duplicate_diagnostics_and_audit_history() -> None:
    service = CommercialProductService()
    csv_text = (
        "customer_id,canonical_name,display_name,aliases,notes,active\n"
        "cust-dup,Duplicate Name,Duplicate Name,,ok,true\n"
        "cust-dup,Duplicate Name,Duplicate Name,,duplicate,true\n"
    ).encode("utf-8")
    preview = service.preview_knowledge_entity_import_csv(
        entity_type="customer",
        file_bytes=csv_text,
    )
    assert preview["accepted_count"] == 0
    assert preview["rejected_count"] == 2
    assert any(
        item.get("code") == "duplicate_row_identity"
        for item in list(preview.get("diagnostics") or [])
    )

    with pytest.raises(ValueError, match="partial success not allowed"):
        service.import_knowledge_entities_from_csv(
            entity_type="customer",
            file_bytes=csv_text,
            allow_partial_success=False,
        )

    events = service.list_knowledge_audit_events(event_type="knowledge_csv_imported")
    assert events == []

    ok_csv = (
        "customer_id,canonical_name,display_name,aliases,notes,active\n"
        "cust-ok,Customer OK,Customer OK,,ok,true\n"
    ).encode("utf-8")
    service.import_knowledge_entities_from_csv(
        entity_type="customer",
        file_bytes=ok_csv,
        allow_partial_success=True,
    )
    events = service.list_knowledge_audit_events(event_type="knowledge_csv_imported")
    assert len(events) == 1
