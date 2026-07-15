"""Deterministic PDF export helpers for commercial documents."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha1
from pathlib import Path
from typing import Any

from atlas_core.domain.commercial_document import (
    CommercialDocument,
    CommercialDocumentRevision,
    CommercialDocumentType,
)


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    normalized = str(value).strip()
    return normalized or default


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_decimal(value: Decimal | Any) -> str:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    try:
        return f"{Decimal(str(value)):.2f}"
    except Exception:
        return _safe_text(value)


@dataclass(frozen=True)
class PdfSectionConfig:
    include_branding: bool = True
    include_document_header: bool = True
    include_customer: bool = True
    include_project: bool = True
    include_line_items: bool = True
    include_totals: bool = True
    include_scope: bool = True
    include_exclusions: bool = True
    include_alternates: bool = True
    include_notes: bool = True
    include_terms: bool = True
    include_issue_and_status: bool = True


class CommercialDocumentPdfExportService:
    """Build deterministic, reproducible PDF bytes for document revisions."""

    def suggested_filename(
        self,
        *,
        document: CommercialDocument,
        presentation: str,
        revision_number: int,
    ) -> str:
        number = _safe_text(document.document_number) or document.document_id
        normalized_number = "-".join(number.replace("_", "-").split())
        normalized_view = "-".join(_safe_text(presentation).lower().split())
        return f"{normalized_number}-r{revision_number}-{normalized_view}.pdf"

    def build_pdf_bytes(
        self,
        *,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        presentation: str,
        section_config: PdfSectionConfig,
        branding: dict[str, Any] | None = None,
    ) -> bytes:
        lines = self._build_lines(
            document=document,
            revision=revision,
            presentation=presentation,
            section_config=section_config,
            branding=branding or {},
        )
        return self._build_pdf_from_lines(lines)

    def export_pdf(
        self,
        *,
        output_dir: str | Path,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        presentation: str,
        section_config: PdfSectionConfig,
        branding: dict[str, Any] | None = None,
    ) -> Path:
        file_name = self.suggested_filename(
            document=document,
            presentation=presentation,
            revision_number=revision.revision_number,
        )
        path = Path(output_dir) / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            self.build_pdf_bytes(
                document=document,
                revision=revision,
                presentation=presentation,
                section_config=section_config,
                branding=branding,
            )
        )
        return path

    def export_content_hash(
        self,
        *,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        presentation: str,
        section_config: PdfSectionConfig,
        branding: dict[str, Any] | None = None,
    ) -> str:
        payload = self.build_pdf_bytes(
            document=document,
            revision=revision,
            presentation=presentation,
            section_config=section_config,
            branding=branding,
        )
        return sha1(payload).hexdigest()

    def _build_lines(
        self,
        *,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        presentation: str,
        section_config: PdfSectionConfig,
        branding: dict[str, Any],
    ) -> list[str]:
        lines: list[str] = []
        view = _safe_text(presentation).strip().lower() or "document"

        if section_config.include_branding:
            lines.append(
                f"Organization: {_safe_text(branding.get('organization_name')) or document.organization_id}"
            )
            lines.append(
                f"Branding Logo: {_safe_text(branding.get('logo_reference')) or 'not_configured'}"
            )
            lines.append("")

        if section_config.include_document_header:
            lines.append(f"Presentation: {view}")
            lines.append(f"Document Type: {document.document_type.value}")
            lines.append(
                f"Document Number: {_safe_text(document.document_number) or document.document_id}"
            )
            lines.append(f"Revision Number: {revision.revision_number}")
            lines.append(f"Revision Date: {revision.revision_date}")
            lines.append(
                f"Revision Reason: {_safe_text(revision.revision_reason) or 'n/a'}"
            )
            lines.append("")

        if section_config.include_customer:
            lines.append(f"Customer: {_safe_text(document.customer_id) or 'n/a'}")

        if section_config.include_project:
            lines.append(f"Project: {_safe_text(document.project_id) or 'n/a'}")
            lines.append(f"Project Code: {_safe_text(document.project_code) or 'n/a'}")
            lines.append("")

        metadata = dict(document.document_metadata or {})
        if bool(metadata.get("is_change_order", False)) and document.document_type in {
            CommercialDocumentType.SALES_ORDER,
            CommercialDocumentType.RETURN_ORDER,
        }:
            lines.append("CHANGE ORDER")
            lines.append(
                f"CO Number: {_safe_text(metadata.get('change_order_number')) or 'n/a'}"
            )
            lines.append(
                "Change Type: "
                + (
                    _safe_text(
                        metadata.get("change_order_type")
                        or metadata.get("change_order_direction")
                    )
                    or "n/a"
                )
            )
            lines.append(
                "Base Bid Reference: "
                + (_safe_text(metadata.get("base_bid_reference")) or "n/a")
            )
            lines.append(
                "Owner Change Reference: "
                + (_safe_text(metadata.get("owner_change_reference")) or "n/a")
            )
            lines.append(
                "Revised Contract Value: "
                + (_safe_text(metadata.get("revised_contract_value")) or "n/a")
            )
            lines.append(
                "Change Summary: "
                + (
                    _safe_text(metadata.get("change_reason"))
                    or _safe_text(metadata.get("internal_notes"))
                    or "n/a"
                )
            )
            lines.append("")

        sorted_lines = sorted(
            list(revision.lines or []),
            key=lambda item: (item.display_sequence, item.sequence, item.line_id),
        )
        visible_columns = self._visible_columns(document)
        group_index = self._group_index(document)
        group_subtotals = self._group_subtotals(sorted_lines)
        if section_config.include_line_items:
            lines.append("Line Items")
            for item in sorted_lines:
                presentation_metadata = item.presentation_metadata
                line_type = item.presentation_line_type
                group_id = _safe_text(presentation_metadata.get("group_id"), "")
                if line_type == "blank_spacer":
                    lines.append("")
                    continue
                if line_type == "comment":
                    lines.append(f"Comment: {_safe_text(item.description)}")
                    continue
                if line_type == "group_header":
                    lines.append(f"Group: {_safe_text(item.description)}")
                    continue
                if line_type == "subtotal":
                    group_payload: dict[str, Any] = dict(group_index.get(group_id, {}))
                    if bool(group_payload.get("show_subtotal", True)):
                        subtotal_value = group_subtotals.get(group_id, Decimal("0"))
                        lines.append(
                            f"Subtotal {_safe_text(group_payload.get('name'), _safe_text(item.description))}: {_format_decimal(subtotal_value)}"
                        )
                    continue
                row_parts = []
                for column in visible_columns:
                    if column == "description":
                        row_parts.append(f"Desc {_safe_text(item.description)}")
                    elif column == "quantity":
                        row_parts.append(f"Qty {_format_decimal(item.quantity)}")
                    elif column == "unit_price":
                        row_parts.append(f"Unit {_format_decimal(item.unit_price)}")
                    elif column == "extended_price":
                        row_parts.append(f"Ext {_format_decimal(item.extended_amount)}")
                    elif column == "sku_or_part_number":
                        row_parts.append(
                            f"SKU {_safe_text(item.product_or_service_reference)}"
                        )
                    elif column == "manufacturer":
                        row_parts.append(
                            f"Mfr {_safe_text((item.line_metadata or {}).get('manufacturer'))}"
                        )
                    elif column == "item_type":
                        row_parts.append(f"Type {line_type}")
                if not row_parts:
                    row_parts.append(f"Desc {_safe_text(item.description)}")
                lines.append(" - " + " | ".join(row_parts))
            if not sorted_lines:
                lines.append(" - none")
            lines.append("")

        if section_config.include_totals:
            lines.append(f"Currency: {_safe_text(revision.totals.currency) or 'USD'}")
            lines.append(f"Subtotal: {_format_decimal(revision.totals.subtotal)}")
            lines.append(
                f"Discount Total: {_format_decimal(revision.totals.discount_total)}"
            )
            lines.append(f"Tax Total: {_format_decimal(revision.totals.tax_total)}")
            lines.append(f"Grand Total: {_format_decimal(revision.totals.grand_total)}")
            lines.append("")

        if section_config.include_scope:
            lines.append(
                f"Scope: {_safe_text((document.terms_and_conditions_snapshot or {}).get('scope')) or 'n/a'}"
            )
        if section_config.include_exclusions:
            lines.append(
                f"Exclusions: {_safe_text((document.terms_and_conditions_snapshot or {}).get('exclusions')) or 'n/a'}"
            )
        if section_config.include_alternates:
            lines.append(
                f"Alternates: {_safe_text((document.terms_and_conditions_snapshot or {}).get('alternates')) or 'n/a'}"
            )

        if section_config.include_notes:
            lines.append(f"Notes: {_safe_text(revision.notes) or 'n/a'}")

        if section_config.include_terms:
            terms_reference = dict(document.terms_and_conditions_reference or {})
            terms_snapshot = dict(document.terms_and_conditions_snapshot or {})
            lines.append(
                "Terms Reference: "
                + (
                    _safe_text(terms_reference.get("block_id"))
                    or _safe_text(terms_reference.get("resolved_default_block_id"))
                    or "n/a"
                )
            )
            lines.append(
                f"Terms Version: {_safe_text(terms_reference.get('version')) or _safe_text(terms_snapshot.get('version')) or 'n/a'}"
            )
            lines.append(
                f"Terms Effective Date: {_safe_text(terms_snapshot.get('effective_date')) or 'n/a'}"
            )
            terms_content = _safe_text(terms_snapshot.get("content")) or "n/a"
            lines.append(f"Terms and Conditions: {terms_content}")

        if section_config.include_issue_and_status:
            lines.append(f"Issue Date: {_safe_text(revision.issued_at) or 'n/a'}")
            lines.append(f"Status: {document.lifecycle_state.value}")
            lines.append(f"Approval: {document.approval_state.value}")

        return lines

    def _group_index(self, document: CommercialDocument) -> dict[str, dict[str, Any]]:
        metadata = dict(document.document_metadata or {})
        presentation = dict(metadata.get("presentation") or {})
        groups = [
            dict(item)
            for item in list(presentation.get("groups") or [])
            if isinstance(item, dict)
        ]
        return {
            _safe_text(group.get("group_id"), ""): group
            for group in groups
            if _safe_text(group.get("group_id"), "")
        }

    def _group_subtotals(self, lines: list[Any]) -> dict[str, Decimal]:
        subtotals: dict[str, Decimal] = {}
        for line in lines:
            group_id = _safe_text(line.presentation_metadata.get("group_id"), "")
            if not group_id or not line.contributes_to_totals:
                continue
            subtotals[group_id] = (
                subtotals.get(group_id, Decimal("0")) + line.extended_amount
            )
        return subtotals

    def _visible_columns(self, document: CommercialDocument) -> list[str]:
        metadata = dict(document.document_metadata or {})
        presentation = dict(metadata.get("presentation") or {})
        values = [
            _safe_text(item, "")
            for item in list(presentation.get("visible_columns") or [])
            if _safe_text(item, "")
        ]
        return values or ["description", "quantity", "unit_price", "extended_price"]

    def _build_pdf_from_lines(self, lines: list[str]) -> bytes:
        lines_per_page = 52
        chunks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            current.append(line)
            if len(current) >= lines_per_page:
                chunks.append(current)
                current = []
        if current or not chunks:
            chunks.append(current)

        page_objects: list[tuple[int, int, bytes]] = []
        object_id = 3
        for chunk in chunks:
            page_id = object_id
            content_id = object_id + 1
            content = self._content_stream(chunk)
            page_objects.append((page_id, content_id, content))
            object_id += 2

        font_id = object_id
        objects: dict[int, bytes] = {}
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        kids = " ".join(f"{page_id} 0 R" for page_id, _, _ in page_objects)
        objects[2] = (
            f"<< /Type /Pages /Kids [{kids}] /Count {len(page_objects)} >>".encode(
                "ascii"
            )
        )
        for page_id, content_id, content in page_objects:
            objects[page_id] = (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
            objects[content_id] = (
                f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
                + content
                + b"\nendstream"
            )
        objects[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        return self._build_pdf_bytes(objects)

    def _content_stream(self, lines: list[str]) -> bytes:
        parts: list[str] = ["BT", "/F1 10 Tf", "12 TL", "40 760 Td"]
        for line in lines:
            truncated = line[:160]
            parts.append(f"({_escape_pdf_text(truncated)}) Tj")
            parts.append("T*")
        parts.append("ET")
        return "\n".join(parts).encode("utf-8")

    def _build_pdf_bytes(self, objects: dict[int, bytes]) -> bytes:
        header = b"%PDF-1.4\n"
        body = bytearray()
        offsets: dict[int, int] = {}
        for object_id in sorted(objects.keys()):
            offsets[object_id] = len(header) + len(body)
            body.extend(f"{object_id} 0 obj\n".encode("ascii"))
            body.extend(objects[object_id])
            body.extend(b"\nendobj\n")

        startxref = len(header) + len(body)
        max_id = max(objects.keys())
        xref = bytearray()
        xref.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
        xref.extend(b"0000000000 65535 f \n")
        for object_id in range(1, max_id + 1):
            offset = offsets.get(object_id, 0)
            xref.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

        trailer = (
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{startxref}\n%%EOF\n"
        ).encode("ascii")
        return header + bytes(body) + bytes(xref) + trailer
