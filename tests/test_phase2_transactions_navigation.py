from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_transactions_nav_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def test_transactions_workspace_contract_has_expected_sections() -> None:
    contract = app._workspace_navigation_contract("Transactions", "application")

    secondary_keys = [item["secondary_key"] for item in contract]
    assert secondary_keys == [
        "overview",
        "estimates",
        "sales_orders",
        "purchase_orders",
        "rfqs",
        "vendor_quotes",
        "receiving",
        "vendor_bills",
        "customer_invoices",
        "change_orders",
    ]

    estimate_section = next(
        item for item in contract if item["secondary_key"] == "estimates"
    )
    tertiary_keys = [
        entry["tertiary_key"]
        for entry in estimate_section.get("supported_tertiary_actions", [])
    ]
    assert tertiary_keys == [
        "add",
        "browse",
        "edit",
        "customer_view",
        "internal_view",
        "revisions",
        "issue",
        "accept",
        "decline",
        "related_documents",
        "activity",
        "export",
    ]

    sales_order_section = next(
        item for item in contract if item["secondary_key"] == "sales_orders"
    )
    sales_order_actions = [
        entry["tertiary_key"]
        for entry in sales_order_section.get("supported_tertiary_actions", [])
    ]
    assert sales_order_actions == [
        "add",
        "browse",
        "edit",
        "lines",
        "demand",
        "fulfillment",
        "related_documents",
        "activity",
        "export",
    ]


def test_transactions_page_is_primary_workspace() -> None:
    assert app._active_primary_workspace("Transactions", None) == "Transactions"
    assert app._active_workspace_mode("Transactions", None) == "application"


def test_transactions_object_workspace_routes_and_adapter_keys() -> None:
    assert app._selection_route("estimate") == "Object Workspace"
    assert app._selection_route("purchase_order") == "Object Workspace"
    assert app._universal_object_adapter_key("request_for_quote") == "rfq"
    assert app._universal_object_adapter_key("receiving") == "receiving_record"
