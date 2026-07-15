"""Deterministic document generation service with template precedence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from typing import Any
from uuid import uuid4

from atlas_core.contracts.document_generation_contracts import (
    DocumentTemplate,
    DocumentTemplateVersion,
    OutputArtifact,
    OutputFormat,
    RenderContext,
    RenderDiagnostic,
    RenderRequest,
    RenderResult,
    RenderSection,
    TemplateAssignment,
    TemplateSource,
    TemplateStatus,
)
from atlas_core.domain.commercial_document import (
    CommercialDocument,
    CommercialDocumentRevision,
)
from atlas_core.services.commercial_document_pdf_export_service import (
    CommercialDocumentPdfExportService,
    PdfSectionConfig,
)


def _safe_text(value: Any, default: str = "") -> str:
    normalized = str(value or "").strip()
    return normalized or default


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


@dataclass(frozen=True)
class _ResolvedTemplate:
    template: DocumentTemplate
    source: TemplateSource


class DocumentGenerationService:
    """Template resolution + deterministic rendering for commercial documents."""

    def __init__(
        self,
        *,
        serialized_templates: list[dict[str, Any]] | None = None,
        pdf_export_service: CommercialDocumentPdfExportService | None = None,
    ) -> None:
        self._templates: list[DocumentTemplate] = [
            DocumentTemplate.from_dict(dict(item))
            for item in list(serialized_templates or [])
            if isinstance(item, dict)
        ]
        self._pdf_export_service = (
            pdf_export_service or CommercialDocumentPdfExportService()
        )

    def templates_payload(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._templates]

    def create_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor_id: str,
        title: str,
        document_family: str,
        content: str,
        section_config: dict[str, bool] | None = None,
        status: TemplateStatus = TemplateStatus.ACTIVE,
        is_default: bool = False,
        customer_id: str | None = None,
        project_id: str | None = None,
        transaction_id: str | None = None,
    ) -> DocumentTemplate:
        normalized_family = _safe_text(document_family).lower()
        if normalized_family not in {
            "estimate",
            "sales_order",
            "return_order",
            "credit_memo",
        }:
            raise ValueError("unsupported document_family")
        version = DocumentTemplateVersion(
            template_version_id=f"tmplv-{uuid4().hex[:16]}",
            version_number=1,
            content=_safe_text(content),
            content_hash=hashlib.sha1(_safe_text(content).encode("utf-8")).hexdigest(),
            section_config=dict(section_config or {}),
            created_by=_safe_text(actor_id, "system"),
        )
        template = DocumentTemplate(
            template_id=f"tmpl-{uuid4().hex[:16]}",
            tenant_id=_safe_text(tenant_id),
            organization_id=_safe_text(organization_id),
            title=_safe_text(title),
            document_family=normalized_family,
            status=status,
            is_default=bool(is_default),
            customer_id=customer_id,
            project_id=project_id,
            transaction_id=transaction_id,
            archived=False,
            versions=[version],
            created_by=_safe_text(actor_id, "system"),
            updated_by=_safe_text(actor_id, "system"),
        )
        self._templates = self._upsert_template(template)
        if template.is_default and template.scope_rank == 1:
            self._demote_other_defaults(template)
        return template

    def create_template_version(
        self,
        *,
        template_id: str,
        actor_id: str,
        content: str,
        section_config: dict[str, bool] | None = None,
        status: TemplateStatus | None = None,
    ) -> DocumentTemplate:
        template = self._template_required(template_id)
        latest = template.current_version
        next_version = DocumentTemplateVersion(
            template_version_id=f"tmplv-{uuid4().hex[:16]}",
            version_number=latest.version_number + 1,
            content=_safe_text(content),
            content_hash=hashlib.sha1(_safe_text(content).encode("utf-8")).hexdigest(),
            section_config=dict(section_config or latest.section_config),
            created_by=_safe_text(actor_id, "system"),
        )
        updated = DocumentTemplate(
            **{
                **template.to_dict(),
                "status": (status or template.status).value,
                "versions": [*template.versions, next_version],
                "updated_by": _safe_text(actor_id, "system"),
            }
        )
        self._templates = self._upsert_template(updated)
        return updated

    def resolve_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str,
        customer_id: str | None,
        project_id: str | None,
        transaction_id: str | None,
        explicit_template_id: str | None = None,
    ) -> _ResolvedTemplate:
        if _safe_text(explicit_template_id):
            candidate = self._template_required(_safe_text(explicit_template_id))
            if candidate.archived or candidate.status != TemplateStatus.ACTIVE:
                raise ValueError("explicit template is not active")
            if candidate.tenant_id != _safe_text(tenant_id):
                raise ValueError("explicit template tenant mismatch")
            if candidate.organization_id != _safe_text(organization_id):
                raise ValueError("explicit template organization mismatch")
            if candidate.document_family != _safe_text(document_family).lower():
                raise ValueError("explicit template document family mismatch")
            if candidate.customer_id and candidate.customer_id != _safe_text(
                customer_id
            ):
                raise ValueError("explicit template customer scope mismatch")
            if candidate.project_id and candidate.project_id != _safe_text(project_id):
                raise ValueError("explicit template project scope mismatch")
            if candidate.transaction_id and candidate.transaction_id != _safe_text(
                transaction_id
            ):
                raise ValueError("explicit template transaction scope mismatch")
            return _ResolvedTemplate(candidate, TemplateSource.EXPLICIT)

        candidates = [
            item
            for item in self._templates
            if item.tenant_id == _safe_text(tenant_id)
            and item.organization_id == _safe_text(organization_id)
            and item.document_family == _safe_text(document_family).lower()
            and not item.archived
            and item.status == TemplateStatus.ACTIVE
        ]

        scoped: list[tuple[_ResolvedTemplate, tuple[int, int, str]]] = []
        for item in candidates:
            if item.transaction_id and item.transaction_id != _safe_text(
                transaction_id
            ):
                continue
            if item.project_id and item.project_id != _safe_text(project_id):
                continue
            if item.customer_id and item.customer_id != _safe_text(customer_id):
                continue
            if item.transaction_id:
                source = TemplateSource.TRANSACTION
            elif item.project_id:
                source = TemplateSource.PROJECT
            elif item.customer_id:
                source = TemplateSource.CUSTOMER
            elif item.is_default:
                source = TemplateSource.TENANT_DEFAULT
            else:
                continue
            scoped.append(
                (
                    _ResolvedTemplate(item, source),
                    (
                        item.scope_rank,
                        item.current_version.version_number,
                        item.updated_at,
                    ),
                )
            )

        if scoped:
            scoped.sort(key=lambda item: item[1], reverse=True)
            return scoped[0][0]

        return _ResolvedTemplate(
            self._fallback_template(document_family),
            TemplateSource.APPLICATION_FALLBACK,
        )

    def render_document(
        self,
        *,
        request: RenderRequest,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        branding: dict[str, Any] | None = None,
    ) -> RenderResult:
        revision_template = dict(revision.template_assignment or {})
        revision_snapshot = dict(revision.template_version_snapshot or {})
        diagnostics: list[RenderDiagnostic] = []

        if revision_template and revision_snapshot:
            assignment = TemplateAssignment(
                template_id=_safe_text(revision_template.get("template_id")),
                template_version_id=_safe_text(
                    revision_template.get("template_version_id")
                ),
                version_number=int(revision_template.get("version_number") or 1),
                source=TemplateSource.REVISION_SNAPSHOT,
            )
            version_snapshot = deepcopy(revision_snapshot)
            diagnostics.append(
                RenderDiagnostic(
                    code="revision_snapshot_template",
                    message="Using template snapshot captured on this revision.",
                )
            )
        else:
            resolved = self.resolve_template(
                tenant_id=request.tenant_id,
                organization_id=request.organization_id,
                document_family=request.document_family,
                customer_id=document.customer_id,
                project_id=document.project_id,
                transaction_id=document.document_id,
                explicit_template_id=request.explicit_template_id,
            )
            version = resolved.template.current_version
            assignment = TemplateAssignment(
                template_id=resolved.template.template_id,
                template_version_id=version.template_version_id,
                version_number=version.version_number,
                source=resolved.source,
            )
            version_snapshot = {
                "template_id": resolved.template.template_id,
                "template_title": resolved.template.title,
                "document_family": resolved.template.document_family,
                "template_version_id": version.template_version_id,
                "version_number": version.version_number,
                "content": version.content,
                "content_hash": version.content_hash,
                "section_config": dict(version.section_config),
            }

        context = RenderContext(
            document_snapshot=document.to_dict(),
            revision_snapshot=revision.to_dict(),
            branding=dict(branding or {}),
        )
        section_config = self._section_config(version_snapshot)
        sections = [
            RenderSection(key=key, included=value)
            for key, value in sorted(section_config.items(), key=lambda item: item[0])
        ]

        if request.output_format == OutputFormat.PDF:
            payload = self._pdf_export_service.build_pdf_bytes(
                document=document,
                revision=revision,
                presentation=request.presentation,
                section_config=PdfSectionConfig(**section_config),
                branding=context.branding,
            )
            file_name = self._pdf_export_service.suggested_filename(
                document=document,
                presentation=request.presentation,
                revision_number=revision.revision_number,
            )
            mime_type = "application/pdf"
        else:
            html = self._render_html(
                template_content=_safe_text(version_snapshot.get("content"), ""),
                document=document,
                revision=revision,
                context=context,
            )
            payload = html.encode("utf-8")
            number = _safe_text(document.document_number) or document.document_id
            file_name = (
                f"{number}-r{revision.revision_number}-{request.presentation}.html"
            )
            mime_type = "text/html"

        content_hash = hashlib.sha1(payload).hexdigest()
        artifact = OutputArtifact(
            artifact_id=_stable_id(
                "artifact",
                document.document_id,
                str(revision.revision_number),
                assignment.template_version_id,
                request.output_format.value,
                content_hash,
            ),
            file_name=file_name,
            mime_type=mime_type,
            output_format=request.output_format,
            content_hash=content_hash,
            payload=payload,
        )
        return RenderResult(
            assignment=assignment,
            template_version_snapshot=version_snapshot,
            sections=sections,
            artifact=artifact,
            diagnostics=diagnostics,
        )

    def _render_html(
        self,
        *,
        template_content: str,
        document: CommercialDocument,
        revision: CommercialDocumentRevision,
        context: RenderContext,
    ) -> str:
        rows = sorted(
            list(revision.lines or []),
            key=lambda item: (item.display_sequence, item.sequence, item.line_id),
        )
        line_items = "".join(
            [
                (
                    "<tr>"
                    + f"<td>{_safe_text(line.description)}</td>"
                    + f"<td>{line.quantity}</td>"
                    + f"<td>{line.unit_price}</td>"
                    + f"<td>{line.extended_amount}</td>"
                    + "</tr>"
                )
                for line in rows
                if line.contributes_to_totals
            ]
        )
        terms_snapshot = dict(
            revision.terms_and_conditions_snapshot
            or document.terms_and_conditions_snapshot
            or {}
        )
        template = (
            template_content
            or self._fallback_template(
                document.document_type.value
            ).current_version.content
        )
        replacements = {
            "{{organization_name}}": _safe_text(
                context.branding.get("organization_name"), document.organization_id
            ),
            "{{document_number}}": _safe_text(
                document.document_number, document.document_id
            ),
            "{{document_type}}": document.document_type.value,
            "{{revision_number}}": str(revision.revision_number),
            "{{customer_id}}": _safe_text(document.customer_id, "n/a"),
            "{{project_id}}": _safe_text(document.project_id, "n/a"),
            "{{subtotal}}": f"{revision.totals.subtotal:.2f}",
            "{{discount_total}}": f"{revision.totals.discount_total:.2f}",
            "{{tax_total}}": f"{revision.totals.tax_total:.2f}",
            "{{grand_total}}": f"{revision.totals.grand_total:.2f}",
            "{{terms_content}}": _safe_text(terms_snapshot.get("content"), "n/a"),
            "{{line_items_rows}}": line_items
            or '<tr><td colspan="4">No line items</td></tr>',
        }
        rendered = template
        for token, value in replacements.items():
            rendered = rendered.replace(token, value)
        return rendered

    def _section_config(self, template_snapshot: dict[str, Any]) -> dict[str, bool]:
        defaults = PdfSectionConfig().__dict__.copy()
        incoming = dict(template_snapshot.get("section_config") or {})
        for key in list(defaults.keys()):
            if key in incoming:
                defaults[key] = bool(incoming[key])
        return defaults

    def _upsert_template(self, template: DocumentTemplate) -> list[DocumentTemplate]:
        updated = []
        replaced = False
        for item in self._templates:
            if item.template_id == template.template_id:
                updated.append(template)
                replaced = True
            else:
                updated.append(item)
        if not replaced:
            updated.append(template)
        return updated

    def _demote_other_defaults(self, target: DocumentTemplate) -> None:
        updated: list[DocumentTemplate] = []
        for item in self._templates:
            if (
                item.template_id != target.template_id
                and item.tenant_id == target.tenant_id
                and item.organization_id == target.organization_id
                and item.document_family == target.document_family
                and item.scope_rank == 1
                and item.is_default
            ):
                updated.append(
                    DocumentTemplate(**{**item.to_dict(), "is_default": False})
                )
            else:
                updated.append(item)
        self._templates = updated

    def _template_required(self, template_id: str) -> DocumentTemplate:
        normalized = _safe_text(template_id)
        for item in self._templates:
            if item.template_id == normalized:
                return item
        raise ValueError("template was not found")

    def _fallback_template(self, document_family: str) -> DocumentTemplate:
        family = _safe_text(document_family, "estimate").lower()
        content = (
            "<html><body>"
            "<h1>{{organization_name}}</h1>"
            "<h2>{{document_type}} {{document_number}} · Revision {{revision_number}}</h2>"
            "<p>Customer: {{customer_id}} | Project: {{project_id}}</p>"
            "<table><thead><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Extended</th></tr></thead>"
            "<tbody>{{line_items_rows}}</tbody></table>"
            "<p>Subtotal: {{subtotal}} | Discount: {{discount_total}} | Tax: {{tax_total}} | Total: {{grand_total}}</p>"
            "<p>Terms: {{terms_content}}</p>"
            "</body></html>"
        )
        version = DocumentTemplateVersion(
            template_version_id=f"fallback-{family}-v1",
            version_number=1,
            content=content,
            content_hash=hashlib.sha1(content.encode("utf-8")).hexdigest(),
            section_config={},
            created_by="system",
        )
        return DocumentTemplate(
            template_id=f"fallback-{family}",
            tenant_id="*",
            organization_id="*",
            title=f"Fallback {family.title()} Template",
            document_family=family,
            status=TemplateStatus.ACTIVE,
            is_default=False,
            versions=[version],
            created_by="system",
            updated_by="system",
        )
