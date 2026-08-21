from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_core.contracts import EstimateLineItem, ProposalStatus, SalesOrderStatus
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_proposal_sales_order_service import (
    CommercialProposalSalesOrderWorkflowService,
)


def _service(tenant_id: str, root: str) -> CommercialProposalSalesOrderWorkflowService:
    return CommercialProposalSalesOrderWorkflowService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def _seed_commercial_workflow(
    service: CommercialProposalSalesOrderWorkflowService,
) -> None:
    service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
    )
    service.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Conference room refresh",
        estimated_value=Decimal("12500.00"),
    )
    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
        opportunity_id="opp-1",
        notes=["Scope reviewed with the customer"],
        line_items=[
            EstimateLineItem(
                line_item_id="est-line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
            )
        ],
    )


def test_proposal_lifecycle_and_conversion_to_sales_order(tmp_path) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))
    _seed_commercial_workflow(service)

    proposal = service.create_proposal_for_estimate("est-1")
    ready_proposal = service.mark_proposal_ready(proposal.proposal_id)
    sent_proposal = service.send_proposal(proposal.proposal_id)
    accepted_proposal = service.accept_proposal(proposal.proposal_id)

    assert proposal.status == ProposalStatus.DRAFT
    assert ready_proposal.status == ProposalStatus.READY
    assert sent_proposal.status == ProposalStatus.SENT
    assert accepted_proposal.status == ProposalStatus.ACCEPTED
    loaded_estimate = service.get_estimate("est-1")
    assert loaded_estimate is not None
    assert loaded_estimate.proposal_id == proposal.proposal_id

    sales_order = service.convert_accepted_estimate_to_sales_order("est-1")
    loaded_sales_order = service.get_sales_order(sales_order.sales_order_id)

    assert sales_order.status == SalesOrderStatus.DRAFT
    assert sales_order.estimate_id == "est-1"
    assert sales_order.proposal_id == proposal.proposal_id
    assert sales_order.line_items[0].estimate_line_item_id == "est-line-1"
    assert sales_order.line_items[0].quantity == Decimal("2")
    assert sales_order.line_items[0].unit_price == Decimal("4500.00")
    assert sales_order.notes == ["Scope reviewed with the customer"]
    assert loaded_sales_order is not None
    assert loaded_sales_order.sales_order_id == sales_order.sales_order_id

    opened_sales_order = service.open_sales_order(sales_order.sales_order_id)
    partially_fulfilled_sales_order = service.mark_sales_order_partially_fulfilled(
        sales_order.sales_order_id
    )
    fulfilled_sales_order = service.fulfill_sales_order(sales_order.sales_order_id)
    closed_sales_order = service.close_sales_order(sales_order.sales_order_id)

    assert opened_sales_order.status == SalesOrderStatus.OPEN
    assert (
        partially_fulfilled_sales_order.status == SalesOrderStatus.PARTIALLY_FULFILLED
    )
    assert fulfilled_sales_order.status == SalesOrderStatus.FULFILLED
    assert closed_sales_order.status == SalesOrderStatus.CLOSED


def test_proposal_to_sales_order_conversion_rejects_duplicates_and_invalid_states(
    tmp_path,
) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))
    _seed_commercial_workflow(service)

    proposal = service.create_proposal_for_estimate("est-1")

    with pytest.raises(ValueError, match="proposal must be accepted before conversion"):
        service.convert_accepted_estimate_to_sales_order("est-1")

    service.send_proposal(proposal.proposal_id)
    service.accept_proposal(proposal.proposal_id)
    service.convert_accepted_estimate_to_sales_order("est-1")

    with pytest.raises(ValueError, match="estimate has already been converted"):
        service.convert_accepted_estimate_to_sales_order("est-1")

    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-2",
        customer_id="customer-1",
        opportunity_id="opp-1",
    )
    with pytest.raises(ValueError, match="estimate must be linked to a proposal"):
        service.convert_accepted_estimate_to_sales_order("est-2")


def test_proposal_and_sales_order_tenant_isolation(tmp_path) -> None:
    service_a = _service("tenant-a", str(tmp_path / "Atlas"))
    service_b = _service("tenant-b", str(tmp_path / "Atlas"))
    _seed_commercial_workflow(service_a)
    _seed_commercial_workflow(service_b)

    proposal_a = service_a.create_proposal_for_estimate("est-1")
    proposal_b = service_b.create_proposal_for_estimate(
        "est-1",
        proposal_id="prop-b-1",
    )

    assert service_a.get_proposal(proposal_a.proposal_id) is not None
    assert service_a.get_proposal(proposal_b.proposal_id) is None
    assert service_b.get_proposal(proposal_a.proposal_id) is None

    service_a.send_proposal(proposal_a.proposal_id)
    service_a.accept_proposal(proposal_a.proposal_id)
    sales_order_a = service_a.convert_accepted_estimate_to_sales_order(
        "est-1",
        sales_order_id="so-a-1",
    )

    assert service_a.get_sales_order(sales_order_a.sales_order_id) is not None
    assert service_b.get_sales_order(sales_order_a.sales_order_id) is None
    assert [proposal.proposal_id for proposal in service_a.list_proposals()] == [
        proposal_a.proposal_id,
    ]
    assert [
        sales_order.sales_order_id for sales_order in service_a.list_sales_orders()
    ] == [
        sales_order_a.sales_order_id,
    ]
