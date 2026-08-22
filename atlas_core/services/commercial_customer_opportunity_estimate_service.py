"""Commercial customer, opportunity, and estimate service for Atlas Core."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from atlas_core.contracts.commercial_spine_contracts import (
    CustomerAccount,
    Estimate,
    EstimateLineItem,
    Opportunity,
    OpportunityStatus,
    ProjectJobLink,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle

_UNSET = object()


class CommercialCustomerOpportunityEstimateService:
    """Tenant-scoped CRUD and linkage service for the front half of commercial flow."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        if repositories.tenant_id is None or repositories.tenant_root is None:
            raise ValueError("tenant-scoped repository bundle is required")
        if repositories.commercial_repository is None:
            raise ValueError("commercial_repository is required")
        self.repositories = repositories
        self.tenant_id = repositories.tenant_id
        self.tenant_root = repositories.tenant_root
        self.commercial_repository = repositories.commercial_repository

    def create_customer_account(
        self,
        *,
        organization_id: str,
        customer_id: str,
        name: str,
        account_number: str | None = None,
        legal_name: str | None = None,
        billing_email: str | None = None,
        active: bool = True,
        notes: list[str] | None = None,
    ) -> CustomerAccount:
        record = CustomerAccount(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            customer_id=customer_id,
            name=name,
            account_number=account_number,
            legal_name=legal_name,
            billing_email=billing_email,
            active=active,
            notes=list(notes or []),
        )
        self.commercial_repository.save_customer_account(record)
        return record

    def update_customer_account(
        self,
        customer_id: str,
        *,
        organization_id: str | None = None,
        name: Any = _UNSET,
        account_number: Any = _UNSET,
        legal_name: Any = _UNSET,
        billing_email: Any = _UNSET,
        active: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> CustomerAccount:
        record = self.get_customer_account(customer_id, organization_id=organization_id)
        if record is None:
            raise ValueError("customer account was not found")
        payload = record.to_dict()
        if name is not _UNSET:
            payload["name"] = name
        if account_number is not _UNSET:
            payload["account_number"] = account_number
        if legal_name is not _UNSET:
            payload["legal_name"] = legal_name
        if billing_email is not _UNSET:
            payload["billing_email"] = billing_email
        if active is not _UNSET:
            payload["active"] = active
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = CustomerAccount(**payload)
        self.commercial_repository.save_customer_account(updated)
        return updated

    def get_customer_account(
        self,
        customer_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerAccount | None:
        record = self.commercial_repository.load_customer_account(customer_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_customer_accounts(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[CustomerAccount]:
        records = self.commercial_repository.list_customer_accounts()
        return self._filter_organization(records, organization_id)

    def create_opportunity(
        self,
        *,
        organization_id: str,
        opportunity_id: str,
        customer_id: str,
        name: str,
        estimated_value: Decimal | None = None,
        close_date: str | None = None,
        notes: list[str] | None = None,
    ) -> Opportunity:
        customer = self._require_customer_account(
            customer_id,
            organization_id=organization_id,
        )
        record = Opportunity(
            tenant_id=self.tenant_id,
            organization_id=customer.organization_id,
            opportunity_id=opportunity_id,
            customer_id=customer.customer_id,
            name=name,
            estimated_value=estimated_value,
            close_date=close_date,
            notes=list(notes or []),
        )
        self.commercial_repository.save_opportunity(record)
        return record

    def update_opportunity(
        self,
        opportunity_id: str,
        *,
        organization_id: str | None = None,
        customer_id: str | None = None,
        name: Any = _UNSET,
        status: Any = _UNSET,
        estimated_value: Any = _UNSET,
        close_date: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> Opportunity:
        record = self.get_opportunity(opportunity_id, organization_id=organization_id)
        if record is None:
            raise ValueError("opportunity was not found")
        payload = record.to_dict()
        if customer_id is not None:
            customer = self._require_customer_account(
                customer_id,
                organization_id=organization_id or record.organization_id,
            )
            payload["customer_id"] = customer.customer_id
            payload["organization_id"] = customer.organization_id
        if name is not _UNSET:
            payload["name"] = name
        if status is not _UNSET:
            payload["status"] = (
                status.value if isinstance(status, OpportunityStatus) else status
            )
        if estimated_value is not _UNSET:
            payload["estimated_value"] = estimated_value
        if close_date is not _UNSET:
            payload["close_date"] = close_date
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = Opportunity(**payload)
        self.commercial_repository.save_opportunity(updated)
        return updated

    def set_opportunity_status(
        self,
        opportunity_id: str,
        *,
        organization_id: str | None = None,
        status: OpportunityStatus,
    ) -> Opportunity:
        record = self.get_opportunity(opportunity_id, organization_id=organization_id)
        if record is None:
            raise ValueError("opportunity was not found")
        if status == OpportunityStatus.WON:
            record.mark_won()
        elif status == OpportunityStatus.LOST:
            record.mark_lost()
        elif status == OpportunityStatus.ON_HOLD:
            record.mark_on_hold()
        elif status == OpportunityStatus.QUALIFIED:
            record.status = OpportunityStatus.QUALIFIED
        else:
            record.status = OpportunityStatus.OPEN
        self.commercial_repository.save_opportunity(record)
        return record

    def get_opportunity(
        self,
        opportunity_id: str,
        *,
        organization_id: str | None = None,
    ) -> Opportunity | None:
        record = self.commercial_repository.load_opportunity(opportunity_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_opportunities(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[Opportunity]:
        records = self.commercial_repository.list_opportunities()
        return self._filter_organization(records, organization_id)

    def create_estimate(
        self,
        *,
        organization_id: str,
        estimate_id: str,
        customer_id: str,
        opportunity_id: str | None = None,
        proposal_id: str | None = None,
        project_job_link: ProjectJobLink | dict[str, Any] | None = None,
        line_items: list[EstimateLineItem | dict[str, Any]] | None = None,
        notes: list[str] | None = None,
    ) -> Estimate:
        customer = self._require_customer_account(
            customer_id,
            organization_id=organization_id,
        )
        opportunity = self._require_opportunity(
            opportunity_id,
            customer_id=customer.customer_id,
            organization_id=organization_id,
        )
        normalized_project_job_link = self._normalize_project_job_link(project_job_link)
        normalized_line_items = [
            self._normalize_estimate_line_item(item) for item in list(line_items or [])
        ]
        record = Estimate(
            tenant_id=self.tenant_id,
            organization_id=customer.organization_id,
            estimate_id=estimate_id,
            customer_id=customer.customer_id,
            opportunity_id=opportunity.opportunity_id if opportunity else None,
            proposal_id=proposal_id,
            project_job_link=normalized_project_job_link,
            line_items=normalized_line_items,
            notes=list(notes or []),
        )
        self.commercial_repository.save_estimate(record)
        return record

    def update_estimate(
        self,
        estimate_id: str,
        *,
        organization_id: str | None = None,
        customer_id: str | None = None,
        opportunity_id: Any = _UNSET,
        proposal_id: Any = _UNSET,
        project_job_link: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> Estimate:
        record = self.get_estimate(estimate_id, organization_id=organization_id)
        if record is None:
            raise ValueError("estimate was not found")
        payload = record.to_dict()
        target_customer_id = customer_id or record.customer_id
        target_organization_id = organization_id or record.organization_id
        if customer_id is not None:
            customer = self._require_customer_account(
                customer_id,
                organization_id=target_organization_id,
            )
            payload["customer_id"] = customer.customer_id
            payload["organization_id"] = customer.organization_id
            target_customer_id = customer.customer_id
            target_organization_id = customer.organization_id
        if opportunity_id is not _UNSET:
            opportunity = self._require_opportunity(
                opportunity_id,
                customer_id=target_customer_id,
                organization_id=target_organization_id,
            )
            payload["opportunity_id"] = (
                opportunity.opportunity_id if opportunity is not None else None
            )
        elif customer_id is not None and payload.get("opportunity_id") is not None:
            self._require_opportunity(
                payload["opportunity_id"],
                customer_id=target_customer_id,
                organization_id=target_organization_id,
            )
        if proposal_id is not _UNSET:
            payload["proposal_id"] = proposal_id
        if project_job_link is not _UNSET:
            payload["project_job_link"] = self._normalize_project_job_link(
                project_job_link
            )
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = Estimate(**payload)
        self.commercial_repository.save_estimate(updated)
        return updated

    def add_estimate_line_item(
        self,
        estimate_id: str,
        line_item: EstimateLineItem | dict[str, Any],
        *,
        organization_id: str | None = None,
    ) -> Estimate:
        record = self.get_estimate(estimate_id, organization_id=organization_id)
        if record is None:
            raise ValueError("estimate was not found")
        payload = record.to_dict()
        line_items = [dict(item) for item in payload.get("line_items", [])]
        new_line_item = self._normalize_estimate_line_item(line_item)
        if any(
            item.get("line_item_id") == new_line_item.line_item_id
            for item in line_items
        ):
            raise ValueError("estimate line item already exists")
        line_items.append(new_line_item.to_dict())
        payload["line_items"] = line_items
        updated = Estimate(**payload)
        self.commercial_repository.save_estimate(updated)
        return updated

    def update_estimate_line_item(
        self,
        estimate_id: str,
        line_item_id: str,
        *,
        organization_id: str | None = None,
        description: Any = _UNSET,
        quantity: Any = _UNSET,
        unit_price: Any = _UNSET,
        catalog_item_id: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> Estimate:
        record = self.get_estimate(estimate_id, organization_id=organization_id)
        if record is None:
            raise ValueError("estimate was not found")
        payload = record.to_dict()
        line_items = []
        found = False
        for item_payload in payload.get("line_items", []):
            item = EstimateLineItem(**dict(item_payload))
            if item.line_item_id != line_item_id:
                line_items.append(item.to_dict())
                continue
            found = True
            item_payload_dict = item.to_dict()
            if description is not _UNSET:
                item_payload_dict["description"] = description
            if quantity is not _UNSET:
                item_payload_dict["quantity"] = quantity
            if unit_price is not _UNSET:
                item_payload_dict["unit_price"] = unit_price
            if catalog_item_id is not _UNSET:
                item_payload_dict["catalog_item_id"] = catalog_item_id
            if notes is not _UNSET:
                item_payload_dict["notes"] = list(notes or [])
            line_items.append(EstimateLineItem(**item_payload_dict).to_dict())
        if not found:
            raise ValueError("estimate line item was not found")
        payload["line_items"] = line_items
        updated = Estimate(**payload)
        self.commercial_repository.save_estimate(updated)
        return updated

    def remove_estimate_line_item(
        self,
        estimate_id: str,
        line_item_id: str,
        *,
        organization_id: str | None = None,
    ) -> Estimate:
        record = self.get_estimate(estimate_id, organization_id=organization_id)
        if record is None:
            raise ValueError("estimate was not found")
        payload = record.to_dict()
        line_items = [
            dict(item)
            for item in payload.get("line_items", [])
            if str(item.get("line_item_id") or "") != str(line_item_id)
        ]
        if len(line_items) == len(payload.get("line_items", [])):
            raise ValueError("estimate line item was not found")
        payload["line_items"] = line_items
        updated = Estimate(**payload)
        self.commercial_repository.save_estimate(updated)
        return updated

    def get_estimate(
        self,
        estimate_id: str,
        *,
        organization_id: str | None = None,
    ) -> Estimate | None:
        record = self.commercial_repository.load_estimate(estimate_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_estimates(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[Estimate]:
        records = self.commercial_repository.list_estimates()
        return self._filter_organization(records, organization_id)

    def calculate_estimate_total(
        self,
        estimate_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        estimate = self.get_estimate(estimate_id, organization_id=organization_id)
        if estimate is None:
            raise ValueError("estimate was not found")
        total = Decimal("0")
        for line_item in estimate.line_items:
            total += line_item.quantity * line_item.unit_price
        return total

    def _require_customer_account(
        self,
        customer_id: str,
        *,
        organization_id: str | None,
    ) -> CustomerAccount:
        record = self.get_customer_account(customer_id, organization_id=organization_id)
        if record is None:
            raise ValueError("customer account was not found")
        return record

    def _require_opportunity(
        self,
        opportunity_id: str | None,
        *,
        customer_id: str,
        organization_id: str | None,
    ) -> Opportunity | None:
        if opportunity_id is None:
            return None
        record = self.get_opportunity(opportunity_id, organization_id=organization_id)
        if record is None:
            raise ValueError("opportunity was not found")
        if record.customer_id != customer_id:
            raise ValueError("opportunity does not belong to the selected customer")
        return record

    def _filter_organization(
        self,
        records: list[Any],
        organization_id: str | None,
    ) -> list[Any]:
        if organization_id is None:
            return [
                record
                for record in records
                if getattr(record, "tenant_id", None) == self.tenant_id
            ]
        return [
            record
            for record in records
            if getattr(record, "tenant_id", None) == self.tenant_id
            and getattr(record, "organization_id", None) == organization_id
        ]

    @staticmethod
    def _normalize_project_job_link(
        value: ProjectJobLink | dict[str, Any] | None,
    ) -> ProjectJobLink | None:
        if value is None or isinstance(value, ProjectJobLink):
            return value
        return ProjectJobLink(**value)

    @staticmethod
    def _normalize_estimate_line_item(
        value: EstimateLineItem | dict[str, Any],
    ) -> EstimateLineItem:
        if isinstance(value, EstimateLineItem):
            return value
        return EstimateLineItem(**value)


__all__ = ["CommercialCustomerOpportunityEstimateService"]
