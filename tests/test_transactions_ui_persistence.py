import json
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path

from atlas_core.services.project_workspace_service import ProjectWorkspaceService
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)
from atlas_core.domain.commercial_document import CommercialDocumentType, ApprovalState


def _utc_now():
    return datetime.now(UTC).isoformat()


def _create_project(root: Path, project_id: str):
    project_dir = root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    # write minimal required repository files similar to other tests
    (project_dir / "project.json").write_text(
        json.dumps({"project_id": project_id, "name": project_id, "client": "ACME"}),
        encoding="utf-8",
    )
    (project_dir / "metadata.json").write_text(
        json.dumps(
            {"project_name": project_id, "created_at": _utc_now(), "owner": "ACME"}
        ),
        encoding="utf-8",
    )
    (project_dir / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_id": project_id,
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "project_manifest.json").write_text(json.dumps({}), encoding="utf-8")
    psvc = ProjectWorkspaceService(root)
    return psvc, project_id


def test_estimate_create_and_persist(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "ui-proj-a")

    svc = TransactionsWorkspaceService(
        serialized_terms_blocks=[],
        active_tenant_id="local",
        active_organization_id="atlas",
    )

    _ = svc.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=project_id,
        project_code="UIA",
        customer_id="cust-x",
    )

    # persist
    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test-ui"
    )

    # ensure persisted file present
    project_dir = Path(psvc.manager.project_repository.project_location(project_id))
    tx_dir = project_dir / "review" / "transactions"
    assert tx_dir.exists()
    files = list(tx_dir.glob("*.json"))
    assert any(files)


def test_line_mutation_and_reload(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "ui-proj-b")
    svc = TransactionsWorkspaceService(
        serialized_terms_blocks=[],
        active_tenant_id="local",
        active_organization_id="atlas",
    )

    est = svc.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=project_id,
        project_code="UIB",
        customer_id="cust-y",
    )

    svc._commercial_service.add_line(
        est,
        description="Widget",
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
    )

    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test-ui"
    )

    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    reloaded = next(d for d in docs if d.get("document_id") == est.document_id)
    assert any(
        (li.get("description") or "") == "Widget"
        for li in list(reloaded.get("lines") or [])
    )


def test_approval_persistence(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "ui-proj-c")
    svc = TransactionsWorkspaceService(
        serialized_terms_blocks=[],
        active_tenant_id="local",
        active_organization_id="atlas",
    )

    est = svc.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=project_id,
        project_code="UIC",
        customer_id="cust-z",
    )
    svc.set_approval_state(
        document_id=est.document_id, approval_state=ApprovalState.APPROVED
    )
    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test-ui"
    )

    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    reloaded = next(d for d in docs if d.get("document_id") == est.document_id)
    assert reloaded.get("approval_state") == ApprovalState.APPROVED.value


def test_sales_order_creation_and_lineage(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "ui-proj-d")
    svc = TransactionsWorkspaceService(
        serialized_terms_blocks=[],
        active_tenant_id="local",
        active_organization_id="atlas",
    )

    est = svc.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=project_id,
        project_code="UID",
        customer_id="cust-s",
    )
    svc._commercial_service.add_line(
        est, description="X", quantity=Decimal("1"), unit_price=Decimal("5")
    )
    svc.set_approval_state(
        document_id=est.document_id, approval_state=ApprovalState.APPROVED
    )
    so = svc.create_sales_order_from_estimate(
        estimate_document_id=est.document_id, inherit_terms_from_estimate=True
    )
    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test-ui"
    )

    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    reloaded_so = next(d for d in docs if d.get("document_id") == so.document_id)
    # lineage
    assert any(
        (li.get("source_document_id") == est.document_id)
        for li in list(reloaded_so.get("lines") or [])
    )
    assert any(
        (
            r.get("relationship_type") == "derived_from_estimate"
            and r.get("related_document_id") == est.document_id
        )
        for r in list(reloaded_so.get("relationships") or [])
    )


def test_terms_and_audit_events_and_passive_noop(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "ui-proj-e")
    svc = TransactionsWorkspaceService(
        serialized_terms_blocks=[
            {
                "block_id": "t1",
                "document_family": "estimate",
                "version": 1,
                "content": "terms",
                "status": "active",
                "archived": False,
                "is_default": True,
                "title": "Default Estimate Terms",
            }
        ],
        active_tenant_id="local",
        active_organization_id="atlas",
    )

    est = svc.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=project_id,
        project_code="UIE",
        customer_id="cust-t",
    )
    # assign resolved terms
    svc.refresh_draft_terms(document_id=est.document_id)
    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test-ui"
    )

    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    reloaded = next(d for d in docs if d.get("document_id") == est.document_id)
    assert reloaded.get("terms_and_conditions_reference") is not None
    assert reloaded.get("terms_and_conditions_snapshot") is not None

    # audit events: estimate_created and transaction.persisted should exist once
    events = psvc.list_audit_history(project_id)
    actions = [e.get("action") for e in events]
    assert actions.count("estimate_created") == 1
    assert actions.count("transaction.persisted") >= 1

    # passive in-memory save (no persist) should not create a new audit event
    before = len(events)
    # simulate passive session save: no persist_documents_to_project call
    _ = svc.to_payload()
    after_events = psvc.list_audit_history(project_id)
    assert len(after_events) == before
