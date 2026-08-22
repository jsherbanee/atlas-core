from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_core.contracts import EstimateLineItem, OpportunityStatus
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_customer_opportunity_estimate_service import (
    CommercialCustomerOpportunityEstimateService,
)


def _service(tenant_id: str, root: str) -> CommercialCustomerOpportunityEstimateService:
    return CommercialCustomerOpportunityEstimateService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def test_service_can_create_update_list_and_load_customer_opportunity_estimate(
    tmp_path,
) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))

    customer = service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
        billing_email="ops@acme.example",
    )
    updated_customer = service.update_customer_account(
        "customer-1",
        name="Acme Systems",
        billing_email="billing@acme.example",
    )

    opportunity = service.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Conference room refresh",
        estimated_value=Decimal("12500.00"),
    )
    won_opportunity = service.set_opportunity_status(
        "opp-1",
        status=OpportunityStatus.WON,
    )

    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
        opportunity_id="opp-1",
        line_items=[
            EstimateLineItem(
                line_item_id="line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
            )
        ],
    )
    service.add_estimate_line_item(
        "est-1",
        EstimateLineItem(
            line_item_id="line-2",
            description="Mounting hardware",
            quantity=Decimal("4"),
            unit_price=Decimal("125.00"),
            catalog_item_id="cat-2",
        ),
    )
    service.update_estimate_line_item(
        "est-1",
        "line-2",
        quantity=Decimal("5"),
    )
    service.update_estimate(
        "est-1",
        notes=["Reviewed with customer"],
    )

    loaded_customer = service.get_customer_account("customer-1")
    loaded_opportunity = service.get_opportunity("opp-1")
    loaded_estimate = service.get_estimate("est-1")

    assert customer.tenant_id == "tenant-a"
    assert updated_customer.name == "Acme Systems"
    assert loaded_customer is not None
    assert loaded_customer.billing_email == "billing@acme.example"
    assert opportunity.customer_id == "customer-1"
    assert won_opportunity.status == OpportunityStatus.WON
    assert service.list_customer_accounts()[0].customer_id == "customer-1"
    assert service.list_opportunities()[0].opportunity_id == "opp-1"
    assert service.list_estimates()[0].estimate_id == "est-1"
    assert loaded_opportunity is not None
    assert loaded_opportunity.status == OpportunityStatus.WON
    assert loaded_estimate is not None
    assert loaded_estimate.customer_id == "customer-1"
    assert loaded_estimate.opportunity_id == "opp-1"
    assert len(loaded_estimate.line_items) == 2
    assert loaded_estimate.line_items[1].quantity == Decimal("5")
    assert loaded_estimate.notes == ["Reviewed with customer"]
    assert service.calculate_estimate_total("est-1") == Decimal("9625.00")


def test_service_rejects_invalid_references_and_relinking_mismatches(tmp_path) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))

    service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
    )
    service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-2",
        name="Beta Integrators",
    )
    service.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Refresh",
    )
    service.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-2",
        customer_id="customer-2",
        name="Expansion",
    )

    with pytest.raises(ValueError, match="customer account was not found"):
        service.create_opportunity(
            organization_id="org-1",
            opportunity_id="opp-missing",
            customer_id="customer-missing",
            name="Broken",
        )

    with pytest.raises(ValueError, match="opportunity does not belong"):
        service.create_estimate(
            organization_id="org-1",
            estimate_id="est-1",
            customer_id="customer-1",
            opportunity_id="opp-2",
        )

    estimate = service.create_estimate(
        organization_id="org-1",
        estimate_id="est-2",
        customer_id="customer-1",
        opportunity_id="opp-1",
    )
    assert estimate.opportunity_id == "opp-1"

    with pytest.raises(ValueError, match="opportunity does not belong"):
        service.update_estimate("est-2", customer_id="customer-2")

    with pytest.raises(ValueError, match="estimate line item was not found"):
        service.update_estimate_line_item("est-2", "missing-line")

    with pytest.raises(ValueError, match="estimate line item was not found"):
        service.remove_estimate_line_item("est-2", "missing-line")


def test_tenant_isolation_is_preserved_by_tenant_scoped_repositories(tmp_path) -> None:
    service_a = _service("tenant-a", str(tmp_path / "Atlas"))
    service_b = _service("tenant-b", str(tmp_path / "Atlas"))

    service_a.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Tenant A Customer",
    )
    service_b.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Tenant B Customer",
    )

    service_a.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Tenant A Opportunity",
    )
    service_b.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Tenant B Opportunity",
    )

    customer_a = service_a.get_customer_account("customer-1")
    customer_b = service_b.get_customer_account("customer-1")
    opportunity_a = service_a.get_opportunity("opp-1")
    opportunity_b = service_b.get_opportunity("opp-1")

    assert customer_a is not None and customer_a.name == "Tenant A Customer"
    assert customer_b is not None and customer_b.name == "Tenant B Customer"
    assert opportunity_a is not None and opportunity_a.name == "Tenant A Opportunity"
    assert opportunity_b is not None and opportunity_b.name == "Tenant B Opportunity"
    assert [customer.name for customer in service_a.list_customer_accounts()] == [
        "Tenant A Customer"
    ]
    assert [customer.name for customer in service_b.list_customer_accounts()] == [
        "Tenant B Customer"
    ]
    assert [opportunity.name for opportunity in service_a.list_opportunities()] == [
        "Tenant A Opportunity"
    ]
    assert [opportunity.name for opportunity in service_b.list_opportunities()] == [
        "Tenant B Opportunity"
    ]
