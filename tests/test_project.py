import pytest

from atlas_core.domain import Project, ProjectLifecycleEvent, ProjectStatus


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
        "lifecycle_events": [],
    }


def test_lifecycle_event_creation():
    event = ProjectLifecycleEvent(
        from_status="opportunity",
        to_status=ProjectStatus.SUBMITTED,
        note=" Bid sent. ",
        changed_by=" Estimator ",
    )

    assert event.from_status is ProjectStatus.OPPORTUNITY
    assert event.to_status is ProjectStatus.SUBMITTED
    assert event.note == "Bid sent."
    assert event.changed_by == "Estimator"
    assert isinstance(event.changed_at, str)


def test_project_status_transition_records_lifecycle_event():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")

    project.mark_submitted(note="Submitted to GC.", changed_by="Alex")

    assert project.status is ProjectStatus.SUBMITTED
    assert len(project.lifecycle_events) == 1
    assert project.lifecycle_events[0].from_status is ProjectStatus.INTAKE
    assert project.lifecycle_events[0].to_status is ProjectStatus.SUBMITTED
    assert project.lifecycle_events[0].note == "Submitted to GC."
    assert project.lifecycle_events[0].changed_by == "Alex"


def test_opportunity_to_submitted_to_awarded_to_active_preserves_project_data():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")
    project.add_building("Main Building")

    project.mark_opportunity()
    project.mark_submitted()
    project.mark_awarded()
    project.mark_active()

    assert project.project_id == "p-001"
    assert project.buildings == ["Main Building"]
    assert project.status is ProjectStatus.ACTIVE
    assert [
        event.to_status
        for event in project.lifecycle_events
    ] == [
        ProjectStatus.OPPORTUNITY,
        ProjectStatus.SUBMITTED,
        ProjectStatus.AWARDED,
        ProjectStatus.ACTIVE,
    ]


def test_to_dict_includes_lifecycle_events():
    project = Project(project_id="p-001", name="City Hall Refresh", client="Acme")

    project.mark_awarded(note="Awarded by owner.", changed_by="Sam")

    data = project.to_dict()
    assert data["lifecycle_events"] == [
        {
            "from_status": "intake",
            "to_status": "awarded",
            "note": "Awarded by owner.",
            "changed_by": "Sam",
            "changed_at": project.lifecycle_events[0].changed_at,
        }
    ]
