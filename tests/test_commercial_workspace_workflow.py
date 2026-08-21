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
    "commercial_workspace_workflow_tests",
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
        return []

    def list_vendor_bills(self, **kwargs: Any) -> list[Any]:
        self._record("list_vendor_bills", **kwargs)
        return []


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
                        "counts_by_status": {"draft": 1},
                    },
                    "sales_order_backlog": {
                        "total_count": 1,
                        "backlog_count": 1,
                        "backlog_amount": "2000.00",
                    },
                    "invoice_statuses": {
                        "total_count": 0,
                        "counts_by_status": {},
                        "total_amount": "0.00",
                    },
                    "vendor_bill_statuses": {
                        "total_count": 0,
                        "counts_by_status": {},
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
        return self._ok({"reservations": []})

    def create_customer_account(self, request: Any) -> SimpleNamespace:
        self._record("create_customer_account", request)
        maybe_error = self._maybe_error("create_customer_account")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"customer_account": {"customer_id": request.customer_id}})

    def create_opportunity(self, request: Any) -> SimpleNamespace:
        self._record("create_opportunity", request)
        maybe_error = self._maybe_error("create_opportunity")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"opportunity": {"opportunity_id": request.opportunity_id}})

    def create_estimate(self, request: Any) -> SimpleNamespace:
        self._record("create_estimate", request)
        maybe_error = self._maybe_error("create_estimate")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"estimate": {"estimate_id": request.estimate_id}})

    def add_estimate_line_item(self, request: Any) -> SimpleNamespace:
        self._record("add_estimate_line_item", request)
        maybe_error = self._maybe_error("add_estimate_line_item")
        if maybe_error is not None:
            return maybe_error
        return self._ok({"estimate": {"estimate_id": request.estimate_id}})

    def remove_estimate_line_item(self, request: Any) -> SimpleNamespace:
        self._record("remove_estimate_line_item", request)
        return self._ok({"estimate": {"estimate_id": request.estimate_id}})

    def create_proposal_for_estimate(self, request: Any) -> SimpleNamespace:
        self._record("create_proposal_for_estimate", request)
        return self._ok({"proposal": {"proposal_id": "prop-1", "status": "draft"}})

    def mark_proposal_ready(self, request: Any) -> SimpleNamespace:
        self._record("mark_proposal_ready", request)
        return self._ok(
            {"proposal": {"proposal_id": request.proposal_id, "status": "ready"}}
        )

    def send_proposal(self, request: Any) -> SimpleNamespace:
        self._record("send_proposal", request)
        return self._ok(
            {"proposal": {"proposal_id": request.proposal_id, "status": "sent"}}
        )

    def accept_proposal(self, request: Any) -> SimpleNamespace:
        self._record("accept_proposal", request)
        return self._ok(
            {"proposal": {"proposal_id": request.proposal_id, "status": "accepted"}}
        )

    def convert_accepted_estimate_to_sales_order(self, request: Any) -> SimpleNamespace:
        self._record("convert_accepted_estimate_to_sales_order", request)
        return self._ok({"sales_order": {"sales_order_id": "so-1", "status": "open"}})


def _services(*, errors: set[str] | None = None) -> CommercialWorkspaceServices:
    return CommercialWorkspaceServices(
        facade=cast(Any, _FakeFacade()),
        boundary=cast(Any, _FakeBoundary(errors=errors)),
        tenant_context=CommercialMvpTenantContext(
            tenant_id="tenant-a",
            organization_id="org-1",
        ),
    )


def _render(
    *,
    pressed: set[str] | None = None,
    text_values: dict[str, str] | None = None,
    errors: set[str] | None = None,
) -> tuple[_FakeStreamlit, _FakeFacade, _FakeBoundary]:
    st = _FakeStreamlit(pressed=pressed, text_values=text_values)
    services = _services(errors=errors)
    app.render_commercial_workspace_page(
        st,
        None,
        tenant_id="tenant-a",
        organization_id="org-1",
        services=services,
    )
    return st, cast(Any, services.facade), cast(Any, services.boundary)


def test_estimate_subtotal_and_sales_order_status_render() -> None:
    st, _, _ = _render()

    assert "Estimate subtotal: $2,000.00" in st.captions
    assert "Selected sales order status: open" in st.captions


def test_workflow_controls_call_boundary_and_render_successes() -> None:
    st, facade, boundary = _render(
        pressed={
            "Create Customer / Account",
            "Create Opportunity",
            "Create Estimate",
            "Add Line Item",
            "Remove Line Item",
            "Mark Ready",
            "Send",
            "Accept",
            "Convert to Sales Order",
        },
        text_values={
            "Customer ID": "customer-new",
            "Name": "New Customer",
            "Opportunity ID": "opp-new",
            "Opportunity Name": "New Opportunity",
            "Estimated Value": "15000.00",
            "Close Date": "2026-08-21",
            "Estimate ID": "est-new",
            "Proposal ID": "prop-new",
            "Line Item ID": "line-new",
            "Description": "Display package",
            "Quantity": "2",
            "Unit Price": "1000.00",
            "Catalog Item ID": "cat-new",
            "Notes": "Initial notes",
            "Line Notes": "Line note",
        },
    )

    assert any(name == "create_customer_account" for name, _ in boundary.calls)
    assert any(name == "create_opportunity" for name, _ in boundary.calls)
    assert any(name == "create_estimate" for name, _ in boundary.calls)
    assert any(name == "add_estimate_line_item" for name, _ in boundary.calls)
    assert any(name == "remove_estimate_line_item" for name, _ in boundary.calls)
    assert any(name == "mark_proposal_ready" for name, _ in boundary.calls)
    assert any(name == "send_proposal" for name, _ in boundary.calls)
    assert any(name == "accept_proposal" for name, _ in boundary.calls)
    assert any(
        name == "convert_accepted_estimate_to_sales_order" for name, _ in boundary.calls
    )
    assert "Customer / account created." in st.successes
    assert "Opportunity created." in st.successes
    assert "Estimate created." in st.successes
    assert "Estimate line item added." in st.successes
    assert "Estimate line item removed." in st.successes
    assert "Proposal marked ready." in st.successes
    assert "Proposal sent." in st.successes
    assert "Proposal accepted." in st.successes
    assert "Sales order created." in st.successes
    assert any(title == "list_customer_accounts" for title, _ in facade.calls)


def test_validation_errors_render_deterministically() -> None:
    st, _, boundary = _render(
        pressed={"Create Customer / Account"},
        text_values={"Customer ID": "customer-new", "Name": "New Customer"},
        errors={"create_customer_account"},
    )

    assert any(name == "create_customer_account" for name, _ in boundary.calls)
    assert (
        st.errors and st.errors[0] == "validation_error: create_customer_account failed"
    )
