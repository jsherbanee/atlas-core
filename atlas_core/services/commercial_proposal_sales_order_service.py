"""Commercial proposal and sales-order workflow service for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.contracts.commercial_spine_contracts import (
    Estimate,
    Proposal,
    ProposalStatus,
    ProjectJobLink,
    SalesOrder,
    SalesOrderLineItem,
    SalesOrderStatus,
)
from atlas_core.services.commercial_customer_opportunity_estimate_service import (
    CommercialCustomerOpportunityEstimateService,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


_UNSET = object()


class CommercialProposalSalesOrderWorkflowService(
    CommercialCustomerOpportunityEstimateService
):
    """Tenant-scoped proposal workflow and estimate-to-sales-order conversion."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        super().__init__(repositories)

    def create_proposal_for_estimate(
        self,
        estimate_id: str,
        *,
        organization_id: str | None = None,
        proposal_id: str | None = None,
        notes: list[str] | None = None,
    ) -> Proposal:
        estimate = self._require_estimate(estimate_id, organization_id=organization_id)
        if estimate.proposal_id is not None:
            existing = self.get_proposal(
                estimate.proposal_id,
                organization_id=estimate.organization_id,
            )
            if existing is not None:
                raise ValueError("estimate already has a proposal")
        proposal_id = proposal_id or f"prop-{estimate.estimate_id}"
        if (
            self.get_proposal(proposal_id, organization_id=estimate.organization_id)
            is not None
        ):
            raise ValueError("proposal already exists")
        self._require_customer_account(
            estimate.customer_id,
            organization_id=estimate.organization_id,
        )
        if estimate.opportunity_id is not None:
            self._require_opportunity(
                estimate.opportunity_id,
                customer_id=estimate.customer_id,
                organization_id=estimate.organization_id,
            )
        proposal = Proposal(
            tenant_id=self.tenant_id,
            organization_id=estimate.organization_id,
            proposal_id=proposal_id,
            estimate_id=estimate.estimate_id,
            customer_id=estimate.customer_id,
            notes=list(notes or []),
        )
        self.commercial_repository.save_proposal(proposal)
        estimate_payload = estimate.to_dict()
        estimate_payload["proposal_id"] = proposal.proposal_id
        self.commercial_repository.save_estimate(Estimate(**estimate_payload))
        return proposal

    def update_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
        notes: Any = _UNSET,
    ) -> Proposal:
        proposal = self.get_proposal(proposal_id, organization_id=organization_id)
        if proposal is None:
            raise ValueError("proposal was not found")
        payload = proposal.to_dict()
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = Proposal(**payload)
        self.commercial_repository.save_proposal(updated)
        return updated

    def mark_proposal_ready(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.mark_ready()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def mark_proposal_proposed(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        return self.mark_proposal_ready(proposal_id, organization_id=organization_id)

    def send_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.send()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def accept_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.accept()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def reject_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.decline()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def mark_proposal_rejected(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        return self.reject_proposal(proposal_id, organization_id=organization_id)

    def expire_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.expire()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def cancel_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal:
        proposal = self._require_proposal(proposal_id, organization_id=organization_id)
        proposal.cancel()
        self.commercial_repository.save_proposal(proposal)
        return proposal

    def get_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None = None,
    ) -> Proposal | None:
        proposal = self.commercial_repository.load_proposal(proposal_id)
        if proposal is None:
            return None
        if proposal.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and proposal.organization_id != organization_id:
            return None
        return proposal

    def list_proposals(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[Proposal]:
        proposals = self.commercial_repository.list_proposals()
        return self._filter_organization(proposals, organization_id)

    def create_sales_order(
        self,
        *,
        organization_id: str,
        sales_order_id: str,
        customer_id: str,
        estimate_id: str | None = None,
        proposal_id: str | None = None,
        project_job_link: ProjectJobLink | dict[str, Any] | None = None,
        line_items: list[SalesOrderLineItem | dict[str, Any]] | None = None,
        notes: list[str] | None = None,
        status: SalesOrderStatus = SalesOrderStatus.DRAFT,
    ) -> SalesOrder:
        customer = self._require_customer_account(
            customer_id,
            organization_id=organization_id,
        )
        estimate = None
        if estimate_id is not None:
            estimate = self._require_estimate(
                estimate_id,
                organization_id=organization_id,
            )
            if estimate.customer_id != customer.customer_id:
                raise ValueError("estimate does not belong to the selected customer")
            if estimate.opportunity_id is not None:
                self._require_opportunity(
                    estimate.opportunity_id,
                    customer_id=estimate.customer_id,
                    organization_id=estimate.organization_id,
                )
        if proposal_id is not None:
            proposal = self._require_proposal(
                proposal_id,
                organization_id=organization_id,
            )
            if proposal.customer_id != customer.customer_id:
                raise ValueError("proposal does not belong to the selected customer")
            if estimate is not None and proposal.estimate_id != estimate.estimate_id:
                raise ValueError("proposal does not belong to the selected estimate")
        if (
            self.get_sales_order(sales_order_id, organization_id=organization_id)
            is not None
        ):
            raise ValueError("sales order already exists")
        record = SalesOrder(
            tenant_id=self.tenant_id,
            organization_id=customer.organization_id,
            sales_order_id=sales_order_id,
            customer_id=customer.customer_id,
            estimate_id=estimate.estimate_id if estimate is not None else None,
            proposal_id=proposal_id,
            project_job_link=self._normalize_project_job_link(project_job_link),
            status=status,
            line_items=[
                self._normalize_sales_order_line_item(item)
                for item in list(line_items or [])
            ],
            notes=list(notes or []),
        )
        self.commercial_repository.save_sales_order(record)
        return record

    def update_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
        notes: Any = _UNSET,
        project_job_link: Any = _UNSET,
    ) -> SalesOrder:
        sales_order = self.get_sales_order(
            sales_order_id, organization_id=organization_id
        )
        if sales_order is None:
            raise ValueError("sales order was not found")
        payload = sales_order.to_dict()
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        if project_job_link is not _UNSET:
            payload["project_job_link"] = self._normalize_project_job_link(
                project_job_link
            )
        updated = SalesOrder(**payload)
        self.commercial_repository.save_sales_order(updated)
        return updated

    def open_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder:
        return self._transition_sales_order(
            sales_order_id,
            organization_id=organization_id,
            transition="open",
        )

    def mark_sales_order_partially_fulfilled(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder:
        return self._transition_sales_order(
            sales_order_id,
            organization_id=organization_id,
            transition="partially_fulfilled",
        )

    def fulfill_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder:
        return self._transition_sales_order(
            sales_order_id,
            organization_id=organization_id,
            transition="fulfill",
        )

    def close_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder:
        return self._transition_sales_order(
            sales_order_id,
            organization_id=organization_id,
            transition="close",
        )

    def cancel_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder:
        return self._transition_sales_order(
            sales_order_id,
            organization_id=organization_id,
            transition="cancel",
        )

    def get_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> SalesOrder | None:
        sales_order = self.commercial_repository.load_sales_order(sales_order_id)
        if sales_order is None:
            return None
        if sales_order.tenant_id != self.tenant_id:
            return None
        if (
            organization_id is not None
            and sales_order.organization_id != organization_id
        ):
            return None
        return sales_order

    def list_sales_orders(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[SalesOrder]:
        sales_orders = self.commercial_repository.list_sales_orders()
        return self._filter_organization(sales_orders, organization_id)

    def convert_accepted_estimate_to_sales_order(
        self,
        estimate_id: str,
        *,
        organization_id: str | None = None,
        sales_order_id: str | None = None,
    ) -> SalesOrder:
        estimate = self._require_estimate(estimate_id, organization_id=organization_id)
        if estimate.proposal_id is None:
            raise ValueError("estimate must be linked to a proposal before conversion")
        proposal = self._require_proposal(
            estimate.proposal_id,
            organization_id=organization_id or estimate.organization_id,
        )
        if proposal.estimate_id != estimate.estimate_id:
            raise ValueError("proposal does not belong to the selected estimate")
        if proposal.status != ProposalStatus.ACCEPTED:
            raise ValueError("proposal must be accepted before conversion")
        if self._sales_order_for_estimate(estimate.estimate_id) is not None:
            raise ValueError("estimate has already been converted to a sales order")
        sales_order_id = sales_order_id or f"so-{estimate.estimate_id}"
        if (
            self.get_sales_order(
                sales_order_id, organization_id=estimate.organization_id
            )
            is not None
        ):
            raise ValueError("sales order already exists")
        copied_line_items = [
            SalesOrderLineItem(
                line_item_id=item.line_item_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                catalog_item_id=item.catalog_item_id,
                notes=list(item.notes),
                estimate_line_item_id=item.line_item_id,
            )
            for item in estimate.line_items
        ]
        sales_order = SalesOrder(
            tenant_id=self.tenant_id,
            organization_id=estimate.organization_id,
            sales_order_id=sales_order_id,
            customer_id=estimate.customer_id,
            estimate_id=estimate.estimate_id,
            proposal_id=proposal.proposal_id,
            project_job_link=estimate.project_job_link,
            status=SalesOrderStatus.DRAFT,
            line_items=copied_line_items,
            notes=list(estimate.notes),
        )
        self.commercial_repository.save_sales_order(sales_order)
        return sales_order

    def _require_estimate(
        self,
        estimate_id: str,
        *,
        organization_id: str | None,
    ) -> Estimate:
        estimate = self.get_estimate(estimate_id, organization_id=organization_id)
        if estimate is None:
            raise ValueError("estimate was not found")
        return estimate

    def _require_proposal(
        self,
        proposal_id: str,
        *,
        organization_id: str | None,
    ) -> Proposal:
        proposal = self.get_proposal(proposal_id, organization_id=organization_id)
        if proposal is None:
            raise ValueError("proposal was not found")
        return proposal

    def _sales_order_for_estimate(self, estimate_id: str) -> SalesOrder | None:
        for sales_order in self.commercial_repository.list_sales_orders():
            if sales_order.tenant_id != self.tenant_id:
                continue
            if sales_order.estimate_id == estimate_id:
                return sales_order
        return None

    def _transition_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None,
        transition: str,
    ) -> SalesOrder:
        sales_order = self.get_sales_order(
            sales_order_id, organization_id=organization_id
        )
        if sales_order is None:
            raise ValueError("sales order was not found")
        if transition == "open":
            sales_order.open()
        elif transition == "partially_fulfilled":
            sales_order.mark_partially_fulfilled()
        elif transition == "fulfill":
            sales_order.fulfill()
        elif transition == "close":
            sales_order.close()
        elif transition == "cancel":
            sales_order.cancel()
        else:
            raise ValueError("unknown sales order transition")
        self.commercial_repository.save_sales_order(sales_order)
        return sales_order

    @staticmethod
    def _normalize_sales_order_line_item(
        value: SalesOrderLineItem | dict[str, Any],
    ) -> SalesOrderLineItem:
        if isinstance(value, SalesOrderLineItem):
            return value
        return SalesOrderLineItem(**value)

    @staticmethod
    def _normalize_project_job_link(
        value: ProjectJobLink | dict[str, Any] | None,
    ) -> ProjectJobLink | None:
        if value is None:
            return None
        if isinstance(value, ProjectJobLink):
            return value
        return ProjectJobLink(**value)


__all__ = ["CommercialProposalSalesOrderWorkflowService"]
