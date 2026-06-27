import pytest

from atlas_core.domain import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)


def make_line(
    line_id: str = "line-001",
    quantity: float = 2,
    unit_cost: float = 100,
    received_quantity: float = 0,
) -> PurchaseOrderLine:
    return PurchaseOrderLine(
        line_id=line_id,
        equipment_id="eq-001",
        description="Display",
        quantity=quantity,
        unit_cost=unit_cost,
        received_quantity=received_quantity,
    )


def make_purchase_order(
    lines: list[PurchaseOrderLine] | None = None,
) -> PurchaseOrder:
    return PurchaseOrder(
        purchase_order_id="po-001",
        project_id="project-001",
        vendor_id="midwich",
        vendor_name="Midwich",
        baseline_id="baseline-001",
        lines=lines or [],
    )


def test_creating_valid_po():
    po = PurchaseOrder(
        purchase_order_id=" po-001 ",
        project_id=" project-001 ",
        vendor_id=" midwich ",
        vendor_name=" Midwich ",
        baseline_id=" baseline-001 ",
        status="issued",
        notes=[" Confirm freight. "],
    )

    assert po.purchase_order_id == "po-001"
    assert po.project_id == "project-001"
    assert po.vendor_id == "midwich"
    assert po.vendor_name == "Midwich"
    assert po.baseline_id == "baseline-001"
    assert po.status is PurchaseOrderStatus.ISSUED
    assert isinstance(po.created_at, str)
    assert po.notes == ["Confirm freight."]


def test_creating_valid_po_line():
    line = PurchaseOrderLine(
        line_id=" line-001 ",
        equipment_id=" eq-001 ",
        description=" Display ",
        quantity=2,
        unit_cost=100,
        received_quantity=1,
        notes=[" Order black finish. "],
    )

    assert line.line_id == "line-001"
    assert line.equipment_id == "eq-001"
    assert line.description == "Display"
    assert line.quantity == 2
    assert line.unit_cost == 100
    assert line.received_quantity == 1
    assert line.notes == ["Order black finish."]


def test_rejecting_blank_po_vendor_name():
    with pytest.raises(ValueError, match="vendor_name cannot be blank"):
        PurchaseOrder(
            purchase_order_id="po-001",
            project_id="project-001",
            vendor_id="midwich",
            vendor_name=" ",
        )


def test_rejecting_invalid_line_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        PurchaseOrderLine(
            line_id="line-001",
            description="Display",
            quantity=0,
        )


def test_rejecting_negative_unit_cost():
    with pytest.raises(ValueError, match="unit_cost cannot be negative"):
        PurchaseOrderLine(
            line_id="line-001",
            description="Display",
            unit_cost=-1,
        )


def test_adding_line():
    po = make_purchase_order()
    line = make_line()

    po.add_line(line)

    assert po.lines == [line]


def test_issuing_po():
    po = make_purchase_order()

    po.issue()

    assert po.status is PurchaseOrderStatus.ISSUED
    assert isinstance(po.issued_at, str)


def test_cancelling_po():
    po = make_purchase_order()

    po.cancel()

    assert po.status is PurchaseOrderStatus.CANCELLED


def test_closing_po():
    po = make_purchase_order()

    po.close()

    assert po.status is PurchaseOrderStatus.CLOSED


def test_receiving_partial_line_sets_status_partially_received():
    po = make_purchase_order(lines=[make_line(quantity=2)])

    po.receive_line("line-001", 1)

    assert po.lines[0].received_quantity == 1
    assert po.status is PurchaseOrderStatus.PARTIALLY_RECEIVED


def test_receiving_full_line_sets_status_received():
    po = make_purchase_order(lines=[make_line(quantity=2)])

    po.receive_line("line-001", 2)

    assert po.lines[0].received_quantity == 2
    assert po.status is PurchaseOrderStatus.RECEIVED


def test_total_cost():
    po = make_purchase_order(
        lines=[
            make_line(line_id="line-001", quantity=2, unit_cost=100),
            make_line(line_id="line-002", quantity=3, unit_cost=50),
        ]
    )

    assert po.total_cost() == 350


def test_to_dict_output():
    line = make_line(quantity=2, unit_cost=100, received_quantity=1)
    po = PurchaseOrder(
        purchase_order_id="po-001",
        project_id="project-001",
        vendor_id="midwich",
        vendor_name="Midwich",
        baseline_id="baseline-001",
        status=PurchaseOrderStatus.PARTIALLY_RECEIVED,
        lines=[line],
        issued_at="2026-06-27T12:30:00",
        created_at="2026-06-27T12:00:00",
        notes=["Confirm freight."],
    )

    assert po.to_dict() == {
        "purchase_order_id": "po-001",
        "project_id": "project-001",
        "vendor_id": "midwich",
        "vendor_name": "Midwich",
        "baseline_id": "baseline-001",
        "status": "partially_received",
        "lines": [line.to_dict()],
        "issued_at": "2026-06-27T12:30:00",
        "created_at": "2026-06-27T12:00:00",
        "notes": ["Confirm freight."],
    }
