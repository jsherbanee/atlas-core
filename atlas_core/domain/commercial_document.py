"""Shared commercial document domain models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or None


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("value must be a dictionary when provided")
    return dict(value)


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("value must be a list when provided")
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("list items must be dictionaries")
        normalized.append(dict(item))
    return normalized


def _decimal(field_name: str, value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal value") from exc


def _decimal_non_negative(field_name: str, value: Any) -> Decimal:
    parsed = _decimal(field_name, value)
    if parsed < Decimal("0"):
        raise ValueError(f"{field_name} cannot be negative")
    return parsed


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class CommercialDocumentType(str, Enum):
    ESTIMATE = "estimate"
    PROPOSAL = "proposal"
    SALES_ORDER = "sales_order"
    PURCHASE_ORDER = "purchase_order"
    RFQ = "rfq"
    VENDOR_QUOTE = "vendor_quote"
    RECEIVING_RECORD = "receiving_record"
    VENDOR_BILL = "vendor_bill"
    CUSTOMER_INVOICE = "customer_invoice"
    CHANGE_ORDER = "change_order"


class CommercialDocumentLifecycleState(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ISSUED = "issued"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ApprovalState(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SyncDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class SyncStatus(str, Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    SYNCED = "synced"
    FAILED = "failed"


COMMERCIAL_DOCUMENT_LIFECYCLE_TRANSITIONS: dict[
    CommercialDocumentLifecycleState, set[CommercialDocumentLifecycleState]
] = {
    CommercialDocumentLifecycleState.DRAFT: {
        CommercialDocumentLifecycleState.IN_REVIEW,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.IN_REVIEW: {
        CommercialDocumentLifecycleState.DRAFT,
        CommercialDocumentLifecycleState.APPROVED,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.APPROVED: {
        CommercialDocumentLifecycleState.IN_REVIEW,
        CommercialDocumentLifecycleState.ISSUED,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.ISSUED: {
        CommercialDocumentLifecycleState.PARTIALLY_FULFILLED,
        CommercialDocumentLifecycleState.FULFILLED,
        CommercialDocumentLifecycleState.CLOSED,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.PARTIALLY_FULFILLED: {
        CommercialDocumentLifecycleState.FULFILLED,
        CommercialDocumentLifecycleState.CLOSED,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.FULFILLED: {
        CommercialDocumentLifecycleState.CLOSED,
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.CLOSED: {
        CommercialDocumentLifecycleState.ARCHIVED,
    },
    CommercialDocumentLifecycleState.ARCHIVED: set(),
}


@dataclass
class CommercialDocumentDiagnostic:
    code: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.code = _required_text("code", self.code)
        self.message = _required_text("message", self.message)
        if not isinstance(self.severity, DiagnosticSeverity):
            self.severity = DiagnosticSeverity(self.severity)
        self.details = dict(self.details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "details": dict(self.details),
        }


@dataclass
class CommercialDocumentSyncMetadata:
    integration: str = "quickbooks"
    status: SyncStatus = SyncStatus.NOT_READY
    direction: SyncDirection = SyncDirection.OUTBOUND
    external_object_type: str | None = None
    external_id: str | None = None
    external_revision: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    retry_count: int = 0
    source_hash: str | None = None
    reconciliation_state: str | None = None

    def __post_init__(self) -> None:
        self.integration = _required_text("integration", self.integration).lower()
        if self.integration != "quickbooks":
            raise ValueError("integration must be quickbooks")
        if not isinstance(self.status, SyncStatus):
            self.status = SyncStatus(self.status)
        if not isinstance(self.direction, SyncDirection):
            self.direction = SyncDirection(self.direction)
        self.external_object_type = _optional_text(self.external_object_type)
        self.external_id = _optional_text(self.external_id)
        self.external_revision = _optional_text(self.external_revision)
        self.last_attempt_at = _optional_text(self.last_attempt_at)
        self.last_success_at = _optional_text(self.last_success_at)
        self.failure_code = _optional_text(self.failure_code)
        self.failure_message = _optional_text(self.failure_message)
        self.source_hash = _optional_text(self.source_hash)
        self.reconciliation_state = _optional_text(self.reconciliation_state)
        self.retry_count = int(self.retry_count)
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration": self.integration,
            "status": self.status.value,
            "direction": self.direction.value,
            "external_object_type": self.external_object_type,
            "external_id": self.external_id,
            "external_revision": self.external_revision,
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "retry_count": self.retry_count,
            "source_hash": self.source_hash,
            "reconciliation_state": self.reconciliation_state,
        }


@dataclass
class CommercialDocumentLineItem:
    line_id: str
    sequence: int
    description: str
    quantity: Decimal = Decimal("0")
    unit_of_measure: str | None = None
    unit_price: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    project_code: str | None = None
    source_document_id: str | None = None
    source_line_id: str | None = None
    related_document_id: str | None = None
    related_line_id: str | None = None
    product_or_service_reference: str | None = None
    fulfillment_state: str | None = None
    accounting_sync_reference: str | None = None

    def __post_init__(self) -> None:
        self.line_id = _required_text("line_id", self.line_id)
        self.sequence = int(self.sequence)
        if self.sequence <= 0:
            raise ValueError("sequence must be greater than 0")
        self.description = _required_text("description", self.description)
        self.quantity = _decimal_non_negative("quantity", self.quantity)
        self.unit_price = _decimal_non_negative("unit_price", self.unit_price)
        self.unit_cost = _decimal_non_negative("unit_cost", self.unit_cost)
        self.discount = _decimal_non_negative("discount", self.discount)
        self.tax_rate = _decimal_non_negative("tax_rate", self.tax_rate)
        self.unit_of_measure = _optional_text(self.unit_of_measure)
        self.project_code = _optional_text(self.project_code)
        self.source_document_id = _optional_text(self.source_document_id)
        self.source_line_id = _optional_text(self.source_line_id)
        self.related_document_id = _optional_text(self.related_document_id)
        self.related_line_id = _optional_text(self.related_line_id)
        self.product_or_service_reference = _optional_text(
            self.product_or_service_reference
        )
        self.fulfillment_state = _optional_text(self.fulfillment_state)
        self.accounting_sync_reference = _optional_text(self.accounting_sync_reference)

    @property
    def extended_amount(self) -> Decimal:
        return (self.quantity * self.unit_price) - self.discount

    @property
    def tax_amount(self) -> Decimal:
        return self.extended_amount * self.tax_rate

    @property
    def total_amount(self) -> Decimal:
        return self.extended_amount + self.tax_amount

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "sequence": self.sequence,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_of_measure": self.unit_of_measure,
            "unit_price": str(self.unit_price),
            "unit_cost": str(self.unit_cost),
            "discount": str(self.discount),
            "tax_rate": str(self.tax_rate),
            "extended_amount": str(self.extended_amount),
            "project_code": self.project_code,
            "source_document_id": self.source_document_id,
            "source_line_id": self.source_line_id,
            "related_document_id": self.related_document_id,
            "related_line_id": self.related_line_id,
            "product_or_service_reference": self.product_or_service_reference,
            "fulfillment_state": self.fulfillment_state,
            "accounting_sync_reference": self.accounting_sync_reference,
        }


@dataclass
class CommercialDocumentRelationship:
    relationship_id: str
    relationship_type: str
    related_document_id: str
    related_line_id: str | None = None
    source_line_id: str | None = None

    def __post_init__(self) -> None:
        self.relationship_id = _required_text("relationship_id", self.relationship_id)
        self.relationship_type = _required_text(
            "relationship_type", self.relationship_type
        )
        self.related_document_id = _required_text(
            "related_document_id", self.related_document_id
        )
        self.related_line_id = _optional_text(self.related_line_id)
        self.source_line_id = _optional_text(self.source_line_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type,
            "related_document_id": self.related_document_id,
            "related_line_id": self.related_line_id,
            "source_line_id": self.source_line_id,
        }


@dataclass
class CommercialDocumentTotals:
    currency: str = "USD"
    subtotal: Decimal = Decimal("0")
    discount_total: Decimal = Decimal("0")
    tax_total: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.currency = _required_text("currency", self.currency).upper()
        self.subtotal = _decimal_non_negative("subtotal", self.subtotal)
        self.discount_total = _decimal_non_negative(
            "discount_total", self.discount_total
        )
        self.tax_total = _decimal_non_negative("tax_total", self.tax_total)
        self.grand_total = _decimal_non_negative("grand_total", self.grand_total)

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "subtotal": str(self.subtotal),
            "discount_total": str(self.discount_total),
            "tax_total": str(self.tax_total),
            "grand_total": str(self.grand_total),
        }

    @classmethod
    def from_lines(
        cls,
        lines: list[CommercialDocumentLineItem],
        *,
        currency: str = "USD",
    ) -> "CommercialDocumentTotals":
        subtotal = sum(
            (line.quantity * line.unit_price for line in lines), Decimal("0")
        )
        discount_total = sum((line.discount for line in lines), Decimal("0"))
        tax_total = sum((line.tax_amount for line in lines), Decimal("0"))
        grand_total = (subtotal - discount_total) + tax_total
        return cls(
            currency=currency,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )


@dataclass
class CommercialDocumentRevision:
    revision_id: str
    revision_number: int
    lifecycle_state: CommercialDocumentLifecycleState
    approval_state: ApprovalState
    revision_label: str | None = None
    revision_reason: str | None = None
    revision_date: str = field(default_factory=_utc_now)
    parent_revision_id: str | None = None
    superseded_by_revision_id: str | None = None
    superseded_at: str | None = None
    is_current: bool = True
    is_archived: bool = False
    archived_at: str | None = None
    created_by: str | None = None
    issued_at: str | None = None
    immutable: bool = False
    notes: str | None = None
    lines: list[CommercialDocumentLineItem] = field(default_factory=list)
    totals: CommercialDocumentTotals = field(default_factory=CommercialDocumentTotals)
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.revision_id = _required_text("revision_id", self.revision_id)
        self.revision_number = int(self.revision_number)
        if self.revision_number <= 0:
            raise ValueError("revision_number must be greater than 0")
        if not isinstance(self.lifecycle_state, CommercialDocumentLifecycleState):
            self.lifecycle_state = CommercialDocumentLifecycleState(
                self.lifecycle_state
            )
        if not isinstance(self.approval_state, ApprovalState):
            self.approval_state = ApprovalState(self.approval_state)
        self.revision_label = _optional_text(self.revision_label)
        self.revision_reason = _optional_text(self.revision_reason)
        self.parent_revision_id = _optional_text(self.parent_revision_id)
        self.superseded_by_revision_id = _optional_text(self.superseded_by_revision_id)
        self.superseded_at = _optional_text(self.superseded_at)
        self.archived_at = _optional_text(self.archived_at)
        self.created_by = _optional_text(self.created_by)
        self.issued_at = _optional_text(self.issued_at)
        self.notes = _optional_text(self.notes)
        if self.revision_reason is None and self.notes is not None:
            self.revision_reason = self.notes
        if self.notes is None and self.revision_reason is not None:
            self.notes = self.revision_reason
        self.revision_date = _required_text("revision_date", self.revision_date)
        self.lines = [
            (
                line
                if isinstance(line, CommercialDocumentLineItem)
                else CommercialDocumentLineItem(**line)
            )
            for line in self.lines
        ]
        if not isinstance(self.totals, CommercialDocumentTotals):
            self.totals = CommercialDocumentTotals(**dict(self.totals))

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "revision_number": self.revision_number,
            "lifecycle_state": self.lifecycle_state.value,
            "approval_state": self.approval_state.value,
            "revision_label": self.revision_label,
            "revision_reason": self.revision_reason,
            "revision_date": self.revision_date,
            "parent_revision_id": self.parent_revision_id,
            "superseded_by_revision_id": self.superseded_by_revision_id,
            "superseded_at": self.superseded_at,
            "is_current": self.is_current,
            "is_archived": self.is_archived,
            "archived_at": self.archived_at,
            "created_by": self.created_by,
            "issued_at": self.issued_at,
            "immutable": self.immutable,
            "notes": self.notes,
            "lines": [line.to_dict() for line in self.lines],
            "totals": self.totals.to_dict(),
            "created_at": self.created_at,
        }


@dataclass
class CommercialNumberingPolicy:
    tenant_id: str
    organization_id: str
    document_type: CommercialDocumentType
    prefix: str
    syntax_template: str = "{PREFIX}-{SEQUENCE}"
    suffix: str = ""
    separator: str = "-"
    sequence_padding: int = 5
    starting_sequence: int = 1
    reset_policy: str = "never"
    next_sequence: int = 1
    last_reset_period: str = ""
    allocated_numbers: list[str] = field(default_factory=list)

    _ALLOWED_TOKENS = {
        "{PREFIX}",
        "{TYPE}",
        "{YEAR}",
        "{MONTH}",
        "{PROJECT_CODE}",
        "{SEQUENCE}",
        "{SUFFIX}",
    }

    def __post_init__(self) -> None:
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.organization_id = _required_text("organization_id", self.organization_id)
        if not isinstance(self.document_type, CommercialDocumentType):
            self.document_type = CommercialDocumentType(self.document_type)
        self.prefix = _required_text("prefix", self.prefix)
        if (
            not isinstance(self.syntax_template, str)
            or not self.syntax_template.strip()
        ):
            raise ValueError("syntax_template cannot be blank")
        self.syntax_template = self.syntax_template.strip()
        self.suffix = str(self.suffix or "").strip()
        self.separator = str(self.separator or "-")
        if not self.separator.strip():
            raise ValueError("separator cannot be blank")
        self.separator = self.separator.strip()
        self.sequence_padding = int(self.sequence_padding)
        if self.sequence_padding <= 0:
            raise ValueError("sequence_padding must be greater than 0")
        self.starting_sequence = int(self.starting_sequence)
        if self.starting_sequence <= 0:
            raise ValueError("starting_sequence must be greater than 0")
        self.reset_policy = str(self.reset_policy or "never").strip().lower()
        if self.reset_policy not in {"never", "year", "month"}:
            raise ValueError("reset_policy must be one of never, year, month")
        self.next_sequence = int(self.next_sequence)
        if self.next_sequence <= 0:
            raise ValueError("next_sequence must be greater than 0")
        if self.next_sequence < self.starting_sequence:
            self.next_sequence = self.starting_sequence
        self.last_reset_period = str(self.last_reset_period or "").strip()

        tokens = {
            part
            for part in self.syntax_template.split("{")
            if "}" in part
            for part in ["{" + part.split("}", 1)[0] + "}"]
        }
        invalid_tokens = sorted(
            token for token in tokens if token not in self._ALLOWED_TOKENS
        )
        if invalid_tokens:
            raise ValueError(
                f"unsupported numbering tokens: {', '.join(invalid_tokens)}"
            )
        if "{SEQUENCE}" not in self.syntax_template:
            raise ValueError("syntax_template must include {SEQUENCE}")
        seen: set[str] = set()
        normalized: list[str] = []
        for value in list(self.allocated_numbers or []):
            candidate = _required_text("allocated_number", str(value))
            if candidate in seen:
                continue
            normalized.append(candidate)
            seen.add(candidate)
        self.allocated_numbers = normalized

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            parsed = value.strip().replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(parsed)
            except ValueError:
                pass
        return datetime.now(UTC)

    def _period_key(self, *, context: dict[str, Any] | None) -> str:
        if self.reset_policy == "never":
            return ""
        timestamp = self._coerce_datetime((context or {}).get("as_of"))
        if self.reset_policy == "year":
            return f"{timestamp.year:04d}"
        return f"{timestamp.year:04d}-{timestamp.month:02d}"

    def _effective_sequence(self, *, context: dict[str, Any] | None) -> int:
        period_key = self._period_key(context=context)
        if (
            self.reset_policy != "never"
            and period_key
            and period_key != self.last_reset_period
        ):
            return self.starting_sequence
        return max(self.starting_sequence, self.next_sequence)

    def _render_number(self, *, sequence: int, context: dict[str, Any] | None) -> str:
        normalized_context = dict(context or {})
        timestamp = self._coerce_datetime(normalized_context.get("as_of"))
        project_code = str(normalized_context.get("project_code") or "").strip()
        replacements = {
            "{PREFIX}": self.prefix,
            "{TYPE}": self.document_type.value.upper().replace("_", "-"),
            "{YEAR}": f"{timestamp.year:04d}",
            "{MONTH}": f"{timestamp.month:02d}",
            "{PROJECT_CODE}": project_code,
            "{SEQUENCE}": f"{sequence:0{self.sequence_padding}d}",
            "{SUFFIX}": self.suffix,
        }
        rendered = self.syntax_template
        for token, value in replacements.items():
            rendered = rendered.replace(token, value)
        separator = self.separator
        while f"{separator}{separator}" in rendered:
            rendered = rendered.replace(f"{separator}{separator}", separator)
        return rendered.strip(separator).strip()

    def preview(self, *, context: dict[str, Any] | None = None) -> str:
        sequence = self._effective_sequence(context=context)
        return self._render_number(sequence=sequence, context=context)

    def allocate(self, *, context: dict[str, Any] | None = None) -> str:
        sequence = self._effective_sequence(context=context)
        number = self._render_number(sequence=sequence, context=context)
        if number in self.allocated_numbers:
            raise ValueError("document number already allocated")
        self.allocated_numbers.append(number)
        self.next_sequence = sequence + 1
        if self.reset_policy != "never":
            self.last_reset_period = self._period_key(context=context)
        return number

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "document_type": self.document_type.value,
            "prefix": self.prefix,
            "syntax_template": self.syntax_template,
            "suffix": self.suffix,
            "separator": self.separator,
            "sequence_padding": self.sequence_padding,
            "starting_sequence": self.starting_sequence,
            "reset_policy": self.reset_policy,
            "next_sequence": self.next_sequence,
            "last_reset_period": self.last_reset_period,
            "allocated_numbers": list(self.allocated_numbers),
        }


@dataclass
class CommercialDocument:
    document_id: str
    tenant_id: str
    organization_id: str
    document_type: CommercialDocumentType
    lifecycle_state: CommercialDocumentLifecycleState = (
        CommercialDocumentLifecycleState.DRAFT
    )
    approval_state: ApprovalState = ApprovalState.NOT_REQUESTED
    document_number: str | None = None
    project_id: str | None = None
    project_code: str | None = None
    customer_id: str | None = None
    vendor_id: str | None = None
    source_document_id: str | None = None
    source_relationship_type: str | None = None
    duplicated_from_document_id: str | None = None
    duplicated_by: str | None = None
    duplicated_at: str | None = None
    terms_and_conditions_reference: dict[str, Any] | None = None
    terms_and_conditions_snapshot: dict[str, Any] | None = None
    numbering_policy_snapshot: dict[str, Any] | None = None
    revision_number: int = 1
    lines: list[CommercialDocumentLineItem] = field(default_factory=list)
    relationships: list[CommercialDocumentRelationship] = field(default_factory=list)
    diagnostics: list[CommercialDocumentDiagnostic] = field(default_factory=list)
    sync_metadata: CommercialDocumentSyncMetadata = field(
        default_factory=CommercialDocumentSyncMetadata
    )
    totals: CommercialDocumentTotals = field(default_factory=CommercialDocumentTotals)
    revisions: list[CommercialDocumentRevision] = field(default_factory=list)
    export_activity: list[dict[str, Any]] = field(default_factory=list)
    future_email_metadata: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.document_id = _required_text("document_id", self.document_id)
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.organization_id = _required_text("organization_id", self.organization_id)
        if not isinstance(self.document_type, CommercialDocumentType):
            self.document_type = CommercialDocumentType(self.document_type)
        if not isinstance(self.lifecycle_state, CommercialDocumentLifecycleState):
            self.lifecycle_state = CommercialDocumentLifecycleState(
                self.lifecycle_state
            )
        if not isinstance(self.approval_state, ApprovalState):
            self.approval_state = ApprovalState(self.approval_state)
        self.document_number = _optional_text(self.document_number)
        self.project_id = _optional_text(self.project_id)
        self.project_code = _optional_text(self.project_code)
        self.customer_id = _optional_text(self.customer_id)
        self.vendor_id = _optional_text(self.vendor_id)
        self.source_document_id = _optional_text(self.source_document_id)
        self.source_relationship_type = _optional_text(self.source_relationship_type)
        self.duplicated_from_document_id = _optional_text(
            self.duplicated_from_document_id
        )
        self.duplicated_by = _optional_text(self.duplicated_by)
        self.duplicated_at = _optional_text(self.duplicated_at)
        self.terms_and_conditions_reference = _optional_dict(
            self.terms_and_conditions_reference
        )
        self.terms_and_conditions_snapshot = _optional_dict(
            self.terms_and_conditions_snapshot
        )
        self.numbering_policy_snapshot = _optional_dict(self.numbering_policy_snapshot)

        self.revision_number = int(self.revision_number)
        if self.revision_number <= 0:
            raise ValueError("revision_number must be greater than 0")

        self.lines = [
            (
                line
                if isinstance(line, CommercialDocumentLineItem)
                else CommercialDocumentLineItem(**line)
            )
            for line in self.lines
        ]
        self.relationships = [
            (
                relationship
                if isinstance(relationship, CommercialDocumentRelationship)
                else CommercialDocumentRelationship(**relationship)
            )
            for relationship in self.relationships
        ]
        self.diagnostics = [
            (
                diagnostic
                if isinstance(diagnostic, CommercialDocumentDiagnostic)
                else CommercialDocumentDiagnostic(**diagnostic)
            )
            for diagnostic in self.diagnostics
        ]
        if not isinstance(self.sync_metadata, CommercialDocumentSyncMetadata):
            self.sync_metadata = CommercialDocumentSyncMetadata(
                **dict(self.sync_metadata)
            )
        if not isinstance(self.totals, CommercialDocumentTotals):
            self.totals = CommercialDocumentTotals(**dict(self.totals))
        self.revisions = [
            (
                revision
                if isinstance(revision, CommercialDocumentRevision)
                else CommercialDocumentRevision(**revision)
            )
            for revision in self.revisions
        ]
        self.export_activity = _list_of_dicts(self.export_activity)
        self.future_email_metadata = _list_of_dicts(self.future_email_metadata)
        self.created_at = _required_text("created_at", self.created_at)
        self.updated_at = _required_text("updated_at", self.updated_at)

        if self.lifecycle_state == CommercialDocumentLifecycleState.ISSUED:
            for revision in self.revisions:
                if revision.revision_number == self.revision_number:
                    revision.immutable = True

    @property
    def is_mutable(self) -> bool:
        return self.lifecycle_state in {
            CommercialDocumentLifecycleState.DRAFT,
            CommercialDocumentLifecycleState.IN_REVIEW,
            CommercialDocumentLifecycleState.APPROVED,
        }

    def can_transition_to(self, target_state: CommercialDocumentLifecycleState) -> bool:
        if not isinstance(target_state, CommercialDocumentLifecycleState):
            target_state = CommercialDocumentLifecycleState(target_state)
        return (
            target_state
            in COMMERCIAL_DOCUMENT_LIFECYCLE_TRANSITIONS[self.lifecycle_state]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "document_type": self.document_type.value,
            "document_number": self.document_number,
            "lifecycle_state": self.lifecycle_state.value,
            "approval_state": self.approval_state.value,
            "revision_number": self.revision_number,
            "project_id": self.project_id,
            "project_code": self.project_code,
            "customer_id": self.customer_id,
            "vendor_id": self.vendor_id,
            "source_document_id": self.source_document_id,
            "source_relationship_type": self.source_relationship_type,
            "duplicated_from_document_id": self.duplicated_from_document_id,
            "duplicated_by": self.duplicated_by,
            "duplicated_at": self.duplicated_at,
            "terms_and_conditions_reference": self.terms_and_conditions_reference,
            "terms_and_conditions_snapshot": self.terms_and_conditions_snapshot,
            "numbering_policy_snapshot": self.numbering_policy_snapshot,
            "lines": [line.to_dict() for line in self.lines],
            "relationships": [
                relationship.to_dict() for relationship in self.relationships
            ],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "sync_metadata": self.sync_metadata.to_dict(),
            "totals": self.totals.to_dict(),
            "revisions": [revision.to_dict() for revision in self.revisions],
            "export_activity": [dict(item) for item in self.export_activity],
            "future_email_metadata": [
                dict(item) for item in self.future_email_metadata
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CommercialDocument":
        normalized = dict(payload)
        # Backward-compatible fallback for older payloads that used status.
        if "lifecycle_state" not in normalized and "status" in normalized:
            normalized["lifecycle_state"] = normalized["status"]
        normalized.pop("status", None)
        if "revision_number" not in normalized:
            normalized["revision_number"] = 1
        if "sync_metadata" not in normalized:
            normalized["sync_metadata"] = {}
        if "totals" not in normalized:
            normalized["totals"] = {}
        if "revisions" not in normalized:
            normalized["revisions"] = []
        if "terms_and_conditions_reference" not in normalized:
            normalized["terms_and_conditions_reference"] = None
        if "terms_and_conditions_snapshot" not in normalized:
            normalized["terms_and_conditions_snapshot"] = None
        if "source_document_id" not in normalized:
            normalized["source_document_id"] = None
        if "source_relationship_type" not in normalized:
            normalized["source_relationship_type"] = None
        if "duplicated_from_document_id" not in normalized:
            normalized["duplicated_from_document_id"] = None
        if "duplicated_by" not in normalized:
            normalized["duplicated_by"] = None
        if "duplicated_at" not in normalized:
            normalized["duplicated_at"] = None
        if "numbering_policy_snapshot" not in normalized:
            normalized["numbering_policy_snapshot"] = None
        if "export_activity" not in normalized:
            normalized["export_activity"] = []
        if "future_email_metadata" not in normalized:
            normalized["future_email_metadata"] = []
        return cls(**normalized)
