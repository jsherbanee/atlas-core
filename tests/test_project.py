import pytest

from atlas_core.domain import Project, ProjectStatus


def test_creating_valid_project():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")

    assert project.project_id == "p-001"
    assert project.name == "City Hall Refresh"
    assert project.client == "Acme"
    assert project.status is ProjectStatus.INTAKE
    assert project.target_margin == 0.28
    assert project.cslb_scope == "C7"
    assert project.is_ready_for_estimate()


def test_rejecting_blank_project_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Project(project_id="p-001", name=" ", client="Acme")


def test_adding_buildings():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")

    project.add_building("Main Building")
    project.add_building("Annex")

    assert project.buildings == ["Main Building", "Annex"]


def test_adding_notes():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")

    project.add_note("Confirm cabling pathway.")
    project.add_note("Owner prefers phased install.")

    assert project.notes == [
        "Confirm cabling pathway.",
        "Owner prefers phased install.",
    ]


def test_to_dict_output():
    project = Project(
        project_id="p-001",
        name="City Hall Refresh",
        client="Acme",
        location="Oakland, CA",
        bid_date="2026-07-15",
        status=ProjectStatus.ESTIMATING,
        google_drive_folder="drive-folder-id",
        output_folder="/tmp/atlas/p-001",
        target_margin=0.32,
    )
    project.add_building("Main Building")
    project.add_note("Confirm cabling pathway.")

    assert project.to_dict() == {
        "project_id": "p-001",
        "name": "City Hall Refresh",
        "client": "Acme",
        "location": "Oakland, CA",
        "bid_date": "2026-07-15",
        "status": "estimating",
        "buildings": ["Main Building"],
        "google_drive_folder": "drive-folder-id",
        "output_folder": "/tmp/atlas/p-001",
        "target_margin": 0.32,
        "cslb_scope": "C7",
        "notes": ["Confirm cabling pathway."],
    }
