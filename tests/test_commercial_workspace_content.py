from __future__ import annotations

from contextlib import contextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Literal, cast

from atlas_core.contracts.commercial_api_contracts import CommercialMvpTenantContext
from atlas_core.ui.commercial_workspace import (
    CommercialWorkspaceServices,
)

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "atlas_core"
    / "ui"
    / "commercial_workspace.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "commercial_workspace_content_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def _response(payload: dict[str, Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(ok=True, payload=payload or {}, error=None)


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.columns_requested: list[Any] = []
        self.button_calls: list[dict[str, Any]] = []
        self.selectbox_calls: list[dict[str, Any]] = []
        self.text_input_calls: list[dict[str, Any]] = []
        self.text_area_calls: list[dict[str, Any]] = []
        self.form_labels: list[str] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.infos: list[str] = []
        self.rerun_called = False

    def __enter__(self) -> "_FakeStreamlit":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False

    def columns(self, spec: int | list[Any], **kwargs: Any) -> list["_FakeStreamlit"]:
        _ = kwargs
        self.columns_requested.append(spec)
        size = len(spec) if isinstance(spec, list) else spec
        return [self for _ in range(size)]

    def form(self, label: str) -> "_FakeStreamlit":
        self.form_labels.append(label)
        return self

    def form_submit_button(self, label: str, **kwargs: Any) -> bool:
        _ = kwargs
        self.button_calls.append({"label": label, "kind": "form_submit"})
        return False

    def button(self, label: str, **kwargs: Any) -> bool:
        self.button_calls.append({"label": label, **kwargs})
        return False

    def selectbox(
        self, label: str, options: list[Any], index: int = 0, **kwargs: Any
    ) -> Any:
        self.selectbox_calls.append(
            {"label": label, "options": list(options), **kwargs}
        )
        if not options:
            return ""
        if 0 <= index < len(options):
            return options[index]
        return options[0]

    def text_input(self, label: str, **kwargs: Any) -> str:
        self.text_input_calls.append({"label": label, **kwargs})
        return str(kwargs.get("value") or "")

    def text_area(self, label: str, **kwargs: Any) -> str:
        self.text_area_calls.append({"label": label, **kwargs})
        return str(kwargs.get("value") or "")

    def markdown(self, text: str, **kwargs: Any) -> None:
        _ = kwargs
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def rerun(self) -> None:
        self.rerun_called = True


class _FakeFacade:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))

    def _row(self, **values: Any) -> SimpleNamespace:
        return SimpleNamespace(**values)

    def list_customer_accounts(self, **kwargs: Any) -> list[Any]:
        self._record("list_customer_accounts", **kwargs)
        return [
            self._row(
                customer_id="customer-1",
                name="Acme Integrators",
                account_number="A-1",
                billing_email="ap@acme.example",
                active=True,
            )
        ]

    def list_opportunities(self, **kwargs: Any) -> list[Any]:
        self._record("list_opportunities", **kwargs)
        return [
            self._row(
                opportunity_id="opp-1",
                customer_id="customer-1",
                name="Conference room refresh",
                status="open",
                estimated_value="12500.00",
            )
        ]

    def list_estimates(self, **kwargs: Any) -> list[Any]:
        self._record("list_estimates", **kwargs)
        return [
            self._row(
                estimate_id="est-1",
                customer_id="customer-1",
                opportunity_id="opp-1",
                proposal_id="prop-1",
                line_items=[
                    {
                        "line_item_id": "est-1-line-1",
                        "description": "Display package",
                        "quantity": "2",
                        "unit_price": "1000.00",
                    }
                ],
            )
        ]

    def list_proposals(self, **kwargs: Any) -> list[Any]:
        self._record("list_proposals", **kwargs)
        return [
            self._row(
                proposal_id="prop-1",
                estimate_id="est-1",
                customer_id="customer-1",
                status="draft",
                sent_at="",
                responded_at="",
            )
        ]

    def list_sales_orders(self, **kwargs: Any) -> list[Any]:
        self._record("list_sales_orders", **kwargs)
        return [
            self._row(
                sales_order_id="so-1",
                estimate_id="est-1",
                proposal_id="prop-1",
                customer_id="customer-1",
                status="open",
                line_items=[
                    {
                        "line_item_id": "so-1-line-1",
                        "description": "Display package",
                        "quantity": "2",
                        "unit_price": "1000.00",
                    }
                ],
            )
        ]

    def list_customer_invoices(self, **kwargs: Any) -> list[Any]:
        self._record("list_customer_invoices", **kwargs)
        return [
            self._row(
                customer_invoice_id="ci-1",
                sales_order_id="so-1",
                customer_id="customer-1",
                status="draft",
                quickbooks_sync_reference={"status": "pending"},
                line_items=[],
            )
        ]

    def list_vendor_bills(self, **kwargs: Any) -> list[Any]:
        self._record("list_vendor_bills", **kwargs)
        return [
            self._row(
                vendor_bill_id="vb-1",
                vendor_id="vendor-1",
                vendor_name="AV Partner",
                status="draft",
                quickbooks_sync_reference={"status": "pending"},
                line_items=[],
            )
        ]


class _FakeBoundary:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def get_commercial_reporting_snapshot(self, request: Any) -> SimpleNamespace:
        self.calls.append(("get_commercial_reporting_snapshot", request))
        return _response(
            {
                "snapshot": {
                    "estimate_pipeline": {
                        "total_estimates": 1,
                        "counts_by_stage": {"draft": 1},
                        "total_estimate_value": "2000.00",
                    },
                    "proposal_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"draft": 1},
                    },
                    "sales_order_backlog": {
                        "total_count": 1,
                        "backlog_count": 1,
                        "backlog_amount": "2000.00",
                    },
                    "invoice_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"draft": 1},
                        "total_amount": "0.00",
                    },
                    "vendor_bill_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"draft": 1},
                        "total_amount": "0.00",
                    },
                    "inventory_availability": {
                        "total_positions": 1,
                        "total_on_hand": "5",
                        "total_reserved": "1",
                        "total_available": "4",
                    },
                    "quickbooks_sync": {
                        "total_references": 2,
                        "counts_by_status": {"pending": 2},
                    },
                }
            }
        )

    def check_inventory_availability(self, request: Any) -> SimpleNamespace:
        self.calls.append(("check_inventory_availability", request))
        return _response(
            {
                "sales_order_id": request.sales_order_id,
                "availability": [
                    {
                        "sales_order_id": request.sales_order_id,
                        "sales_order_line_item_id": "so-1-line-1",
                        "catalog_item_id": "cat-1",
                        "requested_quantity": "2",
                        "available_quantity": "5",
                        "selected_location_id": "loc-1",
                        "selected_position_id": "pos-1",
                        "can_reserve": True,
                    }
                ],
            }
        )

    def reserve_inventory(self, request: Any) -> SimpleNamespace:
        self.calls.append(("reserve_inventory", request))
        return _response(
            {
                "sales_order_id": request.sales_order_id,
                "reservations": [{"reservation_id": "res-1"}],
            }
        )

    def __getattr__(self, name: str):
        def _handler(request: Any) -> SimpleNamespace:
            self.calls.append((name, request))
            return _response({})

        return _handler


def test_commercial_workspace_renders_all_minimal_panels(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_facade = _FakeFacade()
    fake_boundary = _FakeBoundary()
    services = CommercialWorkspaceServices(
        facade=cast(Any, fake_facade),
        boundary=cast(Any, fake_boundary),
        tenant_context=CommercialMvpTenantContext(
            tenant_id="tenant-a",
            organization_id="org-1",
        ),
    )

    page_headers: list[tuple[str, str]] = []
    section_cards: list[tuple[str, str]] = []
    report_tables: list[list[dict[str, Any]]] = []
    empty_states: list[dict[str, Any]] = []

    monkeypatch.setattr(
        app,
        "_shared_render_page_header",
        lambda _st, title, subtitle: page_headers.append((title, subtitle)),
    )

    @contextmanager
    def fake_section_card(st: Any, title: str, subtitle: str = ""):
        _ = st
        section_cards.append((title, subtitle))
        yield

    monkeypatch.setattr(app, "_shared_render_section_card", fake_section_card)
    monkeypatch.setattr(
        app,
        "_shared_render_report_table",
        lambda _st, rows: report_tables.append(list(rows)),
    )
    monkeypatch.setattr(
        app,
        "_shared_render_guided_empty_state",
        lambda _st, **kwargs: empty_states.append(dict(kwargs)),
    )

    app.render_commercial_workspace_page(
        fake_st,
        None,
        tenant_id="tenant-a",
        organization_id="org-1",
        services=services,
    )

    assert page_headers == [
        (
            "Sales",
            "Manage the path from opportunity and estimate through sales order, inventory, invoice, and vendor bill.",
        )
    ]
    assert [title for title, _ in section_cards] == [
        "Needs Attention",
        "Sales Pipeline",
        "Estimates",
        "Sales Orders and Invoices",
        "Inventory",
        "Vendor Bills and QuickBooks Status",
        "Customers",
    ]

    visible_copy = " ".join(
        [
            *(text for header in page_headers for text in header),
            *(text for section in section_cards for text in section),
            *fake_st.captions,
            *fake_st.markdowns,
        ]
    ).lower()
    for internal_phrase in (
        "tenant-scoped",
        "organization atlas",
        "quickbooks sync state",
        "commercial mvp",
    ):
        assert internal_phrase not in visible_copy

    assert any(title == "list_customer_accounts" for title, _ in fake_facade.calls)
    assert any(title == "list_opportunities" for title, _ in fake_facade.calls)
    assert any(title == "list_estimates" for title, _ in fake_facade.calls)
    assert any(title == "list_sales_orders" for title, _ in fake_facade.calls)
    assert any(title == "list_customer_invoices" for title, _ in fake_facade.calls)
    assert any(title == "list_vendor_bills" for title, _ in fake_facade.calls)
    assert {
        name: sum(call_name == name for call_name, _ in fake_facade.calls)
        for name in {
            "list_customer_accounts",
            "list_opportunities",
            "list_estimates",
            "list_proposals",
            "list_sales_orders",
            "list_customer_invoices",
            "list_vendor_bills",
        }
    } == {
        "list_customer_accounts": 1,
        "list_opportunities": 1,
        "list_estimates": 1,
        "list_proposals": 1,
        "list_sales_orders": 1,
        "list_customer_invoices": 1,
        "list_vendor_bills": 1,
    }

    inventory_call = next(
        request
        for name, request in fake_boundary.calls
        if name == "check_inventory_availability"
    )
    assert inventory_call.sales_order_id == "so-1"

    snapshot_rows = next(
        rows
        for rows in report_tables
        if rows and rows[0].get("Summary") == "Estimates in Progress"
    )
    assert {row["Summary"] for row in snapshot_rows} == {
        "Estimates in Progress",
        "Proposals",
        "Sales Orders",
        "Invoices",
        "Vendor Bills",
        "Inventory",
        "QuickBooks Status",
    }
    assert any(
        row.get("Customer ID") == "customer-1"
        for table in report_tables
        for row in table
    )
    assert any(
        row.get("Opportunity ID") == "opp-1" for table in report_tables for row in table
    )
    assert any(
        row.get("Estimate ID") == "est-1" for table in report_tables for row in table
    )
    assert any(
        row.get("Sales Order ID") == "so-1" for table in report_tables for row in table
    )
    assert any(
        row.get("Proposal ID") == "prop-1" for table in report_tables for row in table
    )
    assert any(
        row.get("Invoice ID") == "ci-1" for table in report_tables for row in table
    )
    assert any(
        row.get("Vendor Bill ID") == "vb-1" for table in report_tables for row in table
    )
    assert empty_states == []
