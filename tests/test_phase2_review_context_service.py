import pytest

from atlas_core.services.phase2_review_context_service import (
    build_sample_review_context,
    get_sample_projects,
)


def test_sample_project_catalog_contains_maw() -> None:
    projects = get_sample_projects()

    assert projects == [
        {
            "id": "maw",
            "label": "Music Academy of the West (MAW)",
            "description": "Canonical sample/reference project.",
        }
    ]


def test_build_sample_review_context_returns_phase2_outputs() -> None:
    context = build_sample_review_context("maw")

    readiness = context["review"].readiness
    brief = context["brief"]
    revision = context["revision_comparison"]

    assert context["sample_project_id"] == "maw"
    assert context["sample_project_name"] == "Music Academy of the West"
    assert readiness is not None
    assert readiness.readiness_score is not None
    assert readiness.readiness_level is not None
    assert brief.brief_title
    assert isinstance(brief.prioritized_reviewer_actions, list)
    assert revision.summary["change_count"] > 0


def test_unknown_sample_project_id_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported sample project id"):
        build_sample_review_context("unknown")
