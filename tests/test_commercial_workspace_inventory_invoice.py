from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Literal, cast

from atlas_core.contracts.commercial_api_contracts import CommercialMvpTenantContext
from atlas_core.ui.commercial_workspace import CommercialWorkspaceServices

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "atlas_core"
    / "ui"
    / "commercial_workspace.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "commercial_workspace_inventory_invoice_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def _response(
    *,
    ok: bool = True,
    payload: dict[str, Any] | None = None,
    code: str = "validation_error",
    message: str = "Validation failed",
) -> SimpleNamespace:
    error = None if ok else SimpleNamespace(code=code, field=None, message=message)
    return SimpleNamespace(ok=ok, payload=payload or {}, error=error)


class _FakeStreamlit:
    def __init__(
        self,
        *,
        pressed: set[str] | None = None,
        text_values: dict[str, str] | None = None,
    ) -> None:
        self.session_state: dict[str, Any] = {}
        self.pressed = set(pressed or set())
        self.text_values = dict(text_values or {})
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
        self.dataframes: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []
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

    def container(self, border: bool = False) -> "_FakeStreamlit":
        _ = border
        return self

    def form(self, label: str) -> "_FakeStreamlit":
        self.form_labels.append(label)
        return self

    def form_submit_button(self, label: str, **kwargs: Any) -> bool:
        _ = kwargs
        self.button_calls.append({"label": label, "kind": "form_submit"})
        return label in self.pressed

    def button(self, label: str, **kwargs: Any) -> bool:
        self.button_calls.append({"label": label, **kwargs})
        key = kwargs.get("key")
        return label in self.pressed or (isinstance(key, str) and key in self.pressed)

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
        if label in self.text_values:
            return self.text_values[label]
        return str(kwargs.get("value") or "")

    def text_area(self, label: str, **kwargs: Any) -> str:
        self.text_area_calls.append({"label": label, **kwargs})
        if label in self.text_values:
            return self.text_values[label]
        return str(kwargs.get("value") or "")

    def markdown(self, text: str, **kwargs: Any) -> None:
        _ = kwargs
        self.markdowns.append(text)

    def subheader(self, text: str) -> None:
        self.markdowns.append(f"SUBHEADER: {text}")

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def dataframe(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        self.dataframes.append((rows, kwargs))

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
                status="accepted",
                sent_at="2026-08-21T10:00:00Z",
                responded_at="2026-08-21T11:00:00Z",
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
                line_items=[
                    {
                        "line_item_id": "ci-1-line-1",
                        "description": "Display package",
                        "quantity": "2",
                        "unit_price": "1000.00",
                    }
                ],
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
                line_items=[
                    {
                        "line_item_id": "vb-1-line-1",
                        "description": "Mounting hardware",
                        "quantity": "5",
                        "unit_price": "125.00",
                    }
                ],
            )
        ]


class _FakeBoundary:
    def __init__(self, *, errors: set[str] | None = None) -> None:
        self.errors = set(errors or set())
        self.calls: list[tuple[str, Any]] = []

    def _record(self, name: str, request: Any) -> None:
        self.calls.append((name, request))

    def _ok(self, payload: dict[str, Any]) -> SimpleNamespace:
        return _response(payload=payload)

    def _maybe_error(self, name: str) -> SimpleNamespace | None:
        if name in self.errors:
            return _response(ok=False, message=f"{name} failed")
        return None

    def get_commercial_reporting_snapshot(self, request: Any) -> SimpleNamespace:
        self._record("get_commercial_reporting_snapshot", request)
        return self._ok(
            {
                "snapshot": {
                    "estimate_pipeline": {
                        "total_estimates": 1,
                        "counts_by_stage": {"draft": 1},
                        "total_estimate_value": "2000.00",
                    },
                    "proposal_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"accepted": 1},
                    },
                    "sales_order_backlog": {
                        "total_count": 1,
                        "backlog_count": 1,
                        "backlog_amount": "2000.00",
                    },
                    "invoice_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"draft": 1},
                        "total_amount": "2000.00",
                    },
                    "vendor_bill_statuses": {
                        "total_count": 1,
                        "counts_by_status": {"draft": 1},
                        "total_amount": "625.00",
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
        self._record("check_inventory_availability", request)
        return self._ok(
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
        self._record("reserve_inventory", request)
        maybe_error = self._maybe_error("reserve_inventory")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"reservations": []})

    def generate_customer_invoice_from_sales_order(
        self, request: Any
    ) -> SimpleNamespace:
        self._record("generate_customer_invoice_from_sales_order", request)
        maybe_error = self._maybe_error("generate_customer_invoice_from_sales_order")
        if maybe_error is not None:
            return maybe_error
        return self._ok(
            {
                "customer_invoice": {
                    "customer_invoice_id": "ci-1",
                    "sales_order_id": request.sales_order_id,
                    "status": "draft",
                }
            }
        )

    def create_vendor_bill(self, request: Any) -> SimpleNamespace:
        self._record("create_vendor_bill", request)
        maybe_error = self._maybe_error("create_vendor_bill")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"vendor_bill": {"vendor_bill_id": request.vendor_bill_id}})

    def mark_customer_invoice_sync_pending(self, request: Any) -> SimpleNamespace:
        self._record("mark_customer_invoice_sync_pending", request)
        maybe_error = self._maybe_error("mark_customer_invoice_sync_pending")
        if maybe_error is not None:
            return maybe_error
        return self._ok(
            {"customer_invoice": {"customer_invoice_id": request.customer_invoice_id}}
        )

    def mark_vendor_bill_sync_pending(self, request: Any) -> SimpleNamespace:
        self._record("mark_vendor_bill_sync_pending", request)
        maybe_error = self._maybe_error("mark_vendor_bill_sync_pending")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"vendor_bill": {"vendor_bill_id": request.vendor_bill_id}})


def _render(
    *,
    pressed: set[str] | None = None,
    text_values: dict[str, str] | None = None,
    errors: set[str] | None = None,
) -> tuple[_FakeStreamlit, Any, Any]:
    st = _FakeStreamlit(pressed=pressed, text_values=text_values)
    facade = _FakeFacade()
    boundary = _FakeBoundary(errors=errors)
    services = CommercialWorkspaceServices(
        facade=cast(Any, facade),
        boundary=cast(Any, boundary),
        tenant_context=CommercialMvpTenantContext(
            tenant_id="tenant-1",
            organization_id="org-1",
        ),
    )
    app.render_commercial_workspace_page(
        st,
        services=services,
        tenant_id="tenant-1",
        organization_id="org-1",
    )
    return st, facade, boundary


def _find_table(st: _FakeStreamlit, predicate: Any) -> list[dict[str, Any]]:
    for rows, _ in st.dataframes:
        if rows and predicate(rows):
            return rows
    raise AssertionError("expected table not rendered")


def test_inventory_invoice_and_vendor_bill_controls_call_boundary_and_render_successes() -> (
    None
):
    st, facade, boundary = _render(
        pressed={
            "Reserve Inventory",
            "Generate Customer Invoice",
            "Mark Customer Invoice Sync Pending",
            "Create Vendor Bill",
            "Mark Vendor Bill Sync Pending",
        },
        text_values={
            "Vendor Bill ID": "vb-new",
            "Vendor ID": "vendor-new",
            "Vendor Name": "New Vendor",
            "Purchase Order ID": "po-1",
            "Procurement Need ID": "need-1",
            "Entered At": "2026-08-21T12:00:00Z",
            "Due At": "2026-09-21",
            "Line Item ID": "vb-new-line-1",
            "Line Description": "Rack hardware",
            "Quantity": "5",
            "Unit Price": "125.00",
            "Notes": "Initial vendor bill",
        },
    )

    assert [name for name, _ in boundary.calls] == [
        "get_commercial_reporting_snapshot",
        "check_inventory_availability",
        "reserve_inventory",
        "generate_customer_invoice_from_sales_order",
        "mark_customer_invoice_sync_pending",
        "create_vendor_bill",
        "mark_vendor_bill_sync_pending",
    ]
    assert "Inventory reserved." in st.successes
    assert "Customer invoice created." in st.successes
    assert "Customer invoice marked sync pending." in st.successes
    assert "Vendor bill created." in st.successes
    assert "Vendor bill marked sync pending." in st.successes

    inventory_rows = _find_table(
        st, lambda rows: rows[0].get("Sales Order ID") == "so-1"
    )
    assert inventory_rows[0]["Catalog Item ID"] == "cat-1"
    assert inventory_rows[0]["Location"] == "loc-1"
    assert inventory_rows[0]["Can Reserve"] == "Yes"

    invoice_rows = _find_table(st, lambda rows: rows[0].get("Invoice ID") == "ci-1")
    assert invoice_rows[0]["Status"] == "draft"
    assert invoice_rows[0]["Sync"] == "pending"
    assert invoice_rows[0]["Invoice Value"] == "$2,000.00"

    vendor_bill_rows = _find_table(
        st, lambda rows: rows[0].get("Vendor Bill ID") == "vb-1"
    )
    assert vendor_bill_rows[0]["Status"] == "draft"
    assert vendor_bill_rows[0]["Sync"] == "pending"
    assert vendor_bill_rows[0]["Bill Value"] == "$625.00"

    quickbooks_rows = _find_table(
        st, lambda rows: any(row.get("Summary") == "QuickBooks Sync" for row in rows)
    )
    assert (
        next(
            row["Total"]
            for row in quickbooks_rows
            if row["Summary"] == "QuickBooks Sync"
        )
        == "2"
    )


def test_inventory_invoice_and_vendor_bill_validation_errors_render_deterministically() -> (
    None
):
    st, facade, boundary = _render(
        pressed={
            "Reserve Inventory",
            "Generate Customer Invoice",
            "Create Vendor Bill",
        },
        text_values={
            "Vendor Bill ID": "vb-new",
            "Vendor ID": "vendor-new",
            "Vendor Name": "New Vendor",
            "Line Item ID": "vb-new-line-1",
            "Line Description": "Rack hardware",
            "Quantity": "5",
            "Unit Price": "125.00",
        },
        errors={"generate_customer_invoice_from_sales_order", "create_vendor_bill"},
    )

    assert [name for name, _ in boundary.calls] == [
        "get_commercial_reporting_snapshot",
        "check_inventory_availability",
        "reserve_inventory",
        "generate_customer_invoice_from_sales_order",
        "create_vendor_bill",
    ]
    assert "Inventory reserved." in st.successes
    assert (
        "validation_error: generate_customer_invoice_from_sales_order failed"
        in st.errors
    )
    assert "validation_error: create_vendor_bill failed" in st.errors
