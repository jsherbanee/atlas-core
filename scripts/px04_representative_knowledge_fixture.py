"""Build a deterministic PX-04 representative Knowledge validation fixture.

This script is for development and test validation only. It does not mutate the
application runtime session and does not enable automatic production seeding.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.commercial_catalog_seed_service import (
    CommercialCatalogSeedService,
)
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.master_library import CommercialProductService
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


def build_px04_representative_fixture() -> dict[str, object]:
    tenant_id = "px04-validation"
    organization_id = "atlas"

    product_service = CommercialProductService()
    customer = product_service.create_customer(
        customer_id="PX04-CUST-001",
        canonical_name="PX-04 Customer",
        display_name="PX-04 Customer",
        attributes={
            "status": "active",
            "primary_email": "",
            "billing_address": "",
        },
    )
    manufacturer = product_service.create_manufacturer(
        manufacturer_id="px04-mfr",
        canonical_name="PX-04 Manufacturer",
        display_name="PX-04 Manufacturer",
        manufacturer_code="PX04M",
    )
    vendor = product_service.create_vendor(
        vendor_id="px04-vendor",
        canonical_name="PX-04 Distributor",
        display_name="PX-04 Distributor",
        vendor_code="PX04V",
    )
    product = product_service.create_product(
        manufacturer_id="px04-mfr",
        manufacturer="PX-04 Manufacturer",
        manufacturer_part_number="PX04-SKU-1",
        product_name="PX-04 Speaker",
        product_description="Representative validation SKU",
        category="audio",
        lifecycle_status="active",
    )
    offering = product_service.create_vendor_offering(
        vendor_id="px04-vendor",
        vendor="PX-04 Distributor",
        atlas_product_uuid=product["atlas_product_uuid"],
        vendor_sku="PX04-DIST-SKU-1",
        purchasing_channel="distributor",
        direct_from_manufacturer=False,
        authorization_status="authorized",
        minimum_order_quantity=1,
        order_multiple=1,
        unit_of_measure="ea",
        pack_quantity=1,
        lead_time_notes="standard stock",
    )
    service = product_service.create_service_entity(
        service_id="PX04-SVC-001",
        canonical_name="PX-04 Programming",
        display_name="PX-04 Programming",
        attributes={"rate": 125.0, "applicability": "project labor"},
    )

    catalog_service = CommercialKnowledgeService()
    seed_service = CommercialCatalogSeedService(catalog_service)
    seed_result = seed_service.load_seed_data(
        tenant_id=tenant_id,
        organization_id=organization_id,
        imported_by="px04-fixture",
        force_reload=True,
        enable_pdf_finalize=False,
    )
    fee = catalog_service.upsert_catalog_item(
        catalog_item_id="fee:px04:freight",
        item_type="fee",
        code="PX04-FREIGHT",
        name="PX-04 Freight",
        description="Representative freight fee",
        default_sales_price=250.0,
        source="px04_fixture",
    )

    transactions = TransactionsWorkspaceService(
        serialized_catalog_state=catalog_service.to_dict(),
        active_tenant_id=tenant_id,
        active_organization_id=organization_id,
    )
    estimate = transactions.create_draft(
        tenant_id=tenant_id,
        organization_id=organization_id,
        document_type=CommercialDocumentType.ESTIMATE,
        customer_id=customer["attributes"]["customer_id"],
        project_id="PX04-PROJECT-001",
        project_code="PX04",
    )
    first_product = next(
        item
        for item in catalog_service.list_catalog_items()
        if item.get("item_type") == "product"
    )
    transactions.add_catalog_line(
        document_id=estimate.document_id,
        catalog_item_id=first_product["catalog_item_id"],
        quantity=Decimal("1"),
    )

    return {
        "scope": "development/test only",
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "commercial_products": product_service.to_dict(),
        "commercial_knowledge": catalog_service.to_dict(),
        "transactions": transactions.to_payload(),
        "summary": {
            "customer": customer["display_name"],
            "vendor": vendor["display_name"],
            "manufacturer": manufacturer["display_name"],
            "product": product["product_name"],
            "offering": offering["vendor_sku"],
            "service": service["display_name"],
            "fee": fee["name"],
            "seed": seed_result["seed_summary"],
            "estimate": estimate.document_id,
            "deterministic_issue": "Customer primary contact missing",
            "healthy_record": "PX-04 Distributor has an authorized distributor offering",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="/private/tmp/atlas_px04_representative_knowledge_fixture.json",
    )
    args = parser.parse_args()
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(build_px04_representative_fixture(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
