from datetime import UTC, datetime

from atlas_core.domain.commercial_knowledge import CommercialProductLifecycleStatus
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService


def _rows(cost_a: float = 100.0, cost_b: float = 200.0) -> list[dict[str, object]]:
    return [
        {
            "vendor": "AV Partner",
            "manufacturer": "QSC",
            "model": "Core110f",
            "vendor_sku": "QSC-110F",
            "unit_cost": cost_a,
            "list_price": 2999.0,
            "currency": "USD",
            "lead_time": "4 weeks",
            "availability_status": "in_stock",
            "effective_date": "2026-01-01",
            "expiration_date": "2026-12-31",
            "description": "DSP core",
            "confidence": 0.92,
        },
        {
            "vendor": "AV Partner",
            "manufacturer": "QSC",
            "model": "CoreNano",
            "vendor_sku": "QSC-NANO",
            "unit_cost": cost_b,
            "list_price": 2499.0,
            "currency": "USD",
            "lead_time": "6 weeks",
            "availability_status": "limited",
            "effective_date": "2026-01-01",
            "expiration_date": "2026-12-31",
            "description": "Compact DSP",
            "confidence": 0.88,
        },
    ]


def test_immutable_version_creation() -> None:
    service = CommercialKnowledgeService()

    first = service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )
    second = service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=_rows(cost_a=110.0),
    )

    assert first["version"]["version_id"] != second["version"]["version_id"]
    assert len(service.to_dict()["price_sheet_versions"]) == 2


def test_version_comparison_detects_increase_decrease_and_attribute_changes() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )

    updated_rows = _rows(cost_a=130.0, cost_b=190.0)
    updated_rows[0]["lead_time"] = "8 weeks"
    updated_rows[1]["availability_status"] = "out_of_stock"
    updated_rows[1]["vendor_sku"] = "QSC-NANO-2"

    result = service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=updated_rows,
    )
    comparison = result["version"]["comparison_summary"]

    assert comparison["price_increased"]
    assert comparison["price_decreased"]
    assert comparison["lead_time_changed"]
    assert comparison["availability_changed"]
    assert comparison["vendor_sku_changed"]


def test_historical_pricing_preservation_and_price_history_navigation() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(cost_a=100.0),
    )
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=_rows(cost_a=120.0),
    )

    history = service.price_history_for_product("QSC::Core110f")
    assert len(history["historical_prices"]) == 2
    assert history["price_trend"] == "up"
    assert history["known_vendors"] == ["AV Partner"]


def test_product_removal_detection_and_lifecycle_transition() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=[_rows()[0]],
    )

    state = service.to_dict()
    lifecycle = state["product_lifecycle"]["QSC::CoreNano"]["lifecycle_status"]
    assert (
        lifecycle
        == CommercialProductLifecycleStatus.MISSING_FROM_LATEST_PRICE_SHEET.value
    )


def test_stale_pricing_detection_and_knowledge_freshness() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )

    stale_date = datetime(2020, 1, 1, tzinfo=UTC).replace(microsecond=0).isoformat()
    state = service.to_dict()
    state["product_history"]["QSC::Core110f"]["last_updated"] = stale_date

    stale_service = CommercialKnowledgeService(state=state)
    freshness = {item["product"]: item for item in stale_service.freshness_rows()}

    assert freshness["QSC::Core110f"]["current_status"] == "stale"


def test_import_history_and_change_report_exist_after_imports() -> None:
    service = CommercialKnowledgeService()

    first = service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )
    assert first["change_report"]["version_id"]

    second = service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=[_rows()[0]],
    )

    history = service.import_history_rows()
    assert len(history) == 2
    assert history[0]["source_filename"] in {"qsc_v2.csv", "qsc_v1.csv"}
    assert second["change_report"]["products_removed"] == ["QSC::CoreNano"]


def test_dashboard_summary_includes_required_commercial_metrics() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="AV Partner",
        manufacturer="QSC",
        sheet_name="QSC Price Sheet",
        description="Primary",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=_rows(),
    )

    dashboard = service.dashboard_summary()
    assert dashboard["manufacturers"] == 1
    assert dashboard["vendors"] == 1
    assert dashboard["products"] >= 1
    assert "coverage_percentage" in dashboard
    assert "commercial_confidence" in dashboard
