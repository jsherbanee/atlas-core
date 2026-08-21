"""Commercial Workspace MVP UI surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from atlas_core.contracts.commercial_api_contracts import (
    AcceptProposalRequest,
    AddEstimateLineItemRequest,
    CheckInventoryAvailabilityRequest,
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
    MarkCustomerInvoiceSyncPendingRequest,
    MarkProposalReadyRequest,
    MarkVendorBillSyncPendingRequest,
    RejectProposalRequest,
    RemoveEstimateLineItemRequest,
    ReserveInventoryRequest,
    SendProposalRequest,
)
from atlas_core.contracts.commercial_spine_contracts import (
    EstimateLineItem,
    VendorBillLineItem,
)
from atlas_core.repository import build_local_tenant_repository_bundle
from atlas_core.services.commercial_mvp_api_boundary import CommercialMvpApiBoundary
from atlas_core.services.commercial_mvp_application_facade import (
    CommercialMvpApplicationFacade,
)
from atlas_core.services.runtime_workspace import ensure_runtime_workspace_root
from atlas_core.ui.workspace_framework import (
    render_guided_empty_state as _shared_render_guided_empty_state,
    render_page_header as _shared_render_page_header,
    render_report_table as _shared_render_report_table,
    render_section_card as _shared_render_section_card,
)


@dataclass(frozen=True)
class CommercialWorkspaceServices:
    facade: CommercialMvpApplicationFacade
    boundary: CommercialMvpApiBoundary
    tenant_context: CommercialMvpTenantContext


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)


def _commercial_bundle_root() -> Path:
    return ensure_runtime_workspace_root()


def _commercial_services(
    *,
    tenant_id: str,
    organization_id: str,
) -> CommercialWorkspaceServices:
    bundle = build_local_tenant_repository_bundle(
        tenant_id,
        _commercial_bundle_root(),
    )
    facade = CommercialMvpApplicationFacade(bundle)
    boundary = CommercialMvpApiBoundary(facade)
    tenant_context = CommercialMvpTenantContext(
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    return CommercialWorkspaceServices(
        facade=facade,
        boundary=boundary,
        tenant_context=tenant_context,
    )


def _to_mapping(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return dict(record)
    if hasattr(record, "to_dict") and callable(getattr(record, "to_dict")):
        return dict(record.to_dict())
    if is_dataclass(record):
        return dict(asdict(cast(Any, record)))
    return dict(getattr(record, "__dict__", {}))


def _decimal_or_none(value: Any) -> Decimal | None:
    normalized = _safe_text(value, "")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation, ValueError:
        raise ValueError(f"{normalized} is not a valid decimal amount")


def _decimal_text(value: Any) -> str:
    if value is None or value == "":
        return "0.00"
    try:
        return f"{Decimal(str(value)):,.2f}"
    except InvalidOperation, ValueError:
        return _safe_text(value, "0.00")


def _money_text(value: Any) -> str:
    return f"${_decimal_text(value)}"


def _note_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _line_total(line_items: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for item in line_items:
        quantity = _decimal_or_none(item.get("quantity")) or Decimal("0")
        unit_price = _decimal_or_none(item.get("unit_price")) or Decimal("0")
        total += quantity * unit_price
    return total


def _sync_status(value: dict[str, Any] | None) -> str:
    if not value:
        return "n/a"
    return _safe_text(value.get("status"), "n/a")


def _render_response_message(
    st: Any, response: CommercialMvpApiResponse, success: str
) -> None:
    if response.ok:
        st.success(success)
        return
    error = response.error
    if error is None:
        st.error("Request failed")
        return
    field_suffix = f" ({error.field})" if error.field else ""
    st.error(f"{error.code}{field_suffix}: {error.message}")


def _snapshot_rows(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "Summary": "Estimate Pipeline",
            "Total": _safe_text(
                snapshot.get("estimate_pipeline", {}).get("total_estimates"), "0"
            ),
            "Breakdown": "; ".join(
                f"{key}: {value}"
                for key, value in sorted(
                    dict(
                        snapshot.get("estimate_pipeline", {}).get("counts_by_stage")
                        or {}
                    ).items()
                )
            )
            or "None",
            "Value": _money_text(
                snapshot.get("estimate_pipeline", {}).get("total_estimate_value")
            ),
        },
        {
            "Summary": "Proposal Status",
            "Total": _safe_text(
                snapshot.get("proposal_statuses", {}).get("total_count"), "0"
            ),
            "Breakdown": "; ".join(
                f"{key}: {value}"
                for key, value in sorted(
                    dict(
                        snapshot.get("proposal_statuses", {}).get("counts_by_status")
                        or {}
                    ).items()
                )
            )
            or "None",
            "Value": "-",
        },
        {
            "Summary": "Sales Order Backlog",
            "Total": _safe_text(
                snapshot.get("sales_order_backlog", {}).get("total_count"), "0"
            ),
            "Breakdown": f"Backlog { _safe_text(snapshot.get('sales_order_backlog', {}).get('backlog_count'), '0') }",
            "Value": _money_text(
                snapshot.get("sales_order_backlog", {}).get("backlog_amount")
            ),
        },
        {
            "Summary": "Invoice Status",
            "Total": _safe_text(
                snapshot.get("invoice_statuses", {}).get("total_count"), "0"
            ),
            "Breakdown": "; ".join(
                f"{key}: {value}"
                for key, value in sorted(
                    dict(
                        snapshot.get("invoice_statuses", {}).get("counts_by_status")
                        or {}
                    ).items()
                )
            )
            or "None",
            "Value": _money_text(
                snapshot.get("invoice_statuses", {}).get("total_amount")
            ),
        },
        {
            "Summary": "Vendor Bill Status",
            "Total": _safe_text(
                snapshot.get("vendor_bill_statuses", {}).get("total_count"), "0"
            ),
            "Breakdown": "; ".join(
                f"{key}: {value}"
                for key, value in sorted(
                    dict(
                        snapshot.get("vendor_bill_statuses", {}).get("counts_by_status")
                        or {}
                    ).items()
                )
            )
            or "None",
            "Value": _money_text(
                snapshot.get("vendor_bill_statuses", {}).get("total_amount")
            ),
        },
        {
            "Summary": "Inventory Availability",
            "Total": _safe_text(
                snapshot.get("inventory_availability", {}).get("total_positions"), "0"
            ),
            "Breakdown": "On hand "
            + _decimal_text(
                snapshot.get("inventory_availability", {}).get("total_on_hand")
            )
            + " · Reserved "
            + _decimal_text(
                snapshot.get("inventory_availability", {}).get("total_reserved")
            ),
            "Value": _decimal_text(
                snapshot.get("inventory_availability", {}).get("total_available")
            ),
        },
        {
            "Summary": "QuickBooks Sync",
            "Total": _safe_text(
                snapshot.get("quickbooks_sync", {}).get("total_references"), "0"
            ),
            "Breakdown": "; ".join(
                f"{key}: {value}"
                for key, value in sorted(
                    dict(
                        snapshot.get("quickbooks_sync", {}).get("counts_by_status")
                        or {}
                    ).items()
                )
            )
            or "None",
            "Value": "-",
        },
    ]


def _render_snapshot_section(st: Any, services: CommercialWorkspaceServices) -> None:
    response = services.boundary.get_commercial_reporting_snapshot(
        GetCommercialReportingSnapshotRequest(context=services.tenant_context)
    )
    if not response.ok or response.payload is None:
        _render_response_message(st, response, "Commercial snapshot loaded.")
        return

    snapshot = dict(response.payload.get("snapshot") or {})
    with _shared_render_section_card(
        st,
        "Commercial Snapshot",
        subtitle="Tenant-scoped pipeline, backlog, inventory, and QuickBooks sync summaries.",
    ):
        st.caption(
            f"Tenant {services.tenant_context.tenant_id} · Organization {services.tenant_context.organization_id or 'n/a'}"
        )
        st.columns(1)
        _shared_render_report_table(st, _snapshot_rows(snapshot))


def _customer_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        rows.append(
            {
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Name": _safe_text(data.get("name"), ""),
                "Account Number": _safe_text(data.get("account_number"), ""),
                "Billing Email": _safe_text(data.get("billing_email"), ""),
                "Active": "Yes" if bool(data.get("active", True)) else "No",
            }
        )
    return rows


def _opportunity_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        rows.append(
            {
                "Opportunity ID": _safe_text(data.get("opportunity_id"), ""),
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Name": _safe_text(data.get("name"), ""),
                "Status": _safe_text(data.get("status"), ""),
                "Estimated Value": _money_text(data.get("estimated_value")),
            }
        )
    return rows


def _estimate_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        line_items = [dict(item) for item in list(data.get("line_items") or [])]
        rows.append(
            {
                "Estimate ID": _safe_text(data.get("estimate_id"), ""),
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Opportunity ID": _safe_text(data.get("opportunity_id"), ""),
                "Proposal ID": _safe_text(data.get("proposal_id"), ""),
                "Line Items": str(len(line_items)),
                "Estimate Value": _money_text(_line_total(line_items)),
            }
        )
    return rows


def _inventory_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        rows.append(
            {
                "Sales Order ID": _safe_text(data.get("sales_order_id"), ""),
                "Line Item ID": _safe_text(data.get("sales_order_line_item_id"), ""),
                "Catalog Item ID": _safe_text(data.get("catalog_item_id"), ""),
                "Requested": _decimal_text(data.get("requested_quantity")),
                "Available": _decimal_text(data.get("available_quantity")),
                "Location": _safe_text(data.get("selected_location_id"), ""),
                "Can Reserve": "Yes" if bool(data.get("can_reserve")) else "No",
            }
        )
    return rows


def _proposal_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        rows.append(
            {
                "Proposal ID": _safe_text(data.get("proposal_id"), ""),
                "Estimate ID": _safe_text(data.get("estimate_id"), ""),
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Status": _safe_text(data.get("status"), ""),
                "Sent At": _safe_text(data.get("sent_at"), ""),
                "Responded At": _safe_text(data.get("responded_at"), ""),
            }
        )
    return rows


def _sales_order_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        line_items = [dict(item) for item in list(data.get("line_items") or [])]
        rows.append(
            {
                "Sales Order ID": _safe_text(data.get("sales_order_id"), ""),
                "Estimate ID": _safe_text(data.get("estimate_id"), ""),
                "Proposal ID": _safe_text(data.get("proposal_id"), ""),
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Status": _safe_text(data.get("status"), ""),
                "Line Items": str(len(line_items)),
                "Order Value": _money_text(_line_total(line_items)),
            }
        )
    return rows


def _invoice_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        quickbooks = dict(data.get("quickbooks_sync_reference") or {})
        line_items = [dict(item) for item in list(data.get("line_items") or [])]
        rows.append(
            {
                "Invoice ID": _safe_text(data.get("customer_invoice_id"), ""),
                "Sales Order ID": _safe_text(data.get("sales_order_id"), ""),
                "Customer ID": _safe_text(data.get("customer_id"), ""),
                "Status": _safe_text(data.get("status"), ""),
                "Sync": _sync_status(quickbooks),
                "Invoice Value": _money_text(_line_total(line_items)),
            }
        )
    return rows


def _vendor_bill_rows(records: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        data = _to_mapping(record)
        quickbooks = dict(data.get("quickbooks_sync_reference") or {})
        line_items = [dict(item) for item in list(data.get("line_items") or [])]
        rows.append(
            {
                "Vendor Bill ID": _safe_text(data.get("vendor_bill_id"), ""),
                "Vendor ID": _safe_text(data.get("vendor_id"), ""),
                "Vendor Name": _safe_text(data.get("vendor_name"), ""),
                "Status": _safe_text(data.get("status"), ""),
                "Sync": _sync_status(quickbooks),
                "Bill Value": _money_text(_line_total(line_items)),
            }
        )
    return rows


def _select_or_blank(options: list[str]) -> list[str]:
    return options if options else [""]


def _render_customer_section(st: Any, services: CommercialWorkspaceServices) -> None:
    with _shared_render_section_card(
        st,
        "Customer / Account Creation and Listing",
        subtitle="Create customer records and review the tenant-scoped account list.",
    ):
        cols = st.columns([1, 1])
        with cols[0]:
            with st.form("atlas_commercial_customer_account_form"):
                customer_id = st.text_input("Customer ID", value="")
                name = st.text_input("Name", value="")
                account_number = st.text_input("Account Number", value="")
                legal_name = st.text_input("Legal Name", value="")
                billing_email = st.text_input("Billing Email", value="")
                notes = st.text_area("Notes", value="")
                submitted = st.form_submit_button("Create Customer / Account")
            if submitted:
                try:
                    response = services.boundary.create_customer_account(
                        CreateCustomerAccountRequest(
                            context=services.tenant_context,
                            customer_id=customer_id,
                            name=name,
                            account_number=account_number or None,
                            legal_name=legal_name or None,
                            billing_email=billing_email or None,
                            notes=_note_lines(notes),
                        )
                    )
                    _render_response_message(
                        st, response, "Customer / account created."
                    )
                    if response.ok:
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with cols[1]:
            rows = _customer_rows(
                services.facade.list_customer_accounts(
                    organization_id=services.tenant_context.organization_id,
                )
            )
            if rows:
                _shared_render_report_table(st, rows)
            else:
                _shared_render_guided_empty_state(
                    st,
                    why_empty="No customer accounts exist for this tenant yet.",
                    action_to_populate="Create a customer account from the form on the left.",
                    next_location="Customer / Account Creation and Listing.",
                )


def _render_opportunity_section(st: Any, services: CommercialWorkspaceServices) -> None:
    with _shared_render_section_card(
        st,
        "Opportunity Creation and Listing",
        subtitle="Track opportunities against existing customer accounts.",
    ):
        cols = st.columns([1, 1])
        customer_options = [
            _safe_text(row.get("Customer ID"), "")
            for row in _customer_rows(
                services.facade.list_customer_accounts(
                    organization_id=services.tenant_context.organization_id,
                )
            )
        ]
        with cols[0]:
            with st.form("atlas_commercial_opportunity_form"):
                customer_id = st.selectbox(
                    "Customer ID",
                    options=_select_or_blank(customer_options),
                    index=0,
                )
                opportunity_id = st.text_input("Opportunity ID", value="")
                name = st.text_input("Opportunity Name", value="")
                estimated_value = st.text_input("Estimated Value", value="")
                close_date = st.text_input("Close Date", value="")
                notes = st.text_area("Notes", value="")
                submitted = st.form_submit_button("Create Opportunity")
            if submitted:
                try:
                    response = services.boundary.create_opportunity(
                        CreateOpportunityRequest(
                            context=services.tenant_context,
                            customer_id=customer_id,
                            opportunity_id=opportunity_id,
                            name=name,
                            estimated_value=_decimal_or_none(estimated_value),
                            close_date=close_date or None,
                            notes=_note_lines(notes),
                        )
                    )
                    _render_response_message(st, response, "Opportunity created.")
                    if response.ok:
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with cols[1]:
            rows = _opportunity_rows(
                services.facade.list_opportunities(
                    organization_id=services.tenant_context.organization_id,
                )
            )
            if rows:
                _shared_render_report_table(st, rows)
            else:
                _shared_render_guided_empty_state(
                    st,
                    why_empty="No opportunities exist for this tenant yet.",
                    action_to_populate="Create an opportunity from the form on the left.",
                    next_location="Opportunity Creation and Listing.",
                )


def _render_estimate_section(st: Any, services: CommercialWorkspaceServices) -> None:
    with _shared_render_section_card(
        st,
        "Estimate Creation, Listing, and Line Items",
        subtitle="Create estimates, add or remove line items, and inspect current estimate drafts.",
    ):
        cols = st.columns([1, 1])
        opportunity_options = [
            _safe_text(row.get("Opportunity ID"), "")
            for row in _opportunity_rows(
                services.facade.list_opportunities(
                    organization_id=services.tenant_context.organization_id,
                )
            )
        ]
        customer_options = [
            _safe_text(row.get("Customer ID"), "")
            for row in _customer_rows(
                services.facade.list_customer_accounts(
                    organization_id=services.tenant_context.organization_id,
                )
            )
        ]
        with cols[0]:
            with st.form("atlas_commercial_estimate_form"):
                customer_id = st.selectbox(
                    "Customer ID",
                    options=_select_or_blank(customer_options),
                    index=0,
                )
                estimate_id = st.text_input("Estimate ID", value="")
                opportunity_id = st.selectbox(
                    "Opportunity ID",
                    options=[""] + opportunity_options,
                    index=0,
                )
                proposal_id = st.text_input("Proposal ID", value="")
                notes = st.text_area("Notes", value="")
                submitted = st.form_submit_button("Create Estimate")
            if submitted:
                try:
                    response = services.boundary.create_estimate(
                        CreateEstimateRequest(
                            context=services.tenant_context,
                            customer_id=customer_id,
                            estimate_id=estimate_id,
                            opportunity_id=opportunity_id or None,
                            proposal_id=proposal_id or None,
                            notes=_note_lines(notes),
                        )
                    )
                    _render_response_message(st, response, "Estimate created.")
                    if response.ok:
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        estimate_records = services.facade.list_estimates(
            organization_id=services.tenant_context.organization_id,
        )
        estimate_rows = _estimate_rows(estimate_records)
        if estimate_rows:
            _shared_render_report_table(st, estimate_rows)
        else:
            _shared_render_guided_empty_state(
                st,
                why_empty="No estimates exist for this tenant yet.",
                action_to_populate="Create an estimate from the form on the left.",
                next_location="Estimate Creation, Listing, and Line Items.",
            )

        if not estimate_records:
            return

        selected_estimate_id = st.selectbox(
            "Selected Estimate",
            options=[record.estimate_id for record in estimate_records],
            index=0,
            key="atlas_commercial_selected_estimate",
        )
        selected_estimate = next(
            (
                record
                for record in estimate_records
                if record.estimate_id == selected_estimate_id
            ),
            None,
        )
        if selected_estimate is None:
            return
        selected_estimate_data = _to_mapping(selected_estimate)
        line_items = [
            dict(item) for item in list(selected_estimate_data.get("line_items") or [])
        ]
        st.caption(f"Estimate subtotal: {_money_text(_line_total(line_items))}")

        line_cols = st.columns([1, 1])
        with line_cols[0]:
            with st.form("atlas_commercial_estimate_add_line_item_form"):
                line_item_id = st.text_input("Line Item ID", value="")
                description = st.text_input("Description", value="")
                quantity = st.text_input("Quantity", value="1")
                unit_price = st.text_input("Unit Price", value="0")
                catalog_item_id = st.text_input("Catalog Item ID", value="")
                notes = st.text_area("Line Notes", value="")
                submitted = st.form_submit_button("Add Line Item")
            if submitted:
                try:
                    response = services.boundary.add_estimate_line_item(
                        AddEstimateLineItemRequest(
                            context=services.tenant_context,
                            estimate_id=selected_estimate_id,
                            line_item=EstimateLineItem(
                                line_item_id=line_item_id,
                                description=description,
                                quantity=_decimal_or_none(quantity) or Decimal("0"),
                                unit_price=_decimal_or_none(unit_price) or Decimal("0"),
                                catalog_item_id=catalog_item_id or None,
                                notes=_note_lines(notes),
                            ),
                        )
                    )
                    _render_response_message(st, response, "Estimate line item added.")
                    if response.ok:
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        with line_cols[1]:
            if line_items:
                _shared_render_report_table(st, line_items)
                line_item_ids = [
                    _safe_text(item.get("line_item_id"), "") for item in line_items
                ]
                with st.form("atlas_commercial_estimate_remove_line_item_form"):
                    selected_line_item_id = st.selectbox(
                        "Line Item to Remove",
                        options=line_item_ids,
                        index=0,
                    )
                    remove_submitted = st.form_submit_button("Remove Line Item")
                if remove_submitted:
                    try:
                        response = services.boundary.remove_estimate_line_item(
                            RemoveEstimateLineItemRequest(
                                context=services.tenant_context,
                                estimate_id=selected_estimate_id,
                                line_item_id=selected_line_item_id,
                            )
                        )
                        _render_response_message(
                            st, response, "Estimate line item removed."
                        )
                        if response.ok:
                            st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            else:
                st.caption("Selected estimate has no line items yet.")


def _render_inventory_section(st: Any, services: CommercialWorkspaceServices) -> None:
    with _shared_render_section_card(
        st,
        "Inventory Availability and Reservation",
        subtitle="Check sales-order availability and reserve stock from the tenant-scoped inventory service.",
    ):
        sales_order_records = services.facade.list_sales_orders(
            organization_id=services.tenant_context.organization_id,
        )
        if not sales_order_records:
            _shared_render_guided_empty_state(
                st,
                why_empty="No sales orders exist for this tenant yet.",
                action_to_populate="Create and accept an estimate before checking inventory.",
                next_location="Inventory Availability and Reservation.",
            )
            return

        sales_order_id = st.selectbox(
            "Sales Order",
            options=[record.sales_order_id for record in sales_order_records],
            index=0,
            key="atlas_commercial_inventory_sales_order_id",
        )
        availability_response = services.boundary.check_inventory_availability(
            CheckInventoryAvailabilityRequest(
                context=services.tenant_context,
                sales_order_id=sales_order_id,
            )
        )
        if not availability_response.ok or availability_response.payload is None:
            _render_response_message(
                st,
                availability_response,
                "Inventory availability loaded.",
            )
            return

        availability_rows = _inventory_rows(
            list(availability_response.payload.get("availability") or [])
        )
        if availability_rows:
            _shared_render_report_table(st, availability_rows)
        else:
            st.caption(
                "No line-level inventory rows are available for the selected order."
            )

        if st.button(
            "Reserve Inventory",
            key="atlas_commercial_reserve_inventory",
            width="stretch",
        ):
            reserve_response = services.boundary.reserve_inventory(
                ReserveInventoryRequest(
                    context=services.tenant_context,
                    sales_order_id=sales_order_id,
                )
            )
            _render_response_message(st, reserve_response, "Inventory reserved.")
            if reserve_response.ok:
                st.rerun()


def _render_workflow_section(st: Any, services: CommercialWorkspaceServices) -> None:
    with _shared_render_section_card(
        st,
        "Proposal, Sales Order, and Invoice Workflow",
        subtitle="Move accepted estimates through proposal, order, and invoice states.",
    ):
        estimate_records = services.facade.list_estimates(
            organization_id=services.tenant_context.organization_id,
        )
        proposal_records = services.facade.list_proposals(
            organization_id=services.tenant_context.organization_id,
        )
        sales_order_records = services.facade.list_sales_orders(
            organization_id=services.tenant_context.organization_id,
        )
        invoice_records = services.facade.list_customer_invoices(
            organization_id=services.tenant_context.organization_id,
        )

        cols = st.columns([1, 1])
        with cols[0]:
            st.markdown("#### Proposals")
            if estimate_records:
                estimate_id = st.selectbox(
                    "Estimate for Proposal",
                    options=[record.estimate_id for record in estimate_records],
                    index=0,
                    key="atlas_commercial_proposal_estimate_id",
                )
                with st.form("atlas_commercial_proposal_create_form"):
                    proposal_id = st.text_input("Proposal ID", value="")
                    notes = st.text_area("Proposal Notes", value="")
                    submitted = st.form_submit_button("Create Proposal")
                if submitted:
                    try:
                        response = services.boundary.create_proposal_for_estimate(
                            CreateProposalForEstimateRequest(
                                context=services.tenant_context,
                                estimate_id=estimate_id,
                                proposal_id=proposal_id or None,
                                notes=_note_lines(notes),
                            )
                        )
                        _render_response_message(st, response, "Proposal created.")
                        if response.ok:
                            st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            if proposal_records:
                _shared_render_report_table(st, _proposal_rows(proposal_records))
                proposal_id = st.selectbox(
                    "Selected Proposal",
                    options=[record.proposal_id for record in proposal_records],
                    index=0,
                    key="atlas_commercial_selected_proposal",
                )
                action_cols = st.columns(4)
                if action_cols[0].button(
                    "Mark Ready",
                    key="atlas_commercial_mark_proposal_ready",
                    width="stretch",
                ):
                    response = services.boundary.mark_proposal_ready(
                        MarkProposalReadyRequest(
                            context=services.tenant_context,
                            proposal_id=proposal_id,
                        )
                    )
                    _render_response_message(st, response, "Proposal marked ready.")
                    if response.ok:
                        st.rerun()
                if action_cols[1].button(
                    "Send",
                    key="atlas_commercial_send_proposal",
                    width="stretch",
                ):
                    response = services.boundary.send_proposal(
                        SendProposalRequest(
                            context=services.tenant_context,
                            proposal_id=proposal_id,
                        )
                    )
                    _render_response_message(st, response, "Proposal sent.")
                    if response.ok:
                        st.rerun()
                if action_cols[2].button(
                    "Accept",
                    key="atlas_commercial_accept_proposal",
                    width="stretch",
                ):
                    response = services.boundary.accept_proposal(
                        AcceptProposalRequest(
                            context=services.tenant_context,
                            proposal_id=proposal_id,
                        )
                    )
                    _render_response_message(st, response, "Proposal accepted.")
                    if response.ok:
                        st.rerun()
                if action_cols[3].button(
                    "Reject",
                    key="atlas_commercial_reject_proposal",
                    width="stretch",
                ):
                    response = services.boundary.reject_proposal(
                        RejectProposalRequest(
                            context=services.tenant_context,
                            proposal_id=proposal_id,
                        )
                    )
                    _render_response_message(st, response, "Proposal rejected.")
                    if response.ok:
                        st.rerun()
            else:
                st.caption(
                    "Create the first proposal from an estimate to begin the workflow."
                )

        with cols[1]:
            st.markdown("#### Sales Orders and Invoices")
            if estimate_records:
                estimate_id = st.selectbox(
                    "Accepted Estimate",
                    options=[record.estimate_id for record in estimate_records],
                    index=0,
                    key="atlas_commercial_sales_order_estimate_id",
                )
                if st.button(
                    "Convert to Sales Order",
                    key="atlas_commercial_convert_estimate_to_sales_order",
                    width="stretch",
                ):
                    response = (
                        services.boundary.convert_accepted_estimate_to_sales_order(
                            ConvertAcceptedEstimateToSalesOrderRequest(
                                context=services.tenant_context,
                                estimate_id=estimate_id,
                            )
                        )
                    )
                    _render_response_message(st, response, "Sales order created.")
                    if response.ok:
                        st.rerun()
            if sales_order_records:
                _shared_render_report_table(st, _sales_order_rows(sales_order_records))
                sales_order_id = st.selectbox(
                    "Selected Sales Order",
                    options=[record.sales_order_id for record in sales_order_records],
                    index=0,
                    key="atlas_commercial_selected_sales_order",
                )
                selected_sales_order = next(
                    (
                        record
                        for record in sales_order_records
                        if record.sales_order_id == sales_order_id
                    ),
                    None,
                )
                if selected_sales_order is not None:
                    st.caption(
                        f"Selected sales order status: {_safe_text(getattr(selected_sales_order, 'status', None), 'n/a')}"
                    )
                if st.button(
                    "Generate Customer Invoice",
                    key="atlas_commercial_generate_invoice",
                    width="stretch",
                ):
                    response = (
                        services.boundary.generate_customer_invoice_from_sales_order(
                            GenerateCustomerInvoiceFromSalesOrderRequest(
                                context=services.tenant_context,
                                sales_order_id=sales_order_id,
                            )
                        )
                    )
                    _render_response_message(st, response, "Customer invoice created.")
                    if response.ok:
                        st.rerun()
            else:
                st.caption(
                    "Sales orders appear here after converting accepted estimates."
                )
            if invoice_records:
                _shared_render_report_table(st, _invoice_rows(invoice_records))
                invoice_id = st.selectbox(
                    "Customer Invoice",
                    options=[record.customer_invoice_id for record in invoice_records],
                    index=0,
                    key="atlas_commercial_selected_customer_invoice",
                )
                if st.button(
                    "Mark Customer Invoice Sync Pending",
                    key="atlas_commercial_mark_invoice_sync_pending",
                    width="stretch",
                ):
                    response = services.boundary.mark_customer_invoice_sync_pending(
                        MarkCustomerInvoiceSyncPendingRequest(
                            context=services.tenant_context,
                            customer_invoice_id=invoice_id,
                        )
                    )
                    _render_response_message(
                        st, response, "Customer invoice marked sync pending."
                    )
                    if response.ok:
                        st.rerun()


def _render_vendor_bill_and_sync_section(
    st: Any, services: CommercialWorkspaceServices
) -> None:
    with _shared_render_section_card(
        st,
        "Vendor Bills and QuickBooks Sync Readiness",
        subtitle="Create vendor bills manually and mark invoice / bill records for sync readiness.",
    ):
        cols = st.columns([1, 1])
        with cols[0]:
            with st.form("atlas_commercial_vendor_bill_form"):
                vendor_bill_id = st.text_input("Vendor Bill ID", value="")
                vendor_id = st.text_input("Vendor ID", value="")
                vendor_name = st.text_input("Vendor Name", value="")
                purchase_order_id = st.text_input("Purchase Order ID", value="")
                procurement_need_id = st.text_input("Procurement Need ID", value="")
                entered_at = st.text_input("Entered At", value="")
                due_at = st.text_input("Due At", value="")
                line_item_id = st.text_input("Line Item ID", value="")
                description = st.text_input("Line Description", value="")
                quantity = st.text_input("Quantity", value="1")
                unit_price = st.text_input("Unit Price", value="0")
                notes = st.text_area("Notes", value="")
                submitted = st.form_submit_button("Create Vendor Bill")
            if submitted:
                try:
                    response = services.boundary.create_vendor_bill(
                        CreateVendorBillRequest(
                            context=services.tenant_context,
                            vendor_bill_id=vendor_bill_id,
                            vendor_id=vendor_id,
                            vendor_name=vendor_name,
                            purchase_order_id=purchase_order_id or None,
                            procurement_need_id=procurement_need_id or None,
                            entered_at=entered_at or None,
                            due_at=due_at or None,
                            line_items=[
                                VendorBillLineItem(
                                    line_item_id=line_item_id,
                                    description=description,
                                    quantity=_decimal_or_none(quantity) or Decimal("0"),
                                    unit_price=_decimal_or_none(unit_price)
                                    or Decimal("0"),
                                )
                            ],
                            notes=_note_lines(notes),
                        )
                    )
                    _render_response_message(st, response, "Vendor bill created.")
                    if response.ok:
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with cols[1]:
            vendor_bill_records = services.facade.list_vendor_bills(
                organization_id=services.tenant_context.organization_id,
            )
            if vendor_bill_records:
                _shared_render_report_table(st, _vendor_bill_rows(vendor_bill_records))
                vendor_bill_id = st.selectbox(
                    "Selected Vendor Bill",
                    options=[record.vendor_bill_id for record in vendor_bill_records],
                    index=0,
                    key="atlas_commercial_selected_vendor_bill",
                )
                if st.button(
                    "Mark Vendor Bill Sync Pending",
                    key="atlas_commercial_mark_vendor_bill_sync_pending",
                    width="stretch",
                ):
                    response = services.boundary.mark_vendor_bill_sync_pending(
                        MarkVendorBillSyncPendingRequest(
                            context=services.tenant_context,
                            vendor_bill_id=vendor_bill_id,
                        )
                    )
                    _render_response_message(
                        st, response, "Vendor bill marked sync pending."
                    )
                    if response.ok:
                        st.rerun()
            else:
                _shared_render_guided_empty_state(
                    st,
                    why_empty="No vendor bills exist for this tenant yet.",
                    action_to_populate="Create a vendor bill from the form on the left.",
                    next_location="Vendor Bills and QuickBooks Sync.",
                )


def render_commercial_workspace_page(
    st: Any,
    workspace_service: Any | None = None,
    *,
    tenant_id: str | None = None,
    organization_id: str | None = None,
    services: CommercialWorkspaceServices | None = None,
) -> None:
    _ = workspace_service
    resolved_services = services or _commercial_services(
        tenant_id=_safe_text(tenant_id, "local"),
        organization_id=_safe_text(organization_id, "atlas"),
    )
    _shared_render_page_header(
        st,
        "Commercial Workspace",
        "Tenant-scoped commercial MVP surface for customers, opportunities, estimates, proposals, sales orders, invoices, vendor bills, and QuickBooks sync state.",
    )
    _render_snapshot_section(st, resolved_services)
    _render_customer_section(st, resolved_services)
    _render_opportunity_section(st, resolved_services)
    _render_estimate_section(st, resolved_services)
    _render_inventory_section(st, resolved_services)
    _render_workflow_section(st, resolved_services)
    _render_vendor_bill_and_sync_section(st, resolved_services)


__all__ = ["CommercialWorkspaceServices", "render_commercial_workspace_page"]
