"""Deterministic Organization merge orchestration for Knowledge role records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from atlas_core.domain import Organization, OrganizationRole
from atlas_core.services.master_library.commercial_product_service import (
    CommercialProductService,
)
from atlas_core.services.organization_directory_service import (
    OrganizationDirectoryService,
)

ROLE_ENTITY_TYPES = {
    "customer": OrganizationRole.CUSTOMER,
    "vendor": OrganizationRole.VENDOR,
    "manufacturer": OrganizationRole.MANUFACTURER,
}


class OrganizationMergeService:
    def __init__(
        self,
        *,
        organization_directory: OrganizationDirectoryService,
        product_service: CommercialProductService,
        tenant_id: str,
        organization_scope_id: str,
    ) -> None:
        self.organization_directory = organization_directory
        self.product_service = product_service
        self.tenant_id = _required("tenant_id", tenant_id)
        self.organization_scope_id = _required(
            "organization_scope_id", organization_scope_id
        )

    def ensure_organization_for_role_record(self, entity_id: str) -> Organization:
        entity = self._role_entity(entity_id)
        role = self._role_for_entity(entity)
        attributes = dict(entity.get("attributes") or {})
        existing_org_id = _safe_text(attributes.get("organization_id"))
        if existing_org_id:
            existing = self.organization_directory.get_organization(existing_org_id)
            if existing is not None:
                self.organization_directory.add_role_profile(
                    organization_id=existing.organization_id,
                    role=role,
                    profile=self._role_profile(entity),
                )
                self.product_service.link_role_entity_to_organization(
                    entity_id=entity_id,
                    organization_id=existing.organization_id,
                    role=role.value,
                )
                self._sync_organization_entity(existing)
                return existing
        organization = self.organization_directory.create_organization(
            name=_display_name(entity),
            role=role,
            website=_safe_text(attributes.get("website")) or None,
            phone=_safe_text(attributes.get("primary_phone") or attributes.get("phone"))
            or None,
            email=_safe_text(attributes.get("primary_email") or attributes.get("email"))
            or None,
            address=_safe_text(
                attributes.get("billing_address") or attributes.get("address")
            )
            or None,
            notes=_safe_text(entity.get("notes")) or None,
            aliases=list(entity.get("aliases") or []),
            tenant_id=self.tenant_id,
            organization_scope_id=self.organization_scope_id,
            role_profiles={role.value: self._role_profile(entity)},
        )
        self.product_service.link_role_entity_to_organization(
            entity_id=entity_id,
            organization_id=organization.organization_id,
            role=role.value,
        )
        self._sync_organization_entity(organization)
        self._audit(
            "organization_role_profile_created",
            organization.organization_id,
            {"source_entity_id": entity_id, "role": role.value},
        )
        return organization

    def duplicate_suggestions_for_role_record(
        self, entity_id: str
    ) -> list[dict[str, Any]]:
        entity = self._role_entity(entity_id)
        attributes = dict(entity.get("attributes") or {})
        candidate = {
            "canonical_name": entity.get("canonical_name"),
            "display_name": entity.get("display_name"),
            "aliases": list(entity.get("aliases") or []),
            "website": attributes.get("website"),
            "email": attributes.get("primary_email") or attributes.get("email"),
            "phone": attributes.get("primary_phone") or attributes.get("phone"),
            "address": attributes.get("billing_address") or attributes.get("address"),
            "tax_identifier_ref": attributes.get("tax_identifier_ref"),
        }
        return self.organization_directory.duplicate_suggestions(
            tenant_id=self.tenant_id,
            organization_scope_id=self.organization_scope_id,
            candidate=candidate,
        )

    def preview_merge(
        self,
        *,
        primary_organization_id: str,
        source_entity_ids: list[str],
        conflict_resolutions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sources = [self._source_payload(entity_id) for entity_id in source_entity_ids]
        preview = self.organization_directory.preview_merge(
            primary_organization_id=primary_organization_id,
            source_organizations=sources,
            tenant_id=self.tenant_id,
            organization_scope_id=self.organization_scope_id,
            conflict_resolutions=conflict_resolutions,
        )
        counts = self._relationship_reassignment_preview(source_entity_ids)
        preview["relationship_reassignment_preview"] = counts
        self._audit(
            "organization_merge_previewed",
            primary_organization_id,
            {
                "source_entity_ids": list(source_entity_ids),
                "correlation_id": preview.get("correlation_id"),
                "relationship_reassignment_preview": counts,
            },
        )
        return preview

    def confirm_merge(
        self,
        *,
        primary_organization_id: str,
        source_entity_ids: list[str],
        actor: str,
        reason: str,
        conflict_resolutions: dict[str, Any] | None = None,
        permission_granted: bool,
    ) -> dict[str, Any]:
        before = deepcopy(self.product_service.to_dict())
        try:
            preview = self.preview_merge(
                primary_organization_id=primary_organization_id,
                source_entity_ids=source_entity_ids,
                conflict_resolutions=conflict_resolutions,
            )
            relationship_counts = self.product_service.reassign_knowledge_relationships(
                source_entity_ids=source_entity_ids,
                target_entity_id=f"organization:{primary_organization_id}",
            )
            organization = self.organization_directory.confirm_merge(
                primary_organization_id=primary_organization_id,
                source_organizations=[
                    self._source_payload(entity_id) for entity_id in source_entity_ids
                ],
                tenant_id=self.tenant_id,
                organization_scope_id=self.organization_scope_id,
                actor=actor,
                reason=reason,
                conflict_resolutions=conflict_resolutions,
                permission_granted=permission_granted,
                relationship_reassignment_counts=relationship_counts,
            )
            for entity_id in source_entity_ids:
                self.product_service.mark_role_entity_merged(
                    entity_id=entity_id,
                    organization_id=primary_organization_id,
                    actor=actor,
                    reason=reason,
                    correlation_id=_safe_text(preview.get("correlation_id")),
                )
            self._sync_organization_entity(organization)
            self._audit(
                "organization_merge_confirmed",
                primary_organization_id,
                {
                    "source_entity_ids": list(source_entity_ids),
                    "actor": actor,
                    "reason": reason,
                    "correlation_id": preview.get("correlation_id"),
                    "relationship_reassignment_counts": relationship_counts,
                },
            )
            return {
                "organization": organization.to_dict(),
                "preview": preview,
                "relationship_reassignment_counts": relationship_counts,
            }
        except Exception:
            self.product_service.state = before
            self._audit(
                "organization_merge_failed",
                primary_organization_id,
                {"source_entity_ids": list(source_entity_ids)},
            )
            raise

    def legacy_redirect(self, entity_id: str) -> dict[str, Any] | None:
        entity = self.product_service.get_knowledge_entity(entity_id)
        if not entity:
            return None
        attributes = dict(entity.get("attributes") or {})
        target = _safe_text(attributes.get("merged_into_organization_id"))
        if not target:
            return None
        organization = self.organization_directory.get_organization(target)
        return organization.to_dict() if organization is not None else None

    def _role_entity(self, entity_id: str) -> dict[str, Any]:
        entity = self.product_service.get_knowledge_entity(entity_id)
        if entity is None:
            raise ValueError("Knowledge role record not found")
        role = _safe_text(entity.get("entity_type"))
        if role not in ROLE_ENTITY_TYPES:
            raise ValueError("Only Customer, Vendor, and Manufacturer records merge")
        attributes = dict(entity.get("attributes") or {})
        if _safe_text(attributes.get("merge_status")) == "redirected":
            raise ValueError("Merged source records are read-only redirects")
        return entity

    @staticmethod
    def _role_for_entity(entity: dict[str, Any]) -> OrganizationRole:
        role = ROLE_ENTITY_TYPES.get(_safe_text(entity.get("entity_type")))
        if role is None:
            raise ValueError("Unsupported role entity type")
        return role

    def _source_payload(self, entity_id: str) -> dict[str, Any]:
        entity = self._role_entity(entity_id)
        role = self._role_for_entity(entity)
        attributes = dict(entity.get("attributes") or {})
        return {
            "source_entity_id": entity_id,
            "role": role.value,
            "canonical_name": entity.get("canonical_name"),
            "display_name": entity.get("display_name"),
            "website": attributes.get("website"),
            "phone": attributes.get("primary_phone") or attributes.get("phone"),
            "email": attributes.get("primary_email") or attributes.get("email"),
            "address": attributes.get("billing_address") or attributes.get("address"),
            "notes": entity.get("notes"),
            "aliases": list(entity.get("aliases") or []),
            "profile": self._role_profile(entity),
        }

    def _role_profile(self, entity: dict[str, Any]) -> dict[str, Any]:
        role = self._role_for_entity(entity)
        attributes = dict(entity.get("attributes") or {})
        identifier_key = {
            OrganizationRole.CUSTOMER: "customer_id",
            OrganizationRole.VENDOR: "vendor_id",
            OrganizationRole.MANUFACTURER: "manufacturer_id",
        }[role]
        identifier = _safe_text(
            attributes.get(identifier_key),
            _safe_text(entity.get("entity_id")).split(":", 1)[-1],
        )
        profile = {
            "source_entity_id": entity.get("entity_id"),
            "identifiers": [identifier] if identifier else [],
            "display_name": entity.get("display_name"),
        }
        for key in [
            "billing_terms",
            "payment_terms",
            "tax_exemption_status",
            "purchasing_channel",
            "manufacturer_code",
            "default_vendor",
            "support_information",
            "manufacturer_representative",
        ]:
            if _safe_text(attributes.get(key)):
                profile[key] = attributes.get(key)
        return profile

    def _relationship_reassignment_preview(
        self, source_entity_ids: list[str]
    ) -> dict[str, int]:
        sources = set(source_entity_ids)
        count = 0
        for item in self.product_service.state.get(
            "knowledge_relationships", {}
        ).values():
            if (
                item.get("source_entity_id") in sources
                or item.get("target_entity_id") in sources
            ):
                count += 1
        return {
            "knowledge_relationships": count,
            "legacy_records": len(source_entity_ids),
        }

    def _sync_organization_entity(self, organization: Organization) -> None:
        self.product_service.upsert_organization_entity(
            organization_id=organization.organization_id,
            canonical_name=organization.canonical_name,
            display_name=organization.display_name,
            roles=[role.value for role in organization.supported_roles],
            aliases=list(organization.aliases),
            notes=organization.notes or "",
            attributes={
                "tenant_id": organization.tenant_id,
                "organization_scope_id": organization.organization_scope_id,
                "role_profiles": dict(organization.role_profiles),
                "merge_history": list(organization.merge_history),
                "redirected_from": list(organization.redirected_from),
            },
            active=organization.active,
        )

    def _audit(
        self,
        event_type: str,
        organization_id: str,
        payload: dict[str, Any],
    ) -> None:
        self.product_service._append_knowledge_audit(
            event_type=event_type,
            entity_id=f"organization:{organization_id}",
            payload={
                "tenant_id": self.tenant_id,
                "organization_scope_id": self.organization_scope_id,
                **payload,
            },
        )


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _required(label: str, value: Any) -> str:
    text = _safe_text(value)
    if not text:
        raise PermissionError(f"{label} is required")
    return text


def _display_name(entity: dict[str, Any]) -> str:
    return _safe_text(
        entity.get("display_name"),
        _safe_text(entity.get("canonical_name"), "Organization"),
    )
