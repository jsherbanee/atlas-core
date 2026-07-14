"""Registry-backed adapters for Atlas universal object contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from atlas_core.contracts.universal_object_contract import (
    UNIVERSAL_OBJECT_SCHEMA_VERSION,
    UniversalObject,
    UniversalObjectAction,
    UniversalObjectActivity,
    UniversalObjectIdentity,
    UniversalObjectIntelligenceHooks,
    UniversalObjectLifecycle,
    UniversalObjectLifecycleTransition,
    UniversalObjectMetadata,
    UniversalObjectPresentation,
    UniversalObjectRelationship,
)
from atlas_core.domain.av_lifecycle import AVLifecycleEngine, LifecyclePlan
from atlas_core.domain import Project

_LIFECYCLE_ENGINE = AVLifecycleEngine.default()

UniversalObjectBuilder = Callable[..., UniversalObject]


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or default


def _normalize_name(value: Any) -> str:
    return " ".join(_safe_text(value, "").strip().split())


def _source_dates(source: Any) -> tuple[str | None, str | None]:
    if isinstance(source, Project):
        return (None, None)
    payload = dict(source) if isinstance(source, dict) else {}
    return (
        _safe_text(payload.get("created_at"), "") or None,
        _safe_text(payload.get("updated_at"), "") or None,
    )


def _status_and_lifecycle(source: Any) -> tuple[str | None, str | None, bool]:
    if isinstance(source, Project):
        status = _safe_text(getattr(source.status, "value", source.status), "")
        return (status or None, status or None, False)
    payload = dict(source) if isinstance(source, dict) else {}
    active = bool(payload.get("active", True))
    archived = bool(payload.get("archived", False) or not active)
    status = _safe_text(
        payload.get("status"),
        _safe_text(
            payload.get("current_status"), _safe_text(payload.get("review_status"), "")
        ),
    )
    lifecycle = _safe_text(
        payload.get("lifecycle_state"),
        _safe_text(
            payload.get("lifecycle_status"),
            _safe_text(payload.get("lifecycle_stage"), status),
        ),
    )
    lifecycle_plan_payload = payload.get("lifecycle_plan")
    if isinstance(lifecycle_plan_payload, dict) and lifecycle_plan_payload.get(
        "current_stage_key"
    ):
        lifecycle = _safe_text(
            lifecycle_plan_payload.get("current_stage_key"), lifecycle
        )
        status = _safe_text(
            lifecycle_plan_payload.get("legacy_project_status"),
            _safe_text(lifecycle_plan_payload.get("current_stage_status"), status),
        )
    return (status or None, lifecycle or None, archived)


def _default_actions(
    *, archived: bool, document_available: bool
) -> list[UniversalObjectAction]:
    actions = [
        UniversalObjectAction("open", "Open", "open", target_route="object"),
        UniversalObjectAction(
            "edit",
            "Edit",
            "edit",
            enabled=not archived,
            disabled_reason=("Object is archived" if archived else None),
        ),
        UniversalObjectAction(
            "archive",
            "Archive",
            "archive",
            enabled=not archived,
            destructive=True,
            confirmation_required=True,
            disabled_reason=("Object is already archived" if archived else None),
        ),
        UniversalObjectAction(
            "restore",
            "Restore",
            "restore",
            enabled=archived,
            disabled_reason=(None if archived else "Object is active"),
        ),
        UniversalObjectAction("export", "Export", "export"),
        UniversalObjectAction("view_activity", "View Activity", "view_activity"),
        UniversalObjectAction(
            "view_documents",
            "View Documents",
            "view_documents",
            enabled=document_available,
            disabled_reason=(None if document_available else "No documents available"),
        ),
        UniversalObjectAction(
            "return_to_origin", "Return to Origin", "return_to_origin"
        ),
    ]
    return actions


def _default_lifecycle(
    *, state: str | None, archived: bool, source: dict[str, Any] | None = None
) -> UniversalObjectLifecycle:
    current_state = state or ("archived" if archived else "active")
    transitions = [
        UniversalObjectLifecycleTransition(state="archived", reason="archive"),
        UniversalObjectLifecycleTransition(state="active", reason="restore"),
    ]
    if source is not None:
        lifecycle_plan_payload = source.get("lifecycle_plan")
        if isinstance(lifecycle_plan_payload, dict) and lifecycle_plan_payload.get(
            "current_stage_key"
        ):
            try:
                plan = LifecyclePlan.from_dict(lifecycle_plan_payload)
                transitions = [
                    UniversalObjectLifecycleTransition(
                        state=item.to_stage_key,
                        reason=item.label,
                    )
                    for item in _LIFECYCLE_ENGINE.available_transitions(plan)
                ]
            except Exception:
                transitions = transitions
    return UniversalObjectLifecycle(
        current_state=current_state,
        allowed_transitions=transitions,
        terminal_states=["archived"],
        archived=archived,
    )


def _project_scope(source: Any, explicit_project_id: str | None) -> str | None:
    if explicit_project_id:
        return explicit_project_id
    if isinstance(source, Project):
        return _safe_text(source.project_id, "") or None
    payload = dict(source) if isinstance(source, dict) else {}
    for key in ["workspace_id", "project_id", "atlas_bid_id"]:
        value = _safe_text(payload.get(key), "")
        if value:
            return value
    return None


def _make_identity(
    *,
    object_id: str,
    object_type: str,
    tenant_id: str,
    owning_workspace: str,
    canonical_display_name: str,
    secondary_identifier: str | None,
    owning_project_id: str | None,
    status: str | None,
    lifecycle_state: str | None,
    created_at: str | None,
    updated_at: str | None,
    source_authority: str,
) -> UniversalObjectIdentity:
    return UniversalObjectIdentity(
        object_id=object_id,
        object_type=object_type,
        tenant_id=tenant_id,
        owning_workspace=owning_workspace,
        canonical_display_name=canonical_display_name,
        secondary_identifier=secondary_identifier,
        owning_project_id=owning_project_id,
        status=status,
        lifecycle_state=lifecycle_state,
        schema_version=UNIVERSAL_OBJECT_SCHEMA_VERSION,
        source_authority=source_authority,
        created_at=created_at,
        updated_at=updated_at,
    )


def _relationship_targets(source: dict[str, Any]) -> list[tuple[str, str, str]]:
    targets: list[tuple[str, str, str]] = []
    for key, relationship_type, object_type in [
        ("related_products", "related-product", "product"),
        ("project_references", "used-in-project", "project"),
        ("referenced_drawings", "references", "drawing"),
        ("referenced_specifications", "references", "specification"),
        ("referenced_equipment", "references", "equipment"),
        ("referenced_systems", "references", "system"),
        ("referenced_evidence", "references", "evidence"),
    ]:
        for item in list(source.get(key) or []):
            if isinstance(item, dict):
                target_id = ""
                for candidate_key in [
                    "target_product_id",
                    "project_id",
                    "equipment_id",
                    "drawing_number",
                    "section",
                    "system",
                    "source_file",
                ]:
                    target_id = _safe_text(item.get(candidate_key), "")
                    if target_id:
                        break
                display_name = _safe_text(
                    item.get("display_name"),
                    _safe_text(
                        item.get("project_name"),
                        _safe_text(item.get("title"), target_id),
                    ),
                )
            else:
                target_id = _safe_text(item, "")
                display_name = target_id
            if target_id:
                targets.append((relationship_type, object_type, display_name))
    return targets


def _build_relationships(
    identity: UniversalObjectIdentity,
    source: dict[str, Any],
) -> list[UniversalObjectRelationship]:
    relationships: list[UniversalObjectRelationship] = []
    for index, (relationship_type, object_type, display_name) in enumerate(
        _relationship_targets(source)
    ):
        target_identity = UniversalObjectIdentity(
            object_id=display_name,
            object_type=object_type,
            tenant_id=identity.tenant_id,
            owning_workspace=(
                "Knowledge"
                if object_type
                in {
                    "customer",
                    "vendor",
                    "manufacturer",
                    "product",
                    "service",
                    "contact",
                    "location",
                    "project",
                }
                else "Projects"
            ),
            owning_project_id=(
                identity.owning_project_id
                if object_type
                in {"drawing", "specification", "equipment", "system", "evidence"}
                else None
            ),
            canonical_display_name=display_name,
            source_authority="atlas_reference",
        )
        relationships.append(
            UniversalObjectRelationship(
                relationship_id=f"{identity.universal_object_id}:{relationship_type}:{index}",
                source_identity=identity,
                target_identity=target_identity,
                relationship_type=relationship_type,
                direction="outgoing",
                tenant_id=identity.tenant_id,
            )
        )
    return relationships


def _activity_from_source(
    identity: UniversalObjectIdentity,
    source: dict[str, Any],
) -> list[UniversalObjectActivity]:
    activity_rows = list(source.get("activity_events") or [])
    activities: list[UniversalObjectActivity] = []
    for index, row in enumerate(activity_rows):
        if not isinstance(row, dict):
            continue
        activities.append(
            UniversalObjectActivity(
                activity_id=_safe_text(
                    row.get("activity_id"),
                    f"{identity.universal_object_id}:activity:{index}",
                ),
                object_identity=identity,
                activity_type=_safe_text(row.get("activity_type"), "updated"),
                actor=_safe_text(row.get("actor"), "system"),
                timestamp=_safe_text(
                    row.get("timestamp"),
                    identity.updated_at or identity.created_at or "n/a",
                ),
                tenant_id=identity.tenant_id,
                summary=_safe_text(row.get("summary"), "Activity"),
                details=dict(row.get("details") or {}),
                source=_safe_text(row.get("source"), "atlas"),
                related_objects=[
                    dict(item)
                    for item in list(row.get("related_objects") or [])
                    if isinstance(item, dict)
                ],
                before_state_ref=_safe_text(row.get("before_state_ref"), "") or None,
                after_state_ref=_safe_text(row.get("after_state_ref"), "") or None,
                project_scope=identity.owning_project_id,
            )
        )
    return activities


def _presentation(
    identity: UniversalObjectIdentity,
    *,
    secondary_label: str | None,
    supported_views: list[str],
    relationship_groups: list[str],
    activity_available: bool,
    document_available: bool,
) -> UniversalObjectPresentation:
    return UniversalObjectPresentation(
        primary_label=identity.canonical_display_name,
        secondary_label=secondary_label,
        icon_key=identity.object_type,
        status_label=identity.status,
        status_severity=(
            "warning"
            if identity.status and "review" in identity.status.lower()
            else "neutral"
        ),
        identity_fields=[
            "canonical_display_name",
            "object_type",
            "object_id",
            "secondary_identifier",
            "status",
            "lifecycle_state",
        ],
        summary_fields=["description", "aliases", "warnings"],
        supported_views=supported_views,
        supported_actions=[
            "open",
            "edit",
            "archive",
            "restore",
            "export",
            "view_activity",
            "view_documents",
            "return_to_origin",
        ],
        relationship_groups=relationship_groups,
        activity_available=activity_available,
        document_available=document_available,
    )


def _metadata_from_source(
    source: dict[str, Any], *, archived: bool
) -> UniversalObjectMetadata:
    return UniversalObjectMetadata(
        description=_safe_text(
            source.get("description"),
            _safe_text(source.get("notes"), _safe_text(source.get("title"), "")),
        )
        or None,
        aliases=[
            _safe_text(item, "")
            for item in list(source.get("aliases") or [])
            if _safe_text(item, "")
        ],
        tags=[
            _safe_text(item, "")
            for item in list(source.get("tags") or [])
            if _safe_text(item, "")
        ],
        external_identifiers={
            key: value
            for key, value in {
                "external_identifier": _safe_text(
                    source.get("external_identifier"), ""
                ),
                "client_project_number": _safe_text(
                    source.get("client_project_number"), ""
                ),
                "internal_project_number": _safe_text(
                    source.get("internal_project_number"), ""
                ),
            }.items()
            if value
        },
        source_references=[
            _safe_text(item, "")
            for item in list(
                source.get("source_refs") or source.get("source_documents") or []
            )
            if _safe_text(item, "")
        ],
        confidence=_safe_text(source.get("confidence"), "") or None,
        warnings=[
            _safe_text(item, "")
            for item in list(source.get("warnings") or [])
            if _safe_text(item, "")
        ],
        archived=archived,
        revision=_safe_text(
            source.get("revision"), _safe_text(source.get("version"), "")
        )
        or None,
        custom_metadata={
            key: value
            for key, value in dict(source).items()
            if key
            not in {
                "description",
                "notes",
                "title",
                "aliases",
                "tags",
                "external_identifier",
                "source_refs",
                "source_documents",
                "confidence",
                "warnings",
                "revision",
                "version",
            }
        },
        stewardship=_safe_text(source.get("owner"), "") or None,
        provenance={
            "source_file": _safe_text(source.get("source_file"), ""),
            "source_row": source.get("source_row"),
            "source_page": source.get("page"),
        },
    )


def _project_to_object(
    project: Project, *, tenant_id: str, owning_workspace: str
) -> UniversalObject:
    status, lifecycle_state, archived = _status_and_lifecycle(project)
    identity = _make_identity(
        object_id=_safe_text(project.project_id, "project"),
        object_type="project",
        tenant_id=tenant_id,
        owning_workspace=owning_workspace,
        owning_project_id=_safe_text(project.project_id, "") or None,
        canonical_display_name=_safe_text(project.name, "Project"),
        secondary_identifier=_safe_text(project.client_project_number, "")
        or _safe_text(project.internal_project_number, "")
        or None,
        status=status,
        lifecycle_state=lifecycle_state,
        created_at=None,
        updated_at=None,
        source_authority="project_domain",
    )
    metadata = UniversalObjectMetadata(
        description=_safe_text(project.location, "") or None,
        external_identifiers={
            key: value
            for key, value in {
                "client_project_number": _safe_text(project.client_project_number, ""),
                "internal_project_number": _safe_text(
                    project.internal_project_number, ""
                ),
            }.items()
            if value
        },
    )
    return UniversalObject(
        identity=identity,
        metadata=metadata,
        actions=_default_actions(archived=archived, document_available=True),
        lifecycle=_default_lifecycle(state=lifecycle_state, archived=archived),
        presentation=_presentation(
            identity,
            secondary_label=_safe_text(project.client, "") or None,
            supported_views=[
                "summary",
                "lifecycle",
                "details",
                "relationships",
                "activity",
                "history",
                "documents",
            ],
            relationship_groups=[
                "Related Customers",
                "Related Documents",
                "Related Services",
            ],
            activity_available=True,
            document_available=True,
        ),
        intelligence_hooks=UniversalObjectIntelligenceHooks(ai_context_eligible=True),
    )


def _dict_object(
    object_type: str,
    source: dict[str, Any],
    *,
    tenant_id: str,
    owning_workspace: str,
    owning_project_id: str | None,
    object_id_keys: list[str],
    display_name_keys: list[str],
    secondary_identifier_keys: list[str],
    source_authority: str,
    secondary_label: str | None,
    supported_views: list[str],
    relationship_groups: list[str],
    document_available: bool = False,
) -> UniversalObject:
    object_id = next(
        (
            _safe_text(source.get(key), "")
            for key in object_id_keys
            if _safe_text(source.get(key), "")
        ),
        "",
    )
    display_name = next(
        (
            _safe_text(source.get(key), "")
            for key in display_name_keys
            if _safe_text(source.get(key), "")
        ),
        object_id,
    )
    secondary_identifier = next(
        (
            _safe_text(source.get(key), "")
            for key in secondary_identifier_keys
            if _safe_text(source.get(key), "")
        ),
        "",
    )
    status, lifecycle_state, archived = _status_and_lifecycle(source)
    created_at, updated_at = _source_dates(source)
    identity = _make_identity(
        object_id=object_id,
        object_type=object_type,
        tenant_id=tenant_id,
        owning_workspace=owning_workspace,
        canonical_display_name=display_name,
        secondary_identifier=secondary_identifier or None,
        owning_project_id=owning_project_id,
        status=status,
        lifecycle_state=lifecycle_state,
        created_at=created_at,
        updated_at=updated_at,
        source_authority=source_authority,
    )
    return UniversalObject(
        identity=identity,
        metadata=_metadata_from_source(source, archived=archived),
        relationships=_build_relationships(identity, source),
        activity=_activity_from_source(identity, source),
        actions=_default_actions(
            archived=archived, document_available=document_available
        ),
        lifecycle=_default_lifecycle(
            state=lifecycle_state,
            archived=archived,
            source=source,
        ),
        presentation=_presentation(
            identity,
            secondary_label=secondary_label,
            supported_views=supported_views,
            relationship_groups=relationship_groups,
            activity_available=bool(source.get("activity_events")),
            document_available=document_available,
        ),
        intelligence_hooks=UniversalObjectIntelligenceHooks(
            confidence=_safe_text(source.get("confidence"), "") or None,
            unresolved_issues=[
                _safe_text(item, "")
                for item in list(source.get("warnings") or [])
                if _safe_text(item, "")
            ],
            ai_context_eligible=True,
        ),
    )


@dataclass(frozen=True)
class UniversalObjectAdapterDefinition:
    object_type: str
    builder: UniversalObjectBuilder


class UniversalObjectRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, UniversalObjectAdapterDefinition] = {}

    def register(
        self,
        object_type: str,
        builder: UniversalObjectBuilder,
    ) -> None:
        key = _safe_text(object_type).lower()
        if key in self._adapters:
            raise ValueError(f"duplicate universal object adapter registration: {key}")
        self._adapters[key] = UniversalObjectAdapterDefinition(
            object_type=key,
            builder=builder,
        )

    def adapt(
        self,
        object_type: str,
        source: Any,
        *,
        tenant_id: str,
        owning_workspace: str,
        owning_project_id: str | None = None,
    ) -> UniversalObject:
        key = _safe_text(object_type).lower()
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(f"no universal object adapter registered for {key}")
        return adapter.builder(
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        )

    def resolve_identity(
        self,
        object_type: str,
        source: Any,
        *,
        tenant_id: str,
        owning_workspace: str,
        owning_project_id: str | None = None,
    ) -> UniversalObjectIdentity:
        return self.adapt(
            object_type,
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        ).identity

    def presentation_metadata(
        self,
        object_type: str,
        source: Any,
        *,
        tenant_id: str,
        owning_workspace: str,
        owning_project_id: str | None = None,
    ) -> UniversalObjectPresentation | None:
        return self.adapt(
            object_type,
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        ).presentation

    def supported_actions(
        self,
        object_type: str,
        source: Any,
        *,
        tenant_id: str,
        owning_workspace: str,
        owning_project_id: str | None = None,
    ) -> list[UniversalObjectAction]:
        return self.adapt(
            object_type,
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        ).actions

    def supported_relationship_groups(
        self,
        object_type: str,
        source: Any,
        *,
        tenant_id: str,
        owning_workspace: str,
        owning_project_id: str | None = None,
    ) -> list[str]:
        presentation = self.presentation_metadata(
            object_type,
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        )
        if presentation is None:
            return []
        return list(presentation.relationship_groups)

    def registered_object_types(self) -> list[str]:
        return sorted(self._adapters.keys())


def build_default_universal_object_registry() -> UniversalObjectRegistry:
    registry = UniversalObjectRegistry()

    registry.register(
        "project",
        lambda source, *, tenant_id, owning_workspace, owning_project_id=None: (
            _project_to_object(
                source, tenant_id=tenant_id, owning_workspace=owning_workspace
            )
            if isinstance(source, Project)
            else _dict_object(
                "project",
                dict(source),
                tenant_id=tenant_id,
                owning_workspace=owning_workspace,
                owning_project_id=_project_scope(source, owning_project_id),
                object_id_keys=[
                    "workspace_id",
                    "project_id",
                    "atlas_bid_id",
                    "entity_id",
                ],
                display_name_keys=[
                    "project_name",
                    "display_name",
                    "project",
                    "canonical_name",
                ],
                secondary_identifier_keys=[
                    "client_project_number",
                    "internal_project_number",
                ],
                source_authority="project_repository",
                secondary_label=_safe_text(dict(source).get("customer"), "") or None,
                supported_views=[
                    "summary",
                    "lifecycle",
                    "details",
                    "relationships",
                    "activity",
                    "history",
                    "documents",
                ],
                relationship_groups=[
                    "Related Customers",
                    "Related Documents",
                    "Related Services",
                ],
                document_available=True,
            )
        ),
    )

    registry.register(
        "commercial_document",
        lambda source, *, tenant_id, owning_workspace, owning_project_id=None: _dict_object(
            "commercial_document",
            dict(source),
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=_project_scope(source, owning_project_id),
            object_id_keys=["document_id", "object_id", "entity_id"],
            display_name_keys=[
                "document_number",
                "display_name",
                "title",
                "document_id",
            ],
            secondary_identifier_keys=["document_number", "project_code"],
            source_authority="commercial_document",
            secondary_label=(
                _safe_text(dict(source).get("project_code"), "")
                or _safe_text(dict(source).get("project_id"), "")
                or _safe_text(dict(source).get("customer_id"), "")
                or _safe_text(dict(source).get("vendor_id"), "")
                or None
            ),
            supported_views=[
                "summary",
                "details",
                "relationships",
                "activity",
                "history",
                "lifecycle",
            ],
            relationship_groups=[
                "Related Documents",
                "Related Projects",
                "Related Customers",
                "Related Vendors",
            ],
            document_available=True,
        ),
    )

    for commercial_type in [
        "estimate",
        "sales_order",
        "return_order",
        "credit_memo",
        "purchase_order",
        "rfq",
        "vendor_quote",
        "receiving_record",
        "vendor_bill",
        "customer_invoice",
        "change_order",
    ]:
        registry.register(
            commercial_type,
            lambda source, *, tenant_id, owning_workspace, owning_project_id=None, commercial_type=commercial_type: _dict_object(
                commercial_type,
                dict(source),
                tenant_id=tenant_id,
                owning_workspace=owning_workspace,
                owning_project_id=_project_scope(source, owning_project_id),
                object_id_keys=["document_id", "object_id", "entity_id"],
                display_name_keys=[
                    "document_number",
                    "display_name",
                    "title",
                    "document_id",
                ],
                secondary_identifier_keys=["document_number", "project_code"],
                source_authority="commercial_document",
                secondary_label=(
                    _safe_text(dict(source).get("project_code"), "")
                    or _safe_text(dict(source).get("project_id"), "")
                    or _safe_text(dict(source).get("customer_id"), "")
                    or _safe_text(dict(source).get("vendor_id"), "")
                    or None
                ),
                supported_views=[
                    "summary",
                    "details",
                    "relationships",
                    "activity",
                    "history",
                    "lifecycle",
                ],
                relationship_groups=[
                    "Related Documents",
                    "Related Projects",
                    "Related Customers",
                    "Related Vendors",
                ],
                document_available=True,
            ),
        )

    for (
        object_type,
        object_id_keys,
        display_keys,
        secondary_keys,
        relationship_groups,
    ) in [
        (
            "customer",
            ["customer_id", "entity_id", "customer"],
            ["display_name", "canonical_name", "customer"],
            ["customer_id"],
            ["Related Projects", "Related Contacts", "Related Services"],
        ),
        (
            "vendor",
            ["vendor_id", "entity_id", "vendor"],
            ["display_name", "canonical_name", "vendor"],
            ["vendor_code", "vendor_id"],
            ["Related Products", "Related Manufacturers", "Related Projects"],
        ),
        (
            "manufacturer",
            ["manufacturer_id", "entity_id", "manufacturer"],
            ["display_name", "canonical_name", "manufacturer"],
            ["manufacturer_code", "manufacturer_id"],
            ["Related Products", "Related Vendors", "Related Projects"],
        ),
        (
            "product",
            ["atlas_product_uuid", "product_id", "entity_id", "canonical_sku", "model"],
            ["product_name", "display_name", "canonical_name", "model"],
            ["canonical_sku", "manufacturer_part_number", "product_id"],
            ["Related Vendors", "Related Manufacturers", "Related Projects"],
        ),
        (
            "service",
            ["service_id", "entity_id", "service"],
            ["display_name", "canonical_name", "service"],
            ["service_id"],
            ["Related Customers", "Related Projects"],
        ),
        (
            "contact",
            ["contact_id", "entity_id", "contact"],
            ["display_name", "canonical_name", "contact"],
            ["email", "contact_id"],
            ["Related Customers", "Related Projects", "Related Organizations"],
        ),
        (
            "location",
            ["location_id", "entity_id", "location"],
            ["display_name", "canonical_name", "location"],
            ["external_identifier", "location_id"],
            ["Related Projects", "Related Customers"],
        ),
        (
            "drawing",
            ["drawing_number", "object_id"],
            ["drawing_number", "title"],
            ["title"],
            ["Related Equipment", "Related Specifications", "Related Evidence"],
        ),
        (
            "specification",
            ["section", "object_id"],
            ["section", "title"],
            ["title"],
            ["Related Drawings", "Related Equipment", "Related Evidence"],
        ),
        (
            "equipment",
            ["equipment_id", "object_id"],
            ["equipment_id", "model", "display_name"],
            ["model", "manufacturer"],
            [
                "Related Drawings",
                "Related Specifications",
                "Related Systems",
                "Related Evidence",
            ],
        ),
        (
            "system",
            ["system", "object_id"],
            ["system", "display_name"],
            ["equipment_count"],
            ["Related Equipment", "Related Drawings", "Related Specifications"],
        ),
        (
            "room",
            ["room", "room_or_area", "object_id"],
            ["room", "room_or_area", "display_name"],
            ["system"],
            ["Related Equipment", "Related Systems"],
        ),
        (
            "evidence",
            ["object_id", "source_file"],
            ["source_file", "display_name"],
            ["page"],
            ["Related Documents", "Related Objects"],
        ),
        (
            "rfi",
            ["rfi_id", "object_id", "title"],
            ["title", "display_name"],
            ["category"],
            ["Related Documents", "Related Objects"],
        ),
        (
            "organization",
            ["organization_id", "entity_id", "organization"],
            ["display_name", "organization", "canonical_name"],
            ["roles"],
            ["Related Contacts", "Related Projects"],
        ),
        (
            "price_list",
            ["source_file", "object_id"],
            ["source_file", "display_name"],
            ["vendor", "manufacturer"],
            ["Related Vendors", "Related Manufacturers", "Related Products"],
        ),
    ]:
        registry.register(
            object_type,
            lambda source, *, tenant_id, owning_workspace, owning_project_id=None, object_type=object_type, object_id_keys=object_id_keys, display_keys=display_keys, secondary_keys=secondary_keys, relationship_groups=relationship_groups: _dict_object(
                object_type,
                dict(source),
                tenant_id=tenant_id,
                owning_workspace=owning_workspace,
                owning_project_id=owning_project_id,
                object_id_keys=object_id_keys,
                display_name_keys=display_keys,
                secondary_identifier_keys=secondary_keys,
                source_authority="atlas_adapter",
                secondary_label=(
                    _safe_text(dict(source).get("customer"), "")
                    or _safe_text(dict(source).get("vendor"), "")
                    or _safe_text(dict(source).get("manufacturer"), "")
                    or _safe_text(dict(source).get("title"), "")
                    or None
                ),
                supported_views=[
                    "summary",
                    "details",
                    "relationships",
                    "activity",
                    "history",
                ],
                relationship_groups=relationship_groups,
                document_available=object_type
                in {"drawing", "specification", "equipment", "evidence", "project"},
            ),
        )

    registry.register(
        "master_product",
        lambda source, *, tenant_id, owning_workspace, owning_project_id=None: registry.adapt(
            "product",
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        ),
    )
    registry.register(
        "project_record",
        lambda source, *, tenant_id, owning_workspace, owning_project_id=None: registry.adapt(
            "project",
            source,
            tenant_id=tenant_id,
            owning_workspace=owning_workspace,
            owning_project_id=owning_project_id,
        ),
    )
    return registry
