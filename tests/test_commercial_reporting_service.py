from __future__ import annotations

from decimal import Decimal

from atlas_core.contracts import (
    EstimateLineItem,
    ProcurementNeed,
    ProjectJobLink,
    QuickBooksSyncReference,
    SalesOrderStatus,
)
from atlas_core.repository.contracts import RepositoryBundle
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_invoice_vendor_bill_service import (
    CommercialInvoiceVendorBillService,
)
from atlas_core.services.commercial_reporting_service import (
    CommercialReportingService,
)
from atlas_core.services.inventory_service import InventoryService


def _bundle(tenant_id: str, root: str) -> RepositoryBundle:
    return build_local_tenant_repository_bundle(tenant_id, root)


def _operational_service(
    tenant_id: str, root: str
) -> CommercialInvoiceVendorBillService:
    return CommercialInvoiceVendorBillService(_bundle(tenant_id, root))


def _inventory_service(tenant_id: str, root: str) -> InventoryService:
    return InventoryService(_bundle(tenant_id, root))


def _reporting_service(tenant_id: str, root: str) -> CommercialReportingService:
    return CommercialReportingService(_bundle(tenant_id, root))


def _seed_estimate_pipeline(
    service: CommercialInvoiceVendorBillService,
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
        line_items=[
            EstimateLineItem(
                line_item_id="est-1-line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
            )
        ],
    )
    proposal_1 = service.create_proposal_for_estimate("est-1")
    service.send_proposal(proposal_1.proposal_id)
    service.accept_proposal(proposal_1.proposal_id)
    service.convert_accepted_estimate_to_sales_order("est-1")
    service.create_customer_invoice_from_sales_order("so-est-1")

    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-2",
        customer_id="customer-1",
        opportunity_id="opp-1",
        line_items=[
            EstimateLineItem(
                line_item_id="est-2-line-1",
                description="Room control panel",
                quantity=Decimal("1"),
                unit_price=Decimal("2500.00"),
                catalog_item_id="cat-2",
            )
        ],
    )
    proposal_2 = service.create_proposal_for_estimate("est-2")
    service.send_proposal(proposal_2.proposal_id)

    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-3",
        customer_id="customer-1",
        opportunity_id="opp-1",
    )

    service.create_sales_order(
        organization_id="org-1",
        sales_order_id="so-2",
        customer_id="customer-1",
        line_items=[
            {
                "line_item_id": "so-2-line-1",
                "description": "Supplemental mounting hardware",
                "quantity": Decimal("1"),
                "unit_price": Decimal("2500.00"),
                "catalog_item_id": "cat-2",
            }
        ],
        status=SalesOrderStatus.OPEN,
    )


def _seed_inventory(
    service: InventoryService,
) -> None:
    service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display processor",
    )
    service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-2",
        sku="SKU-2",
        description="Room control panel",
    )
    service.create_inventory_location(
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
    )
    service.create_inventory_location(
        organization_id="org-1",
        location_id="loc-2",
        name="Project staging",
    )
    service.create_inventory_position(
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("10"),
        quantity_reserved=Decimal("2"),
    )
    service.create_inventory_position(
        organization_id="org-1",
        position_id="pos-2",
        catalog_item_id="cat-2",
        location_id="loc-2",
        quantity_on_hand=Decimal("5"),
        quantity_reserved=Decimal("1"),
    )


def _seed_financial_records(
    service: CommercialInvoiceVendorBillService,
) -> None:
    service.commercial_repository.save_procurement_need(
        ProcurementNeed(
            tenant_id=service.tenant_id,
            organization_id="org-1",
            procurement_need_id="need-1",
            catalog_item_id="cat-1",
            quantity_required=Decimal("3"),
            vendor_id="vendor-1",
            sales_order_id="so-est-1",
            project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        )
    )
    procurement_need = ProcurementNeed(
        tenant_id=service.tenant_id,
        organization_id="org-1",
        procurement_need_id="need-2",
        catalog_item_id="cat-2",
        quantity_required=Decimal("1"),
        vendor_id="vendor-2",
        sales_order_id="so-2",
    )
    procurement_need.request()
    procurement_need.quote()
    service.commercial_repository.save_procurement_need(procurement_need)

    bill_1 = service.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-1",
        vendor_id="vendor-1",
        vendor_name="Tenant Supply One",
        procurement_need_id="need-1",
        line_items=[
            {
                "line_item_id": "vb-1-line-1",
                "description": "Display processor",
                "quantity": Decimal("1"),
                "unit_price": Decimal("5200.00"),
                "catalog_item_id": "cat-1",
            }
        ],
    )
    service.mark_vendor_bill_ready(bill_1.vendor_bill_id)
    service.issue_vendor_bill(bill_1.vendor_bill_id)
    service.mark_vendor_bill_sync_synced(
        bill_1.vendor_bill_id,
        external_id="qb-bill-1",
    )

    bill_2 = service.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-2",
        vendor_id="vendor-2",
        vendor_name="Tenant Supply Two",
        procurement_need_id="need-2",
        line_items=[],
        quickbooks_sync_reference=QuickBooksSyncReference(
            tenant_id=service.tenant_id,
            organization_id="org-1",
            sync_reference_id="vb-2-sync",
            entity_type="vendor_bill",
            entity_id="vb-2",
        ),
    )
    service.mark_vendor_bill_sync_pending(bill_2.vendor_bill_id)
    service.mark_vendor_bill_sync_failed(
        bill_2.vendor_bill_id,
        error_code="QB-500",
        error_message="Ledger unavailable",
    )

    invoice = service.get_customer_invoice("ci-so-est-1")
    assert invoice is not None
    service.mark_customer_invoice_ready(invoice.customer_invoice_id)
    service.issue_customer_invoice(invoice.customer_invoice_id)
    service.mark_customer_invoice_sync_pending(invoice.customer_invoice_id)
    service.mark_customer_invoice_sync_synced(
        invoice.customer_invoice_id,
        external_id="qb-inv-1",
    )


def test_reporting_summaries_cover_the_commercial_workflow(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    operational = _operational_service("tenant-a", root)
    inventory = _inventory_service("tenant-a", root)
    reporting = _reporting_service("tenant-a", root)

    _seed_estimate_pipeline(operational)
    _seed_inventory(inventory)
    _seed_financial_records(operational)

    estimate_summary = reporting.estimate_pipeline_summary(organization_id="org-1")
    proposal_summary = reporting.proposal_status_summary(organization_id="org-1")
    sales_order_summary = reporting.sales_order_backlog_summary(organization_id="org-1")
    invoice_summary = reporting.invoice_status_summary(organization_id="org-1")
    vendor_bill_summary = reporting.vendor_bill_status_summary(organization_id="org-1")
    inventory_summary = reporting.inventory_availability_summary(
        organization_id="org-1"
    )
    procurement_summary = reporting.procurement_need_summary(organization_id="org-1")
    sync_summary = reporting.quickbooks_sync_summary(organization_id="org-1")

    assert estimate_summary.total_estimates == 3
    assert estimate_summary.counts_by_stage == {
        "invoiced": 1,
        "proposal_linked": 1,
        "unconverted": 1,
    }
    assert estimate_summary.totals_by_stage["invoiced"] == Decimal("9000.00")
    assert estimate_summary.totals_by_stage["proposal_linked"] == Decimal("2500.00")
    assert estimate_summary.total_estimate_value == Decimal("11500.00")

    assert proposal_summary.total_count == 2
    assert proposal_summary.counts_by_status == {
        "accepted": 1,
        "sent": 1,
    }

    assert sales_order_summary.total_count == 2
    assert sales_order_summary.counts_by_status == {
        "draft": 1,
        "open": 1,
    }
    assert sales_order_summary.backlog_count == 2
    assert sales_order_summary.backlog_amount == Decimal("11500.00")
    assert sales_order_summary.totals_by_status["draft"] == Decimal("9000.00")
    assert sales_order_summary.totals_by_status["open"] == Decimal("2500.00")
    assert sales_order_summary.total_amount == Decimal("11500.00")

    assert invoice_summary.total_count == 1
    assert invoice_summary.counts_by_status == {"issued": 1}
    assert invoice_summary.totals_by_status["issued"] == Decimal("9000.00")
    assert invoice_summary.total_amount == Decimal("9000.00")

    assert vendor_bill_summary.total_count == 2
    assert vendor_bill_summary.counts_by_status == {"draft": 1, "entered": 1}
    assert vendor_bill_summary.totals_by_status["entered"] == Decimal("5200.00")

    assert inventory_summary.total_positions == 2
    assert inventory_summary.total_on_hand == Decimal("15")
    assert inventory_summary.total_reserved == Decimal("3")
    assert inventory_summary.total_available == Decimal("12")
    assert [row.catalog_item_id for row in inventory_summary.rows] == ["cat-1", "cat-2"]

    assert procurement_summary.total_count == 2
    assert procurement_summary.counts_by_status == {
        "identified": 1,
        "quoted": 1,
    }
    assert procurement_summary.quantities_by_status["identified"] == Decimal("3")
    assert procurement_summary.quantities_by_status["quoted"] == Decimal("1")

    assert sync_summary.total_references == 3
    assert sync_summary.counts_by_status == {
        "failed": 1,
        "synced": 2,
    }
    assert sync_summary.counts_by_entity_type == {
        "customer_invoice": 1,
        "vendor_bill": 2,
    }

    snapshot = reporting.build_commercial_reporting_snapshot(organization_id="org-1")
    assert snapshot.estimate_pipeline.total_estimates == 3
    assert snapshot.quickbooks_sync.total_references == 3


def test_reporting_is_tenant_scoped_and_empty_is_deterministic(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    operational_a = _operational_service("tenant-a", root)
    inventory_a = _inventory_service("tenant-a", root)
    reporting_a = _reporting_service("tenant-a", root)

    operational_b = _operational_service("tenant-b", root)
    inventory_b = _inventory_service("tenant-b", root)
    reporting_b = _reporting_service("tenant-b", root)
    empty_reporting = _reporting_service("tenant-c", root)

    _seed_estimate_pipeline(operational_a)
    _seed_inventory(inventory_a)
    _seed_financial_records(operational_a)

    _seed_estimate_pipeline(operational_b)
    _seed_inventory(inventory_b)
    _seed_financial_records(operational_b)

    report_a = reporting_a.build_commercial_reporting_snapshot(organization_id="org-1")
    report_b = reporting_b.build_commercial_reporting_snapshot(organization_id="org-1")
    empty_report = empty_reporting.build_commercial_reporting_snapshot(
        organization_id="org-1"
    )

    assert report_a.estimate_pipeline.total_estimates == 3
    assert report_b.estimate_pipeline.total_estimates == 3
    assert report_a.quickbooks_sync.total_references == 3
    assert report_b.quickbooks_sync.total_references == 3
    assert empty_report.estimate_pipeline.total_estimates == 0
    assert empty_report.proposal_statuses.total_count == 0
    assert empty_report.sales_order_backlog.total_count == 0
    assert empty_report.invoice_statuses.total_count == 0
    assert empty_report.vendor_bill_statuses.total_count == 0
    assert empty_report.inventory_availability.total_positions == 0
    assert empty_report.procurement_needs.total_count == 0
    assert empty_report.quickbooks_sync.total_references == 0
