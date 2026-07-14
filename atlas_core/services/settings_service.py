"""Settings workspace service for organization and personal preferences."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
        }

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "organization_settings": {},
            "personal_preferences": {},
            "audit_events": [],
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
