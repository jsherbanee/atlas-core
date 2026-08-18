from pathlib import Path

from atlas_core.services.master_library import CommercialProductService
from atlas_core.services.project_workspace_service import ProjectWorkspaceService


def _create_project(manager, project_id, root):
    project_payload = {"project_id": project_id, "name": project_id}
    metadata_payload = {}
    workspace_payload = {"workspace_state": {}}
    return manager.project_repository.create(
        project_id, project_payload, metadata_payload, workspace_payload
    )


def test_vendor_and_product_persistence_and_isolation(tmp_path: Path) -> None:
    root = tmp_path / "AtlasProjects"
    svc = ProjectWorkspaceService(workspace_root=str(root))

    # Create two projects
    _create_project(svc.manager, "proj-a", root)
    _create_project(svc.manager, "proj-b", root)

    # Project A: create vendor and product
    prod_service_a = CommercialProductService()
    prod_service_a.create_manufacturer(
        manufacturer_id="mfr-1", canonical_name="Mfr One"
    )
    prod_service_a.create_vendor(
        vendor_id="vendor-a", canonical_name="Vendor A", vendor_code="VA"
    )
    product = prod_service_a.create_product(
        manufacturer_id="mfr-1",
        manufacturer="Mfr One",
        manufacturer_part_number="P-100",
        product_name="Prod 100",
        product_description="Desc",
        category="general",
    )

    # Persist artifact for Project A
    svc.save_review_artifact("proj-a", "commercial_products", prod_service_a.to_dict())

    # Load into fresh service to simulate reopen
    artifact = svc.manager.review_repository.load_artifact(
        "proj-a", "commercial_products"
    )
    assert isinstance(artifact, dict)
    reopened = CommercialProductService(state=artifact)

    # Vendor and product exist after reopen
    assert reopened.get_vendor("vendor-a") is not None
    assert reopened.get_product(product["atlas_product_uuid"]) is not None

    # Project B should not have Project A's artifact
    artifact_b = svc.manager.review_repository.load_artifact(
        "proj-b", "commercial_products"
    )
    assert artifact_b is None


def test_field_fidelity_and_updates_and_archive(tmp_path: Path) -> None:
    root = tmp_path / "AtlasProjects"
    svc = ProjectWorkspaceService(workspace_root=str(root))
    _create_project(svc.manager, "proj-c", root)

    service = CommercialProductService()
    service.create_manufacturer(manufacturer_id="mfr-x", canonical_name="Mfr X")
    service.create_vendor(
        vendor_id="vendor-x", canonical_name="Vendor X", vendor_code="VX"
    )
    product = service.create_product(
        manufacturer_id="mfr-x",
        manufacturer="Mfr X",
        manufacturer_part_number="PX-1",
        product_name="Prod X",
        product_description="Desc",
        category="general",
    )

    # Persist
    svc.save_review_artifact("proj-c", "commercial_products", service.to_dict())

    # Reopen
    artifact = svc.manager.review_repository.load_artifact(
        "proj-c", "commercial_products"
    )
    reopened = CommercialProductService(state=artifact)

    # Field fidelity
    v = reopened.get_vendor("vendor-x")
    assert v["canonical_name"] == "Vendor X"

    p = reopened.get_product(product["atlas_product_uuid"])
    assert p["manufacturer_part_number"] == "PX-1"

    # Update durability
    reopened.update_vendor("vendor-x", updates={"display_name": "Vendor X Updated"})
    svc.save_review_artifact("proj-c", "commercial_products", reopened.to_dict())

    artifact2 = svc.manager.review_repository.load_artifact(
        "proj-c", "commercial_products"
    )
    reopened2 = CommercialProductService(state=artifact2)
    assert reopened2.get_vendor("vendor-x")["display_name"] == "Vendor X Updated"

    # Archive/restore durability
    reopened2.set_vendor_active("vendor-x", False)
    svc.save_review_artifact("proj-c", "commercial_products", reopened2.to_dict())
    artifact3 = svc.manager.review_repository.load_artifact(
        "proj-c", "commercial_products"
    )
    reopened3 = CommercialProductService(state=artifact3)
    assert reopened3.get_vendor("vendor-x")["active"] is False

    # restore
    reopened3.set_vendor_active("vendor-x", True)
    svc.save_review_artifact("proj-c", "commercial_products", reopened3.to_dict())
    artifact4 = svc.manager.review_repository.load_artifact(
        "proj-c", "commercial_products"
    )
    reopened4 = CommercialProductService(state=artifact4)
    assert reopened4.get_vendor("vendor-x")["active"] is True


def test_empty_project_compatibility(tmp_path: Path) -> None:
    root = tmp_path / "AtlasProjects"
    svc = ProjectWorkspaceService(workspace_root=str(root))
    _create_project(svc.manager, "proj-empty", root)

    # No artifact present
    artifact = svc.manager.review_repository.load_artifact(
        "proj-empty", "commercial_products"
    )
    assert artifact is None


def test_idempotent_persistence(tmp_path: Path) -> None:
    root = tmp_path / "AtlasProjects"
    svc = ProjectWorkspaceService(workspace_root=str(root))
    _create_project(svc.manager, "proj-idempotent", root)

    service = CommercialProductService()
    service.create_vendor(vendor_id="vendor-i", canonical_name="Vendor I")
    payload = service.to_dict()
    svc.save_review_artifact("proj-idempotent", "commercial_products", payload)
    svc.save_review_artifact("proj-idempotent", "commercial_products", payload)

    artifact = svc.manager.review_repository.load_artifact(
        "proj-idempotent", "commercial_products"
    )
    assert artifact == payload
