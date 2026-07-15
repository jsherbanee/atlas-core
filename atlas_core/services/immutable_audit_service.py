"""Immutable audit activity engine with history compatibility adapters."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Protocol

from atlas_core.contracts.audit_contracts import (
    AuditActor,
    AuditExportRecord,
    AuditPermissionReference,
    AuditRetentionClass,
    AuditTarget,
    ImmutableAuditEvent,
    now_iso,
)


class _HistoryProtocol(Protocol):
    def append_event(
        self, project_id: str, event_type: str, payload: dict[str, Any]
    ) -> None: ...

    def list_events(
        self, project_id: str, limit: int = 100
    ) -> list[dict[str, Any]]: ...


_REDACT_KEYS = {
    "password",
    "token",
    "secret",
    "api_key",
    "private_key",
    "access_key",
    "authorization",
    "credential",
}


class ImmutableAuditService:
    """Append-only audit events persisted through the existing HistoryRepository."""

    def __init__(self, history_repository: _HistoryProtocol) -> None:
        self.history_repository = history_repository

    def append_event(
        self,
        *,
        project_id: str,
        action: str,
        actor_id: str,
        actor_type: str = "user",
        actor_display_name: str | None = None,
        tenant_id: str,
        organization_id: str,
        target_type: str,
        target_id: str,
        source: str = "atlas",
        correlation_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        permission_reference: dict[str, Any] | None = None,
        retention_class: AuditRetentionClass = AuditRetentionClass.OPERATIONAL,
    ) -> ImmutableAuditEvent:
        occurred_at = now_iso()
        redacted_before = self._redact_payload(before or {})
        redacted_after = self._redact_payload(after or {})
        redacted_context = self._redact_payload(context or {})
        previous_event_id = self._latest_event_id(project_id)
        event = ImmutableAuditEvent(
            event_id=self._stable_event_id(
                project_id=project_id,
                action=action,
                occurred_at=occurred_at,
                tenant_id=tenant_id,
                organization_id=organization_id,
                target_type=target_type,
                target_id=target_id,
                source=source,
                correlation_id=correlation_id,
            ),
            action=action,
            actor=AuditActor(
                actor_id=actor_id,
                actor_type=actor_type,
                display_name=actor_display_name,
            ),
            target=AuditTarget(
                target_type=target_type,
                target_id=target_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
            occurred_at=occurred_at,
            retention_class=retention_class,
            source=source,
            correlation_id=correlation_id,
            before=redacted_before,
            after=redacted_after,
            change_summary=self._change_summary(redacted_before, redacted_after),
            context=redacted_context,
            permission_reference=(
                AuditPermissionReference.from_dict(permission_reference)
                if isinstance(permission_reference, dict)
                else None
            ),
            previous_event_id=previous_event_id,
        )
        self.history_repository.append_event(project_id, "audit_event", event.to_dict())
        return event

    def list_events(
        self,
        *,
        project_id: str,
        tenant_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = self.history_repository.list_events(
            project_id, limit=max(limit * 3, 100)
        )
        normalized = [
            self._normalize_history_event(project_id=project_id, row=item)
            for item in rows
            if isinstance(item, dict)
        ]
        filtered = [
            item
            for item in normalized
            if item is not None
            and dict(item.get("target") or {}).get("tenant_id") == tenant_id
            and dict(item.get("target") or {}).get("organization_id") == organization_id
        ]
        filtered.sort(
            key=lambda item: (
                str(item.get("occurred_at") or ""),
                str(item.get("event_id") or ""),
            )
        )
        return filtered[-max(1, int(limit)) :]

    def export_events(
        self,
        *,
        project_id: str,
        tenant_id: str,
        organization_id: str,
        limit: int = 5000,
    ) -> dict[str, Any]:
        events = self.list_events(
            project_id=project_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            limit=limit,
        )
        canonical = json.dumps(events, sort_keys=True, separators=(",", ":"))
        export_digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
        export = AuditExportRecord(
            export_id=f"audit-export:{project_id}:{export_digest}",
            generated_at=now_iso(),
            project_id=project_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            event_count=len(events),
            events=events,
        )
        return export.to_dict()

    def _normalize_history_event(
        self,
        *,
        project_id: str,
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        event_type = str(row.get("event_type") or "").strip()
        timestamp = str(row.get("timestamp") or now_iso())
        payload = dict(row.get("payload") or {})

        if event_type == "audit_event" and isinstance(payload, dict):
            try:
                return ImmutableAuditEvent.from_dict(payload).to_dict()
            except ValueError:
                return None

        legacy_target = AuditTarget(
            target_type="project",
            target_id=project_id,
            tenant_id=str(payload.get("tenant_id") or "local"),
            organization_id=str(payload.get("organization_id") or "atlas"),
            project_id=project_id,
        )
        action = event_type or "legacy.event"
        material = {
            "action": action,
            "timestamp": timestamp,
            "payload": payload,
            "project_id": project_id,
        }
        legacy_event_id = hashlib.sha1(
            json.dumps(material, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        event = ImmutableAuditEvent(
            event_id=f"audit-legacy:{legacy_event_id}",
            action=f"legacy.{action}",
            actor=AuditActor(actor_id="legacy-system", actor_type="system"),
            target=legacy_target,
            occurred_at=timestamp,
            retention_class=AuditRetentionClass.OPERATIONAL,
            source="history_compatibility",
            before={},
            after={},
            change_summary={"changed_fields": sorted(payload.keys())},
            context=self._redact_payload(payload),
        )
        return event.to_dict()

    @staticmethod
    def _stable_event_id(
        *,
        project_id: str,
        action: str,
        occurred_at: str,
        tenant_id: str,
        organization_id: str,
        target_type: str,
        target_id: str,
        source: str,
        correlation_id: str | None,
    ) -> str:
        token = json.dumps(
            {
                "project_id": project_id,
                "action": action,
                "occurred_at": occurred_at,
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "target_type": target_type,
                "target_id": target_id,
                "source": source,
                "correlation_id": correlation_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:20]
        return f"audit:{digest}"

    def _latest_event_id(self, project_id: str) -> str | None:
        rows = self.history_repository.list_events(project_id, limit=200)
        for row in rows:
            payload = dict(row.get("payload") or {}) if isinstance(row, dict) else {}
            if str(row.get("event_type") or "") == "audit_event" and payload.get(
                "event_id"
            ):
                return str(payload.get("event_id"))
        return None

    @classmethod
    def _change_summary(
        cls,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        before_keys = set(before.keys())
        after_keys = set(after.keys())
        changed = sorted(
            key
            for key in before_keys | after_keys
            if deepcopy(before.get(key)) != deepcopy(after.get(key))
        )
        return {
            "added_fields": sorted(after_keys - before_keys),
            "removed_fields": sorted(before_keys - after_keys),
            "changed_fields": changed,
        }

    @classmethod
    def _redact_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in dict(payload or {}).items():
            normalized_key = str(key).strip().lower()
            if any(token in normalized_key for token in _REDACT_KEYS):
                redacted[key] = "[REDACTED]"
                continue
            if isinstance(value, dict):
                redacted[key] = cls._redact_payload(value)
                continue
            if isinstance(value, list):
                redacted[key] = [
                    cls._redact_payload(item) if isinstance(item, dict) else item
                    for item in value
                ]
                continue
            redacted[key] = value
        return redacted
