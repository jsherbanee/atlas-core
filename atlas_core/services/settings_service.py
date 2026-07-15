"""Settings workspace service for organization and personal preferences."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any
from uuid import uuid4

from atlas_core.contracts.audit_contracts import (
    AuditActor,
    AuditRetentionClass,
    AuditTarget,
    ImmutableAuditEvent,
)
from atlas_core.domain.commercial_document import (
    CommercialDocumentType,
    CommercialNumberingPolicy,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tenant_scope_key(tenant_id: str, organization_id: str) -> str:
    return f"{tenant_id.strip()}::{organization_id.strip()}"


def _user_scope_key(tenant_id: str, organization_id: str, user_id: str) -> str:
    return f"{tenant_id.strip()}::{organization_id.strip()}::{user_id.strip()}"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_optional_text(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return normalized or None


def _parse_iso_or_none(value: str | None) -> datetime | None:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO date value: {normalized}") from exc


def _is_effective(
    *,
    effective_date: str | None,
    expiration_date: str | None,
    as_of: str,
) -> bool:
    as_of_dt = _parse_iso_or_none(as_of)
    if as_of_dt is None:
        as_of_dt = datetime.now(UTC)
    effective_dt = _parse_iso_or_none(effective_date)
    expiration_dt = _parse_iso_or_none(expiration_date)
    if effective_dt is not None and as_of_dt < effective_dt:
        return False
    if expiration_dt is not None and as_of_dt > expiration_dt:
        return False
    return True


_ALLOWED_PERSONAL_PREFERENCE_KEYS = {
    "default_landing_workspace",
    "density",
    "table_page_size",
    "date_display_format",
    "timezone",
    "reduced_motion",
}


_RESTRICTED_PERSONAL_OVERRIDE_KEYS = {
    "numbering",
    "security",
    "billing",
    "retention",
    "integration_policy",
}


_ALLOWED_TERMS_DOCUMENT_FAMILIES = {
    CommercialDocumentType.ESTIMATE.value,
    CommercialDocumentType.SALES_ORDER.value,
    CommercialDocumentType.RETURN_ORDER.value,
    CommercialDocumentType.CUSTOMER_INVOICE.value,
}


_ALLOWED_TEMPLATE_DOCUMENT_FAMILIES = {
    document_type.value for document_type in CommercialDocumentType
}


_ALLOWED_INTEGRATION_PROVIDERS = {
    "quickbooks_online",
    "xero",
    "microsoft_365",
    "google_workspace",
    "generic_api",
    "generic_webhook",
}


_ALLOWED_APPLICABILITY_TYPES = {
    "state",
    "regional",
    "county",
    "municipal",
    "surcharge",
}


_ALLOWED_RULE_CALCULATION_TYPES = {
    "percentage",
    "fixed",
}


_ALLOWED_TEMPLATE_STATUS = {"draft", "active"}


_ALLOWED_TERMS_STATUS = {"draft", "active"}


@dataclass(frozen=True)
class PersonalPreferences:
    default_landing_workspace: str = "Atlas"
    density: str = "comfortable"
    table_page_size: int = 25
    date_display_format: str = "YYYY-MM-DD"
    timezone: str = "UTC"
    reduced_motion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_landing_workspace": self.default_landing_workspace,
            "density": self.density,
            "table_page_size": self.table_page_size,
            "date_display_format": self.date_display_format,
            "timezone": self.timezone,
            "reduced_motion": self.reduced_motion,
        }


@dataclass(frozen=True)
class OrganizationProfile:
    legal_name: str = ""
    display_name: str = ""
    logo_reference: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    physical_address: str | None = None
    mailing_address: str | None = None
    default_currency: str = "USD"
    default_timezone: str = "UTC"
    country: str | None = None
    tax_identification_reference: str | None = None

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "OrganizationProfile":
        legal_name = _normalize_text(payload.get("legal_name"))
        display_name = _normalize_text(payload.get("display_name"))
        email = _normalize_optional_text(payload.get("email"))
        if email and "@" not in email:
            raise ValueError("organization profile email must contain @")
        website = _normalize_optional_text(payload.get("website"))
        if website and not (
            website.startswith("http://") or website.startswith("https://")
        ):
            raise ValueError(
                "organization profile website must start with http:// or https://"
            )
        currency = _normalize_text(payload.get("default_currency") or "USD").upper()
        if len(currency) != 3:
            raise ValueError("default_currency must be a 3-letter code")
        timezone = _normalize_text(payload.get("default_timezone") or "UTC")
        return OrganizationProfile(
            legal_name=legal_name,
            display_name=display_name,
            logo_reference=_normalize_optional_text(payload.get("logo_reference")),
            website=website,
            phone=_normalize_optional_text(payload.get("phone")),
            email=email,
            physical_address=_normalize_optional_text(payload.get("physical_address")),
            mailing_address=_normalize_optional_text(payload.get("mailing_address")),
            default_currency=currency,
            default_timezone=timezone,
            country=_normalize_optional_text(payload.get("country")),
            tax_identification_reference=_normalize_optional_text(
                payload.get("tax_identification_reference")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "legal_name": self.legal_name,
            "display_name": self.display_name,
            "logo_reference": self.logo_reference,
            "website": self.website,
            "phone": self.phone,
            "email": self.email,
            "physical_address": self.physical_address,
            "mailing_address": self.mailing_address,
            "default_currency": self.default_currency,
            "default_timezone": self.default_timezone,
            "country": self.country,
            "tax_identification_reference": self.tax_identification_reference,
        }


@dataclass(frozen=True)
class TaxSurchargeRule:
    rule_id: str
    title: str
    applicability_type: str
    calculation_type: str
    value: str
    effective_date: str | None
    expiration_date: str | None
    exemptions: list[str]
    document_types: list[str]
    line_applicability: str
    priority: int
    compound: bool
    archived: bool
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TaxSurchargeRule":
        rule_id = _normalize_text(payload.get("rule_id"))
        if not rule_id:
            raise ValueError("rule_id is required")
        title = _normalize_text(payload.get("title"))
        if not title:
            raise ValueError("title is required")
        applicability_type = _normalize_text(payload.get("applicability_type")).lower()
        if applicability_type not in _ALLOWED_APPLICABILITY_TYPES:
            raise ValueError("unsupported applicability_type")
        calculation_type = _normalize_text(payload.get("calculation_type")).lower()
        if calculation_type not in _ALLOWED_RULE_CALCULATION_TYPES:
            raise ValueError("unsupported calculation_type")
        value = str(payload.get("value") or "0")
        if Decimal(value) < Decimal("0"):
            raise ValueError("value cannot be negative")
        effective_date = _normalize_optional_text(payload.get("effective_date"))
        expiration_date = _normalize_optional_text(payload.get("expiration_date"))
        _parse_iso_or_none(effective_date)
        _parse_iso_or_none(expiration_date)
        priority = int(payload.get("priority") or 100)
        if priority < 0:
            raise ValueError("priority cannot be negative")
        line_applicability = _normalize_text(
            payload.get("line_applicability") or "all"
        ).lower()
        if line_applicability not in {"all", "taxable", "non_taxable"}:
            raise ValueError("unsupported line_applicability")
        document_types = [
            _normalize_text(item).lower()
            for item in list(payload.get("document_types") or [])
            if _normalize_text(item)
        ]
        if not document_types:
            document_types = [item.value for item in CommercialDocumentType]
        for document_type in document_types:
            if document_type not in _ALLOWED_TEMPLATE_DOCUMENT_FAMILIES:
                raise ValueError("unsupported document type in tax/surcharge rule")
        created_at = _normalize_text(payload.get("created_at")) or _now_iso()
        created_by = _normalize_text(payload.get("created_by")) or "system"
        updated_at = _normalize_text(payload.get("updated_at")) or created_at
        updated_by = _normalize_text(payload.get("updated_by")) or created_by
        exemptions = [
            _normalize_text(item)
            for item in list(payload.get("exemptions") or [])
            if _normalize_text(item)
        ]
        return TaxSurchargeRule(
            rule_id=rule_id,
            title=title,
            applicability_type=applicability_type,
            calculation_type=calculation_type,
            value=str(Decimal(value)),
            effective_date=effective_date,
            expiration_date=expiration_date,
            exemptions=exemptions,
            document_types=document_types,
            line_applicability=line_applicability,
            priority=priority,
            compound=bool(payload.get("compound", False)),
            archived=bool(payload.get("archived", False)),
            created_at=created_at,
            created_by=created_by,
            updated_at=updated_at,
            updated_by=updated_by,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "applicability_type": self.applicability_type,
            "calculation_type": self.calculation_type,
            "value": self.value,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "exemptions": list(self.exemptions),
            "document_types": list(self.document_types),
            "line_applicability": self.line_applicability,
            "priority": self.priority,
            "compound": self.compound,
            "archived": self.archived,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class IntegrationConnection:
    provider: str
    enabled: bool
    status: str
    connection_metadata: dict[str, Any]
    secret_references: dict[str, str]
    updated_at: str
    updated_by: str

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "IntegrationConnection":
        provider = _normalize_text(payload.get("provider")).lower()
        if provider not in _ALLOWED_INTEGRATION_PROVIDERS:
            raise ValueError("unsupported integration provider")
        secret_references_payload = dict(payload.get("secret_references") or {})
        secret_references: dict[str, str] = {}
        for key, value in secret_references_payload.items():
            normalized_key = _normalize_text(key)
            normalized_value = _normalize_text(value)
            if not normalized_key or not normalized_value:
                continue
            if not normalized_value.startswith("secret://"):
                raise ValueError("secret references must use secret:// scheme")
            secret_references[normalized_key] = normalized_value
        return IntegrationConnection(
            provider=provider,
            enabled=bool(payload.get("enabled", False)),
            status=_normalize_text(payload.get("status") or "disconnected").lower(),
            connection_metadata=dict(payload.get("connection_metadata") or {}),
            secret_references=secret_references,
            updated_at=_normalize_text(payload.get("updated_at")) or _now_iso(),
            updated_by=_normalize_text(payload.get("updated_by")) or "system",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "status": self.status,
            "connection_metadata": dict(self.connection_metadata),
            "secret_references": dict(self.secret_references),
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class SecurityPolicy:
    require_mfa: bool = False
    session_timeout_minutes: int = 480
    password_policy_reference: str | None = None
    allowed_ip_ranges: list[str] | None = None

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "SecurityPolicy":
        session_timeout_minutes = int(payload.get("session_timeout_minutes") or 480)
        if session_timeout_minutes < 15:
            raise ValueError("session_timeout_minutes must be at least 15")
        allowed_ip_ranges = [
            _normalize_text(item)
            for item in list(payload.get("allowed_ip_ranges") or [])
            if _normalize_text(item)
        ]
        return SecurityPolicy(
            require_mfa=bool(payload.get("require_mfa", False)),
            session_timeout_minutes=session_timeout_minutes,
            password_policy_reference=_normalize_optional_text(
                payload.get("password_policy_reference")
            ),
            allowed_ip_ranges=allowed_ip_ranges,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "require_mfa": self.require_mfa,
            "session_timeout_minutes": self.session_timeout_minutes,
            "password_policy_reference": self.password_policy_reference,
            "allowed_ip_ranges": list(self.allowed_ip_ranges or []),
        }


@dataclass(frozen=True)
class TermsAndConditionsBlock:
    block_id: str
    title: str
    document_family: str
    status: str
    content: str
    version: int
    effective_date: str | None
    expiration_date: str | None
    is_default: bool
    customer_id: str | None
    project_id: str | None
    transaction_id: str | None
    archived: bool
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str
    previous_block_id: str | None = None

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TermsAndConditionsBlock":
        block_id = _normalize_text(payload.get("block_id"))
        if not block_id:
            raise ValueError("block_id is required")
        title = _normalize_text(payload.get("title"))
        if not title:
            raise ValueError("title is required")
        document_family = _normalize_text(payload.get("document_family")).lower()
        if document_family not in _ALLOWED_TERMS_DOCUMENT_FAMILIES:
            raise ValueError("unsupported terms document_family")
        status = _normalize_text(payload.get("status", "draft")).lower()
        if status not in _ALLOWED_TERMS_STATUS:
            raise ValueError("status must be draft or active")
        content = _normalize_text(payload.get("content"))
        if not content:
            raise ValueError("content is required")
        version = int(payload.get("version", 1))
        if version <= 0:
            raise ValueError("version must be greater than 0")

        effective_date = _normalize_optional_text(payload.get("effective_date"))
        expiration_date = _normalize_optional_text(payload.get("expiration_date"))
        _parse_iso_or_none(effective_date)
        _parse_iso_or_none(expiration_date)

        created_at = _normalize_text(payload.get("created_at")) or _now_iso()
        created_by = _normalize_text(payload.get("created_by")) or "system"
        updated_at = _normalize_text(payload.get("updated_at")) or created_at
        updated_by = _normalize_text(payload.get("updated_by")) or created_by

        return TermsAndConditionsBlock(
            block_id=block_id,
            title=title,
            document_family=document_family,
            status=status,
            content=content,
            version=version,
            effective_date=effective_date,
            expiration_date=expiration_date,
            is_default=bool(payload.get("is_default", False)),
            customer_id=_normalize_optional_text(payload.get("customer_id")),
            project_id=_normalize_optional_text(payload.get("project_id")),
            transaction_id=_normalize_optional_text(payload.get("transaction_id")),
            archived=bool(payload.get("archived", False)),
            created_at=created_at,
            created_by=created_by,
            updated_at=updated_at,
            updated_by=updated_by,
            previous_block_id=_normalize_optional_text(
                payload.get("previous_block_id")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "title": self.title,
            "document_family": self.document_family,
            "status": self.status,
            "content": self.content,
            "version": self.version,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "is_default": self.is_default,
            "customer_id": self.customer_id,
            "project_id": self.project_id,
            "transaction_id": self.transaction_id,
            "archived": self.archived,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "previous_block_id": self.previous_block_id,
        }

    @property
    def scope_rank(self) -> int:
        if self.transaction_id:
            return 4
        if self.project_id:
            return 3
        if self.customer_id:
            return 2
        return 1

    @property
    def is_tenant_default_candidate(self) -> bool:
        return (
            self.customer_id is None
            and self.project_id is None
            and self.transaction_id is None
            and not self.archived
            and self.status == "active"
        )


@dataclass(frozen=True)
class DocumentTemplateBlock:
    template_id: str
    title: str
    document_family: str
    status: str
    content: str
    version: int
    section_config: dict[str, bool]
    visible_columns: list[str]
    branding_logo_reference: str | None
    is_default: bool
    customer_id: str | None
    project_id: str | None
    transaction_id: str | None
    archived: bool
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str
    previous_template_id: str | None = None

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "DocumentTemplateBlock":
        template_id = _normalize_text(payload.get("template_id"))
        if not template_id:
            raise ValueError("template_id is required")
        title = _normalize_text(payload.get("title"))
        if not title:
            raise ValueError("title is required")
        document_family = _normalize_text(payload.get("document_family")).lower()
        if document_family not in _ALLOWED_TEMPLATE_DOCUMENT_FAMILIES:
            raise ValueError("unsupported template document_family")
        status = _normalize_text(payload.get("status", "draft")).lower()
        if status not in _ALLOWED_TEMPLATE_STATUS:
            raise ValueError("status must be draft or active")
        content = _normalize_text(payload.get("content"))
        if not content:
            raise ValueError("content is required")
        version = int(payload.get("version", 1))
        if version <= 0:
            raise ValueError("version must be greater than 0")
        section_config_payload = dict(payload.get("section_config") or {})
        section_config = {
            key: bool(value) for key, value in section_config_payload.items()
        }
        visible_columns = [
            _normalize_text(item)
            for item in list(payload.get("visible_columns") or [])
            if _normalize_text(item)
        ]

        created_at = _normalize_text(payload.get("created_at")) or _now_iso()
        created_by = _normalize_text(payload.get("created_by")) or "system"
        updated_at = _normalize_text(payload.get("updated_at")) or created_at
        updated_by = _normalize_text(payload.get("updated_by")) or created_by

        return DocumentTemplateBlock(
            template_id=template_id,
            title=title,
            document_family=document_family,
            status=status,
            content=content,
            version=version,
            section_config=section_config,
            visible_columns=visible_columns,
            branding_logo_reference=_normalize_optional_text(
                payload.get("branding_logo_reference")
            ),
            is_default=bool(payload.get("is_default", False)),
            customer_id=_normalize_optional_text(payload.get("customer_id")),
            project_id=_normalize_optional_text(payload.get("project_id")),
            transaction_id=_normalize_optional_text(payload.get("transaction_id")),
            archived=bool(payload.get("archived", False)),
            created_at=created_at,
            created_by=created_by,
            updated_at=updated_at,
            updated_by=updated_by,
            previous_template_id=_normalize_optional_text(
                payload.get("previous_template_id")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "title": self.title,
            "document_family": self.document_family,
            "status": self.status,
            "content": self.content,
            "version": self.version,
            "section_config": dict(self.section_config),
            "visible_columns": list(self.visible_columns),
            "branding_logo_reference": self.branding_logo_reference,
            "is_default": self.is_default,
            "customer_id": self.customer_id,
            "project_id": self.project_id,
            "transaction_id": self.transaction_id,
            "archived": self.archived,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "previous_template_id": self.previous_template_id,
        }

    @property
    def scope_rank(self) -> int:
        if self.transaction_id:
            return 4
        if self.project_id:
            return 3
        if self.customer_id:
            return 2
        return 1

    @property
    def is_tenant_default_candidate(self) -> bool:
        return (
            self.customer_id is None
            and self.project_id is None
            and self.transaction_id is None
            and not self.archived
            and self.status == "active"
        )


class SettingsService:
    """In-session settings authority for tenant-scoped and user-scoped preferences."""

    def __init__(self, *, state: dict[str, Any] | None = None) -> None:
        incoming = dict(state or {})
        self.state: dict[str, Any] = {
            "organization_settings": dict(incoming.get("organization_settings") or {}),
            "personal_preferences": dict(incoming.get("personal_preferences") or {}),
            "audit_events": [
                dict(item)
                for item in list(incoming.get("audit_events") or [])
                if isinstance(item, dict)
            ],
            "immutable_audit_events": [
                dict(item)
                for item in list(incoming.get("immutable_audit_events") or [])
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "organization_settings": {},
            "personal_preferences": {},
            "audit_events": [],
            "immutable_audit_events": [],
        }

    def _scope_payload(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> dict[str, Any]:
        key = _tenant_scope_key(tenant_id, organization_id)
        return dict(self.state["organization_settings"].get(key) or {})

    def _store_scope_payload(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        payload: dict[str, Any],
    ) -> None:
        key = _tenant_scope_key(tenant_id, organization_id)
        self.state["organization_settings"][key] = dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def _append_audit(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        action: str,
        details: dict[str, Any],
    ) -> None:
        self.state["audit_events"].append(
            {
                "timestamp": _now_iso(),
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "actor": actor,
                "action": action,
                "details": deepcopy(details),
            }
        )
        occurred_at = _now_iso()
        material = {
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "actor": actor,
            "action": action,
            "timestamp": occurred_at,
            "details": details,
        }
        digest = hashlib.sha1(
            json.dumps(material, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        immutable_event = ImmutableAuditEvent(
            event_id=f"audit-settings:{digest}",
            action=action,
            actor=AuditActor(
                actor_id=_normalize_text(actor) or "system", actor_type="user"
            ),
            target=AuditTarget(
                target_type="settings",
                target_id=f"{tenant_id}::{organization_id}",
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=None,
            ),
            occurred_at=occurred_at,
            retention_class=AuditRetentionClass.COMPLIANCE,
            source="settings_service",
            before={},
            after={},
            change_summary={
                "added_fields": sorted(dict(details).keys()),
                "removed_fields": [],
                "changed_fields": sorted(dict(details).keys()),
            },
            context=deepcopy(dict(details)),
        )
        immutable_rows = [
            dict(item)
            for item in list(self.state.get("immutable_audit_events") or [])
            if isinstance(item, dict)
        ]
        immutable_rows.append(immutable_event.to_dict())
        self.state["immutable_audit_events"] = immutable_rows[-2000:]

    def _default_numbering_policy(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
    ) -> CommercialNumberingPolicy:
        doc_label = document_type.value.upper().replace("_", "-")
        prefix = f"{organization_id}-{doc_label}".upper().replace("_", "-")
        return CommercialNumberingPolicy(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            prefix=prefix,
            syntax_template="{PREFIX}-{SEQUENCE}",
            suffix="",
            separator="-",
            sequence_padding=5,
            starting_sequence=1,
            reset_policy="never",
            next_sequence=1,
            allocated_numbers=[],
        )

    def organization_profile(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> OrganizationProfile:
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        payload = dict(scoped.get("organization_profile") or {})
        return OrganizationProfile.from_dict(payload)

    def update_organization_profile(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        updates: dict[str, Any],
    ) -> OrganizationProfile:
        prior = self.organization_profile(
            tenant_id=tenant_id, organization_id=organization_id
        )
        merged = prior.to_dict()
        merged.update(dict(updates or {}))
        current = OrganizationProfile.from_dict(merged)
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        scoped["organization_profile"] = current.to_dict()
        self._store_scope_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            payload=scoped,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.profile.updated",
            details={"prior": prior.to_dict(), "current": current.to_dict()},
        )
        return current

    def list_tax_surcharge_rules(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        include_archived: bool = False,
    ) -> list[TaxSurchargeRule]:
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        rows: list[TaxSurchargeRule] = []
        for item in list(scoped.get("tax_surcharge_rules") or []):
            if not isinstance(item, dict):
                continue
            try:
                row = TaxSurchargeRule.from_dict(item)
            except ValueError:
                continue
            if not include_archived and row.archived:
                continue
            rows.append(row)
        rows.sort(key=lambda item: (item.priority, item.title, item.rule_id))
        return rows

    def _store_tax_surcharge_rules(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        rows: list[TaxSurchargeRule],
    ) -> None:
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        scoped["tax_surcharge_rules"] = [item.to_dict() for item in rows]
        self._store_scope_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            payload=scoped,
        )

    def create_tax_surcharge_rule(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        title: str,
        applicability_type: str,
        calculation_type: str,
        value: Decimal,
        effective_date: str | None,
        expiration_date: str | None,
        exemptions: list[str] | None,
        document_types: list[str] | None,
        line_applicability: str,
        priority: int,
        compound: bool,
    ) -> TaxSurchargeRule:
        now = _now_iso()
        row = TaxSurchargeRule.from_dict(
            {
                "rule_id": f"tax-rule-{uuid4().hex[:12]}",
                "title": title,
                "applicability_type": applicability_type,
                "calculation_type": calculation_type,
                "value": str(value),
                "effective_date": effective_date,
                "expiration_date": expiration_date,
                "exemptions": list(exemptions or []),
                "document_types": list(document_types or []),
                "line_applicability": line_applicability,
                "priority": priority,
                "compound": bool(compound),
                "archived": False,
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        rows = self.list_tax_surcharge_rules(
            tenant_id=tenant_id,
            organization_id=organization_id,
            include_archived=True,
        )
        rows.append(row)
        self._store_tax_surcharge_rules(
            tenant_id=tenant_id,
            organization_id=organization_id,
            rows=rows,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.tax_surcharge.created",
            details={"rule_id": row.rule_id, "title": row.title},
        )
        return row

    def update_tax_surcharge_rule(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        rule_id: str,
        actor: str,
        updates: dict[str, Any],
    ) -> TaxSurchargeRule:
        rows = self.list_tax_surcharge_rules(
            tenant_id=tenant_id,
            organization_id=organization_id,
            include_archived=True,
        )
        updated_rows: list[TaxSurchargeRule] = []
        result: TaxSurchargeRule | None = None
        for item in rows:
            if item.rule_id != _normalize_text(rule_id):
                updated_rows.append(item)
                continue
            merged = item.to_dict()
            merged.update(dict(updates or {}))
            merged["updated_at"] = _now_iso()
            merged["updated_by"] = actor
            result = TaxSurchargeRule.from_dict(merged)
            updated_rows.append(result)
        if result is None:
            raise ValueError("tax/surcharge rule was not found")
        self._store_tax_surcharge_rules(
            tenant_id=tenant_id,
            organization_id=organization_id,
            rows=updated_rows,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.tax_surcharge.updated",
            details={"rule_id": result.rule_id},
        )
        return result

    def preview_tax_surcharge_calculation(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: str,
        subtotal: Decimal,
        line_is_taxable: bool = True,
        as_of: str | None = None,
        exemption_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        document = _normalize_text(document_type).lower()
        amount = Decimal(str(subtotal))
        timestamp = _normalize_text(as_of) or _now_iso()
        exemptions = {
            _normalize_text(item)
            for item in list(exemption_codes or [])
            if _normalize_text(item)
        }
        applied: list[dict[str, Any]] = []
        total = Decimal("0")
        base_for_compound = amount
        rows = [
            item
            for item in self.list_tax_surcharge_rules(
                tenant_id=tenant_id,
                organization_id=organization_id,
                include_archived=False,
            )
            if document in set(item.document_types)
            and _is_effective(
                effective_date=item.effective_date,
                expiration_date=item.expiration_date,
                as_of=timestamp,
            )
        ]
        rows.sort(key=lambda item: (item.priority, item.rule_id))
        for item in rows:
            if exemptions.intersection(set(item.exemptions)):
                continue
            if item.line_applicability == "taxable" and not line_is_taxable:
                continue
            if item.line_applicability == "non_taxable" and line_is_taxable:
                continue
            value = Decimal(item.value)
            if item.calculation_type == "percentage":
                calculated = (base_for_compound * value) / Decimal("100")
            else:
                calculated = value
            calculated = calculated.quantize(Decimal("0.01"))
            total += calculated
            if item.compound:
                base_for_compound += calculated
            applied.append(
                {
                    "rule_id": item.rule_id,
                    "title": item.title,
                    "calculated_amount": str(calculated),
                    "compound": item.compound,
                }
            )
        grand_total = (amount + total).quantize(Decimal("0.01"))
        return {
            "subtotal": str(amount.quantize(Decimal("0.01"))),
            "tax_surcharge_total": str(total.quantize(Decimal("0.01"))),
            "grand_total": str(grand_total),
            "applied_rules": applied,
        }

    def list_integration_connections(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[IntegrationConnection]:
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        rows: list[IntegrationConnection] = []
        for item in list(scoped.get("integration_connections") or []):
            if not isinstance(item, dict):
                continue
            try:
                rows.append(IntegrationConnection.from_dict(item))
            except ValueError:
                continue
        rows.sort(key=lambda item: item.provider)
        return rows

    def upsert_integration_connection(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        provider: str,
        enabled: bool,
        status: str,
        connection_metadata: dict[str, Any] | None,
        secret_references: dict[str, str] | None,
    ) -> IntegrationConnection:
        row = IntegrationConnection.from_dict(
            {
                "provider": provider,
                "enabled": bool(enabled),
                "status": status,
                "connection_metadata": dict(connection_metadata or {}),
                "secret_references": dict(secret_references or {}),
                "updated_at": _now_iso(),
                "updated_by": actor,
            }
        )
        existing = self.list_integration_connections(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        merged = [item for item in existing if item.provider != row.provider]
        merged.append(row)
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        scoped["integration_connections"] = [item.to_dict() for item in merged]
        self._store_scope_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            payload=scoped,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.integration.updated",
            details={
                "provider": row.provider,
                "enabled": row.enabled,
                "status": row.status,
                "connection_metadata_keys": sorted(row.connection_metadata.keys()),
                "secret_reference_keys": sorted(row.secret_references.keys()),
            },
        )
        return row

    def security_policy(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> SecurityPolicy:
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        return SecurityPolicy.from_dict(dict(scoped.get("security_policy") or {}))

    def update_security_policy(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        updates: dict[str, Any],
    ) -> SecurityPolicy:
        prior = self.security_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        merged = prior.to_dict()
        merged.update(dict(updates or {}))
        current = SecurityPolicy.from_dict(merged)
        scoped = self._scope_payload(
            tenant_id=tenant_id, organization_id=organization_id
        )
        scoped["security_policy"] = current.to_dict()
        self._store_scope_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            payload=scoped,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.security_policy.updated",
            details={"current": current.to_dict()},
        )
        return current

    def list_numbering_policies(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> dict[CommercialDocumentType, CommercialNumberingPolicy]:
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(
            self.state["organization_settings"].get(key, {}).get("numbering_policies")
            or {}
        )
        policies: dict[CommercialDocumentType, CommercialNumberingPolicy] = {}
        for document_type in CommercialDocumentType:
            payload = scoped.get(document_type.value)
            if isinstance(payload, dict):
                policies[document_type] = CommercialNumberingPolicy(**payload)
            else:
                policies[document_type] = self._default_numbering_policy(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    document_type=document_type,
                )
        return policies

    def _validate_duplicate_templates(
        self,
        *,
        policies: dict[CommercialDocumentType, CommercialNumberingPolicy],
    ) -> None:
        signatures: dict[str, CommercialDocumentType] = {}
        for doc_type, policy in policies.items():
            signature = "::".join(
                [
                    policy.syntax_template,
                    policy.prefix,
                    policy.suffix,
                    policy.separator,
                    policy.reset_policy,
                    str(policy.sequence_padding),
                ]
            )
            if "{TYPE}" in policy.syntax_template:
                continue
            prior = signatures.get(signature)
            if prior is not None and prior != doc_type:
                raise ValueError(
                    "duplicate numbering policy signature detected without {TYPE} token"
                )
            signatures[signature] = doc_type

    def _store_policies(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        policies: dict[CommercialDocumentType, CommercialNumberingPolicy],
    ) -> None:
        self._validate_duplicate_templates(policies=policies)
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(self.state["organization_settings"].get(key) or {})
        scoped["numbering_policies"] = {
            doc_type.value: policy.to_dict() for doc_type, policy in policies.items()
        }
        self.state["organization_settings"][key] = scoped

    def update_numbering_policy(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        actor: str,
        syntax_template: str,
        prefix: str,
        suffix: str,
        starting_sequence: int,
        sequence_padding: int,
        separator: str,
        reset_policy: str,
        include_year_token: bool,
        include_month_token: bool,
        include_project_code_token: bool,
    ) -> CommercialNumberingPolicy:
        policies = self.list_numbering_policies(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        prior = policies[document_type].to_dict()
        policy = CommercialNumberingPolicy(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            prefix=prefix,
            syntax_template=syntax_template,
            suffix=suffix,
            separator=separator,
            sequence_padding=sequence_padding,
            starting_sequence=starting_sequence,
            reset_policy=reset_policy,
            next_sequence=max(starting_sequence, policies[document_type].next_sequence),
            last_reset_period=policies[document_type].last_reset_period,
            allocated_numbers=list(policies[document_type].allocated_numbers),
        )
        if include_year_token and "{YEAR}" not in policy.syntax_template:
            raise ValueError("{YEAR} token is enabled but missing from syntax_template")
        if include_month_token and "{MONTH}" not in policy.syntax_template:
            raise ValueError(
                "{MONTH} token is enabled but missing from syntax_template"
            )
        if (
            include_project_code_token
            and "{PROJECT_CODE}" not in policy.syntax_template
        ):
            raise ValueError(
                "{PROJECT_CODE} token is enabled but missing from syntax_template"
            )
        policies[document_type] = policy
        self._store_policies(
            tenant_id=tenant_id,
            organization_id=organization_id,
            policies=policies,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.numbering_policy.updated",
            details={
                "document_type": document_type.value,
                "prior": prior,
                "current": policy.to_dict(),
            },
        )
        return policy

    def replace_numbering_policies(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        policies_payload: list[dict[str, Any]],
        actor: str,
        reason: str,
    ) -> None:
        policies: dict[CommercialDocumentType, CommercialNumberingPolicy] = {}
        for payload in list(policies_payload or []):
            if not isinstance(payload, dict):
                continue
            policy = CommercialNumberingPolicy(**payload)
            if (
                policy.tenant_id != tenant_id
                or policy.organization_id != organization_id
            ):
                continue
            policies[policy.document_type] = policy
        if not policies:
            return
        self._store_policies(
            tenant_id=tenant_id,
            organization_id=organization_id,
            policies=policies,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.numbering_policy.runtime_sync",
            details={"reason": reason, "count": len(policies)},
        )

    def numbering_policy_for_document_type(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
    ) -> CommercialNumberingPolicy:
        return self.list_numbering_policies(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )[document_type]

    def preview_number(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        project_code: str = "",
        as_of: str = "",
    ) -> str:
        policy = self.numbering_policy_for_document_type(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
        )
        return policy.preview(
            context={
                "project_code": _normalize_text(project_code),
                "as_of": _normalize_text(as_of) or _now_iso(),
            }
        )

    def export_numbering_policies(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        return [
            policy.to_dict()
            for policy in self.list_numbering_policies(
                tenant_id=tenant_id,
                organization_id=organization_id,
            ).values()
        ]

    def _list_terms_blocks_for_scope(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[TermsAndConditionsBlock]:
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(self.state["organization_settings"].get(key) or {})
        payload = list(scoped.get("terms_and_conditions_blocks") or [])
        blocks: list[TermsAndConditionsBlock] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                blocks.append(TermsAndConditionsBlock.from_dict(item))
            except ValueError:
                continue
        return blocks

    def _store_terms_blocks_for_scope(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        blocks: list[TermsAndConditionsBlock],
    ) -> None:
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(self.state["organization_settings"].get(key) or {})
        scoped["terms_and_conditions_blocks"] = [item.to_dict() for item in blocks]
        self.state["organization_settings"][key] = scoped

    def _validate_default_uniqueness(
        self,
        blocks: list[TermsAndConditionsBlock],
    ) -> None:
        default_by_family: dict[str, str] = {}
        for block in blocks:
            if not block.is_default or not block.is_tenant_default_candidate:
                continue
            prior = default_by_family.get(block.document_family)
            if prior and prior != block.block_id:
                raise ValueError(
                    "only one active default is allowed per document family"
                )
            default_by_family[block.document_family] = block.block_id

    def list_terms_and_conditions_blocks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str | None = None,
        include_archived: bool = False,
    ) -> list[TermsAndConditionsBlock]:
        family = _normalize_optional_text(document_family)
        if family is not None:
            family = family.lower()
            if family not in _ALLOWED_TERMS_DOCUMENT_FAMILIES:
                raise ValueError("unsupported terms document_family")
        rows = []
        for block in self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        ):
            if family and block.document_family != family:
                continue
            if not include_archived and block.archived:
                continue
            rows.append(block)
        rows.sort(
            key=lambda item: (item.document_family, item.updated_at, item.version)
        )
        return rows

    def create_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        title: str,
        document_family: str,
        status: str,
        content: str,
        effective_date: str | None,
        expiration_date: str | None,
        is_default: bool,
        customer_id: str | None = None,
        project_id: str | None = None,
        transaction_id: str | None = None,
    ) -> TermsAndConditionsBlock:
        now = _now_iso()
        family = _normalize_text(document_family).lower()
        if family not in _ALLOWED_TERMS_DOCUMENT_FAMILIES:
            raise ValueError("unsupported terms document_family")

        block = TermsAndConditionsBlock.from_dict(
            {
                "block_id": f"terms-{uuid4().hex[:16]}",
                "title": title,
                "document_family": family,
                "status": status,
                "content": content,
                "version": 1,
                "effective_date": effective_date,
                "expiration_date": expiration_date,
                "is_default": bool(is_default),
                "customer_id": customer_id,
                "project_id": project_id,
                "transaction_id": transaction_id,
                "archived": False,
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
            }
        )

        blocks = self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        if block.is_default and not block.is_tenant_default_candidate:
            raise ValueError("default flag is only allowed on tenant-level blocks")

        if block.is_default:
            demoted = []
            for item in blocks:
                if (
                    item.document_family == block.document_family
                    and item.is_tenant_default_candidate
                    and item.is_default
                ):
                    demoted.append(
                        TermsAndConditionsBlock.from_dict(
                            {
                                **item.to_dict(),
                                "is_default": False,
                                "updated_at": now,
                                "updated_by": actor,
                            }
                        )
                    )
                else:
                    demoted.append(item)
            blocks = demoted

        blocks.append(block)
        self._validate_default_uniqueness(blocks)
        self._store_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            blocks=blocks,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.created",
            details={
                "block_id": block.block_id,
                "document_family": block.document_family,
            },
        )
        return block

    def _replace_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block: TermsAndConditionsBlock,
    ) -> TermsAndConditionsBlock:
        blocks = self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        updated: list[TermsAndConditionsBlock] = []
        replaced = False
        for item in blocks:
            if item.block_id == block.block_id:
                updated.append(block)
                replaced = True
            else:
                updated.append(item)
        if not replaced:
            raise ValueError("terms block was not found")
        self._validate_default_uniqueness(updated)
        self._store_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            blocks=updated,
        )
        return block

    def terms_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
    ) -> TermsAndConditionsBlock:
        normalized_id = _normalize_text(block_id)
        for item in self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        ):
            if item.block_id == normalized_id:
                return item
        raise ValueError("terms block was not found")

    def update_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
        actor: str,
        title: str,
        status: str,
        content: str,
        effective_date: str | None,
        expiration_date: str | None,
    ) -> TermsAndConditionsBlock:
        current = self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=block_id,
        )
        now = _now_iso()
        updated = TermsAndConditionsBlock.from_dict(
            {
                **current.to_dict(),
                "title": title,
                "status": status,
                "content": content,
                "effective_date": effective_date,
                "expiration_date": expiration_date,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        self._replace_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block=updated,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.updated",
            details={"block_id": updated.block_id, "version": updated.version},
        )
        return updated

    def create_terms_and_conditions_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
        actor: str,
        title: str | None = None,
        content: str | None = None,
        status: str | None = None,
        effective_date: str | None = None,
        expiration_date: str | None = None,
    ) -> TermsAndConditionsBlock:
        current = self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=block_id,
        )
        now = _now_iso()
        created = TermsAndConditionsBlock.from_dict(
            {
                "block_id": f"terms-{uuid4().hex[:16]}",
                "title": _normalize_text(title) or current.title,
                "document_family": current.document_family,
                "status": _normalize_text(status) or current.status,
                "content": _normalize_text(content) or current.content,
                "version": current.version + 1,
                "effective_date": (
                    _normalize_optional_text(effective_date)
                    if effective_date is not None
                    else current.effective_date
                ),
                "expiration_date": (
                    _normalize_optional_text(expiration_date)
                    if expiration_date is not None
                    else current.expiration_date
                ),
                "is_default": current.is_default,
                "customer_id": current.customer_id,
                "project_id": current.project_id,
                "transaction_id": current.transaction_id,
                "archived": False,
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
                "previous_block_id": current.block_id,
            }
        )

        blocks = self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        blocks = [
            (
                TermsAndConditionsBlock.from_dict(
                    {
                        **item.to_dict(),
                        "is_default": False,
                        "updated_at": now,
                        "updated_by": actor,
                    }
                )
                if item.block_id == current.block_id and current.is_default
                else item
            )
            for item in blocks
        ]
        blocks.append(created)
        self._validate_default_uniqueness(blocks)
        self._store_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            blocks=blocks,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.version_created",
            details={
                "block_id": created.block_id,
                "previous_block_id": current.block_id,
                "version": created.version,
            },
        )
        return created

    def assign_default_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
        actor: str,
    ) -> TermsAndConditionsBlock:
        target = self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=block_id,
        )
        if not target.is_tenant_default_candidate:
            raise ValueError("default assignment requires an active tenant-level block")
        now = _now_iso()
        blocks = self._list_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        updated: list[TermsAndConditionsBlock] = []
        for item in blocks:
            if item.document_family != target.document_family:
                updated.append(item)
                continue
            should_default = item.block_id == target.block_id
            updated.append(
                TermsAndConditionsBlock.from_dict(
                    {
                        **item.to_dict(),
                        "is_default": should_default,
                        "updated_at": now,
                        "updated_by": actor,
                    }
                )
            )
        self._validate_default_uniqueness(updated)
        self._store_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            blocks=updated,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.default_assigned",
            details={
                "block_id": target.block_id,
                "document_family": target.document_family,
            },
        )
        return self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=target.block_id,
        )

    def archive_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
        actor: str,
    ) -> TermsAndConditionsBlock:
        current = self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=block_id,
        )
        now = _now_iso()
        updated = TermsAndConditionsBlock.from_dict(
            {
                **current.to_dict(),
                "archived": True,
                "is_default": False,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        self._replace_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block=updated,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.archived",
            details={"block_id": updated.block_id},
        )
        return updated

    def restore_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        block_id: str,
        actor: str,
    ) -> TermsAndConditionsBlock:
        current = self.terms_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block_id=block_id,
        )
        now = _now_iso()
        should_be_default = bool(current.is_default)
        if (
            not should_be_default
            and current.customer_id is None
            and current.project_id is None
            and current.transaction_id is None
            and current.status == "active"
        ):
            existing_default = next(
                (
                    item
                    for item in self.list_terms_and_conditions_blocks(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        document_family=current.document_family,
                        include_archived=False,
                    )
                    if item.is_default and not item.archived
                ),
                None,
            )
            should_be_default = existing_default is None
        updated = TermsAndConditionsBlock.from_dict(
            {
                **current.to_dict(),
                "archived": False,
                "is_default": should_be_default,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        self._replace_block(
            tenant_id=tenant_id,
            organization_id=organization_id,
            block=updated,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.restored",
            details={"block_id": updated.block_id},
        )
        return updated

    def resolve_terms_and_conditions_block(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str,
        as_of: str | None = None,
        customer_id: str | None = None,
        project_id: str | None = None,
        transaction_id: str | None = None,
    ) -> TermsAndConditionsBlock | None:
        family = _normalize_text(document_family).lower()
        if family not in _ALLOWED_TERMS_DOCUMENT_FAMILIES:
            raise ValueError("unsupported terms document_family")
        timestamp = _normalize_text(as_of) or _now_iso()
        customer = _normalize_optional_text(customer_id)
        project = _normalize_optional_text(project_id)
        transaction = _normalize_optional_text(transaction_id)

        candidates = []
        for block in self.list_terms_and_conditions_blocks(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_family=family,
            include_archived=False,
        ):
            if block.status != "active":
                continue
            if not _is_effective(
                effective_date=block.effective_date,
                expiration_date=block.expiration_date,
                as_of=timestamp,
            ):
                continue
            if block.transaction_id and block.transaction_id != transaction:
                continue
            if block.project_id and block.project_id != project:
                continue
            if block.customer_id and block.customer_id != customer:
                continue
            if (
                block.customer_id is None
                and block.project_id is None
                and block.transaction_id is None
                and not block.is_default
            ):
                continue
            candidates.append(block)

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item.scope_rank,
                item.version,
                item.updated_at,
            ),
            reverse=True,
        )
        return candidates[0]

    def terms_and_conditions_snapshot(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str,
        transaction_id: str | None = None,
        customer_id: str | None = None,
        project_id: str | None = None,
        explicit_block_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        source = "resolved"
        block: TermsAndConditionsBlock | None = None
        if _normalize_optional_text(explicit_block_id):
            block = self.terms_block(
                tenant_id=tenant_id,
                organization_id=organization_id,
                block_id=_normalize_text(explicit_block_id),
            )
            source = "explicit"
        else:
            block = self.resolve_terms_and_conditions_block(
                tenant_id=tenant_id,
                organization_id=organization_id,
                document_family=document_family,
                transaction_id=transaction_id,
                customer_id=customer_id,
                project_id=project_id,
            )
        if block is None:
            return None

        reference = {
            "block_id": block.block_id,
            "document_family": block.document_family,
            "version": block.version,
            "source": source,
            "is_default": block.is_default,
            "customer_id": block.customer_id,
            "project_id": block.project_id,
            "transaction_id": block.transaction_id,
            "resolved_at": _now_iso(),
        }
        snapshot = {
            "block_id": block.block_id,
            "title": block.title,
            "document_family": block.document_family,
            "version": block.version,
            "content": block.content,
            "effective_date": block.effective_date,
            "expiration_date": block.expiration_date,
            "captured_at": _now_iso(),
        }
        return reference, snapshot

    def export_terms_and_conditions_blocks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.list_terms_and_conditions_blocks(
                tenant_id=tenant_id,
                organization_id=organization_id,
                include_archived=True,
            )
        ]

    def replace_terms_and_conditions_blocks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        blocks_payload: list[dict[str, Any]],
        actor: str,
        reason: str,
    ) -> None:
        blocks: list[TermsAndConditionsBlock] = []
        for payload in list(blocks_payload or []):
            if not isinstance(payload, dict):
                continue
            block = TermsAndConditionsBlock.from_dict(payload)
            blocks.append(block)
        if not blocks:
            return
        self._validate_default_uniqueness(blocks)
        self._store_terms_blocks_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            blocks=blocks,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.terms.runtime_sync",
            details={"reason": reason, "count": len(blocks)},
        )

    def _list_document_templates_for_scope(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[DocumentTemplateBlock]:
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(self.state["organization_settings"].get(key) or {})
        payload = list(scoped.get("document_templates") or [])
        rows: list[DocumentTemplateBlock] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                rows.append(DocumentTemplateBlock.from_dict(item))
            except ValueError:
                continue
        return rows

    def _store_document_templates_for_scope(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        templates: list[DocumentTemplateBlock],
    ) -> None:
        key = _tenant_scope_key(tenant_id, organization_id)
        scoped = dict(self.state["organization_settings"].get(key) or {})
        scoped["document_templates"] = [item.to_dict() for item in templates]
        self.state["organization_settings"][key] = scoped

    def _validate_template_default_uniqueness(
        self,
        templates: list[DocumentTemplateBlock],
    ) -> None:
        defaults: dict[str, str] = {}
        for template in templates:
            if not template.is_default or not template.is_tenant_default_candidate:
                continue
            prior = defaults.get(template.document_family)
            if prior and prior != template.template_id:
                raise ValueError(
                    "only one active default template is allowed per document family"
                )
            defaults[template.document_family] = template.template_id

    def list_document_templates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str | None = None,
        include_archived: bool = False,
    ) -> list[DocumentTemplateBlock]:
        family = _normalize_optional_text(document_family)
        if family is not None:
            family = family.lower()
            if family not in _ALLOWED_TEMPLATE_DOCUMENT_FAMILIES:
                raise ValueError("unsupported template document_family")
        rows: list[DocumentTemplateBlock] = []
        for template in self._list_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        ):
            if family and template.document_family != family:
                continue
            if not include_archived and template.archived:
                continue
            rows.append(template)
        rows.sort(
            key=lambda item: (item.document_family, item.updated_at, item.version)
        )
        return rows

    def create_document_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        title: str,
        document_family: str,
        status: str,
        content: str,
        section_config: dict[str, bool] | None,
        is_default: bool,
        customer_id: str | None = None,
        project_id: str | None = None,
        transaction_id: str | None = None,
    ) -> DocumentTemplateBlock:
        now = _now_iso()
        template = DocumentTemplateBlock.from_dict(
            {
                "template_id": f"template-{uuid4().hex[:16]}",
                "title": title,
                "document_family": document_family,
                "status": status,
                "content": content,
                "version": 1,
                "section_config": dict(section_config or {}),
                "visible_columns": [],
                "branding_logo_reference": None,
                "is_default": bool(is_default),
                "customer_id": customer_id,
                "project_id": project_id,
                "transaction_id": transaction_id,
                "archived": False,
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        if template.is_default and not template.is_tenant_default_candidate:
            raise ValueError("default flag is only allowed on tenant-level templates")
        templates = self._list_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        if template.is_default:
            demoted: list[DocumentTemplateBlock] = []
            for item in templates:
                if (
                    item.document_family == template.document_family
                    and item.is_tenant_default_candidate
                    and item.is_default
                ):
                    demoted.append(
                        DocumentTemplateBlock.from_dict(
                            {
                                **item.to_dict(),
                                "is_default": False,
                                "updated_at": now,
                                "updated_by": actor,
                            }
                        )
                    )
                else:
                    demoted.append(item)
            templates = demoted
        templates.append(template)
        self._validate_template_default_uniqueness(templates)
        self._store_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            templates=templates,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.document_template.created",
            details={
                "template_id": template.template_id,
                "document_family": template.document_family,
            },
        )
        return template

    def create_document_template_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        template_id: str,
        actor: str,
        title: str | None = None,
        content: str | None = None,
        status: str | None = None,
        section_config: dict[str, bool] | None = None,
    ) -> DocumentTemplateBlock:
        current = self.document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            template_id=template_id,
        )
        now = _now_iso()
        created = DocumentTemplateBlock.from_dict(
            {
                "template_id": f"template-{uuid4().hex[:16]}",
                "title": _normalize_text(title) or current.title,
                "document_family": current.document_family,
                "status": _normalize_text(status) or current.status,
                "content": _normalize_text(content) or current.content,
                "version": current.version + 1,
                "section_config": dict(section_config or current.section_config),
                "visible_columns": list(current.visible_columns),
                "branding_logo_reference": current.branding_logo_reference,
                "is_default": current.is_default,
                "customer_id": current.customer_id,
                "project_id": current.project_id,
                "transaction_id": current.transaction_id,
                "archived": False,
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
                "previous_template_id": current.template_id,
            }
        )
        templates = self._list_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        templates = [
            (
                DocumentTemplateBlock.from_dict(
                    {
                        **item.to_dict(),
                        "is_default": False,
                        "updated_at": now,
                        "updated_by": actor,
                    }
                )
                if item.template_id == current.template_id and current.is_default
                else item
            )
            for item in templates
        ]
        templates.append(created)
        self._validate_template_default_uniqueness(templates)
        self._store_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            templates=templates,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.document_template.version_created",
            details={
                "template_id": created.template_id,
                "previous_template_id": current.template_id,
                "version": created.version,
            },
        )
        return created

    def document_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        template_id: str,
    ) -> DocumentTemplateBlock:
        normalized = _normalize_text(template_id)
        for item in self._list_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        ):
            if item.template_id == normalized:
                return item
        raise ValueError("document template was not found")

    def assign_default_document_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        template_id: str,
        actor: str,
    ) -> DocumentTemplateBlock:
        target = self.document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            template_id=template_id,
        )
        if not target.is_tenant_default_candidate:
            raise ValueError(
                "default assignment requires an active tenant-level template"
            )
        now = _now_iso()
        templates = self._list_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        updated: list[DocumentTemplateBlock] = []
        for item in templates:
            if item.document_family != target.document_family:
                updated.append(item)
                continue
            updated.append(
                DocumentTemplateBlock.from_dict(
                    {
                        **item.to_dict(),
                        "is_default": item.template_id == target.template_id,
                        "updated_at": now,
                        "updated_by": actor,
                    }
                )
            )
        self._validate_template_default_uniqueness(updated)
        self._store_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            templates=updated,
        )
        return self.document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            template_id=target.template_id,
        )

    def duplicate_document_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        template_id: str,
        actor: str,
        title: str | None = None,
    ) -> DocumentTemplateBlock:
        source = self.document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            template_id=template_id,
        )
        return self.create_document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            title=_normalize_text(title) or f"{source.title} Copy",
            document_family=source.document_family,
            status=source.status,
            content=source.content,
            section_config=source.section_config,
            is_default=False,
            customer_id=source.customer_id,
            project_id=source.project_id,
            transaction_id=source.transaction_id,
        )

    def document_template_preview(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        template_id: str,
    ) -> dict[str, Any]:
        template = self.document_template(
            tenant_id=tenant_id,
            organization_id=organization_id,
            template_id=template_id,
        )
        return {
            "template_id": template.template_id,
            "title": template.title,
            "document_family": template.document_family,
            "version": template.version,
            "status": template.status,
            "section_config": dict(template.section_config),
            "visible_columns": list(template.visible_columns),
            "branding_logo_reference": template.branding_logo_reference,
            "content_preview": template.content[:5000],
        }

    def resolve_document_template(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_family: str,
        customer_id: str | None = None,
        project_id: str | None = None,
        transaction_id: str | None = None,
        explicit_template_id: str | None = None,
    ) -> DocumentTemplateBlock | None:
        if _normalize_optional_text(explicit_template_id):
            selected = self.document_template(
                tenant_id=tenant_id,
                organization_id=organization_id,
                template_id=_normalize_text(explicit_template_id),
            )
            if selected.archived or selected.status != "active":
                raise ValueError("explicit template is not active")
            return selected

        family = _normalize_text(document_family).lower()
        customer = _normalize_optional_text(customer_id)
        project = _normalize_optional_text(project_id)
        transaction = _normalize_optional_text(transaction_id)
        candidates: list[DocumentTemplateBlock] = []
        for template in self.list_document_templates(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_family=family,
            include_archived=False,
        ):
            if template.status != "active":
                continue
            if template.transaction_id and template.transaction_id != transaction:
                continue
            if template.project_id and template.project_id != project:
                continue
            if template.customer_id and template.customer_id != customer:
                continue
            if (
                template.customer_id is None
                and template.project_id is None
                and template.transaction_id is None
                and not template.is_default
            ):
                continue
            candidates.append(template)
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (item.scope_rank, item.version, item.updated_at),
            reverse=True,
        )
        return candidates[0]

    def export_document_templates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.list_document_templates(
                tenant_id=tenant_id,
                organization_id=organization_id,
                include_archived=True,
            )
        ]

    def replace_document_templates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        templates_payload: list[dict[str, Any]],
        actor: str,
        reason: str,
    ) -> None:
        templates: list[DocumentTemplateBlock] = []
        for payload in list(templates_payload or []):
            if not isinstance(payload, dict):
                continue
            templates.append(DocumentTemplateBlock.from_dict(payload))
        if not templates:
            return
        self._validate_template_default_uniqueness(templates)
        self._store_document_templates_for_scope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            templates=templates,
        )
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="organization.document_template.runtime_sync",
            details={"reason": reason, "count": len(templates)},
        )

    def personal_preferences(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
    ) -> PersonalPreferences:
        key = _user_scope_key(tenant_id, organization_id, user_id)
        payload = dict(self.state["personal_preferences"].get(key) or {})
        defaults = PersonalPreferences().to_dict()
        defaults.update(payload)
        return PersonalPreferences(**defaults)

    def update_personal_preferences(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        actor: str,
        updates: dict[str, Any],
    ) -> PersonalPreferences:
        invalid_keys = sorted(
            key
            for key in updates.keys()
            if key not in _ALLOWED_PERSONAL_PREFERENCE_KEYS
        )
        if invalid_keys:
            raise ValueError(
                "unsupported personal preference keys: " + ", ".join(invalid_keys)
            )
        restricted = sorted(
            key for key in updates.keys() if key in _RESTRICTED_PERSONAL_OVERRIDE_KEYS
        )
        if restricted:
            raise ValueError(
                "personal preferences cannot override tenant policy keys: "
                + ", ".join(restricted)
            )

        prior = self.personal_preferences(
            tenant_id=tenant_id,
            organization_id=organization_id,
            user_id=user_id,
        )
        next_payload = prior.to_dict()
        next_payload.update(dict(updates or {}))
        next_preferences = PersonalPreferences(**next_payload)

        key = _user_scope_key(tenant_id, organization_id, user_id)
        self.state["personal_preferences"][key] = next_preferences.to_dict()
        self._append_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            action="personal.preferences.updated",
            details={
                "user_id": user_id,
                "prior": prior.to_dict(),
                "current": next_preferences.to_dict(),
            },
        )
        return next_preferences

    def audit_events(
        self,
        *,
        tenant_id: str,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in list(self.state.get("audit_events") or [])
            if _normalize_text(item.get("tenant_id")) == tenant_id
            and _normalize_text(item.get("organization_id")) == organization_id
        ]

    def immutable_audit_events(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in list(self.state.get("immutable_audit_events") or [])
            if isinstance(item, dict)
            and _normalize_text(dict(item.get("target") or {}).get("tenant_id"))
            == tenant_id
            and _normalize_text(dict(item.get("target") or {}).get("organization_id"))
            == organization_id
        ]
        rows.sort(
            key=lambda item: (
                _normalize_text(item.get("occurred_at")),
                _normalize_text(item.get("event_id")),
            )
        )
        return rows[-max(1, int(limit)) :]
