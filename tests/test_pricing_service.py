from atlas_core.services.pricing_service import PricingService


def test_ingest_csv_price_list_creates_canonical_records():
    csv_payload = b"vendor,manufacturer,model,vendor_sku,description,unit_cost,discount,effective_date,expiration_date,availability_status\nAV Partner,QSC,Core Nano,QSC-CN,Control Processor,1200,10,2026-01-01,2027-01-01,in_stock\n"

    result = PricingService().ingest_price_lists([("vendor_prices.csv", csv_payload)])

    assert len(result["uploaded_price_lists"]) == 1
    assert len(result["vendor_offers"]) == 1
    assert result["vendor_offers"][0]["vendor"] == "AV Partner"
    assert result["vendor_offers"][0]["manufacturer"] == "QSC"
    assert result["vendor_offers"][0]["model"] == "Core Nano"


def test_ingest_csv_manufacturer_list_creates_product_records():
    csv_payload = b"manufacturer,model,description,category,status,aliases,list_price,effective_date,replacement_model\nQSC,Core Nano,Audio DSP,dsp,active,CoreNano|CN,2499,2026-01-01,\n"

    result = PricingService().ingest_price_lists([("mfr_list.csv", csv_payload)])

    assert len(result["manufacturer_products"]) == 1
    record = result["manufacturer_products"][0]
    assert record["manufacturer"] == "QSC"
    assert record["model"] == "Core Nano"
    assert record["aliases"] == ["CN", "CoreNano"]
    assert record["list_price"] == 2499.0


def test_enrich_bom_rows_deterministic_match_exact_then_normalized():
    bom_rows = [
        {
            "bom_item_id": "eq-1",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "description": "Control Processor",
        },
        {
            "bom_item_id": "eq-2",
            "manufacturer": "QSC",
            "model": "CORE-NANO",
            "description": "Control Processor",
        },
    ]
    manufacturer_products = [
        {
            "manufacturer": "QSC",
            "model": "Core Nano",
            "aliases": ["CN"],
            "list_price": 2499.0,
            "effective_date": "2026-01-01",
            "source_file": "mfr_list.csv",
        }
    ]
    vendor_offers = [
        {
            "vendor": "AV Partner",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "vendor_sku": "QSC-CN",
            "unit_cost": 1200.0,
            "effective_date": "2026-01-01",
            "expiration_date": "2027-01-01",
            "source_file": "vendor_prices.csv",
        }
    ]

    enriched = PricingService().enrich_bom_rows(
        bom_rows=bom_rows,
        manufacturer_products=manufacturer_products,
        vendor_offers=vendor_offers,
    )

    assert enriched[0]["matched_manufacturer_product"] == "QSC Core Nano"
    assert enriched[0]["matched_vendor_offer"] == "QSC-CN"
    assert enriched[0]["match_confidence"] == 1.0

    assert enriched[1]["matched_manufacturer_product"] == "QSC Core Nano"
    assert enriched[1]["matched_vendor_offer"] == "QSC-CN"
    assert enriched[1]["match_confidence"] == 0.86


def test_enrich_bom_rows_flags_ambiguous_and_expired_pricing():
    bom_rows = [
        {
            "bom_item_id": "eq-amb",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "description": "Control Processor",
        }
    ]
    manufacturer_products = [
        {
            "manufacturer": "QSC",
            "model": "Core Nano",
            "aliases": [],
            "list_price": 2499.0,
            "effective_date": "2026-01-01",
            "source_file": "mfr_list.csv",
        },
        {
            "manufacturer": "QSC",
            "model": "Core Nano",
            "aliases": [],
            "list_price": 2600.0,
            "effective_date": "2026-01-02",
            "source_file": "mfr_list2.csv",
        },
    ]
    vendor_offers = [
        {
            "vendor": "AV Partner",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "vendor_sku": "QSC-CN-OLD",
            "unit_cost": 1300.0,
            "effective_date": "2024-01-01",
            "expiration_date": "2024-12-31",
            "source_file": "vendor_old.csv",
        },
        {
            "vendor": "Backup Vendor",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "vendor_sku": "QSC-CN-ALT",
            "unit_cost": 1250.0,
            "effective_date": "2026-01-01",
            "expiration_date": "2027-01-01",
            "source_file": "vendor_new.csv",
        },
    ]

    enriched = PricingService().enrich_bom_rows(
        bom_rows=bom_rows,
        manufacturer_products=manufacturer_products,
        vendor_offers=vendor_offers,
    )

    assert enriched[0]["matched_manufacturer_product"] == ""
    assert "Ambiguous" in enriched[0]["pricing_warning"]
