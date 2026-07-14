from __future__ import annotations

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.commercial_document_service import CommercialNumberingService
from atlas_core.services.settings_service import SettingsService
import pytest


def _service() -> SettingsService:
    return SettingsService()


def test_numbering_syntax_validation_rejects_missing_sequence() -> None:
    service = _service()

    with pytest.raises(ValueError, match=r"must include \{SEQUENCE\}"):
        service.update_numbering_policy(
            tenant_id="tenant-a",
            organization_id="org-1",
            document_type=CommercialDocumentType.ESTIMATE,
            actor="tester",
            syntax_template="{PREFIX}-{TYPE}",
            prefix="ATLAS-EST",
            suffix="",
            starting_sequence=1,
            sequence_padding=5,
            separator="-",
            reset_policy="never",
            include_year_token=False,
            include_month_token=False,
            include_project_code_token=False,
        )


def test_numbering_prefix_suffix_and_tokens_render_deterministically() -> None:
    service = _service()
    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.PURCHASE_ORDER,
        actor="tester",
        syntax_template="{PREFIX}-{TYPE}-{YEAR}-{MONTH}-{PROJECT_CODE}-{SEQUENCE}-{SUFFIX}",
        prefix="ACME",
        suffix="FINAL",
        starting_sequence=7,
        sequence_padding=4,
        separator="-",
        reset_policy="never",
        include_year_token=True,
        include_month_token=True,
        include_project_code_token=True,
    )

    preview = service.preview_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.PURCHASE_ORDER,
        project_code="PRJ-7",
        as_of="2026-07-13T00:00:00+00:00",
    )

    assert preview == "ACME-PURCHASE-ORDER-2026-07-PRJ-7-0007-FINAL"


def test_padding_and_reset_policy_monthly() -> None:
    service = _service()
    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
        actor="tester",
        syntax_template="{PREFIX}-{YEAR}-{MONTH}-{SEQUENCE}",
        prefix="RFQ",
        suffix="",
        starting_sequence=10,
        sequence_padding=3,
        separator="-",
        reset_policy="month",
        include_year_token=True,
        include_month_token=True,
        include_project_code_token=False,
    )

    payload = service.export_numbering_policies(
        tenant_id="tenant-a",
        organization_id="org-1",
    )
    numbering_service = CommercialNumberingService(serialized_policies=payload)

    first = numbering_service.allocate_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
        context={"as_of": "2026-01-10T00:00:00+00:00"},
    )
    second = numbering_service.allocate_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
        context={"as_of": "2026-01-11T00:00:00+00:00"},
    )
    march_preview = numbering_service.preview_next_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
        context={"as_of": "2026-03-01T00:00:00+00:00"},
    )

    assert first.endswith("-010")
    assert second.endswith("-011")
    assert march_preview.preview_number.endswith("-010")


def test_preview_does_not_consume_sequence() -> None:
    service = _service()

    first = service.preview_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
    )
    second = service.preview_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
    )

    assert first == second


def test_existing_allocated_numbers_remain_after_policy_edit() -> None:
    service = _service()

    initial_payload = service.export_numbering_policies(
        tenant_id="tenant-a",
        organization_id="org-1",
    )
    numbering_service = CommercialNumberingService(serialized_policies=initial_payload)
    allocated = numbering_service.allocate_number(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        context={"as_of": "2026-01-01T00:00:00+00:00"},
    )
    service.replace_numbering_policies(
        tenant_id="tenant-a",
        organization_id="org-1",
        policies_payload=numbering_service.to_payload(),
        actor="sync",
        reason="test",
    )

    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        actor="tester",
        syntax_template="{PREFIX}-{SEQUENCE}-{SUFFIX}",
        prefix="EST",
        suffix="X",
        starting_sequence=1,
        sequence_padding=5,
        separator="-",
        reset_policy="never",
        include_year_token=False,
        include_month_token=False,
        include_project_code_token=False,
    )

    updated = service.numbering_policy_for_document_type(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
    )
    assert allocated in updated.allocated_numbers


def test_tenant_isolation_for_settings() -> None:
    service = _service()
    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.PROPOSAL,
        actor="tester",
        syntax_template="{PREFIX}-{SEQUENCE}",
        prefix="A-PROP",
        suffix="",
        starting_sequence=1,
        sequence_padding=3,
        separator="-",
        reset_policy="never",
        include_year_token=False,
        include_month_token=False,
        include_project_code_token=False,
    )

    other_preview = service.preview_number(
        tenant_id="tenant-b",
        organization_id="org-1",
        document_type=CommercialDocumentType.PROPOSAL,
    )

    assert other_preview.startswith("ORG-1-PROPOSAL-")


def test_settings_serialization_round_trip() -> None:
    service = _service()
    service.update_personal_preferences(
        tenant_id="tenant-a",
        organization_id="org-1",
        user_id="user-1",
        actor="tester",
        updates={
            "density": "compact",
            "table_page_size": 50,
            "timezone": "America/Los_Angeles",
        },
    )

    payload = service.to_dict()
    restored = SettingsService(state=payload)
    prefs = restored.personal_preferences(
        tenant_id="tenant-a",
        organization_id="org-1",
        user_id="user-1",
    )

    assert prefs.density == "compact"
    assert prefs.table_page_size == 50
    assert prefs.timezone == "America/Los_Angeles"


def test_personal_preferences_defaults_and_overrides() -> None:
    service = _service()
    defaults = service.personal_preferences(
        tenant_id="tenant-a",
        organization_id="org-1",
        user_id="user-1",
    )
    assert defaults.default_landing_workspace == "Atlas"
    assert defaults.density == "comfortable"

    updated = service.update_personal_preferences(
        tenant_id="tenant-a",
        organization_id="org-1",
        user_id="user-1",
        actor="tester",
        updates={
            "default_landing_workspace": "Transactions",
            "density": "compact",
            "date_display_format": "MM/DD/YYYY",
            "reduced_motion": True,
        },
    )

    assert updated.default_landing_workspace == "Transactions"
    assert updated.density == "compact"
    assert updated.date_display_format == "MM/DD/YYYY"
    assert updated.reduced_motion is True


def test_duplicate_policy_validation_requires_type_token_for_shared_template() -> None:
    service = _service()
    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        actor="tester",
        syntax_template="{PREFIX}-{SEQUENCE}",
        prefix="SHARED",
        suffix="",
        starting_sequence=1,
        sequence_padding=4,
        separator="-",
        reset_policy="never",
        include_year_token=False,
        include_month_token=False,
        include_project_code_token=False,
    )

    with pytest.raises(ValueError, match="duplicate numbering policy signature"):
        service.update_numbering_policy(
            tenant_id="tenant-a",
            organization_id="org-1",
            document_type=CommercialDocumentType.PROPOSAL,
            actor="tester",
            syntax_template="{PREFIX}-{SEQUENCE}",
            prefix="SHARED",
            suffix="",
            starting_sequence=1,
            sequence_padding=4,
            separator="-",
            reset_policy="never",
            include_year_token=False,
            include_month_token=False,
            include_project_code_token=False,
        )
