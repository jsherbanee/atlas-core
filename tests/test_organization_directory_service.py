from pathlib import Path

from atlas_core.domain import OrganizationRole
from atlas_core.services.organization_directory_service import (
    OrganizationDirectoryService,
)


def test_create_search_and_duplicate_detection(tmp_path: Path) -> None:
    service = OrganizationDirectoryService(tmp_path / "AtlasProjects")

    created = service.create_organization(
        name="Acme Consulting Group",
        role=OrganizationRole.CONSULTANT,
        aliases=["ACME Group"],
    )

    assert created.organization_id

    search_rows = service.search_organizations(
        "acme",
        role=OrganizationRole.CONSULTANT,
        include_inactive=False,
    )
    assert search_rows
    assert search_rows[0].organization_id == created.organization_id

    duplicate_rows = service.find_likely_duplicates("ACME Consulting Group")
    assert duplicate_rows
    assert duplicate_rows[0].organization_id == created.organization_id


def test_project_stakeholder_linking_supports_multi_role_reuse(tmp_path: Path) -> None:
    service = OrganizationDirectoryService(tmp_path / "AtlasProjects")
    org = service.create_organization(
        name="Unified Engineering",
        role=OrganizationRole.ENGINEER,
    )

    owner_link = service.link_organization_to_project(
        project_id="BID-2026-1001",
        organization_id=org.organization_id,
        role=OrganizationRole.OWNER_CLIENT,
        is_primary=True,
    )
    engineer_link = service.link_organization_to_project(
        project_id="BID-2026-1001",
        organization_id=org.organization_id,
        role=OrganizationRole.ENGINEER,
    )

    links = service.list_project_stakeholders("BID-2026-1001")
    assert len(links) == 2
    assert owner_link.organization_id == engineer_link.organization_id
    assert {item.role.value for item in links} == {
        OrganizationRole.OWNER_CLIENT.value,
        OrganizationRole.ENGINEER.value,
    }
