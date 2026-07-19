from pathlib import Path

import pytest

from atlas_core.services.master_library import CommercialProductService
from atlas_core.services.organization_directory_service import (
    OrganizationDirectoryService,
)
from atlas_core.services.organization_merge_service import OrganizationMergeService


def _merge_service(
    tmp_path: Path,
) -> tuple[CommercialProductService, OrganizationMergeService]:
    product_service = CommercialProductService()
    directory = OrganizationDirectoryService(tmp_path / "AtlasProjects")
    return product_service, OrganizationMergeService(
        organization_directory=directory,
        product_service=product_service,
        tenant_id="local",
        organization_scope_id="atlas",
    )


def test_same_role_customer_merge_redirects_legacy_record_and_reassigns_relationships(
    tmp_path: Path,
) -> None:
    product_service, merge_service = _merge_service(tmp_path)
    primary = product_service.create_customer(
        customer_id="cust-acme",
        canonical_name="Acme Systems",
        attributes={"website": "https://acme.example", "primary_phone": "555-0100"},
    )
    duplicate = product_service.create_customer(
        customer_id="cust-acme-west",
        canonical_name="Acme Systems West",
        aliases=["Acme Systems"],
        attributes={"website": "https://acme.example", "primary_phone": "555-0101"},
    )
    contact = product_service.create_contact(
        contact_id="contact-acme",
        canonical_name="Jordan Acme",
    )
    product_service.create_knowledge_relationship(
        source_entity_id=duplicate["entity_id"],
        target_entity_id=contact["entity_id"],
        relationship_type="has_contact",
    )

    organization = merge_service.ensure_organization_for_role_record(
        primary["entity_id"]
    )
    preview = merge_service.preview_merge(
        primary_organization_id=organization.organization_id,
        source_entity_ids=[duplicate["entity_id"]],
    )
    assert preview["relationship_reassignment_preview"]["knowledge_relationships"] == 1
    assert "customer" in preview["roles_after"]

    result = merge_service.confirm_merge(
        primary_organization_id=organization.organization_id,
        source_entity_ids=[duplicate["entity_id"]],
        actor="qa-user",
        reason="Duplicate customer cleanup",
        conflict_resolutions={"phone": "primary"},
        permission_granted=True,
    )

    redirected = product_service.get_knowledge_entity(duplicate["entity_id"])
    assert redirected is not None
    assert redirected["active"] is False
    assert redirected["attributes"]["merge_status"] == "redirected"
    assert (
        redirected["attributes"]["merged_into_organization_id"]
        == organization.organization_id
    )
    legacy_redirect = merge_service.legacy_redirect(duplicate["entity_id"])
    assert legacy_redirect is not None
    assert legacy_redirect["organization_id"] == organization.organization_id
    assert result["relationship_reassignment_counts"]["relationships_reassigned"] == 1
    relationships = product_service.list_knowledge_relationships()
    assert (
        relationships[0]["source_entity_id"]
        == f"organization:{organization.organization_id}"
    )
    assert duplicate["entity_id"] not in [
        item["entity_id"]
        for item in product_service.list_customers(include_inactive=False)
    ]
    assert product_service.search_knowledge_entities(
        "Acme Systems West", entity_type="customer", include_inactive=True
    )


def test_cross_role_organization_consolidation_preserves_role_identifiers(
    tmp_path: Path,
) -> None:
    product_service, merge_service = _merge_service(tmp_path)
    customer = product_service.create_customer(
        customer_id="cust-unified",
        canonical_name="Unified AV",
        attributes={"billing_terms": "Net 30"},
    )
    vendor = product_service.create_vendor(
        vendor_id="vendor-unified",
        canonical_name="Unified AV Supply",
        vendor_code="UAV",
    )
    vendor_entity_id = f"vendor:{vendor['vendor_id']}"
    manufacturer = product_service.create_manufacturer(
        manufacturer_id="mfr-unified",
        canonical_name="Unified AV Manufacturing",
        manufacturer_code="UAV-M",
    )
    manufacturer_entity_id = f"manufacturer:{manufacturer['manufacturer_id']}"

    organization = merge_service.ensure_organization_for_role_record(
        customer["entity_id"]
    )
    merge_service.confirm_merge(
        primary_organization_id=organization.organization_id,
        source_entity_ids=[vendor_entity_id, manufacturer_entity_id],
        actor="qa-user",
        reason="Same legal organization with multiple roles",
        permission_granted=True,
    )

    organization_entity = product_service.get_knowledge_entity(
        f"organization:{organization.organization_id}"
    )
    assert organization_entity is not None
    profiles = organization_entity["attributes"]["role_profiles"]
    assert sorted(profiles) == ["customer", "manufacturer", "vendor"]
    assert profiles["customer"]["identifiers"] == ["cust-unified"]
    assert profiles["vendor"]["identifiers"] == ["vendor-unified"]
    assert profiles["manufacturer"]["identifiers"] == ["mfr-unified"]


def test_duplicate_suggestions_are_deterministic_and_explainable(
    tmp_path: Path,
) -> None:
    product_service, merge_service = _merge_service(tmp_path)
    customer = product_service.create_customer(
        customer_id="cust-north",
        canonical_name="Northstar Group",
        attributes={"website": "https://northstar.example"},
    )
    merge_service.ensure_organization_for_role_record(customer["entity_id"])
    vendor = product_service.create_vendor(
        vendor_id="vendor-north",
        canonical_name="Northstar Distribution",
        website="https://northstar.example",
    )

    suggestions = merge_service.duplicate_suggestions_for_role_record(
        f"vendor:{vendor['vendor_id']}"
    )

    assert suggestions
    assert "website domain" in suggestions[0]["reasons"]
    assert suggestions[0]["confidence_inputs"] == suggestions[0]["reasons"]


def test_merge_requires_scope_permission_actor_and_reason(tmp_path: Path) -> None:
    product_service, merge_service = _merge_service(tmp_path)
    customer = product_service.create_customer(
        customer_id="cust-a",
        canonical_name="Customer A",
    )
    duplicate = product_service.create_customer(
        customer_id="cust-b",
        canonical_name="Customer B",
    )
    organization = merge_service.ensure_organization_for_role_record(
        customer["entity_id"]
    )

    with pytest.raises(PermissionError):
        merge_service.confirm_merge(
            primary_organization_id=organization.organization_id,
            source_entity_ids=[duplicate["entity_id"]],
            actor="qa-user",
            reason="Denied",
            permission_granted=False,
        )
    duplicate_entity = product_service.get_knowledge_entity(duplicate["entity_id"])
    assert duplicate_entity is not None
    assert duplicate_entity["active"] is True

    with pytest.raises(ValueError):
        merge_service.confirm_merge(
            primary_organization_id=organization.organization_id,
            source_entity_ids=[duplicate["entity_id"]],
            actor="",
            reason="Missing actor",
            permission_granted=True,
        )
    with pytest.raises(PermissionError):
        OrganizationMergeService(
            organization_directory=merge_service.organization_directory,
            product_service=product_service,
            tenant_id="",
            organization_scope_id="atlas",
        )


def test_tenant_mismatch_rejects_merge(tmp_path: Path) -> None:
    product_service = CommercialProductService()
    directory = OrganizationDirectoryService(tmp_path / "AtlasProjects")
    merge_service = OrganizationMergeService(
        organization_directory=directory,
        product_service=product_service,
        tenant_id="tenant-a",
        organization_scope_id="org-a",
    )
    customer = product_service.create_customer(
        customer_id="cust-a",
        canonical_name="Tenant Customer",
    )
    organization = merge_service.ensure_organization_for_role_record(
        customer["entity_id"]
    )
    wrong_scope_service = OrganizationMergeService(
        organization_directory=directory,
        product_service=product_service,
        tenant_id="tenant-b",
        organization_scope_id="org-a",
    )

    with pytest.raises(PermissionError):
        wrong_scope_service.preview_merge(
            primary_organization_id=organization.organization_id,
            source_entity_ids=[],
        )


def test_failed_merge_rolls_back_relationship_mutation(tmp_path: Path) -> None:
    product_service, merge_service = _merge_service(tmp_path)
    primary = product_service.create_customer(
        customer_id="cust-main",
        canonical_name="Main Customer",
    )
    source = product_service.create_vendor(
        vendor_id="vendor-main",
        canonical_name="Main Vendor",
    )
    source_entity_id = f"vendor:{source['vendor_id']}"
    contact = product_service.create_contact(
        contact_id="contact-main",
        canonical_name="Main Contact",
    )
    product_service.create_knowledge_relationship(
        source_entity_id=source_entity_id,
        target_entity_id=contact["entity_id"],
        relationship_type="has_contact",
    )
    organization = merge_service.ensure_organization_for_role_record(
        primary["entity_id"]
    )

    with pytest.raises(PermissionError):
        merge_service.confirm_merge(
            primary_organization_id=organization.organization_id,
            source_entity_ids=[source_entity_id],
            actor="qa-user",
            reason="Denied",
            permission_granted=False,
        )

    relationships = product_service.list_knowledge_relationships()
    assert relationships[0]["source_entity_id"] == source_entity_id
    source_entity = product_service.get_knowledge_entity(source_entity_id)
    assert source_entity is not None
    assert source_entity["active"] is True
    assert any(
        item["event_type"] == "organization_merge_failed"
        for item in product_service.list_knowledge_audit_events()
    )
