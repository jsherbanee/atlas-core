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


def _create_project(root: Path, project_id: str) -> tuple[ProjectWorkspaceService, str]:
    project_dir = root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    # write minimal required repository files
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


def test_serialization_round_trip_and_persistence(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "proj-x")

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
        project_code="PX",
        customer_id="cust-x",
    )

    svc._commercial_service.add_line(
        est,
        description="Item A",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        unit_cost=Decimal("50"),
    )

    svc.set_approval_state(
        document_id=est.document_id, approval_state=ApprovalState.APPROVED
    )

    so = svc.create_sales_order_from_estimate(
        estimate_document_id=est.document_id, inherit_terms_from_estimate=True
    )

    # persist to project
    svc.persist_documents_to_project(
        project_id=project_id, project_workspace_service=psvc, actor="test"
    )

    # ensure files written
    project_dir = Path(psvc.manager.project_repository.project_location(project_id))
    tx_dir = project_dir / "review" / "transactions"
    assert tx_dir.exists()
    files = list(tx_dir.glob("*.json"))
    assert any(".json" for f in files)

    # reload from project via loader
    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    assert isinstance(docs, list)
    ids = {d.get("document_id") for d in docs}
    assert est.document_id in ids
    assert so.document_id in ids

    # check approval durability for estimate
    reloaded_est = next(d for d in docs if d.get("document_id") == est.document_id)
    assert reloaded_est.get("approval_state") == ApprovalState.APPROVED.value

    # check lineage: sales order should reference source estimate
    reloaded_so = next(d for d in docs if d.get("document_id") == so.document_id)
    lines = list(reloaded_so.get("lines") or [])
    assert any(li.get("source_document_id") == est.document_id for li in lines)

    # check audit events written once (use manager audit listing)
    events = psvc.list_audit_history(project_id)
    assert any(e.get("action") == "transaction.persisted" for e in events)


def test_project_with_no_transactions_is_compatible(tmp_path):
    workspace_root = tmp_path / "AtlasProjects"
    psvc, project_id = _create_project(workspace_root, "proj-empty")
    # loading transactions from an empty project should return empty list
    docs = TransactionsWorkspaceService.load_serialized_documents_from_project(
        project_id, psvc
    )
    assert docs == []
    # End of test function
