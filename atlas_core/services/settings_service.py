"""Settings workspace service for organization and personal preferences."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
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
}


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
            raise ValueError("document_family must be estimate or sales_order")
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
                raise ValueError("document_family must be estimate or sales_order")
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
            raise ValueError("document_family must be estimate or sales_order")

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
            raise ValueError("document_family must be estimate or sales_order")
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
