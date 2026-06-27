import pytest

from atlas_core.domain import Invoice, InvoiceLine, InvoiceStatus


def make_line(
    line_id: str = "line-001",
    quantity: float = 2,
    unit_cost: float = 100,
) -> InvoiceLine:
    return InvoiceLine(
        line_id=line_id,
        purchase_order_line_id="po-line-001",
        equipment_id="eq-001",
        description="Display",
        quantity=quantity,
        unit_cost=unit_cost,
    )


def make_invoice(lines: list[InvoiceLine] | None = None) -> Invoice:
    return Invoice(
        invoice_id="inv-001",
        project_id="project-001",
        vendor_id="midwich",
        vendor_name="Midwich",
        purchase_order_id="po-001",
        lines=lines or [],
    )


def test_creating_valid_invoice():
    invoice = Invoice(
        invoice_id=" inv-001 ",
        project_id=" project-001 ",
        vendor_id=" midwich ",
        vendor_name=" Midwich ",
        purchase_order_id=" po-001 ",
        status="received",
        notes=[" Confirm tax. "],
    )

    assert invoice.invoice_id == "inv-001"
    assert invoice.project_id == "project-001"
    assert invoice.vendor_id == "midwich"
    assert invoice.vendor_name == "Midwich"
    assert invoice.purchase_order_id == "po-001"
    assert invoice.status is InvoiceStatus.RECEIVED
    assert isinstance(invoice.created_at, str)
    assert invoice.notes == ["Confirm tax."]


def test_creating_valid_invoice_line():
    line = InvoiceLine(
        line_id=" line-001 ",
        purchase_order_line_id=" po-line-001 ",
        equipment_id=" eq-001 ",
        description=" Display ",
        quantity=2,
        unit_cost=100,
        notes=[" Match packing slip. "],
    )

    assert line.line_id == "line-001"
    assert line.purchase_order_line_id == "po-line-001"
    assert line.equipment_id == "eq-001"
    assert line.description == "Display"
    assert line.quantity == 2
    assert line.unit_cost == 100
    assert line.notes == ["Match packing slip."]


def test_rejecting_blank_vendor_name():
    with pytest.raises(ValueError, match="vendor_name cannot be blank"):
        Invoice(
            invoice_id="inv-001",
            project_id="project-001",
            vendor_id="midwich",
            vendor_name=" ",
        )


def test_rejecting_invalid_line_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        InvoiceLine(
            line_id="line-001",
            description="Display",
            quantity=0,
        )


def test_rejecting_negative_unit_cost():
    with pytest.raises(ValueError, match="unit_cost cannot be negative"):
        InvoiceLine(
            line_id="line-001",
            description="Display",
            unit_cost=-1,
        )


def test_adding_line():
    invoice = make_invoice()
    line = make_line()

    invoice.add_line(line)

    assert invoice.lines == [line]


def test_receiving_invoice():
    invoice = make_invoice()

    invoice.receive()

    assert invoice.status is InvoiceStatus.RECEIVED
    assert isinstance(invoice.received_at, str)


def test_approving_invoice():
    invoice = make_invoice()

    invoice.approve()

    assert invoice.status is InvoiceStatus.APPROVED
    assert isinstance(invoice.approved_at, str)


def test_disputing_invoice_with_note():
    invoice = make_invoice()

    invoice.dispute(" Freight charge mismatch. ")

    assert invoice.status is InvoiceStatus.DISPUTED
    assert invoice.notes == ["Freight charge mismatch."]


def test_paying_invoice():
    invoice = make_invoice()

    invoice.pay()

    assert invoice.status is InvoiceStatus.PAID
    assert isinstance(invoice.paid_at, str)


def test_voiding_invoice():
    invoice = make_invoice()

    invoice.void()

    assert invoice.status is InvoiceStatus.VOID


def test_total_cost():
    invoice = make_invoice(
        lines=[
            make_line(line_id="line-001", quantity=2, unit_cost=100),
            make_line(line_id="line-002", quantity=3, unit_cost=50),
        ]
    )

    assert invoice.total_cost() == 350


def test_to_dict_output():
    line = make_line(quantity=2, unit_cost=100)
    invoice = Invoice(
        invoice_id="inv-001",
        project_id="project-001",
        vendor_id="midwich",
        vendor_name="Midwich",
        purchase_order_id="po-001",
        status=InvoiceStatus.APPROVED,
        lines=[line],
        received_at="2026-06-27T12:30:00",
        approved_at="2026-06-27T12:45:00",
        paid_at="2026-06-28T09:00:00",
        created_at="2026-06-27T12:00:00",
        notes=["Confirm tax."],
    )

    assert invoice.to_dict() == {
        "invoice_id": "inv-001",
        "project_id": "project-001",
        "vendor_id": "midwich",
        "vendor_name": "Midwich",
        "purchase_order_id": "po-001",
        "status": "approved",
        "lines": [line.to_dict()],
        "received_at": "2026-06-27T12:30:00",
        "approved_at": "2026-06-27T12:45:00",
        "paid_at": "2026-06-28T09:00:00",
        "created_at": "2026-06-27T12:00:00",
        "notes": ["Confirm tax."],
    }
