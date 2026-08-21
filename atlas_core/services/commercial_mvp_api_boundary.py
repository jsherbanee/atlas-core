"""Commercial MVP API boundary for stable request/response contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from typing import Any, cast

from atlas_core.contracts.commercial_api_contracts import (
    AcceptProposalRequest,
    AddEstimateLineItemRequest,
    CheckInventoryAvailabilityRequest,
    CommercialMvpApiError,
    CommercialMvpApiResponse,
    CommercialMvpTenantContext,
    ConvertAcceptedEstimateToSalesOrderRequest,
    CreateCustomerAccountRequest,
    CreateEstimateRequest,
    CreateOpportunityRequest,
    CreateProposalForEstimateRequest,
    CreateVendorBillRequest,
    GenerateCustomerInvoiceFromSalesOrderRequest,
    GetCommercialReportingSnapshotRequest,
    MarkProposalReadyRequest,
    MarkCustomerInvoiceSyncPendingRequest,
    MarkVendorBillSyncPendingRequest,
    RejectProposalRequest,
    RemoveEstimateLineItemRequest,
    ReserveInventoryRequest,
    SendProposalRequest,
    UpdateEstimateLineItemRequest,
)
from atlas_core.services.commercial_mvp_application_facade import (
    CommercialMvpApplicationFacade,
)


class CommercialMvpApiBoundary:
    """Tenant-scoped boundary that maps DTOs to the APP-01 facade."""

    def __init__(self, facade: CommercialMvpApplicationFacade) -> None:
        self.facade = facade
        self.tenant_id = facade.tenant_id
        self.tenant_root = facade.tenant_root

    def create_customer_account(
        self,
        request: CreateCustomerAccountRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "create_customer_account",
            request,
            CreateCustomerAccountRequest,
            lambda resolved: self.facade.create_customer_account(
                organization_id=self._organization_id(resolved.context),
                customer_id=resolved.customer_id,
                name=resolved.name,
                account_number=resolved.account_number,
                legal_name=resolved.legal_name,
                billing_email=resolved.billing_email,
                active=resolved.active,
                notes=list(resolved.notes),
            ),
            lambda record: {"customer_account": record},
        )

    def create_opportunity(
        self,
        request: CreateOpportunityRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "create_opportunity",
            request,
            CreateOpportunityRequest,
            lambda resolved: self.facade.create_opportunity(
                organization_id=self._organization_id(resolved.context),
                opportunity_id=resolved.opportunity_id,
                customer_id=resolved.customer_id,
                name=resolved.name,
                estimated_value=resolved.estimated_value,
                close_date=resolved.close_date,
                notes=list(resolved.notes),
            ),
            lambda record: {"opportunity": record},
        )

    def create_estimate(
        self,
        request: CreateEstimateRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "create_estimate",
            request,
            CreateEstimateRequest,
            lambda resolved: self.facade.create_estimate(
                organization_id=self._organization_id(resolved.context),
                estimate_id=resolved.estimate_id,
                customer_id=resolved.customer_id,
                opportunity_id=resolved.opportunity_id,
                proposal_id=resolved.proposal_id,
                project_job_link=resolved.project_job_link,
                line_items=list(resolved.line_items),
                notes=list(resolved.notes),
            ),
            lambda record: {"estimate": record},
        )

    def add_estimate_line_item(
        self,
        request: AddEstimateLineItemRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "add_estimate_line_item",
            request,
            AddEstimateLineItemRequest,
            lambda resolved: self.facade.add_estimate_line_item(
                resolved.estimate_id,
                resolved.line_item,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"estimate": record},
        )

    def update_estimate_line_item(
        self,
        request: UpdateEstimateLineItemRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "update_estimate_line_item",
            request,
            UpdateEstimateLineItemRequest,
            lambda resolved: self.facade.update_estimate_line_item(
                resolved.estimate_id,
                resolved.line_item_id,
                organization_id=self._organization_id(resolved.context),
                description=resolved.description,
                quantity=resolved.quantity,
                unit_price=resolved.unit_price,
                catalog_item_id=resolved.catalog_item_id,
                notes=resolved.notes,
            ),
            lambda record: {"estimate": record},
        )

    def remove_estimate_line_item(
        self,
        request: RemoveEstimateLineItemRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "remove_estimate_line_item",
            request,
            RemoveEstimateLineItemRequest,
            lambda resolved: self.facade.remove_estimate_line_item(
                resolved.estimate_id,
                resolved.line_item_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"estimate": record},
        )

    def create_proposal_for_estimate(
        self,
        request: CreateProposalForEstimateRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "create_proposal_for_estimate",
            request,
            CreateProposalForEstimateRequest,
            lambda resolved: self.facade.create_proposal_for_estimate(
                resolved.estimate_id,
                organization_id=self._organization_id(resolved.context),
                proposal_id=resolved.proposal_id,
                notes=list(resolved.notes),
            ),
            lambda record: {"proposal": record},
        )

    def send_proposal(
        self,
        request: SendProposalRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "send_proposal",
            request,
            SendProposalRequest,
            lambda resolved: self.facade.send_proposal(
                resolved.proposal_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"proposal": record},
        )

    def mark_proposal_ready(
        self,
        request: MarkProposalReadyRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "mark_proposal_ready",
            request,
            MarkProposalReadyRequest,
            lambda resolved: self.facade.mark_proposal_ready(
                resolved.proposal_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"proposal": record},
        )

    def accept_proposal(
        self,
        request: AcceptProposalRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "accept_proposal",
            request,
            AcceptProposalRequest,
            lambda resolved: self.facade.accept_proposal(
                resolved.proposal_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"proposal": record},
        )

    def reject_proposal(
        self,
        request: RejectProposalRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "reject_proposal",
            request,
            RejectProposalRequest,
            lambda resolved: self.facade.reject_proposal(
                resolved.proposal_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"proposal": record},
        )

    def convert_accepted_estimate_to_sales_order(
        self,
        request: ConvertAcceptedEstimateToSalesOrderRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "convert_accepted_estimate_to_sales_order",
            request,
            ConvertAcceptedEstimateToSalesOrderRequest,
            lambda resolved: self.facade.convert_accepted_estimate_to_sales_order(
                resolved.estimate_id,
                organization_id=self._organization_id(resolved.context),
                sales_order_id=resolved.sales_order_id,
            ),
            lambda record: {"sales_order": record},
        )

    def check_inventory_availability(
        self,
        request: CheckInventoryAvailabilityRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "check_inventory_availability",
            request,
            CheckInventoryAvailabilityRequest,
            lambda resolved: self.facade.check_inventory_availability_for_sales_order(
                resolved.sales_order_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda records: {
                "sales_order_id": self._request_value(request, "sales_order_id"),
                "availability": records,
            },
        )

    def reserve_inventory(
        self,
        request: ReserveInventoryRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "reserve_inventory",
            request,
            ReserveInventoryRequest,
            lambda resolved: self.facade.reserve_inventory_for_sales_order(
                resolved.sales_order_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda records: {
                "sales_order_id": self._request_value(request, "sales_order_id"),
                "reservations": records,
            },
        )

    def generate_customer_invoice_from_sales_order(
        self,
        request: GenerateCustomerInvoiceFromSalesOrderRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "generate_customer_invoice_from_sales_order",
            request,
            GenerateCustomerInvoiceFromSalesOrderRequest,
            lambda resolved: self.facade.generate_customer_invoice_from_sales_order(
                resolved.sales_order_id,
                organization_id=self._organization_id(resolved.context),
                customer_invoice_id=resolved.customer_invoice_id,
                due_at=resolved.due_at,
                notes=list(resolved.notes),
            ),
            lambda record: {"customer_invoice": record},
        )

    def create_vendor_bill(
        self,
        request: CreateVendorBillRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "create_vendor_bill",
            request,
            CreateVendorBillRequest,
            lambda resolved: self.facade.create_vendor_bill(
                organization_id=self._organization_id(resolved.context),
                vendor_bill_id=resolved.vendor_bill_id,
                vendor_id=resolved.vendor_id,
                vendor_name=resolved.vendor_name,
                purchase_order_id=resolved.purchase_order_id,
                procurement_need_id=resolved.procurement_need_id,
                project_job_link=resolved.project_job_link,
                line_items=list(resolved.line_items),
                entered_at=resolved.entered_at,
                due_at=resolved.due_at,
                notes=list(resolved.notes),
            ),
            lambda record: {"vendor_bill": record},
        )

    def mark_customer_invoice_sync_pending(
        self,
        request: MarkCustomerInvoiceSyncPendingRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "mark_customer_invoice_sync_pending",
            request,
            MarkCustomerInvoiceSyncPendingRequest,
            lambda resolved: self.facade.mark_customer_invoice_sync_pending(
                resolved.customer_invoice_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"customer_invoice": record},
        )

    def mark_vendor_bill_sync_pending(
        self,
        request: MarkVendorBillSyncPendingRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "mark_vendor_bill_sync_pending",
            request,
            MarkVendorBillSyncPendingRequest,
            lambda resolved: self.facade.mark_vendor_bill_sync_pending(
                resolved.vendor_bill_id,
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"vendor_bill": record},
        )

    def get_commercial_reporting_snapshot(
        self,
        request: GetCommercialReportingSnapshotRequest | dict[str, Any],
    ) -> CommercialMvpApiResponse:
        return self._execute(
            "get_commercial_reporting_snapshot",
            request,
            GetCommercialReportingSnapshotRequest,
            lambda resolved: self.facade.get_commercial_reporting_snapshot(
                organization_id=self._organization_id(resolved.context),
            ),
            lambda record: {"snapshot": record},
        )

    def _execute(
        self,
        operation: str,
        request_or_payload: Any,
        request_type: type[Any],
        handler: Callable[[Any], Any],
        payload_builder: Callable[[Any], dict[str, Any]],
    ) -> CommercialMvpApiResponse:
        try:
            request = self._coerce_request(request_or_payload, request_type)
        except (TypeError, ValueError) as exc:
            return self._error_response(
                operation,
                tenant_id=self._payload_tenant_id(request_or_payload),
                organization_id=self._payload_organization_id(request_or_payload),
                message=str(exc),
            )
        if request.context.tenant_id != self.tenant_id:
            return self._error_response(
                operation,
                tenant_id=request.context.tenant_id,
                organization_id=request.context.organization_id,
                message="request tenant does not match bound tenant",
                code="tenant_mismatch",
                field="tenant_id",
            )
        try:
            result = handler(request)
        except ValueError as exc:
            return self._error_response(
                operation,
                tenant_id=request.context.tenant_id,
                organization_id=request.context.organization_id,
                message=str(exc),
            )
        return CommercialMvpApiResponse(
            operation=operation,
            tenant_id=request.context.tenant_id,
            organization_id=request.context.organization_id,
            payload=self._serialize_payload(payload_builder(result)),
        )

    def _coerce_request(
        self,
        request_or_payload: Any,
        request_type: type[Any],
    ) -> Any:
        if isinstance(request_or_payload, request_type):
            return request_or_payload
        if isinstance(request_or_payload, dict):
            return request_type.from_payload(request_or_payload)
        raise TypeError("request payload must be a request contract or dict")

    def _error_response(
        self,
        operation: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        message: str,
        code: str = "validation_error",
        field: str | None = None,
    ) -> CommercialMvpApiResponse:
        return CommercialMvpApiResponse(
            operation=operation,
            tenant_id=tenant_id,
            organization_id=organization_id,
            error=CommercialMvpApiError(code=code, message=message, field=field),
        )

    def _payload_tenant_id(self, request_or_payload: Any) -> str | None:
        context = self._extract_context(request_or_payload)
        if isinstance(context, dict):
            tenant_id = context.get("tenant_id")
            return tenant_id if isinstance(tenant_id, str) else None
        if isinstance(context, CommercialMvpTenantContext):
            return context.tenant_id
        return None

    def _payload_organization_id(self, request_or_payload: Any) -> str | None:
        context = self._extract_context(request_or_payload)
        if isinstance(context, dict):
            organization_id = context.get("organization_id")
            return organization_id if isinstance(organization_id, str) else None
        if isinstance(context, CommercialMvpTenantContext):
            return context.organization_id
        return None

    @staticmethod
    def _extract_context(request_or_payload: Any) -> Any:
        if isinstance(request_or_payload, dict):
            return request_or_payload.get("context")
        return getattr(request_or_payload, "context", None)

    def _request_value(
        self,
        request_or_payload: Any,
        key: str,
    ) -> Any:
        if isinstance(request_or_payload, dict):
            return request_or_payload.get(key)
        return getattr(request_or_payload, key, None)

    def _serialize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if is_dataclass(payload):
            return self._serialize_payload(asdict(cast(Any, payload)))
        return self._serialize_value(payload)

    def _serialize_value(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._serialize_value(asdict(cast(Any, value)))
        if isinstance(value, dict):
            return {
                str(key): self._serialize_value(item) for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._serialize_value(item) for item in value]
        if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
            return self._serialize_value(value.to_dict())
        return value

    @staticmethod
    def _organization_id(context: CommercialMvpTenantContext) -> str:
        if context.organization_id is None:
            raise ValueError("organization_id cannot be blank")
        return context.organization_id


__all__ = ["CommercialMvpApiBoundary"]
