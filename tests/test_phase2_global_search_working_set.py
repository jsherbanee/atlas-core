from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import inspect
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Literal

from atlas_core.domain import Project, ProjectStatus
from atlas_core.contracts.upload_policy import bid_package_upload_policy
from atlas_core.services.master_library import CommercialProductService
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)
import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def _label_tail(label: str) -> str:
    return label[2:] if label.startswith(("⌄ ", "› ")) else label


def test_bid_package_uploader_config_matches_shared_policy() -> None:
    policy = bid_package_upload_policy()

    assert app.SUPPORTED_UPLOAD_TYPES == policy.streamlit_types
    assert "json" not in app.SUPPORTED_UPLOAD_TYPES
    assert app.BID_PACKAGE_UPLOAD_POLICY.help_text == policy.help_text


def test_bid_package_basic_upload_diagnostic_rejects_json_and_oversize() -> None:
    json_result = app._basic_upload_diagnostic("metadata.json", b"{}")
    oversized_result = app.BID_PACKAGE_UPLOAD_POLICY.validate_file(
        name="too-large.pdf",
        size_bytes=app.BID_PACKAGE_UPLOAD_POLICY.max_file_size_bytes + 1,
    )

    assert json_result[0] is False
    assert "Unsupported file type" in json_result[1]
    assert oversized_result.accepted is False
    assert "File exceeds the per-file upload limit." in oversized_result.message
    assert (
        f"{app.BID_PACKAGE_UPLOAD_POLICY.max_file_size_bytes + 1:,} bytes"
        in oversized_result.message
    )


def _button_label_tails(st: Any) -> list[str]:
    return [_label_tail(str(call["label"])) for call in st.button_calls]


@dataclass
class _FakeStreamlit:
    session_state: dict[str, Any]
    rerun_called: bool = False
    captions: list[str] | None = None
    query_params: dict[str, Any] | None = None

    def rerun(self) -> None:
        self.rerun_called = True

    def markdown(self, _text: str, **kwargs: Any) -> None:
        _ = kwargs

    def caption(self, text: str) -> None:
        if self.captions is None:
            self.captions = []
        self.captions.append(text)


class _HomeContractStreamlit:
    def __init__(self, *, pressed: set[str] | None = None) -> None:
        self.session_state: dict[str, Any] = {}
        self.query_params: dict[str, Any] | None = None
        self._pressed = set(pressed or set())
        self.subheaders: list[str] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.dataframes: list[Any] = []
        self.popover_labels: list[str] = []
        self.expander_calls: list[dict[str, Any]] = []
        self.column_specs: list[Any] = []
        self.text_inputs: list[dict[str, Any]] = []
        self.selectbox_calls: list[dict[str, Any]] = []
        self.button_calls: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.text_areas: list[dict[str, Any]] = []
        self.download_buttons: list[dict[str, Any]] = []
        self.rerun_called = False

    def __enter__(self) -> _HomeContractStreamlit:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False

    def subheader(self, text: str) -> None:
        self.subheaders.append(text)

    def columns(
        self, count: int | list[Any], **kwargs: Any
    ) -> list[_HomeContractStreamlit]:
        _ = kwargs
        self.column_specs.append(count)
        size = len(count) if isinstance(count, list) else count
        return [self for _ in range(size)]

    def container(self, border: bool = False) -> _HomeContractStreamlit:
        _ = border
        return self

    def popover(self, _label: str) -> _HomeContractStreamlit:
        self.popover_labels.append(_label)
        return self

    def button(
        self,
        label: str,
        type: str = "secondary",
        use_container_width: bool = False,
        width: str | None = None,
        key: str | None = None,
        disabled: bool = False,
    ) -> bool:
        if width is not None:
            use_container_width = width == "stretch"
        self.button_calls.append(
            {
                "label": label,
                "type": type,
                "key": key,
                "disabled": disabled,
                "use_container_width": use_container_width,
                "width": width,
            }
        )
        _ = (type, use_container_width, width, key, disabled)
        return label in self._pressed or (key is not None and key in self._pressed)

    def selectbox(
        self,
        label: str,
        options: list[Any],
        index: int = 0,
        **kwargs: Any,
    ) -> Any:
        self.selectbox_calls.append(
            {"label": label, "options": list(options), **kwargs}
        )
        if not options:
            return ""
        if 0 <= index < len(options):
            return options[index]
        return options[0]

    def checkbox(self, _label: str, *, value: bool = False, **kwargs: Any) -> bool:
        _ = kwargs
        return value

    def metric(self, label: str, value: str) -> None:
        self.markdowns.append(f"Metric: {label}={value}")

    def expander(self, _label: str, expanded: bool = False) -> _HomeContractStreamlit:
        self.expander_calls.append({"label": _label, "expanded": expanded})
        return self

    def tabs(self, labels: list[str]) -> list[_HomeContractStreamlit]:
        self.markdowns.append("Tabs: " + ", ".join(labels))
        return [self for _ in labels]

    def warning(self, text: str) -> None:
        self.warnings.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def number_input(self, _label: str, *, value: float = 0.0, **kwargs: Any) -> float:
        _ = kwargs
        return value

    def text_area(self, label: str, value: str = "", **kwargs: Any) -> str:
        self.text_areas.append({"label": label, "value": value, **kwargs})
        return value

    def multiselect(self, _label: str, **kwargs: Any) -> list[Any]:
        _ = kwargs
        return []

    def download_button(self, label: str, **kwargs: Any) -> bool:
        self.download_buttons.append({"label": label, **kwargs})
        return False

    def file_uploader(self, *_args: Any, **_kwargs: Any) -> Any:
        return None

    def markdown(self, text: str, **kwargs: Any) -> None:
        _ = kwargs
        self.markdowns.append(text)

    def text_input(self, label: str, **kwargs: Any) -> str:
        self.text_inputs.append({"label": label, **kwargs})
        key = kwargs.get("key")
        if isinstance(key, str):
            state_value = self.session_state.get(key)
            if isinstance(state_value, str):
                return state_value
        return str(kwargs.get("value") or "")

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def dataframe(self, data: Any, **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(data)

    def rerun(self) -> None:
        self.rerun_called = True


class _FakeWorkspaceService:
    def __init__(self, records: list[ProjectWorkspaceRecord]) -> None:
        self._records = records
        self.saved_records: list[ProjectWorkspaceRecord] = []
        self.opened_records: list[str] = []
        self.renamed: list[tuple[str, str]] = []
        self.duplicated: list[tuple[str, str, str | None]] = []
        self.pinned: list[tuple[str, bool]] = []
        self.archived: list[tuple[str, bool]] = []
        self.deleted: list[str] = []

    def list_workspaces(
        self,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[ProjectWorkspaceRecord]:
        records = [
            item for item in self._records if include_archived or not item.archived
        ]
        return list(records)[:limit]

    def preview_next_bid_id(self) -> str:
        return "BID-2099-0001"

    def list_recent_workspaces(self, limit: int = 10) -> list[ProjectWorkspaceRecord]:
        _ = limit
        return [item for item in self._records if not item.archived][:limit]

    def list_pinned_workspaces(self, limit: int = 20) -> list[ProjectWorkspaceRecord]:
        return [item for item in self._records if item.pinned][:limit]

    def list_reference_workspaces(
        self,
        include_archived: bool = False,
    ) -> list[ProjectWorkspaceRecord]:
        records = [item for item in self._records if item.is_reference]
        return [item for item in records if include_archived or not item.archived]

    def list_project_stakeholders(self, _workspace_id: str) -> list[dict[str, Any]]:
        return []

    def read_manifest(self, _workspace_id: str) -> dict[str, Any]:
        return {"document_counts": {}}

    def rename_project(
        self, workspace_id: str, new_name: str
    ) -> ProjectWorkspaceRecord:
        self.renamed.append((workspace_id, new_name))
        record = next(
            item for item in self._records if item.workspace_id == workspace_id
        )
        record.project.name = new_name
        return record

    def duplicate_project(
        self,
        workspace_id: str,
        new_workspace_id: str,
        new_name: str | None = None,
    ) -> ProjectWorkspaceRecord:
        self.duplicated.append((workspace_id, new_workspace_id, new_name))
        source = next(
            item for item in self._records if item.workspace_id == workspace_id
        )
        duplicate = _project_record(
            new_workspace_id, new_name or f"{source.project.name} Copy"
        )
        self._records.insert(0, duplicate)
        return duplicate

    def pin_project(
        self, workspace_id: str, pinned: bool = True
    ) -> ProjectWorkspaceRecord:
        self.pinned.append((workspace_id, pinned))
        record = next(
            item for item in self._records if item.workspace_id == workspace_id
        )
        record.pinned = pinned
        return record

    def archive_project(
        self,
        workspace_id: str,
        archived: bool = True,
    ) -> ProjectWorkspaceRecord:
        self.archived.append((workspace_id, archived))
        record = next(
            item for item in self._records if item.workspace_id == workspace_id
        )
        record.archived = archived
        return record

    def delete_project(self, workspace_id: str) -> None:
        self.deleted.append(workspace_id)
        self._records = [
            item for item in self._records if item.workspace_id != workspace_id
        ]

    def save_record(self, record: ProjectWorkspaceRecord) -> Path:
        self.saved_records.append(record)
        self._records = [
            item for item in self._records if item.workspace_id != record.workspace_id
        ]
        self._records.insert(0, record)
        return Path("workspace.json")

    def mark_workspace_opened(self, workspace_id: str) -> ProjectWorkspaceRecord:
        self.opened_records.append(workspace_id)
        return next(item for item in self._records if item.workspace_id == workspace_id)

    def import_project_bundle(self, import_path: str) -> ProjectWorkspaceRecord:
        name = Path(import_path).stem or "Imported Project"
        record = _project_record(f"imported-{len(self._records) + 1}", name)
        self.save_record(record)
        return record


def _seed_knowledge_service(entity_type: str) -> CommercialProductService:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-qsc",
        canonical_name="QSC",
        display_name="QSC",
        manufacturer_code="QSC",
    )
    service.create_vendor(
        vendor_id="vendor-avp",
        canonical_name="AV Partner",
        display_name="AV Partner",
        vendor_code="AVP",
    )
    if entity_type == "vendor":
        service.create_vendor(
            vendor_id="vendor-01",
            canonical_name="Vendor One",
            display_name="Vendor One",
            vendor_code="V01",
        )
    elif entity_type == "manufacturer":
        service.create_manufacturer(
            manufacturer_id="mfr-01",
            canonical_name="Manufacturer One",
            display_name="Manufacturer One",
            manufacturer_code="M01",
        )
    elif entity_type == "product":
        service.import_price_list_version(
            manufacturer="QSC",
            vendor="AV Partner",
            source_file="seed.csv",
            file_bytes=b"seed",
            import_user="tester",
            rows=[
                {
                    "vendor": "AV Partner",
                    "manufacturer": "QSC",
                    "manufacturer_sku": "Core 110f",
                    "canonical_sku": "CORE-110F",
                    "alternate_skus": ["CORE110F"],
                    "description": "DSP",
                    "product_family": "General",
                    "category": "dsp",
                    "discipline": "audio",
                    "lifecycle_status": "active",
                    "preferred_cost": 1200.0,
                    "msrp": 2999.0,
                    "preferred_vendor": "AV Partner",
                    "vendor_sku": "AVP-CORE110F",
                    "vendor_type": "distributor",
                    "availability_status": "in_stock",
                    "lead_time": "2 weeks",
                    "effective_date": "2026-01-01",
                    "date_verified": "2026-01-05",
                }
            ],
            effective_date="2026-01-01",
        )
    elif entity_type == "service":
        service.create_service_entity(
            service_id="svc-01",
            canonical_name="Service One",
            display_name="Service One",
        )
    elif entity_type == "customer":
        service.create_customer(
            customer_id="CUST-0001",
            canonical_name="Beta Customer",
            display_name="Beta Customer",
        )
        service.create_customer(
            customer_id="CUST-0002",
            canonical_name="Alpha Customer",
            display_name="Alpha Customer",
        )
    return service


class _NullContext:
    def __enter__(self) -> _NullContext:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


class _CreatePageStreamlit:
    def __init__(
        self,
        *,
        submit: bool,
        project_name: str = "",
        client_name: str = "",
        uploaded_files: list[Any] | None = None,
        button_presses: dict[str, bool] | None = None,
        select_values: dict[str, str] | None = None,
    ) -> None:
        self.submit = submit
        self.project_name = project_name
        self.client_name = client_name
        self.uploaded_files = list(uploaded_files or [])
        self.button_presses = dict(button_presses or {})
        self.select_values = dict(select_values or {})
        self.session_state: dict[str, Any] = {}
        self.select_options: dict[str, list[str]] = {}
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.successes: list[str] = []
        self.captions: list[str] = []
        self.rerun_called = False

    def subheader(self, _text: str) -> None:
        return None

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def warning(self, text: str) -> None:
        self.warnings.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def markdown(self, _text: str, **kwargs: Any) -> None:
        _ = kwargs
        return None

    def button(
        self,
        label: str,
        type: str = "secondary",
        disabled: bool = False,
        use_container_width: bool = False,
        width: str | None = None,
        key: str | None = None,
    ) -> bool:
        if width is not None:
            use_container_width = width == "stretch"
        _ = (type, disabled, use_container_width, width, key)
        if disabled:
            return False
        return bool(
            self.button_presses.get(label, False)
            or (key is not None and self.button_presses.get(key, False))
        )

    def form(self, _key: str, clear_on_submit: bool = False) -> _NullContext:
        _ = clear_on_submit
        return _NullContext()

    def text_input(self, label: str, key: str | None = None, **kwargs: Any) -> str:
        _ = (key, kwargs)
        if label == "Project Name":
            return self.project_name
        if label == "Owner / Client":
            return self.client_name
        if label == "Owner / Client stakeholder lookup":
            return self.client_name
        return ""

    def selectbox(
        self,
        _label: str,
        options: list[str],
        index: int = 0,
        **kwargs: Any,
    ) -> str:
        _ = kwargs
        self.select_options[_label] = list(options)
        selected_value = self.select_values.get(_label)
        if selected_value in options:
            return str(selected_value)
        return str(options[index])

    def file_uploader(self, *args: Any, **kwargs: Any) -> list[Any]:
        _ = (args, kwargs)
        return list(self.uploaded_files)

    def multiselect(self, *args: Any, **kwargs: Any) -> list[str]:
        _ = (args, kwargs)
        return []

    def expander(self, _label: str, expanded: bool = False) -> _NullContext:
        _ = expanded
        return _NullContext()

    def form_submit_button(
        self,
        _label: str,
        type: str = "secondary",
        disabled: bool = False,
    ) -> bool:
        _ = type
        if disabled:
            return False
        return self.submit

    def columns(self, count: int, **kwargs: Any) -> list[_CreatePageStreamlit]:
        _ = kwargs
        return [self for _ in range(count)]

    def metric(self, _label: str, _value: str) -> None:
        return None

    def dataframe(self, *args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)
        return None

    def rerun(self) -> None:
        self.rerun_called = True


class _CreatePageWorkspaceServiceWithoutPreview:
    def __init__(self) -> None:
        self.created: list[ProjectWorkspaceRecord] = []
        self.logged_events: list[tuple[str, str, dict[str, Any]]] = []
        self.import_calls: list[tuple[str, list[tuple[str, bytes]]]] = []
        self.inspect_calls = 0
        self.search_queries: list[str] = []
        self.link_calls: list[dict[str, Any]] = []

    def inspect_uploaded_documents(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> Any:
        self.inspect_calls += 1
        accepted_files = []
        diagnostics = []
        warnings: list[str] = []
        seen_names: set[str] = set()
        for name, data in uploaded_files:
            extension = Path(name).suffix.lower()
            duplicate = name.lower() in seen_names
            accepted = (
                extension in {".pdf", ".jpg", ".jpeg", ".xls", ".xlsx", ".doc", ".docx"}
                and len(data) > 0
                and not duplicate
            )
            if accepted:
                messages = ["accepted"]
            elif len(data) == 0:
                messages = ["empty file"]
            elif extension == ".zip":
                messages = ["unsupported extension"]
                warnings.append("could not unpack ZIP archive")
            else:
                messages = ["invalid"]
            diagnostics.append(
                {
                    "name": name,
                    "source_type": "file",
                    "size_bytes": len(data),
                    "zip_source": extension == ".zip",
                    "duplicate_name": duplicate,
                    "duplicate_source_hash": False,
                    "accepted": accepted,
                    "messages": messages,
                }
            )
            if accepted:
                accepted_files.append(SimpleNamespace(name=name, data=data))
            seen_names.add(name.lower())

        return SimpleNamespace(
            accepted_files=accepted_files,
            diagnostics=diagnostics,
            warnings=warnings,
        )

    def create_manual_record(self, **kwargs: Any) -> ProjectWorkspaceRecord:
        name = str(kwargs.get("name") or "")
        client = str(kwargs.get("client") or "")
        record = ProjectWorkspaceRecord(
            workspace_id="BID-2099-0001",
            project=Project(
                project_id="BID-2099-0001",
                name=name,
                client=client,
                status=ProjectStatus.INTAKE,
            ),
        )
        self.created.append(record)
        return record

    def save_record(self, _record: ProjectWorkspaceRecord) -> Path:
        return Path("workspace.json")

    def import_uploaded_documents(
        self,
        workspace_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> ProjectWorkspaceRecord:
        self.import_calls.append((workspace_id, list(uploaded_files)))
        return self.created[-1]

    def log_event(
        self,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.logged_events.append((workspace_id, event_type, dict(payload)))

    def search_stakeholder_organizations(
        self,
        query: str,
        *,
        role: Any = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = (role, include_inactive, limit)
        self.search_queries.append(query)
        if not query.strip():
            return []
        return [
            {
                "organization_id": "org-lookup-owner",
                "canonical_name": "Lookup Owner LLC",
                "display_name": "Lookup Owner LLC",
            }
        ]

    def link_project_stakeholder(
        self,
        *,
        workspace_id: str,
        organization_id: str,
        role: Any,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "role": role,
            "is_primary": is_primary,
        }
        self.link_calls.append(payload)
        return payload


class _CreatePageWorkspaceServiceWithPreview(_CreatePageWorkspaceServiceWithoutPreview):
    def preview_next_bid_id(self) -> str:
        return "BID-2099-0009"


class _CreatePageWorkspaceServiceInspectionFailure(
    _CreatePageWorkspaceServiceWithoutPreview
):
    def inspect_uploaded_documents(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> Any:
        _ = uploaded_files
        raise AttributeError("inspect_uploaded_files missing")


@dataclass
class _FakeUploadedFile:
    name: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


class _StreamingUploadedFile:
    def __init__(self, *, name: str, data: bytes, chunk_size: int = 2) -> None:
        self.name = name
        self.data = data
        self.size = len(data)
        self.chunk_size = chunk_size
        self.position = 0
        self.read_calls = 0
        self.getvalue_calls = 0

    def seek(self, position: int) -> None:
        self.position = position

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self.position >= len(self.data):
            return b""
        active_size = self.chunk_size if size < 0 else min(size, self.chunk_size)
        start = self.position
        stop = min(len(self.data), start + active_size)
        self.position = stop
        return self.data[start:stop]

    def getvalue(self) -> bytes:
        self.getvalue_calls += 1
        raise AssertionError("pending upload persistence should stream file chunks")


def _reference(
    *,
    object_id: str,
    display_name: str,
    object_type: str,
    scope: str,
    route: str = "Overview",
    match_fields: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "object_id": object_id,
        "display_name": display_name,
        "object_type": object_type,
        "secondary_label": "",
        "match_fields": list(match_fields or []),
        "scope": scope,
        "route": route,
        "selection_kind": "equipment",
        "selection_data": {"equipment_id": object_id},
    }


def _project_record(workspace_id: str, project_name: str) -> ProjectWorkspaceRecord:
    return ProjectWorkspaceRecord(
        workspace_id=workspace_id,
        project=Project(
            project_id=workspace_id,
            name=project_name,
            client="Client",
            status=ProjectStatus.INTAKE,
        ),
    )


def test_exact_identifier_match_ranks_first() -> None:
    exact = _reference(
        object_id="AV-601",
        display_name="Drawing AV-601",
        object_type="Drawing",
        scope="project",
        match_fields=["AV-601"],
    )
    partial = _reference(
        object_id="AV-602",
        display_name="Drawing AV-602",
        object_type="Drawing",
        scope="project",
        match_fields=["AV-602"],
    )

    filtered = app._filter_search_results(
        [partial, exact],
        query="AV-601",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["object_id"] == "AV-601"


def test_partial_match_ranks_after_prefix() -> None:
    prefix = _reference(
        object_id="SPK-1",
        display_name="Speaker One",
        object_type="Equipment",
        scope="project",
        match_fields=["Speaker One"],
    )
    partial = _reference(
        object_id="SPK-2",
        display_name="Main Speaker Cluster",
        object_type="Equipment",
        scope="project",
        match_fields=["Main Speaker Cluster"],
    )

    filtered = app._filter_search_results(
        [partial, prefix],
        query="speak",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["object_id"] == "SPK-1"


def test_project_scope_preferred_for_non_exact_matches() -> None:
    project_item = _reference(
        object_id="eq-1",
        display_name="Sony Display",
        object_type="Equipment",
        scope="project",
    )
    app_item = _reference(
        object_id="prod-sony-display",
        display_name="Sony Display",
        object_type="Product",
        scope="application",
    )

    filtered = app._filter_search_results(
        [app_item, project_item],
        query="sony",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["scope"] == "project"


def test_search_grouping_uses_ordered_user_labels() -> None:
    grouped = app._group_search_results(
        [
            _reference(
                object_id="d1",
                display_name="AV-601",
                object_type="Drawing",
                scope="project",
            ),
            _reference(
                object_id="e1",
                display_name="QSC Core",
                object_type="Equipment",
                scope="project",
            ),
            _reference(
                object_id="u1",
                display_name="Custom A",
                object_type="Alpha Custom",
                scope="project",
            ),
            _reference(
                object_id="u2",
                display_name="Custom Z",
                object_type="Zeta Custom",
                scope="project",
            ),
        ]
    )

    assert list(grouped.keys()) == [
        "Equipment",
        "Drawings",
        "Alpha Custom",
        "Zeta Custom",
    ]
    assert len(grouped["Drawings"]) == 1


def test_search_grouping_omits_empty_preferred_groups() -> None:
    grouped = app._group_search_results(
        [
            _reference(
                object_id="v1",
                display_name="ADI",
                object_type="Vendor",
                scope="application",
            )
        ]
    )

    assert list(grouped.keys()) == ["Vendors"]
    assert "Projects" not in grouped


def test_application_nav_exposes_home_with_compatibility_route_key() -> None:
    app_workspace_entries = app.APPLICATION_NAV_GROUPS[0][1]

    assert ("Home", "Mission Control") in app_workspace_entries
    assert ("Administration", "Administration") not in app_workspace_entries


def test_top_navigation_settings_routes_to_administration() -> None:
    st = _FakeStreamlit(session_state={"atlas_active_page": "Mission Control"})
    st.query_params = {"atlas_page": "Administration"}

    app._sync_active_page_from_query_params(st)

    assert st.session_state["atlas_active_page"] == "Administration"


def test_query_params_restore_selected_project_workspace() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={})
    st.query_params = {"atlas_workspace_id": "maw-demo"}
    service = _FakeWorkspaceService([record])

    app._sync_active_workspace_from_query_params(st, service)

    assert st.session_state["atlas_active_workspace_id"] == "maw-demo"


def test_query_params_ignore_unknown_project_workspace() -> None:
    st = _FakeStreamlit(session_state={})
    st.query_params = {"atlas_workspace_id": "missing-project"}
    service = _FakeWorkspaceService([_project_record("maw-demo", "MAW")])

    app._sync_active_workspace_from_query_params(st, service)

    assert "atlas_active_workspace_id" not in st.session_state


def test_atlas_button_routes_back_home() -> None:
    st = _HomeContractStreamlit(pressed={"Atlas"})
    st.query_params = {}
    service = _FakeWorkspaceService([])

    app._render_header(st, service, None, None)

    assert st.session_state["atlas_active_page"] == "Mission Control"
    assert st.rerun_called is True
    assert st.query_params["atlas_page"] == "Mission Control"
    assert st.button_calls[0]["label"] == "Atlas"
    assert st.button_calls[0]["use_container_width"] is False
    assert st.button_calls[0]["width"] == "content"
    assert all(call["label"] != "☰" for call in st.button_calls)


def test_top_navigation_renders_primary_header_buttons() -> None:
    st = _HomeContractStreamlit()

    app._render_top_navigation(st, st.columns(5))

    assert [call["label"] for call in st.button_calls] == [
        "Transactions",
        "Projects",
        "Knowledge",
        "Reports",
        "Settings",
    ]
    assert all(call["width"] == "content" for call in st.button_calls)
    assert all(call["use_container_width"] is False for call in st.button_calls)


def test_top_navigation_hides_public_home_button() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_page"] = "Projects"

    app._render_top_navigation(st, st.columns(5))

    assert [call["label"] for call in st.button_calls] == [
        "Transactions",
        "Projects",
        "Knowledge",
        "Reports",
        "Settings",
    ]
    assert all(call["label"] != "Home" for call in st.button_calls)


def test_top_navigation_highlights_projects_in_project_workspace() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_page"] = "Overview"

    app._render_top_navigation(
        st,
        st.columns(5),
        _project_record("project-a", "Project A"),
    )

    projects_call = next(
        call for call in st.button_calls if call["label"] == "Projects"
    )
    assert projects_call["type"] == "primary"
    assert projects_call["width"] == "content"


def test_top_navigation_highlights_knowledge_and_reports_workspaces() -> None:
    knowledge = _HomeContractStreamlit()
    knowledge.session_state["atlas_active_page"] = "Evidence"

    app._render_top_navigation(knowledge, knowledge.columns(5))

    knowledge_call = next(
        call for call in knowledge.button_calls if call["label"] == "Knowledge"
    )
    assert knowledge_call["type"] == "primary"

    reports = _HomeContractStreamlit()
    reports.session_state["atlas_active_page"] = "Reports"

    app._render_top_navigation(reports, reports.columns(5))

    reports_call = next(
        call for call in reports.button_calls if call["label"] == "Reports"
    )
    assert reports_call["type"] == "primary"


def test_top_navigation_routes_within_current_window() -> None:
    st = _HomeContractStreamlit(pressed={"Projects"})
    st.session_state["atlas_active_page"] = "Mission Control"
    st.query_params = {}

    app._render_top_navigation(st, st.columns(5))

    assert st.session_state["atlas_active_page"] == "Projects"
    assert st.query_params["atlas_page"] == "Projects"
    assert st.rerun_called is True


def test_header_omits_burger_menu_and_keeps_primary_row_fixed() -> None:
    st = _HomeContractStreamlit()

    app._render_header(st, _FakeWorkspaceService([]), None, None)

    assert st.button_calls[0]["label"] == "Atlas"
    assert len(st.button_calls) == 6
    assert all(call["label"] != "☰" for call in st.button_calls)
    assert st.popover_labels == []


def test_transactions_navigation_contract_uses_expected_order_and_labels() -> None:
    contract = app._workspace_navigation_contract("Transactions", "application")

    assert [item["secondary_key"] for item in contract] == [
        "estimates",
        "sales_orders",
        "return_orders",
        "customer_invoices",
        "credit_memos",
        "purchase_orders",
        "vendor_quotes",
        "receiving",
        "vendor_bills",
    ]
    assert [item["label"] for item in contract] == [
        "Estimates",
        "Sales Orders",
        "Return Orders",
        "Invoices",
        "Credit Memos",
        "Purchase Orders (Deferred)",
        "Vendor Quotes (Deferred)",
        "Receiving (Deferred)",
        "Vendor Bills (Deferred)",
    ]
    assert all(
        item["enabled"] is False
        for item in contract
        if item["secondary_key"]
        in {"purchase_orders", "vendor_quotes", "receiving", "vendor_bills"}
    )


def _transaction_service_with_catalog() -> Any:
    return app.TransactionsWorkspaceService(
        active_tenant_id="local",
        active_organization_id="atlas",
        serialized_catalog_state={
            "catalog_items": {
                "product:sku-a": {
                    "catalog_item_id": "product:sku-a",
                    "item_type": "product",
                    "code": "SKU-A",
                    "name": "Product A",
                    "description": "Product line",
                    "status": "active",
                    "cost": 6.0,
                    "default_sales_price": 10.0,
                    "taxable": False,
                    "archived": False,
                },
                "service:svc-a": {
                    "catalog_item_id": "service:svc-a",
                    "item_type": "service",
                    "code": "SVC-A",
                    "name": "Service A",
                    "description": "Service line",
                    "status": "active",
                    "cost": 40.0,
                    "default_sales_price": 75.0,
                    "taxable": False,
                    "archived": False,
                },
            }
        },
    )


def _draft_estimate_with_line() -> tuple[Any, Any]:
    service = _transaction_service_with_catalog()
    document = service.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=app.CommercialDocumentType.ESTIMATE,
        customer_id="cust-1",
        project_id="project-1",
        project_code="PRJ-1",
    )
    service.add_catalog_line(
        document_id=document.document_id,
        catalog_item_id="product:sku-a",
        quantity=Decimal("2"),
    )
    return service, service.get_document(document.document_id)


def test_commercial_transaction_presentation_builds_summary_health_and_totals() -> None:
    _service, document = _draft_estimate_with_line()
    assert document is not None

    presentation = app._commercial_transaction_presentation(document, [document])

    assert presentation["summary"]["family"] == "Estimate"
    assert presentation["summary"]["customer"] == "cust-1"
    assert presentation["summary"]["project"] == "PRJ-1"
    assert presentation["summary"]["total"] == "USD 20.00"
    assert presentation["readiness_state"] == "Ready"
    assert presentation["recommendation"]["title"] == "Ready for internal review"
    assert any(row["Group"] == "Products" for row in presentation["line_rows"])
    assert any(row["Measure"] == "Gross margin" for row in presentation["totals"])


def test_commercial_transaction_workbench_renders_supported_sections() -> None:
    _service, document = _draft_estimate_with_line()
    assert document is not None
    st = _HomeContractStreamlit()

    app._render_commercial_transaction_workbench(
        st,
        document=document,
        all_documents=[document],
        prefix="commercial_workbench_test",
    )

    rendered_text = "\n".join([*st.markdowns, *st.captions])
    assert "Document Summary" in rendered_text
    assert "Commercial Health" in rendered_text
    assert "Commercial Readiness" in rendered_text
    assert "Decision Panel" in rendered_text
    assert "Line Item Workspace" in rendered_text
    assert "Commercial Relationships" in rendered_text
    assert "No significant commercial issues detected." in rendered_text
    assert st.expander_calls == [
        {"label": "Administration and History", "expanded": False}
    ]
    assert not st.errors


def test_commercial_health_finding_precedence_blocks_missing_customer_before_lines() -> (
    None
):
    service = app.TransactionsWorkspaceService(
        active_tenant_id="local",
        active_organization_id="atlas",
    )
    document = service.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=app.CommercialDocumentType.SALES_ORDER,
    )

    presentation = app._commercial_transaction_presentation(document, [document])

    assert presentation["readiness_state"] == "Blocked"
    assert presentation["findings"][0]["title"] == "Customer missing"
    assert presentation["recommendation"]["action"] == "Continue Editing"


def test_commercial_transaction_relationships_show_downstream_document() -> None:
    service, estimate = _draft_estimate_with_line()
    assert estimate is not None
    service._commercial_service.set_approval_state(estimate, app.ApprovalState.APPROVED)
    sales_order = service.create_sales_order_from_estimate(
        estimate_document_id=estimate.document_id,
        inherit_terms_from_estimate=True,
    )

    presentation = app._commercial_transaction_presentation(
        estimate,
        service.list_documents(include_archived=True),
    )

    relationships = presentation["relationships"]
    assert any(
        row["Relationship"] == "Converted to Sales Order"
        and row["Reference"]
        == app._safe_text(sales_order.document_number, sales_order.document_id)
        for row in relationships
    )
    assert presentation["recommendation"]["title"] == "Sales order already exists"


def test_transaction_row_uses_operational_columns_without_internal_id() -> None:
    _service, document = _draft_estimate_with_line()
    assert document is not None

    row = app._transaction_row(document)

    assert "Document Number" in row
    assert "Document ID" not in row
    assert row["Family"] == "Estimate"
    assert row["Readiness"] == "Ready"
    assert row["Next Action"] == "Review Document"


def test_transaction_query_params_restore_family_action_and_document() -> None:
    service, document = _draft_estimate_with_line()
    assert document is not None
    st = _FakeStreamlit(session_state={"atlas_active_page": "Transactions"})
    st.query_params = {
        "atlas_transaction_family": "estimates",
        "atlas_transaction_action": "lines",
        "atlas_transaction_id": document.document_id,
    }

    app._sync_transaction_route_from_query_params(st, service)

    assert st.session_state[app._navigation_secondary_state_key()] == "estimates"
    assert st.session_state[app._navigation_tertiary_state_key()] == "lines"
    assert (
        st.session_state["atlas_transactions_selected_document_id"]
        == document.document_id
    )


def test_knowledge_navigation_contract_is_flat_and_ordered() -> None:
    contract = app._workspace_navigation_contract("Knowledge", "application")

    assert [item["secondary_key"] for item in contract] == [
        "customers",
        "vendors",
        "manufacturers",
        "catalog",
    ]
    assert [item["label"] for item in contract] == [
        "Customers",
        "Vendors",
        "Manufacturers",
        "Catalog",
    ]
    catalog = next(item for item in contract if item["secondary_key"] == "catalog")
    assert [item["tertiary_key"] for item in catalog["supported_tertiary_actions"]] == [
        "products",
        "services",
        "fees",
        "assemblies",
        "browse",
        "add",
        "import",
        "activity",
    ]


def test_knowledge_landing_does_not_render_duplicate_family_actions() -> None:
    st = _HomeContractStreamlit()

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    rendered_labels = [call["label"] for call in st.button_calls]
    assert "Customers" not in rendered_labels
    assert "Vendors" not in rendered_labels
    assert "Manufacturers" not in rendered_labels
    assert "Catalog" not in rendered_labels
    assert all("Knowledge Area" not in item for item in st.markdowns)
    assert all("Why It Matters" not in item for item in st.markdowns)


def test_workspace_navigation_uses_compact_labels_without_literal_arrows() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    labels = [call["label"] for call in st.button_calls]
    label_tails = _button_label_tails(st)
    assert labels[:4] == ["⌄ Customers", "Browse", "Add", "Activity"]
    assert "Vendors" in label_tails
    assert "Manufacturers" in label_tails
    assert "Catalog" in label_tails
    assert all("[v]" not in label and "[>]" not in label for label in labels)
    assert "Browse" in label_tails
    assert "   Browse" not in labels
    assert st.expander_calls == []
    assert [0.16, 0.84] in st.column_specs


@pytest.mark.parametrize(
    ("secondary", "expected_present", "expected_absent"),
    [
        (
            "customers",
            {"Browse", "Add", "Activity"},
            {"Price Lists", "Default Vendor", "Import"},
        ),
        ("vendors", {"Price Lists", "Products"}, {"Default Vendor", "Import"}),
        ("manufacturers", {"Default Vendor", "Products"}, {"Price Lists", "Import"}),
        (
            "catalog",
            {"Services", "Fees", "Assemblies", "Import"},
            {"Price Lists", "Default Vendor"},
        ),
    ],
)
def test_knowledge_accordion_keeps_one_section_expanded(
    secondary: str, expected_present: set[str], expected_absent: set[str]
) -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): secondary,
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    label_tails = set(_button_label_tails(st))
    assert expected_present <= label_tails
    assert expected_absent.isdisjoint(label_tails)


def test_knowledge_accordion_opening_new_section_closes_prior_section() -> None:
    st = _HomeContractStreamlit(
        pressed={"atlas_secondary_Knowledge_application_vendors"}
    )
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == "vendors"
    assert st.session_state[app._navigation_tertiary_state_key()] == "browse"
    assert st.session_state["atlas_active_page"] == "Knowledge"
    assert st.rerun_called is True


def test_knowledge_accordion_clicking_active_section_collapses_it() -> None:
    st = _HomeContractStreamlit(
        pressed={"atlas_secondary_Knowledge_application_catalog"}
    )
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "catalog",
            app._navigation_tertiary_state_key(): "import",
        }
    )

    app._render_workspace_navigation(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == ""
    assert st.session_state[app._navigation_tertiary_state_key()] == ""
    assert st.rerun_called is True


@pytest.mark.parametrize(
    ("button_key", "secondary", "tertiary"),
    [
        (
            "atlas_accordion_tertiary_Knowledge_application_customers_add",
            "customers",
            "add",
        ),
        (
            "atlas_accordion_tertiary_Knowledge_application_vendors_price_lists",
            "vendors",
            "price_lists",
        ),
        (
            "atlas_accordion_tertiary_Knowledge_application_manufacturers_default_vendor",
            "manufacturers",
            "default_vendor",
        ),
        (
            "atlas_accordion_tertiary_Knowledge_application_catalog_import",
            "catalog",
            "import",
        ),
    ],
)
def test_knowledge_expander_links_route_same_window(
    button_key: str, secondary: str, tertiary: str
) -> None:
    st = _HomeContractStreamlit(pressed={button_key})
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): secondary,
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == secondary
    assert st.session_state[app._navigation_tertiary_state_key()] == tertiary
    assert st.session_state["atlas_active_page"] == "Knowledge"
    assert st.rerun_called is True


@pytest.mark.parametrize(
    ("primary", "mode", "current", "pressed_key", "expected_secondary"),
    [
        (
            "Projects",
            "library",
            "all_projects",
            "atlas_secondary_Projects_library_archived_projects",
            "archived_projects",
        ),
        (
            "Transactions",
            "application",
            "estimates",
            "atlas_secondary_Transactions_application_sales_orders",
            "sales_orders",
        ),
        (
            "Settings",
            "application",
            "organization_settings",
            "atlas_secondary_Settings_application_personal_preferences",
            "personal_preferences",
        ),
        (
            "Reports",
            "application",
            "project_reporting",
            "atlas_secondary_Reports_application_exports",
            "exports",
        ),
    ],
)
def test_shared_accordion_exclusive_behavior_across_workspaces(
    primary: str,
    mode: str,
    current: str,
    pressed_key: str,
    expected_secondary: str,
) -> None:
    st = _HomeContractStreamlit(pressed={pressed_key})
    st.session_state.update(
        {
            "atlas_active_page": {
                "Projects": "Projects",
                "Transactions": "Transactions",
                "Settings": "Administration",
                "Reports": "Reports",
            }[primary],
            app._navigation_primary_state_key(): primary,
            app._navigation_mode_state_key(): mode,
            app._navigation_secondary_state_key(): current,
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == expected_secondary
    assert st.rerun_called is True


def test_tertiary_action_keeps_parent_section_expanded() -> None:
    st = _HomeContractStreamlit(
        pressed={"atlas_accordion_tertiary_Transactions_application_sales_orders_add"}
    )
    st.session_state.update(
        {
            "atlas_active_page": "Transactions",
            app._navigation_primary_state_key(): "Transactions",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "sales_orders",
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == "sales_orders"
    assert st.session_state[app._navigation_tertiary_state_key()] == "add"
    assert st.rerun_called is True


def test_collapsed_secondary_state_survives_same_workspace_sync() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "",
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._sync_workspace_navigation_state(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == ""


def test_page_change_initializes_matching_workspace_section() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Documents",
            app._navigation_primary_state_key(): "Projects",
            app._navigation_mode_state_key(): "active",
            app._navigation_secondary_state_key(): "overview",
            app._navigation_tertiary_state_key(): "summary",
            app._navigation_synced_page_key(): "Overview",
        }
    )

    app._sync_workspace_navigation_state(st, record=_project_record("BID-1", "Demo"))

    assert st.session_state[app._navigation_secondary_state_key()] == "documents"
    assert st.session_state[app._navigation_tertiary_state_key()] == "add_files"


def test_expanded_secondary_state_survives_same_workspace_sync() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "vendors",
            app._navigation_tertiary_state_key(): "price_lists",
        }
    )

    app._sync_workspace_navigation_state(st, record=None)

    assert st.session_state[app._navigation_secondary_state_key()] == "vendors"
    assert st.session_state[app._navigation_tertiary_state_key()] == "price_lists"


def test_navigation_has_no_legacy_native_expander_helper() -> None:
    assert not hasattr(app, "_nav_buttons")
    source = inspect.getsource(app._render_workspace_navigation)
    assert ".expander(" not in source


def test_navigation_state_uses_no_independent_open_booleans() -> None:
    st = _HomeContractStreamlit(
        pressed={"atlas_secondary_Knowledge_application_vendors"}
    )
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_workspace_navigation(st, record=None)

    navigation_open_keys = [
        key
        for key in st.session_state
        if key.startswith("atlas_") and key.endswith("_open")
    ]
    assert navigation_open_keys == []


def test_customer_sort_defaults_name_ascending_and_toggles_direction() -> None:
    rows = [
        {"Customer Name": "Beta", "Customer ID": "CUST-0002"},
        {"Customer Name": "Alpha", "Customer ID": "CUST-0001"},
    ]
    st = _HomeContractStreamlit()

    column, direction = app._customer_sort_state(st)
    assert column == "Customer Name"
    assert direction == "asc"
    assert (
        app._sort_customer_rows(rows, column=column, direction=direction)[0][
            "Customer Name"
        ]
        == "Alpha"
    )

    app._toggle_customer_sort(st, "Customer Name")
    column, direction = app._customer_sort_state(st)
    assert direction == "desc"
    assert (
        app._sort_customer_rows(rows, column=column, direction=direction)[0][
            "Customer Name"
        ]
        == "Beta"
    )


def test_customer_id_preview_and_allocation_are_non_reusing() -> None:
    st = _HomeContractStreamlit()
    service = CommercialProductService()

    first_preview = app._preview_customer_id(st, service)
    second_preview = app._preview_customer_id(st, service)
    allocated = app._allocate_customer_id(st, service)

    assert first_preview == "CUST-0001"
    assert second_preview == "CUST-0001"
    assert allocated == "CUST-0001"
    assert app._preview_customer_id(st, service) == "CUST-0002"


def test_customer_id_preview_uses_settings_numbering_policy() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_settings_workspace"] = {
        "knowledge_numbering": {
            "customer": {
                "prefix": "CLIENT",
                "separator": "-",
                "sequence_padding": 3,
                "next_sequence": 7,
                "allocated_ids": [],
            }
        }
    }

    assert app._preview_customer_id(st, CommercialProductService()) == "CLIENT-007"


@pytest.mark.parametrize(
    ("secondary", "expected_labels"),
    [
        (
            "vendors",
            {
                "Create Vendor",
                "Save Vendor Edits",
                "Archive Vendor",
                "Restore Vendor",
            },
        ),
        (
            "manufacturers",
            {
                "Create Manufacturer",
                "Save Manufacturer Edits",
                "Archive Manufacturer",
                "Restore Manufacturer",
            },
        ),
        (
            "products",
            {
                "Create Product",
                "Save Product",
                "Archive Product",
                "Restore Product",
            },
        ),
        (
            "services",
            {
                "Create Service",
                "Save Service",
                "Archive Service",
                "Restore Service",
            },
        ),
    ],
)
def test_knowledge_entity_workspaces_render_crud_actions(
    secondary: str, expected_labels: set[str]
) -> None:
    st = _HomeContractStreamlit()
    entity_type_by_secondary = {
        "vendors": "vendor",
        "manufacturers": "manufacturer",
        "products": "product",
        "services": "service",
    }
    service = _seed_knowledge_service(entity_type_by_secondary[secondary])
    st.session_state["atlas_price_list_library"] = {
        "commercial_products": service.to_dict(),
    }
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): secondary,
            app._navigation_tertiary_state_key(): "browse",
        }
    )

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    rendered_labels = {call["label"] for call in st.button_calls}
    assert expected_labels <= rendered_labels


def test_hidden_knowledge_pages_route_to_contextual_secondary_sections() -> None:
    assert (
        app._secondary_key_for_page("Knowledge", "application", "Contacts")
        == "customers"
    )
    assert (
        app._secondary_key_for_page("Knowledge", "application", "Locations")
        == "customers"
    )
    assert (
        app._secondary_key_for_page("Knowledge", "application", "Price Lists")
        == "vendors"
    )
    assert (
        app._secondary_key_for_page("Knowledge", "application", "Assemblies")
        == "catalog"
    )
    assert (
        app._secondary_key_for_page("Knowledge", "application", "Catalog") == "catalog"
    )


def test_catalog_fees_route_to_fee_workspace() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "catalog",
            app._navigation_tertiary_state_key(): "fees",
        }
    )

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    assert "### Fees" in st.markdowns
    assert any(call["label"] == "Create Fee" for call in st.button_calls)


def test_customer_workspace_uses_single_name_field_and_no_json_controls() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "add",
        }
    )

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    labels = [item["label"] for item in st.text_inputs]
    assert "Customer Name" in labels
    assert "Canonical Name" not in labels
    assert "Display Name" not in labels
    assert all("JSON" not in call["label"] for call in st.download_buttons)


def test_customer_browse_uses_single_selector_and_no_sort_button_row() -> None:
    st = _HomeContractStreamlit()
    service = CommercialProductService()
    service.create_customer(customer_id="CUST-0002", canonical_name="Beta Customer")
    service.create_customer(customer_id="CUST-0001", canonical_name="Alpha Customer")
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "browse",
            "atlas_price_list_library": {"commercial_products": service.to_dict()},
        }
    )

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    labels = [call["label"] for call in st.button_calls]
    assert "Customer Name (A-Z)" not in labels
    assert "Customer ID" not in labels
    selector_labels = [call["label"] for call in st.selectbox_calls]
    assert selector_labels.count("Customer") == 1
    assert "Open Customer" not in selector_labels
    customer_selector = next(
        call for call in st.selectbox_calls if call["label"] == "Customer"
    )
    assert customer_selector["options"][0].startswith("Alpha Customer")
    assert not any(call["label"] == "Browse All" for call in st.expander_calls)
    assert any(call["label"] == "Supporting Details" for call in st.expander_calls)
    rendered_text = "\n".join([*st.markdowns, *st.captions])
    assert "Business Summary" in rendered_text
    assert "Operational Health" in rendered_text
    assert "Recommended Next Step" in rendered_text


def test_customer_knowledge_adapter_prioritizes_missing_contact() -> None:
    service = CommercialProductService()
    customer = service.create_customer(
        customer_id="CUST-1000",
        canonical_name="No Contact Customer",
        display_name="No Contact Customer",
    )
    row = {
        "Customer Name": "No Contact Customer",
        "Customer ID": "CUST-1000",
        "Primary Contact": "",
        "Location": "",
        "Active Projects": 0,
        "Open Commercial Documents": 0,
        "Status": "Active",
        "Last Activity": customer["updated_at"],
        "_entity": customer,
        "_record_key": "CUST-1000",
    }

    presentation = app._customer_knowledge_presentation(row, service)

    assert presentation.findings[0].title == "Primary contact missing"
    assert presentation.recommendation.action == "Add a primary customer contact."
    assert app._knowledge_issue_state(presentation.findings) == "Needs Attention"


def test_vendor_knowledge_adapter_uses_stored_purchasing_path() -> None:
    service = _seed_knowledge_service("product")
    vendor = service.get_vendor("vendor-avp")
    assert vendor is not None
    product = service.product_rows(include_project_only=True)[0]
    offering = service.list_vendor_offerings_by_product(product["atlas_product_uuid"])[
        0
    ]
    row = {
        "Vendor": "AV Partner",
        "Vendor ID": "vendor-avp",
        "Type": "Not defined",
        "Purchasing Channel": app._knowledge_channel_label(
            offering["purchasing_channel"],
            direct=bool(offering.get("direct_from_manufacturer", False)),
        ),
        "Primary Contact": "",
        "Active Offerings": 1,
        "Current Pricing": "Current",
        "Status": "Active",
        "Last Activity": vendor["updated_at"],
        "_entity": vendor,
        "_record_key": "vendor-avp",
    }

    presentation = app._vendor_knowledge_presentation(row, service)

    assert presentation.summary.facts[3]["Value"] == "Through distributor"
    assert any(item.label == "Purchasing path" for item in presentation.usage)


def test_catalog_product_adapter_reports_missing_cost_and_vendor() -> None:
    row = {
        "Item Type": "Product",
        "Name": "Unpriced SKU",
        "Manufacturer": "Maker",
        "Code": "SKU-1",
        "Family": "audio",
        "Status": "Active",
        "Preferred Vendor": "Not available",
        "Current Cost": "Not available",
        "Pricing Age": "Not available",
        "Recent Use": "No recent use",
        "Validation State": "Active",
        "Last Activity": "2026-01-01T00:00:00+00:00",
        "_record_key": "product-1",
    }

    presentation = app._catalog_knowledge_presentation(row)

    assert [item.title for item in presentation.findings][:2] == [
        "No approved vendor",
        "No current cost",
    ]
    assert presentation.recommendation.action == (
        "Select an approved vendor for this product."
    )


def test_knowledge_url_state_restores_selected_customer_record() -> None:
    st = _HomeContractStreamlit()
    service = _seed_knowledge_service("customer")
    st.query_params = {
        "atlas_knowledge_family": "customers",
        "atlas_knowledge_record": "CUST-0002",
    }
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            app._navigation_primary_state_key(): "Knowledge",
            app._navigation_mode_state_key(): "application",
            app._navigation_secondary_state_key(): "customers",
            app._navigation_tertiary_state_key(): "browse",
            "atlas_price_list_library": {"commercial_products": service.to_dict()},
        }
    )

    app._render_application_knowledge_page(st, _FakeWorkspaceService([]))

    assert st.session_state["atlas_ck_customer_selected_record_key"] == "CUST-0002"
    assert st.query_params["atlas_page"] == "Knowledge"
    assert st.query_params["atlas_knowledge_family"] == "customers"
    assert st.query_params["atlas_knowledge_record"] == "CUST-0002"


def test_quick_created_product_rows_ignore_compatibility_aliases() -> None:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-quick",
        canonical_name="Quick Maker",
        display_name="Quick Maker",
        manufacturer_code="QM",
    )
    created = service.create_product(
        manufacturer_id="mfr-quick",
        manufacturer="Quick Maker",
        manufacturer_part_number="SKU-QUICK",
        product_name="Quick SKU",
        product_description="Single SKU",
        category="audio",
        lifecycle_status="active",
    )

    rows = service.product_rows(include_project_only=True)

    assert rows[0]["atlas_product_uuid"] == created["atlas_product_uuid"]
    assert rows[0]["product_name"] == "Quick SKU"


def test_transactions_workspace_source_omits_overview_status_cards() -> None:
    source = inspect.getsource(app._render_transactions_workspace_page)

    assert "Pending Approval" not in source
    assert "Partially Received" not in source
    assert "Vendor Bills Pending Sync" not in source
    assert "Customer Invoices Pending Sync" not in source
    assert "Sync Failures" not in source
    assert '"overview"' not in source


def test_transactions_workspace_source_uses_shared_framework_helpers() -> None:
    source = inspect.getsource(app._render_transactions_workspace_page)

    assert "_shared_render_control_bar" in source
    assert "_render_commercial_transaction_workbench" in source


def test_knowledge_workspace_source_omits_summary_tables_and_health_cards() -> None:
    source = inspect.getsource(app._render_application_knowledge_page)

    assert "Knowledge Area" not in source
    assert "Why It Matters" not in source
    assert "Next Action" not in source
    assert "Library Health" not in source
    assert "Commercial Health" not in source


def test_knowledge_navigation_defaults_seed_secondary_and_tertiary_state() -> None:
    st = _FakeStreamlit(session_state={})

    app._knowledge_navigation_defaults(st)

    assert st.session_state["atlas_knowledge_secondary_group"] == "Customers"
    assert st.session_state["atlas_knowledge_tertiary_page"] == "Browse"


def test_knowledge_navigation_selection_maps_entity_kinds() -> None:
    st = _FakeStreamlit(session_state={})

    app._set_knowledge_navigation_selection(st, kind="manufacturer")

    assert st.session_state["atlas_knowledge_secondary_group"] == "Manufacturers"
    assert st.session_state["atlas_knowledge_tertiary_page"] == "browse"


def test_context_selection_populates_project_object_state() -> None:
    st = _FakeStreamlit(session_state={})

    app._set_context_selection(
        st,
        "drawing",
        {"drawing_number": "AV-601", "title": "Floor Plan"},
    )

    assert st.session_state["atlas_selected_project_object_type"] == "drawing"
    assert st.session_state["atlas_selected_project_object_id"] == "AV-601"
    assert st.session_state["atlas_selected_knowledge_entity_type"] == ""


def test_context_selection_populates_knowledge_entity_state() -> None:
    st = _FakeStreamlit(session_state={})

    app._set_context_selection(
        st,
        "vendor",
        {"vendor": "ADI", "vendor_id": "vendor-adi"},
    )

    assert st.session_state["atlas_selected_knowledge_entity_type"] == "vendor"
    assert st.session_state["atlas_selected_knowledge_entity_id"] == "ADI"
    assert st.session_state["atlas_selected_project_object_type"] == ""


def test_record_return_context_bounds_history_and_dedupes() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_primary_workspace": "Projects",
            "atlas_active_workspace_mode": "active",
            "atlas_active_page": "BOM Review",
            "atlas_active_secondary_section": "bom_review",
            "atlas_active_tertiary_action": "review_items",
            "atlas_active_workspace_id": "maw-demo",
            "atlas_active_project_name": "MAW",
            "atlas_context_selection": {
                "kind": "equipment",
                "data": {"equipment_id": "EQ-1", "manufacturer": "QSC"},
            },
            "atlas_tenant_scope": "local",
            "atlas_navigation_history": [],
        }
    )

    app._apply_context_selection_state(
        st,
        "equipment",
        {"equipment_id": "EQ-1", "manufacturer": "QSC"},
    )
    first = app._record_return_context(st, source_label="Open Product")
    second = app._record_return_context(st, source_label="Open Product")

    assert first["source_route"] == "BOM Review"
    assert second["source_object_id"] == "EQ-1"
    history = st.session_state["atlas_navigation_history"]
    assert len(history) == 1
    assert history[0]["tenant_scope"] == "local"


def test_return_context_rejects_tenant_mismatch() -> None:
    st = _FakeStreamlit(session_state={"atlas_tenant_scope": "local"})
    service = _FakeWorkspaceService([])

    assert (
        app._return_context_is_compatible(
            st,
            service,
            {
                "tenant_scope": "other-tenant",
                "source_route": "BOM Review",
                "source_workspace": "Projects",
            },
        )
        is False
    )


def test_header_search_control_uses_simple_search_placeholder() -> None:
    st = _HomeContractStreamlit()

    app._render_header(st, _FakeWorkspaceService([]), None, None)

    assert st.text_inputs[0]["label"] == "Search"
    assert st.text_inputs[0]["placeholder"] == "Search"
    assert st.text_inputs[0]["label_visibility"] == "collapsed"
    assert all("Global Object Search" not in item for item in st.markdowns)
    assert st.button_calls[0]["label"] == "Atlas"
    assert st.popover_labels == []


def test_header_uses_compact_responsive_column_contract() -> None:
    st = _HomeContractStreamlit()

    app._render_header(st, _FakeWorkspaceService([]), None, None)

    assert st.column_specs == [app.HEADER_NAV_COLUMN_SPEC]


def test_header_uses_single_responsive_row_and_omits_alpha_version_caption() -> None:
    st = _HomeContractStreamlit()

    app._render_header(st, _FakeWorkspaceService([]), None, None)

    assert st.column_specs == [app.HEADER_NAV_COLUMN_SPEC]
    assert all("Controlled Alpha" not in item for item in st.captions)
    assert all("0.1.0-a02" not in item for item in st.captions)


def test_top_navigation_order_places_transactions_first() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_page"] = "Transactions"

    app._render_top_navigation(st, st.columns(5), None)

    assert [call["label"] for call in st.button_calls] == [
        "Transactions",
        "Projects",
        "Knowledge",
        "Reports",
        "Settings",
    ]


def test_top_navigation_highlights_settings_workspace() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_page"] = "Administration"

    app._render_top_navigation(st, st.columns(5))

    settings_call = next(
        call for call in st.button_calls if call["label"] == "Settings"
    )
    assert settings_call["type"] == "primary"


def test_group_for_page_keeps_internal_mission_control_compatibility() -> None:
    assert (
        app._group_for_page(
            "Mission Control",
            _project_record("BID-2026-0001", "Compatibility Project"),
        )
        == "Mission Control"
    )


def test_submit_global_search_ignores_empty_query() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_input_0": "   "})

    app._submit_global_search(st)

    assert "atlas_global_search_query" not in st.session_state


def test_submit_global_search_records_non_empty_query() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_input_0": "  av-601  "})

    app._submit_global_search(st)

    assert st.session_state["atlas_global_search_query"] == "av-601"


def test_submit_global_search_rejects_punctuation_only_input() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_input_0": "..."})

    app._submit_global_search(st)

    assert "atlas_global_search_query" not in st.session_state


def test_submit_global_search_accepts_qsc_and_bid_identifier() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_input_0": "QSC"})
    app._submit_global_search(st)
    assert st.session_state["atlas_global_search_query"] == "QSC"

    st = _FakeStreamlit(session_state={"atlas_global_search_input_0": "BID-2026-0001"})
    app._submit_global_search(st)
    assert st.session_state["atlas_global_search_query"] == "BID-2026-0001"


def test_global_search_query_validation_rejects_punctuation_only_queries() -> None:
    assert app._is_meaningful_global_search_query("...") is False
    assert app._is_meaningful_global_search_query("  ") is False


def test_global_search_query_validation_accepts_compact_identifiers() -> None:
    assert app._is_meaningful_global_search_query("AV-601") is True
    assert app._is_meaningful_global_search_query("INT_0902") is True


def test_global_search_panel_skips_rendering_for_meaningless_queries() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_query": "..."})
    called = False

    def _unexpected(*args: Any, **kwargs: Any) -> None:
        nonlocal called
        _ = (args, kwargs)
        called = True

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(app, "_render_global_search_results", _unexpected)
    monkeypatch.setattr(app, "_global_search_entries", lambda *args, **kwargs: [])
    try:
        app._render_global_search_panel(st, _FakeWorkspaceService([]), None, None)
    finally:
        monkeypatch.undo()

    assert called is False


def test_render_shell_suppresses_body_when_search_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_global_search_query": "AV-601",
            "atlas_active_page": "Projects",
        }
    )
    service = _FakeWorkspaceService([])
    calls: list[str] = []

    monkeypatch.setattr(
        app, "_render_header", lambda *args, **kwargs: calls.append("header")
    )
    monkeypatch.setattr(
        app,
        "_sync_notebook_state_to_context",
        lambda *args, **kwargs: calls.append("sync"),
    )
    monkeypatch.setattr(app, "_breadcrumb", lambda *args, **kwargs: "breadcrumb")
    monkeypatch.setattr(
        app,
        "_render_global_search_panel",
        lambda *args, **kwargs: calls.append("search"),
    )
    monkeypatch.setattr(
        app, "_render_main_content", lambda *args, **kwargs: calls.append("body")
    )
    monkeypatch.setattr(
        app, "_render_status_bar", lambda *args, **kwargs: calls.append("status")
    )

    app._render_shell(st, service, None, None)

    assert "search" in calls
    assert "body" not in calls


def test_render_shell_keeps_visible_error_and_status_when_page_content_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _project_record("maw-demo", "MAW")
    st = _HomeContractStreamlit()
    app._init_session_state(st)
    st.session_state["atlas_active_page"] = "Overview"
    calls: list[str] = []

    monkeypatch.setattr(app, "_render_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_sync_notebook_state_to_context", lambda *args: None)
    monkeypatch.setattr(app, "_active_global_search_query", lambda *_args: "")
    monkeypatch.setattr(app, "_render_return_context_action", lambda *args: None)
    monkeypatch.setattr(app, "_sync_workspace_navigation_state", lambda *args: None)
    monkeypatch.setattr(
        app,
        "_render_workspace_navigation",
        lambda _st, _record, content_renderer=None: content_renderer(),
    )
    monkeypatch.setattr(
        app,
        "_render_main_content",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        app, "_log_application_error", lambda *args, **kwargs: "ERR-CONTENT"
    )
    monkeypatch.setattr(
        app, "_render_status_bar", lambda *args, **kwargs: calls.append("status")
    )

    app._render_shell(st, _FakeWorkspaceService([record]), record, None)

    assert calls == ["status"]
    assert st.errors == [
        "Overview could not be loaded. Reference Error ID: ERR-CONTENT"
    ]
    assert any(
        call.get("key") == "atlas_content_failure_home_overview"
        for call in st.button_calls
    )
    assert any(
        call.get("key") == "atlas_content_failure_retry_overview"
        for call in st.button_calls
    )


def test_breadcrumb_page_label_maps_mission_control_to_home() -> None:
    assert app._breadcrumb_page_label("Mission Control") == "Home"


def test_breadcrumb_page_label_maps_administration_to_settings() -> None:
    assert app._breadcrumb_page_label("Administration") == "Settings"


def test_breadcrumb_for_mission_control_renders_home_for_users() -> None:
    assert app._breadcrumb(None, "Mission Control") == "Atlas / Home"


def test_shell_breadcrumb_hides_redundant_workspace_labels() -> None:
    st = _FakeStreamlit(session_state={"atlas_context_selection": {}})

    assert app._should_render_shell_breadcrumb(st, "Mission Control") is False
    assert app._should_render_shell_breadcrumb(st, "Projects") is False
    assert app._should_render_shell_breadcrumb(st, "Knowledge") is False
    assert app._should_render_shell_breadcrumb(st, "Transactions") is False


def test_shell_breadcrumb_preserves_object_level_context() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_context_selection": {
                "kind": "equipment",
                "data": {"equipment_id": "EQ-1"},
            }
        }
    )

    assert app._should_render_shell_breadcrumb(st, "BOM Review") is True
    assert app._should_render_shell_breadcrumb(st, "Object Workspace") is True


def test_breadcrumb_includes_selected_knowledge_product_context() -> None:
    streamlit_stub = SimpleNamespace(
        session_state={
            "atlas_context_selection": {
                "kind": "master_product",
                "data": {
                    "manufacturer": "QSC",
                    "model": "Core 110f",
                    "canonical_sku": "Core 110f",
                },
            }
        }
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_stub)
    try:
        result = app._breadcrumb(_project_record("maw-demo", "MAW"), "Knowledge")
    finally:
        monkeypatch.undo()

    assert result == "Atlas / Knowledge / Products / QSC Core 110f"


def test_breadcrumb_keeps_project_context_for_active_project_reports() -> None:
    result = app._breadcrumb(_project_record("maw-demo", "MAW"), "Reports")

    assert result == "Atlas / Projects / MAW / Reports"


def test_restore_context_entry_clears_invalid_return_context_and_reruns() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_return_context": {
                "tenant_scope": "other-tenant",
                "source_workspace": "Projects",
                "source_route": "BOM Review",
            },
            "atlas_tenant_scope": "local",
        }
    )

    app._restore_context_entry(
        st,
        _FakeWorkspaceService([]),
        dict(st.session_state["atlas_return_context"]),
    )

    assert st.session_state["atlas_return_context"] == {}
    assert st.rerun_called is True


def test_return_context_label_prefers_source_label_over_route() -> None:
    label = app._return_context_label(
        {"source_label": "Project Summary", "source_route": "Reports"}
    )

    assert label == "Return to Project Summary"


def test_open_knowledge_selection_preserves_project_return_context() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_primary_workspace": "Projects",
            "atlas_active_workspace_mode": "active",
            "atlas_active_page": "BOM Review",
            "atlas_active_secondary_section": "bom_review",
            "atlas_active_tertiary_action": "review_items",
            "atlas_active_workspace_id": "maw-demo",
            "atlas_active_project_name": "MAW",
            "atlas_context_selection": {
                "kind": "equipment",
                "data": {"equipment_id": "EQ-1"},
            },
            "atlas_tenant_scope": "local",
            "atlas_navigation_history": [],
        }
    )

    app._apply_context_selection_state(st, "equipment", {"equipment_id": "EQ-1"})
    app._open_knowledge_selection(
        st,
        kind="manufacturer",
        data={"manufacturer": "QSC", "manufacturer_id": "QSC"},
        source_label="BOM Review",
    )

    assert st.session_state["atlas_active_page"] == "Knowledge"
    assert st.session_state["atlas_selected_knowledge_entity_type"] == "manufacturer"
    assert st.session_state["atlas_active_secondary_section"] == "manufacturers"
    assert st.session_state["atlas_active_tertiary_action"] == "browse"
    assert st.session_state["atlas_return_context"]["source_route"] == "BOM Review"
    assert st.rerun_called is True


def test_restore_context_entry_returns_to_valid_project_route() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={"atlas_tenant_scope": "local"})
    service = _FakeWorkspaceService([record])

    app._restore_context_entry(
        st,
        service,
        {
            "tenant_scope": "local",
            "source_workspace": "Projects",
            "source_route": "Estimate",
            "source_project": "maw-demo",
            "source_secondary": "estimate",
            "source_tertiary": "equipment",
            "source_object_kind": "equipment",
            "source_selection": {"equipment_id": "EQ-1"},
        },
    )

    assert st.session_state["atlas_active_workspace_id"] == "maw-demo"
    assert st.session_state["atlas_active_page"] == "Estimate"
    assert st.session_state["atlas_active_secondary_section"] == "estimate"
    assert st.session_state["atlas_context_selection"]["kind"] == "equipment"
    assert st.rerun_called is True


def test_related_projects_for_customer_uses_repository_data() -> None:
    record = _project_record("maw-demo", "MAW")
    record.project.client = "Acme"
    record.metadata["owner"] = "Acme"
    service = _FakeWorkspaceService([record])

    rows = app._related_projects_for_knowledge_entity(
        service,
        entity_kind="customer",
        data={"customer": "Acme"},
    )

    assert rows[0]["workspace_id"] == "maw-demo"
    assert rows[0]["reason"] == "Customer match"


def test_working_set_supports_project_and_knowledge_records() -> None:
    st = _FakeStreamlit(session_state={"atlas_pinned_objects": []})
    project_object = {
        "object_id": "EQ-1",
        "object_type": "Equipment",
        "display_name": "QSC Core",
    }
    knowledge_object = {
        "object_id": "vendor-adi",
        "object_type": "Vendor",
        "display_name": "ADI",
    }

    app._toggle_pin_reference(st, project_object, should_pin=True)
    app._toggle_pin_reference(st, knowledge_object, should_pin=True)

    assert [
        item["object_type"] for item in st.session_state["atlas_pinned_objects"]
    ] == [
        "Vendor",
        "Equipment",
    ]


def test_mission_control_rendering_uses_operations_center_sections() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService(
        [
            _project_record("project-b", "Project B"),
            _project_record("project-a", "Project A"),
        ]
    )

    app._render_home_page(
        st,
        workspace_service=service,
        record=None,
        context=None,
        mission_control_payload={},
    )

    assert st.subheaders == ["Tenant Operations Center"]
    assert "### My Work" in st.markdowns
    assert "### Recent Activity" in st.markdowns
    assert "### Business Risks" in st.markdowns
    assert "### Continue Working" in st.markdowns
    assert "### Company Snapshot" in st.markdowns
    removed_titles = {
        "### Application Areas",
        "### Portfolio Signals",
        "### Upcoming Timeline",
        "### Projects Requiring Attention",
        "### Workspace Recommendations",
        "### Action Center",
        "### Notifications",
        "### Favorites",
        "### Recent Projects",
    }
    assert all(title not in st.markdowns for title in removed_titles)


def test_atlas_workspace_without_secondary_sections_still_renders_content() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_navigation_primary"] = "Atlas"
    st.session_state["atlas_active_workspace_mode"] = "application"

    app._render_workspace_navigation(
        st,
        record=None,
        content_renderer=lambda: st.markdown("Tenant Operations Center rendered"),
    )

    assert "Tenant Operations Center rendered" in st.markdowns
    assert st.column_specs == []


def test_home_primary_actions_route_correctly() -> None:
    actions = {
        "Create New Project": "Create New Project",
        "Open Existing Project": "Open Existing Project",
        "Manage Projects": "Projects",
    }
    for button_label, expected_page in actions.items():
        st = _HomeContractStreamlit(pressed={button_label})
        service = _FakeWorkspaceService([])

        app._render_home_page(
            st,
            workspace_service=service,
            record=None,
            context=None,
            mission_control_payload={},
        )

        assert st.session_state["atlas_active_page"] == expected_page
        assert st.rerun_called is True


def test_home_primary_actions_use_compact_responsive_columns() -> None:
    st = _HomeContractStreamlit()

    app._render_home_page(
        st,
        workspace_service=_FakeWorkspaceService([]),
        record=None,
        context=None,
        mission_control_payload={},
    )

    assert st.column_specs[0] == [1.0, 1.0, 1.0]


def test_injected_styles_define_centered_content_width() -> None:
    st = _HomeContractStreamlit()

    app._inject_styles(st)

    assert any("max-width: 1440px" in item for item in st.markdowns)
    assert any("width: min(calc(100% - 2rem), 1440px)" in item for item in st.markdowns)


def test_injected_styles_define_visual_system_background_and_accent() -> None:
    st = _HomeContractStreamlit()

    app._inject_styles(st)

    assert any("--atlas-page-bg: #FAFAF9" in item for item in st.markdowns)
    assert any("--atlas-primary: #004225" in item for item in st.markdowns)
    assert any(
        '.stButton > button[kind="primary"]' in item
        and "background: var(--atlas-primary)" in item
        for item in st.markdowns
    )


def test_injected_styles_keep_red_for_error_not_primary_actions() -> None:
    st = _HomeContractStreamlit()

    app._inject_styles(st)

    stylesheet = "\n".join(st.markdowns)
    assert "--atlas-red: #dc2626" in stylesheet
    assert 'button[kind="primary"]' in stylesheet
    assert (
        'button[kind="primary"]' in stylesheet
        and "#dc2626"
        not in stylesheet.split(
            '.stButton > button[kind="primary"]',
            maxsplit=1,
        )[
            1
        ].split("}", maxsplit=1)[0]
    )


def test_injected_styles_include_transactions_primary_nav_contract() -> None:
    st = _HomeContractStreamlit()

    app._inject_styles(st)

    stylesheet = "\n".join(st.markdowns)
    assert ".st-key-atlas_header_nav_Transactions button" in stylesheet
    assert ".st-key-atlas_header_nav_Settings button" in stylesheet
    assert "--atlas-header-search-max-width" in stylesheet
    assert ".st-key-atlas_header_menu_toggle" not in stylesheet
    assert "var(--atlas-heading-3-size)" in stylesheet


def test_injected_styles_define_predictable_search_compression() -> None:
    st = _HomeContractStreamlit()

    app._inject_styles(st)

    stylesheet = "\n".join(st.markdowns)
    assert "@media (max-width: 960px)" in stylesheet
    assert ".st-key-atlas_header_nav_Transactions" in stylesheet
    assert ".st-key-atlas_header_nav_Settings" in stylesheet
    assert '[class*="st-key-atlas_global_search_input_"] input' in stylesheet
    assert "max-width: 11rem" in stylesheet
    assert "max-width: 9.5rem" in stylesheet
    assert "overflow-x: clip" in stylesheet


def test_home_page_renders_operational_sections() -> None:
    st = _HomeContractStreamlit()

    app._render_home_page(st, _FakeWorkspaceService([]), None, None, {})

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Tenant Operations Center" in rendered_text
    assert "My Work" in rendered_text
    assert "Recent Activity" in rendered_text
    assert "Business Risks" in rendered_text
    assert "Continue Working" in rendered_text
    assert "Company Snapshot" in rendered_text


def test_projects_library_page_uses_shared_workspace_sections() -> None:
    records = [
        _project_record("project-b", "Project B"),
        _project_record("project-a", "Project A"),
    ]
    records[0].pinned = True
    records[1].is_reference = True
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService(records)

    app._render_projects_page(st, service)

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Project Operations" in rendered_text
    assert "### Projects" in st.markdowns
    assert "### Selected Project" in st.markdowns
    assert any(call["label"] == "Open Project" for call in st.button_calls)
    assert any(
        call["label"] == "Delete" and call["disabled"] for call in st.button_calls
    )


def test_projects_import_secondary_route_renders_import_workflow() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_page"] = "Import Project"
    service = _FakeWorkspaceService([])

    app._render_main_content(st, service, None, None)

    rendered_text = "\n".join([*st.markdowns, *st.captions])
    assert "Import Project" in rendered_text
    assert "Supported paths" in rendered_text
    assert any(
        call["label"] == "Import Project" and call["disabled"]
        for call in st.button_calls
    )
    assert "Enter a supported project path before importing." in st.captions


def test_import_project_page_maps_to_projects_import_navigation() -> None:
    assert (
        app._secondary_key_for_page("Projects", "library", "Import Project")
        == "import_project"
    )
    assert "Import Project" in app.ALL_ACTIVE_PAGES


def test_project_import_bundle_returns_to_projects_with_feedback() -> None:
    st = _HomeContractStreamlit(pressed={"atlas_import_project_primary"})
    st.session_state["atlas_active_page"] = "Import Project"
    st.session_state["atlas_project_import_path"] = "/tmp/Northstar.atlaspkg"
    service = _FakeWorkspaceService([])

    app._render_main_content(st, service, None, None)

    assert service.list_workspaces()[0].project.name == "Northstar"
    assert st.session_state["atlas_active_page"] == "Projects"
    assert st.session_state[app._navigation_secondary_state_key()] == "all_projects"
    assert st.rerun_called is True
    assert st.session_state["atlas_project_action_feedback"]["level"] == "success"
    assert not st.errors


def test_pinned_projects_page_uses_shared_workspace_sections() -> None:
    record = _project_record("project-a", "Project A")
    record.pinned = True
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([record])

    app._render_pinned_projects_page(st, service)

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Pinned Projects" in rendered_text
    assert "### Pinned Project List" in st.markdowns
    assert "### Selected Pinned Project" in st.markdowns


def test_reference_projects_page_uses_shared_workspace_sections() -> None:
    record = _project_record("reference-a", "Reference A")
    record.is_reference = True
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([record])

    app._render_reference_projects_page(st, service)

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Reference Projects" in rendered_text
    assert "### Reference Project List" in st.markdowns
    assert "### Selected Reference Project" in st.markdowns


def test_recent_projects_page_uses_shared_workspace_sections() -> None:
    record = _project_record("recent-a", "Recent A")
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([record])

    app._render_recent_projects_page(st, service)

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Recent Projects" in rendered_text
    assert "### Recent Project List" in st.markdowns
    assert "### Selected Recent Project" in st.markdowns


def test_footer_renders_tenant_copyright_without_diagnostics() -> None:
    st = _HomeContractStreamlit()

    app._render_status_bar(st, None, None)

    assert "©2026 Corsa Systems. All rights reserved." in st.captions
    assert all("Atlas v" not in item for item in st.captions)
    assert len(st.captions) >= 2


def test_mission_control_my_work_renders_only_actionable_deduplicated_items() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([_project_record("project-a", "Project A")])

    app._render_mission_control_panels(
        st,
        service,
        {
            "actions": [
                {
                    "priority": "High",
                    "title": "Resolve missing docs",
                    "project": "P1",
                    "destination": "Documents",
                },
                {
                    "priority": "High",
                    "title": "Resolve missing docs",
                    "project": "P1",
                    "destination": "Documents",
                },
                {
                    "priority": "Medium",
                    "title": "Optional review",
                    "project": "P1",
                    "destination": "Overview",
                },
            ],
            "timeline": [],
        },
    )

    assert "### My Work" in st.markdowns
    rendered_cards = [
        item
        for item in st.markdowns
        if item.startswith("**") and "Project A" not in item
    ]
    assert rendered_cards == ["**Resolve missing docs**", "**Optional review**"]
    assert any("Project: P1" in item for item in st.captions)


def test_continue_working_renders_project_cards_and_resume_actions() -> None:
    record = _project_record("project-a", "Project A")
    record.project.internal_project_number = "INT-42"
    record.last_opened_at = "2024-01-02T12:00:00+00:00"
    st = _HomeContractStreamlit(pressed={"Resume Project"})
    service = _FakeWorkspaceService([record])

    app._render_mission_control_panels(st, service, {"actions": [], "timeline": []})

    assert any("Project A" in item for item in st.markdowns)
    assert any("INT-42" in item for item in st.captions)
    assert st.rerun_called is True


def test_continue_working_section_limits_to_five_items() -> None:
    records = []
    for index in range(6):
        record = _project_record(f"project-{index}", f"Project {index}")
        record.last_opened_at = f"2024-01-0{index + 1}T12:00:00+00:00"
        records.append(record)
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService(records)

    app._render_mission_control_panels(st, service, {"actions": [], "timeline": []})

    card_markdowns = [item for item in st.markdowns if item.startswith("**Project")]
    assert len(card_markdowns) == 5


def test_continue_working_resume_action_updates_recency() -> None:
    record = _project_record("project-a", "Project A")
    st = _HomeContractStreamlit(pressed={"Resume Project"})
    service = _FakeWorkspaceService([record])

    app._render_mission_control_panels(st, service, {"actions": [], "timeline": []})

    assert service.opened_records == ["project-a"]
    assert service.saved_records == []
    assert st.rerun_called is True


def test_recent_projects_empty_state_message_is_concise() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([])

    app._render_mission_control_panels(st, service, {"actions": [], "timeline": []})

    assert "No recent projects." in st.captions


def test_mission_control_empty_tenant_has_no_placeholder_cards() -> None:
    st = _HomeContractStreamlit()

    app._render_home_page(st, _FakeWorkspaceService([]), None, None, {})

    assert not [item for item in st.markdowns if item.startswith("**")]
    assert "No actionable work items." in st.captions
    assert "No significant operational risks detected." in st.captions


def test_mission_control_populated_tenant_renders_all_operational_sections() -> None:
    record = _project_record("project-a", "Project A")
    record.last_opened_at = "2026-07-18T12:00:00+00:00"
    st = _HomeContractStreamlit()

    app._render_home_page(
        st,
        _FakeWorkspaceService([record]),
        None,
        None,
        {
            "actions": [
                {
                    "priority": "High",
                    "title": "Refresh stale pricing",
                    "project": "Project A",
                    "destination": "Estimate",
                }
            ],
            "timeline": [
                {
                    "event": "Estimate revised",
                    "project": "Project A",
                    "timestamp": "2026-07-19T12:00:00+00:00",
                }
            ],
            "signals": [
                {
                    "status": "Needs Attention",
                    "project": "Project A",
                    "reason": "Pricing requires refresh",
                    "destination": "Estimate",
                }
            ],
        },
    )

    rendered_text = "\n".join([*st.markdowns, *st.captions])
    assert "Refresh stale pricing" in rendered_text
    assert "Project A" in rendered_text
    assert any(
        row.get("Activity") == "Estimate revised"
        for table in st.dataframes
        for row in table
    )
    assert any(
        row.get("Risk") == "Pricing requires refresh"
        for table in st.dataframes
        for row in table
    )


def test_mission_control_responsive_layout_uses_main_and_snapshot_columns() -> None:
    st = _HomeContractStreamlit()

    app._render_home_page(st, _FakeWorkspaceService([]), None, None, {})

    assert [1.0, 1.0, 1.0] in st.column_specs
    assert [2.15, 1.0] in st.column_specs


def test_mission_control_card_ordering_prioritizes_critical_work() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([_project_record("project-a", "Project A")])

    app._render_mission_control_panels(
        st,
        service,
        {
            "actions": [
                {
                    "priority": "Medium",
                    "title": "Review project setup",
                    "project": "Project A",
                    "destination": "Projects",
                },
                {
                    "priority": "Critical",
                    "title": "Resolve blocked estimate",
                    "project": "Project A",
                    "destination": "Estimate",
                },
            ],
            "timeline": [],
        },
    )

    cards = [item for item in st.markdowns if item.startswith("**")]
    assert cards[:2] == ["**Resolve blocked estimate**", "**Review project setup**"]


def test_mission_control_my_work_action_opens_project_destination() -> None:
    record = _project_record("project-a", "Project A")
    st = _HomeContractStreamlit(pressed={"Estimate"})

    app._render_mission_control_panels(
        st,
        _FakeWorkspaceService([record]),
        {
            "actions": [
                {
                    "priority": "High",
                    "title": "Review estimate",
                    "project": "Project A",
                    "destination": "Estimate",
                }
            ],
            "timeline": [],
        },
    )

    assert st.session_state["atlas_active_workspace_id"] == "project-a"
    assert st.session_state["atlas_active_page"] == "Estimate"
    assert st.rerun_called is True


def test_mission_control_risk_section_reports_exceptions_and_clear_state() -> None:
    clear = _HomeContractStreamlit()
    service = _FakeWorkspaceService([_project_record("project-a", "Project A")])

    app._render_mission_control_panels(clear, service, {"actions": [], "signals": []})

    assert "No significant operational risks detected." in clear.captions

    populated = _HomeContractStreamlit()
    app._render_mission_control_panels(
        populated,
        service,
        {
            "actions": [],
            "signals": [
                {
                    "status": "Blocked",
                    "project": "Project A",
                    "reason": "Unresolved RFI",
                    "destination": "Scope & Risk",
                }
            ],
        },
    )

    assert any(
        row.get("Risk") == "Unresolved RFI" and row.get("Severity") == "Critical"
        for table in populated.dataframes
        for row in table
    )


def test_mission_control_activity_section_groups_similar_events() -> None:
    st = _HomeContractStreamlit()

    app._render_mission_control_panels(
        st,
        _FakeWorkspaceService([]),
        {
            "timeline": [
                {
                    "event": "Estimate revised",
                    "project": "Project A",
                    "timestamp": "2026-07-19T12:00:00+00:00",
                },
                {
                    "event": "Estimate revised",
                    "project": "Project A",
                    "timestamp": "2026-07-20T12:00:00+00:00",
                },
            ]
        },
    )

    activity_rows = [
        row
        for table in st.dataframes
        for row in table
        if row.get("Activity") == "Estimate revised"
    ]
    assert activity_rows == [
        {
            "Activity": "Estimate revised",
            "Project": "Project A",
            "Count": 2,
            "Latest": "2026-07-20T12:00:00+00:00",
        }
    ]


def test_mission_control_company_snapshot_limits_to_six_kpis() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([_project_record("project-a", "Project A")])

    app._render_mission_control_panels(
        st,
        service,
        {
            "actions": [
                {
                    "priority": "High",
                    "title": "Review estimate",
                    "project": "Project A",
                    "destination": "Estimate",
                }
            ],
            "timeline": [],
        },
    )

    snapshot = st.dataframes[-1]
    assert len(snapshot) == 6
    assert [row["KPI"] for row in snapshot] == [
        "Active projects",
        "Open work items",
        "Operational risks",
        "Recent changes",
        "Projects in estimating",
        "Setup incomplete",
    ]


def test_footer_shows_tenant_neutral_branding_without_diagnostics() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_active_primary_workspace"] = "Projects"
    st.session_state["atlas_active_secondary_section"] = "overview"

    app._render_status_bar(st, None, None)

    assert any(
        "©2026 Corsa Systems. All rights reserved." in item for item in st.captions
    )
    assert all("commit" not in item for item in st.captions)
    assert all("tests" not in item for item in st.captions)
    assert all(
        phrase not in " ".join(st.captions)
        for phrase in ["Current workspace", "Section:", "Last intake", "Last review"]
    )


def test_page_purpose_defaults_do_not_include_deprecated_explanatory_copy() -> None:
    assert app._PAGE_PURPOSE_SUBTITLES == {}


def test_deprecated_workspace_descriptive_copy_is_absent_from_source() -> None:
    assert app.__file__ is not None
    source = Path(app.__file__).read_text()
    removed_copy = [
        "Shared commercial and reference entities used across projects.",
        "Commercial document workflows with deterministic lifecycle and revision controls.",
        "Primary project library for opening, creating, importing, and managing repository projects.",
        "Delivery-ready outputs and readiness summaries across active work.",
        "Tenant and personal configuration with deterministic policy boundaries.",
    ]
    assert all(item not in source for item in removed_copy)


def test_estimate_add_route_uses_dedicated_workspace_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, bool] = {"value": False}

    class _Metrics:
        draft_documents = 0
        pending_approval = 0
        issued_documents = 0
        open_purchase_orders = 0
        partially_received_purchase_orders = 0
        vendor_bills_pending_sync = 0
        customer_invoices_pending_sync = 0
        sync_failures = 0

    class _Service:
        def overview_metrics(self) -> _Metrics:
            return _Metrics()

    st = _HomeContractStreamlit()
    st.session_state[app._navigation_secondary_state_key()] = "estimates"
    st.session_state[app._navigation_tertiary_state_key()] = "add"

    monkeypatch.setattr(app, "_render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_metric_card", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_transactions_workspace_service", lambda _st: _Service())

    def _capture(*args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)
        called["value"] = True

    monkeypatch.setattr(app, "_render_estimate_add_workspace", _capture)

    app._render_transactions_workspace_page(st, _FakeWorkspaceService([]))

    assert called["value"] is True


def test_estimate_add_workspace_does_not_expose_vendor_id_field() -> None:
    source = inspect.getsource(app._render_estimate_add_workspace)
    assert "Vendor ID" not in source


def test_estimate_catalog_search_rows_supports_item_type_filters() -> None:
    service = app.TransactionsWorkspaceService(
        active_tenant_id="local",
        active_organization_id="atlas",
        serialized_catalog_state={
            "catalog_items": {
                "product:sku-a": {
                    "catalog_item_id": "product:sku-a",
                    "item_type": "product",
                    "code": "SKU-A",
                    "name": "Product A",
                    "description": "Product line",
                    "status": "active",
                    "archived": False,
                },
                "service:svc-a": {
                    "catalog_item_id": "service:svc-a",
                    "item_type": "service",
                    "code": "SVC-A",
                    "name": "Service A",
                    "description": "Service line",
                    "status": "active",
                    "archived": False,
                },
                "fee:fee-a": {
                    "catalog_item_id": "fee:fee-a",
                    "item_type": "fee",
                    "code": "FEE-A",
                    "name": "Fee A",
                    "description": "Fee line",
                    "status": "active",
                    "archived": False,
                },
                "assembly:asm-a": {
                    "catalog_item_id": "assembly:asm-a",
                    "item_type": "assembly",
                    "code": "ASM-A",
                    "name": "Assembly A",
                    "description": "Assembly line",
                    "status": "active",
                    "archived": False,
                },
            }
        },
    )

    rows = app._estimate_catalog_search_rows(
        service,
        search="",
        item_type="all",
        include_archived=False,
    )
    assert {app._safe_text(row.get("item_type"), "") for row in rows} == {
        "product",
        "service",
        "fee",
        "assembly",
    }

    service_rows = app._estimate_catalog_search_rows(
        service,
        search="service",
        item_type="service",
        include_archived=False,
    )
    assert len(service_rows) == 1
    assert service_rows[0]["catalog_item_id"] == "service:svc-a"


def test_estimate_totals_support_manual_sales_price_override() -> None:
    service = app.TransactionsWorkspaceService(
        active_tenant_id="local",
        active_organization_id="atlas",
        serialized_catalog_state={
            "catalog_items": {
                "product:sku-a": {
                    "catalog_item_id": "product:sku-a",
                    "item_type": "product",
                    "code": "SKU-A",
                    "name": "Product A",
                    "description": "Product line",
                    "status": "active",
                    "cost": 6.0,
                    "default_sales_price": 10.0,
                    "taxable": False,
                    "archived": False,
                }
            }
        },
    )
    draft = service.create_draft(
        tenant_id="local",
        organization_id="atlas",
        document_type=app.CommercialDocumentType.ESTIMATE,
        customer_id="cust-1",
    )
    service.add_catalog_line(
        document_id=draft.document_id,
        catalog_item_id="product:sku-a",
        quantity=Decimal("2"),
    )
    document = service.get_document(draft.document_id)
    assert document is not None
    assert document.totals.subtotal == Decimal("20")

    document.lines[0].unit_price = Decimal("12")
    service._commercial_service.recompute_totals(document)
    assert document.totals.subtotal == Decimal("24")


def test_open_search_reference_routes_to_target_page() -> None:
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[])
    reference = {
        "route": "Drawings",
        "selection_kind": "drawing",
        "selection_data": {"drawing_number": "AV-601"},
        "object_id": "AV-601",
        "object_type": "Drawing",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_page"] == "Object Workspace"
    assert st.session_state["atlas_context_selection"]["kind"] == "drawing"
    assert st.session_state["atlas_object_workspace_view"] == "Summary"
    assert st.rerun_called is True


def test_open_search_reference_sets_knowledge_navigation_state() -> None:
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[])
    reference = {
        "route": "Knowledge",
        "selection_kind": "vendor",
        "selection_data": {"vendor_id": "vendor-1"},
        "object_id": "vendor-1",
        "object_type": "Vendor",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_page"] == "Object Workspace"
    assert st.session_state["atlas_knowledge_secondary_group"] == "Vendors"
    assert st.session_state["atlas_knowledge_tertiary_page"] == "browse"
    assert st.session_state["atlas_context_selection"]["kind"] == "vendor"
    assert st.session_state["atlas_return_context"]["source_route"] == "Mission Control"
    assert st.rerun_called is True


def test_open_search_reference_sets_projects_library_navigation_state() -> None:
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[])
    reference = {
        "route": "Projects",
        "selection_kind": "project",
        "selection_data": {"project_id": "BID-2026-1001"},
        "object_id": "BID-2026-1001",
        "object_type": "Project",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_page"] == "Object Workspace"
    assert st.session_state["atlas_active_primary_workspace"] == "Projects"
    assert st.session_state["atlas_active_workspace_mode"] == "active"
    assert st.session_state["atlas_active_secondary_section"] == "overview"
    assert st.rerun_called is True


def test_open_search_reference_sets_projects_active_navigation_state() -> None:
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[])
    reference = {
        "route": "Drawings",
        "selection_kind": "drawing",
        "selection_data": {"drawing_number": "AV-601"},
        "object_id": "AV-601",
        "object_type": "Drawing",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_primary_workspace"] == "Projects"
    assert st.session_state["atlas_active_workspace_mode"] == "active"
    assert st.session_state["atlas_active_secondary_section"] == "project_details"
    assert st.session_state["atlas_active_page"] == "Object Workspace"
    assert st.rerun_called is True


def test_workspace_navigation_uses_two_column_shell_contract() -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_primary_workspace": "Projects",
            "atlas_active_workspace_mode": "library",
            "atlas_active_secondary_section": "overview",
            "atlas_active_tertiary_action": "browse",
            "atlas_active_page": "Projects",
        }
    )
    rendered = {"content": False}

    app._render_workspace_navigation(
        st,
        record=None,
        content_renderer=lambda: rendered.__setitem__("content", True),
    )

    assert app.BODY_SHELL_COLUMN_SPEC in st.column_specs
    assert rendered["content"] is True


def test_application_reports_remain_output_oriented() -> None:
    st = _HomeContractStreamlit()
    service = _FakeWorkspaceService([])
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        app,
        "_collect_workspace_signals",
        lambda *_args, **_kwargs: [
            {
                "project": "MAW",
                "status": "Ready",
                "destination": "Estimate",
                "reason": "Ready for export",
                "review_artifacts": 3,
                "updated_at": "2026-01-01T10:00:00+00:00",
            }
        ],
    )
    try:
        app._render_application_reports_page(st, service)
    finally:
        monkeypatch.undo()

    assert st.dataframes
    first_row = st.dataframes[0][0]
    assert "Output Family" in first_row
    assert "Commercial Documents" in first_row
    assert "Exports" in first_row
    assert "Processing" in first_row
    assert "Next Output" not in first_row


def test_application_reports_source_uses_shared_framework_helpers() -> None:
    source = inspect.getsource(app._render_application_reports_page)

    assert "_shared_render_metric_strip" in source
    assert "_shared_render_section_card" in source
    assert "_shared_render_report_table" in source


def test_workflow_reports_source_uses_shared_framework_helpers() -> None:
    source = inspect.getsource(app._render_workflow_reports_page)

    assert "_shared_render_section_card" in source
    assert "_shared_render_report_table" in source


def test_status_bar_shows_diagnostics_only_for_platform_admin() -> None:
    class _PermissionService:
        def __init__(self, allowed: bool) -> None:
            self._allowed = allowed

        def evaluate(self, _request: Any) -> Any:
            return SimpleNamespace(allowed=self._allowed)

    base_state = {
        "atlas_active_primary_workspace": "Settings",
        "atlas_active_secondary_section": "platform_management",
        "atlas_settings_user_id": "admin-user",
    }

    tenant_view = _HomeContractStreamlit()
    tenant_view.session_state.update(base_state)
    admin_view = _HomeContractStreamlit()
    admin_view.session_state.update(base_state)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        app,
        "_permissions_workspace_service",
        lambda _st: _PermissionService(allowed=False),
    )
    try:
        app._render_status_bar(tenant_view, None, None)
    finally:
        monkeypatch.undo()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        app,
        "_permissions_workspace_service",
        lambda _st: _PermissionService(allowed=True),
    )
    try:
        app._render_status_bar(admin_view, None, None)
    finally:
        monkeypatch.undo()

    assert all("commit" not in item for item in tenant_view.captions)
    assert any("commit" in item for item in admin_view.captions)


def test_open_search_reference_project_updates_recency() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService([record])
    reference = {
        "selection_kind": "project_record",
        "selection_data": {"workspace_id": "maw-demo"},
        "object_id": "maw-demo",
        "object_type": "Project",
    }

    app._open_search_reference(st, service, reference)

    assert service.opened_records == ["maw-demo"]
    assert service.saved_records == []
    assert st.session_state["atlas_active_page"] == "Overview"


def test_sync_workspace_navigation_state_resolves_projects_library_secondary() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Pinned Projects",
            "atlas_context_selection": {"kind": "project", "data": {}},
        }
    )

    app._sync_workspace_navigation_state(st, record=None)

    assert st.session_state["atlas_active_primary_workspace"] == "Projects"
    assert st.session_state["atlas_active_workspace_mode"] == "library"
    assert st.session_state["atlas_active_secondary_section"] == "pinned_projects"


def test_sync_workspace_navigation_state_derives_knowledge_entity_branch() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Knowledge",
            "atlas_context_selection": {
                "kind": "vendor",
                "data": {"vendor": "ADI", "vendor_id": "ADI"},
            },
        }
    )

    app._sync_workspace_navigation_state(st, record=None)

    assert st.session_state["atlas_active_primary_workspace"] == "Knowledge"
    assert st.session_state["atlas_active_secondary_section"] == "vendors"
    assert st.session_state["atlas_active_tertiary_action"] == "browse"


def test_reports_navigation_contract_routes_project_summary_to_dedicated_page() -> None:
    contract = app._workspace_navigation_contract("Projects", "active")
    reports_section = next(
        item for item in contract if item["secondary_key"] == "reports"
    )
    project_summary = next(
        item
        for item in reports_section["supported_tertiary_actions"]
        if item["tertiary_key"] == "project_summary"
    )

    assert project_summary["route"] == "Project Summary"


def test_workspace_state_snapshot_includes_navigation_state() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Overview",
            "atlas_navigation_collapsed": False,
            "atlas_layout_mode": "Desktop",
            "atlas_context_selection": {"kind": "project", "data": {}},
            "atlas_notebook_entries": [],
            "atlas_review_flags": {},
            "atlas_price_list_library": {},
            "atlas_product_resolution_overrides": {},
            "atlas_product_resolution_filters": [],
            "atlas_recently_viewed_objects": [],
            "atlas_pinned_objects": [],
            "atlas_recent_search_queries": [],
            "atlas_recent_opened_results": [],
            "atlas_active_primary_workspace": "Projects",
            "atlas_active_workspace_mode": "active",
            "atlas_active_secondary_section": "overview",
            "atlas_active_tertiary_action": "summary",
            "atlas_selected_entity_type": "drawing",
            "atlas_selected_entity_id": "AV-601",
            "atlas_selected_project_object_type": "drawing",
            "atlas_selected_project_object_id": "AV-601",
            "atlas_selected_knowledge_entity_type": "",
            "atlas_selected_knowledge_entity_id": "",
            "atlas_return_context": {"source_route": "BOM Review"},
            "atlas_navigation_history": [{"source_route": "BOM Review"}],
            "atlas_originating_workspace": "Projects",
            "atlas_originating_route": "BOM Review",
            "atlas_tenant_scope": "local",
        }
    )

    snapshot = app._workspace_state_snapshot(st)

    navigation = dict(snapshot.get("navigation_state") or {})
    assert navigation["primary"] == "Projects"
    assert navigation["mode"] == "active"
    assert navigation["secondary"] == "overview"
    assert navigation["tertiary"] == "summary"
    assert navigation["selected_entity_type"] == "drawing"
    assert navigation["selected_entity_id"] == "AV-601"
    workspace_context = dict(snapshot.get("workspace_context_state") or {})
    assert workspace_context["selected_project_object_type"] == "drawing"
    assert workspace_context["selected_project_object_id"] == "AV-601"
    assert workspace_context["return_context"]["source_route"] == "BOM Review"
    assert workspace_context["originating_route"] == "BOM Review"
    assert workspace_context["tenant_scope"] == "local"


def test_restore_workspace_state_restores_navigation_state() -> None:
    class _RestoreService:
        def load_workspace_state(self, _workspace_id: str) -> dict[str, Any]:
            return {
                "last_open_page": "Overview",
                "filters": {},
                "search_state": {},
                "window_preferences": {},
                "navigation_state": {
                    "primary": "Projects",
                    "mode": "active",
                    "secondary": "project_details",
                    "tertiary": "drawings",
                    "selected_entity_type": "drawing",
                    "selected_entity_id": "AV-601",
                },
                "workspace_context_state": {
                    "selected_project_object_type": "drawing",
                    "selected_project_object_id": "AV-601",
                    "selected_knowledge_entity_type": "vendor",
                    "selected_knowledge_entity_id": "ADI",
                    "return_context": {"source_route": "Estimate"},
                    "navigation_history": [{"source_route": "Estimate"}],
                    "originating_workspace": "Projects",
                    "originating_route": "Estimate",
                    "tenant_scope": "local",
                },
            }

    st = _FakeStreamlit(session_state={})
    record = _project_record("maw-demo", "MAW")

    app._restore_workspace_state(st, _RestoreService(), record)

    assert st.session_state["atlas_active_primary_workspace"] == "Projects"
    assert st.session_state["atlas_active_workspace_mode"] == "active"
    assert st.session_state["atlas_active_secondary_section"] == "project_details"
    assert st.session_state["atlas_active_tertiary_action"] == "drawings"
    assert st.session_state["atlas_selected_entity_type"] == "drawing"
    assert st.session_state["atlas_selected_entity_id"] == "AV-601"
    assert st.session_state["atlas_selected_project_object_type"] == "drawing"
    assert st.session_state["atlas_selected_knowledge_entity_type"] == "vendor"
    assert st.session_state["atlas_return_context"]["source_route"] == "Estimate"
    assert st.session_state["atlas_tenant_scope"] == "local"


def test_query_page_can_override_restored_workspace_page() -> None:
    class _RestoreService:
        def load_workspace_state(self, _workspace_id: str) -> dict[str, Any]:
            return {
                "last_open_page": "Mission Control",
                "filters": {},
                "search_state": {},
                "window_preferences": {},
            }

    st = _FakeStreamlit(session_state={})
    st.query_params = {"atlas_page": "Overview"}
    record = _project_record("maw-demo", "MAW")

    app._restore_workspace_state(st, _RestoreService(), record)
    app._sync_active_page_from_query_params(st)

    assert st.session_state["atlas_active_page"] == "Overview"


def test_blank_root_defaults_to_mission_control() -> None:
    st = _FakeStreamlit(session_state={"atlas_active_page": "Overview"})
    st.query_params = {}

    app._sync_active_page_from_query_params(st, default_to_home=True)

    assert st.session_state["atlas_active_page"] == "Mission Control"


def test_restore_workspace_state_safely_ignores_malformed_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RestoreService:
        def load_workspace_state(self, _workspace_id: str) -> dict[str, Any]:
            raise ValueError("bad state")

    st = _HomeContractStreamlit()
    app._init_session_state(st)
    record = _project_record("maw-demo", "MAW")

    monkeypatch.setattr(
        app,
        "_log_application_error",
        lambda *args, **kwargs: "ERR-RESTORE",
    )

    app._restore_workspace_state_safely(st, _RestoreService(), record)

    assert st.session_state["atlas_active_page"] == "Mission Control"
    assert st.session_state["atlas_loaded_workspace_state_for"] == "maw-demo"
    assert st.session_state["atlas_bootstrap_notice"] == {
        "message": "Saved workspace state was ignored because it could not be restored.",
        "error_id": "ERR-RESTORE",
    }


def test_open_project_record_updates_recency() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService([record])

    app._open_project_record(st, record, service)

    assert service.opened_records == ["maw-demo"]
    assert service.saved_records == []
    assert st.session_state["atlas_active_page"] == "Overview"


def test_project_open_pages_use_lightweight_context_by_default() -> None:
    assert app._project_page_requires_full_context("Overview") is False
    assert app._project_page_requires_full_context("Processing") is False
    assert app._project_page_requires_full_context("Documents") is False
    assert app._project_page_requires_full_context("BOM Review") is True


def test_lightweight_project_context_uses_bootstrap_without_full_review() -> None:
    record = _project_record("maw-demo", "MAW")

    class _BootstrapService(_FakeWorkspaceService):
        def load_workspace_bootstrap(self, _workspace_id: str) -> Any:
            return SimpleNamespace(
                document_counts={"drawings": 2, "specifications": 1},
                processing_counts={"queued": 3, "failed": 1},
                total_document_count=3,
                diagnostics=[],
                to_dict=lambda: {
                    "document_counts": {"drawings": 2, "specifications": 1},
                    "processing_counts": {"queued": 3, "failed": 1},
                    "total_document_count": 3,
                    "active_processing_count": 3,
                    "diagnostics": [],
                },
            )

    context = app._load_lightweight_context_for_record(
        _BootstrapService([record]),
        record,
    )

    assert context["hydration_state"]["mode"] == "lightweight"
    assert "review" not in context
    assert context["import_summary"]["total_files"] == 3
    assert context["import_summary"]["processing_counts"] == {"queued": 3, "failed": 1}


def test_main_bootstrap_failure_renders_recoverable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BootstrapFailureStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {}
            self.query_params: dict[str, Any] = {}
            self.markdowns: list[str] = []
            self.errors: list[str] = []
            self.button_calls: list[dict[str, Any]] = []
            self.rerun_called = False

        def set_page_config(self, **_kwargs: Any) -> None:
            return None

        def markdown(self, text: str, **_kwargs: Any) -> None:
            self.markdowns.append(text)

        def error(self, text: str) -> None:
            self.errors.append(text)

        def columns(self, count: int | list[Any], **_kwargs: Any) -> list[Any]:
            size = len(count) if isinstance(count, list) else count
            return [self for _ in range(size)]

        def button(self, label: str, **kwargs: Any) -> bool:
            self.button_calls.append({"label": label, **kwargs})
            return False

        def rerun(self) -> None:
            self.rerun_called = True

    st = _BootstrapFailureStreamlit()

    monkeypatch.setattr(app, "_load_streamlit", lambda: st)
    monkeypatch.setattr(
        app,
        "_inject_styles",
        lambda _st: (_ for _ in ()).throw(RuntimeError("style boom")),
    )
    monkeypatch.setattr(
        app, "_log_application_error", lambda *args, **kwargs: "ERR-BOOT"
    )

    app.main()

    assert "## Atlas startup could not be completed" in st.markdowns
    assert st.errors == ["Unexpected application error. Reference Error ID: ERR-BOOT"]


def test_overview_primary_actions_use_stable_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _HomeContractStreamlit()
    record = _project_record("maw-demo", "MAW")

    monkeypatch.setattr(app, "_render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        app, "_build_project_analysis_summary", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(app, "_scope_risk_findings", lambda *args, **kwargs: [])
    monkeypatch.setattr(app, "_timeline_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(app, "_review_step_status_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        app,
        "_next_review_action",
        lambda *args, **kwargs: {
            "step": "Review Documents",
            "detail": "Open Documents and run project analysis.",
            "page": "Documents",
        },
    )
    monkeypatch.setattr(app, "_files_by_folder", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        app, "_project_operations_health_conditions", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        app, "_project_operations_current_work", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        app, "_project_operations_timeline_rows", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        app, "_project_operations_context_rows", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(app, "_render_section_title", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        app, "_responsive_control_columns", lambda _st, _spec: _st.columns(4)
    )
    monkeypatch.setattr(
        app, "_render_project_section_safely", lambda *args, **kwargs: None
    )

    app._render_overview_page(st, record, None)

    keys = {call.get("key") for call in st.button_calls}
    assert "atlas_project_ops_open_next_step" in keys
    assert "atlas_project_ops_open_estimate" in keys
    assert "atlas_project_ops_view_drawings" in keys


def test_recent_search_queries_are_deduplicated() -> None:
    st = _FakeStreamlit(session_state={"atlas_recent_search_queries": ["AV-601"]})

    app._record_recent_search_query(st, "av-601")
    app._record_recent_search_query(st, "QSC")

    assert st.session_state["atlas_recent_search_queries"][0] == "QSC"
    assert len(st.session_state["atlas_recent_search_queries"]) == 2


def test_working_set_add_remove_and_move() -> None:
    st = _FakeStreamlit(session_state={"atlas_pinned_objects": []})
    first = {
        "object_id": "A",
        "object_type": "Equipment",
        "display_name": "A",
    }
    second = {
        "object_id": "B",
        "object_type": "Equipment",
        "display_name": "B",
    }

    app._toggle_pin_reference(st, first, should_pin=True)
    app._toggle_pin_reference(st, second, should_pin=True)
    app._move_working_set_item(
        st,
        object_id="A",
        object_type="Equipment",
        direction=-1,
    )

    assert st.session_state["atlas_pinned_objects"][0]["object_id"] == "A"

    app._toggle_pin_reference(st, first, should_pin=False)
    assert all(
        item["object_id"] != "A" for item in st.session_state["atlas_pinned_objects"]
    )


def test_workspace_snapshot_persists_working_set_and_search_history() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Overview",
            "atlas_context_selection": {"kind": "project", "data": {}},
            "atlas_file_search": "",
            "atlas_equipment_search": "",
            "atlas_search_type_filters": [],
            "atlas_relationship_search_enabled": False,
            "atlas_global_search_query": "sony",
            "atlas_global_search_index": 0,
            "atlas_layout_mode": "Desktop",
            "atlas_navigation_collapsed": False,
            "atlas_notebook_entries": [],
            "atlas_review_flags": {},
            "atlas_recently_viewed_objects": [],
            "atlas_pinned_objects": [{"object_id": "EQ-1", "object_type": "Equipment"}],
            "atlas_recent_search_queries": ["sony"],
            "atlas_recent_opened_results": [
                {"object_id": "EQ-1", "object_type": "Equipment"}
            ],
        }
    )

    snapshot = app._workspace_state_snapshot(st)

    assert snapshot["pinned_objects"][0]["object_id"] == "EQ-1"
    assert snapshot["recent_search_queries"] == ["sony"]
    assert snapshot["recent_opened_results"][0]["object_id"] == "EQ-1"


def test_global_search_widget_key_uses_generation_token() -> None:
    st = _FakeStreamlit(session_state={"atlas_global_search_input_generation": 2})

    key = app._global_search_widget_key(st)

    assert key == "atlas_global_search_input_2"


def test_render_global_search_control_uses_separate_input_key() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_global_search_query"] = "AV-601"

    app._render_global_search_control(st, st)

    text_input_call = st.text_inputs[0]
    widget_key = text_input_call["key"]
    assert widget_key == "atlas_global_search_input_0"
    assert st.session_state[widget_key] == "AV-601"
    assert widget_key != "atlas_global_search_query"


def test_clear_global_search_state_clears_query_and_rotates_input_key() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_global_search_query": "AV-601",
            "atlas_global_search_input_generation": 0,
            "atlas_global_search_input_0": "AV-601",
        }
    )

    app._clear_global_search_state(st)

    assert st.session_state["atlas_global_search_query"] == ""
    assert st.session_state["atlas_global_search_input_generation"] == 1
    assert st.session_state["atlas_global_search_input_0"] == "AV-601"


def test_clear_global_search_state_does_not_mutate_legacy_widget_key() -> None:
    class _GuardedSessionState(dict[str, Any]):
        def __setitem__(self, key: str, value: Any) -> None:
            if key == "atlas_global_search":
                raise AssertionError("legacy widget key mutation is not allowed")
            super().__setitem__(key, value)

    st = _FakeStreamlit(
        session_state=_GuardedSessionState(
            {
                "atlas_global_search_query": "AV-601",
                "atlas_global_search_input_generation": 0,
            }
        )
    )

    app._clear_global_search_state(st)

    assert st.session_state["atlas_global_search_query"] == ""


def test_clear_search_button_preserves_route_and_project_context() -> None:
    st = _HomeContractStreamlit(pressed={"Clear Search"})
    st.session_state.update(
        {
            "atlas_active_page": "Knowledge",
            "atlas_active_workspace_id": "workspace-1",
            "atlas_global_search_query": "AV-601",
            "atlas_global_search_input_generation": 0,
        }
    )

    app._render_global_search_results(
        st,
        _FakeWorkspaceService([]),
        filtered=[],
        grouped_refs={},
        query="AV-601",
    )

    assert st.session_state["atlas_global_search_query"] == ""
    assert st.session_state["atlas_global_search_input_generation"] == 1
    assert st.session_state["atlas_active_page"] == "Knowledge"
    assert st.session_state["atlas_active_workspace_id"] == "workspace-1"
    assert st.rerun_called is True


def test_clear_search_is_idempotent() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_global_search_query": "AV-601",
            "atlas_global_search_input_generation": 0,
        }
    )

    app._clear_global_search_state(st)
    app._clear_global_search_state(st)

    assert st.session_state["atlas_global_search_query"] == ""
    assert st.session_state["atlas_global_search_input_generation"] == 2


def test_active_global_search_query_uses_submitted_state_not_widget_input() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_global_search_query": "AV-601",
            "atlas_global_search_input_0": "...",
        }
    )

    query = app._active_global_search_query(st)

    assert query == "AV-601"


def test_open_search_result_clears_search_before_navigation() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_global_search_query": "AV-601",
            "atlas_global_search_input_generation": 0,
        }
    )
    service = _FakeWorkspaceService([])
    captured: dict[str, Any] = {}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        app,
        "_open_search_reference",
        lambda _st, _service, reference: captured.update({"reference": reference}),
    )
    try:
        app._open_search_result(
            st,
            service,
            {
                "object_type": "Project",
                "object_id": "BID-2026-0001",
                "display_name": "Sample",
            },
        )
    finally:
        monkeypatch.undo()

    assert st.session_state["atlas_global_search_query"] == ""
    assert st.session_state["atlas_global_search_input_generation"] == 1
    assert captured["reference"]["object_id"] == "BID-2026-0001"


def test_search_input_is_empty_after_clear_and_rerender() -> None:
    st = _HomeContractStreamlit()
    st.session_state["atlas_global_search_query"] = "AV-601"

    app._clear_global_search_state(st)
    app._render_global_search_control(st, st)

    widget_key = st.text_inputs[0]["key"]
    assert widget_key == "atlas_global_search_input_1"
    assert st.session_state[widget_key] == ""


def test_project_record_identifier_and_secondary_labels() -> None:
    reference = app._build_object_reference(
        kind="project_record",
        data={
            "workspace_id": "legacy-workspace-id",
            "atlas_bid_id": "BID-2026-0012",
            "project_name": "Campus AV Refresh",
            "customer": "City Schools",
            "client_project_number": "CS-4421",
            "internal_project_number": "INT-0902",
            "status": "In Progress",
        },
        project_id="legacy-workspace-id",
        route="Overview",
    )

    assert reference["object_id"] == "BID-2026-0012"
    assert reference["secondary_label"] == (
        "City Schools | Client #CS-4421 | Internal #INT-0902"
    )


def test_project_identifier_match_fields_rank_for_client_and_internal_numbers() -> None:
    reference = {
        "object_id": "BID-2026-0012",
        "display_name": "Campus AV Refresh",
        "object_type": "Project",
        "secondary_label": "City Schools | Client #CS-4421 | Internal #INT-0902",
        "scope": "application",
        "match_fields": [
            "BID-2026-0012",
            "legacy-workspace-id",
            "Campus AV Refresh",
            "City Schools",
            "CS-4421",
            "INT-0902",
        ],
        "selection_kind": "project_record",
        "selection_data": {},
    }

    client_filtered = app._filter_search_results(
        [reference],
        query="CS-4421",
        selected_types=[],
        project_open=False,
    )
    internal_filtered = app._filter_search_results(
        [reference],
        query="INT-0902",
        selected_types=[],
        project_open=False,
    )

    assert len(client_filtered) == 1
    assert len(internal_filtered) == 1


def test_master_product_secondary_label_accepts_float_confidence() -> None:
    label = app._object_secondary_label(
        "master_product",
        {
            "lifecycle_status": "active",
            "vendor": "DIRECT",
            "confidence": 0.91,
        },
    )

    assert "active" in label
    assert "DIRECT" in label
    assert "confidence 0.91" in label


def test_overall_confidence_text_handles_dict_and_float_values() -> None:
    assert app._overall_confidence_text({"overall_confidence": 0.88}) == "0.88"
    assert app._overall_confidence_text(0.91) == "0.91"


def test_breadcrumb_generates_object_specific_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _project_record("maw-demo", "MAW")
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(
            session_state={
                "atlas_context_selection": {
                    "kind": "drawing",
                    "data": {"drawing_number": "AV-601", "title": "Audio Plan"},
                }
            }
        ),
    )

    breadcrumb = app._breadcrumb(record, "Drawings")

    assert breadcrumb == "Atlas / Projects / MAW / Drawings / AV-601"


def test_filter_returns_empty_for_non_matching_query() -> None:
    filtered = app._filter_search_results(
        [
            _reference(
                object_id="EQ-100",
                display_name="Sony FW-65BZ40L",
                object_type="Equipment",
                scope="project",
            )
        ],
        query="no-match-term",
        selected_types=[],
        project_open=True,
    )

    assert filtered == []


def test_open_project_result_activates_workspace() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={})
    st.query_params = {}
    service = _FakeWorkspaceService(records=[record])
    reference = {
        "selection_kind": "project_record",
        "selection_data": {"workspace_id": "maw-demo"},
        "object_id": "maw-demo",
        "object_type": "Project",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_workspace_id"] == "maw-demo"
    assert st.session_state["atlas_active_page"] == "Overview"
    assert st.query_params["atlas_workspace_id"] == "maw-demo"
    assert st.query_params["atlas_page"] == "Overview"


def test_project_context_header_builder_returns_expected_fields() -> None:
    record = _project_record("maw-demo", "MAW")

    header = app._build_project_context_header(
        record,
        customer="Music Academy of the West",
        confidence="84%",
        recommended_next_action="Review Documents",
    )

    assert header.project_name == "MAW"
    assert header.customer == "Music Academy of the West"
    assert header.current_phase == "Intake"
    assert header.project_manager == "Client"
    assert header.current_revision == "Current"
    assert header.current_health == "Needs Attention"
    assert header.recommended_next_action == "Review Documents"


def test_project_context_header_renders_operational_summary_without_metadata() -> None:
    st = _HomeContractStreamlit()
    header = app.ProjectContextHeader(
        project_name="MAW",
        customer="Music Academy",
        current_phase="Estimating",
        overall_status="Needs Review",
        project_manager="Alex",
        last_activity="Jul 20, 2026 10:00",
        current_revision="Rev 2",
        current_health="Normal",
        recommended_next_action="Review Estimate",
    )

    app._render_project_context_header(st, header)

    rendered = "\n".join(st.markdowns)
    assert "Project Manager: Alex" in rendered
    assert "Current Revision: Rev 2" in rendered
    assert "Normal" in rendered
    assert "repository" not in rendered.lower()
    assert "manifest" not in rendered.lower()


def test_project_operations_center_renders_operational_sections() -> None:
    st = _HomeContractStreamlit()
    record = _project_record("project-a", "Project A")

    app._render_overview_page(st, record, context=None)

    rendered_text = "\n".join([*st.subheaders, *st.markdowns, *st.captions])
    assert "Project Operations Center" in rendered_text
    assert "Next Step" in rendered_text
    assert "Project Health" in rendered_text
    assert "Current Work" in rendered_text
    assert "Project Timeline" in rendered_text
    assert "Project Context" in rendered_text
    assert "Project Inspector" in rendered_text
    assert (
        "Tabs: Overview, Activity, Relationships, Documents, History, Administration"
        in rendered_text
    )
    assert "repository" not in rendered_text.lower()
    assert "manifest" not in rendered_text.lower()


def test_project_section_failure_is_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _HomeContractStreamlit()
    st.session_state.update(
        {
            "atlas_active_page": "Overview",
            "atlas_transactions_workspace": {"tenant_id": "tenant-a"},
        }
    )
    record = _project_record("maw-demo", "MAW")
    captured: dict[str, Any] = {}

    def _fake_log(*_args: Any, **kwargs: Any) -> str:
        captured.update(kwargs)
        return "ERR-SECTION"

    monkeypatch.setattr(app, "_log_application_error", _fake_log)

    app._render_project_section_safely(
        st,
        record=record,
        context={"hydration_state": {"mode": "lightweight"}},
        section="Project Inspector",
        renderer=lambda: (_ for _ in ()).throw(RuntimeError("missing relation")),
    )

    assert "This section could not be loaded." in st.warnings
    assert any("ERR-SECTION" in item for item in st.captions)
    assert captured["related_object_id"] == "maw-demo"
    assert captured["hydration_mode"] == "lightweight"
    assert captured["section"] == "Project Inspector"
    assert st.expander_calls == [{"label": "Technical detail", "expanded": False}]


def test_application_error_reference_is_written_when_primary_logging_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    st = _HomeContractStreamlit()
    log_path = tmp_path / "application_errors.jsonl"

    def _raise_logging_error(_st: Any) -> Any:
        _ = _st
        raise RuntimeError("tenant manager unavailable")

    monkeypatch.setattr(app, "_tenant_manager_workspace_service", _raise_logging_error)
    monkeypatch.setattr(app, "_application_error_diagnostic_log_path", lambda: log_path)

    error_id = app._log_application_error(
        st,
        summary="Unexpected application error",
        exception=ValueError("bad lightweight payload"),
        severity="critical",
        tenant_id="tenant-a",
        organization_id="org-a",
        user_id="atlas-ui",
        workspace="Projects",
        route="Overview",
        related_object_id="BID-2026-0002",
        related_object_type="project",
        request_or_session_ref="BID-2026-0002",
        active_page="Overview",
        hydration_mode="lightweight",
        section="Project Timeline",
        recent_action="render",
    )

    rows = [app.json.loads(line) for line in log_path.read_text().splitlines()]
    assert error_id.startswith("ERR-")
    assert rows[0]["error_id"] == error_id
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[0]["project_id"] == "BID-2026-0002"
    assert rows[0]["active_page"] == "Overview"
    assert rows[0]["hydration_mode"] == "lightweight"
    assert rows[0]["section"] == "Project Timeline"
    assert rows[0]["exception_type"] == "ValueError"
    assert "ValueError: bad lightweight payload" in rows[0]["stack_trace"]
    assert rows[0]["logging_exception_type"] == "RuntimeError"


def test_project_health_clear_state_is_actionable() -> None:
    conditions = app._project_operations_health_conditions(
        {
            "documents_requiring_ocr": 0,
            "missing_specifications": 0,
        },
        [
            {
                "step": "Review Documents",
                "status": "complete",
                "page": "Documents",
                "detail": "Documents reviewed.",
            }
        ],
    )
    st = _HomeContractStreamlit()

    app._render_project_health_card(st, conditions)

    assert conditions == []
    assert "Project is progressing normally." in st.captions


def test_project_current_work_queue_uses_supported_review_steps() -> None:
    rows = app._project_operations_current_work(
        [
            {
                "step": "Review Documents",
                "status": "complete",
                "page": "Documents",
            },
            {
                "step": "Review Estimate Coverage",
                "status": "needs review",
                "page": "Estimate",
            },
        ],
        {"step": "Review Estimate Coverage"},
    )

    assert rows == [
        {
            "Title": "Review Estimate Coverage",
            "Owner": "Project Team",
            "Age": "Needs Review",
            "Recommended Action": "Estimate",
            "Priority": "Primary",
        }
    ]


def test_project_timeline_groups_meaningful_completed_events() -> None:
    rows = app._project_operations_timeline_rows(
        [
            {
                "event": "Review Executed",
                "status": "Completed",
                "timestamp": "2026-07-20T10:00:00+00:00",
                "details": "A",
            },
            {
                "event": "Review Executed",
                "status": "Completed",
                "timestamp": "2026-07-21T10:00:00+00:00",
                "details": "B",
            },
            {
                "event": "Estimator Brief Generated",
                "status": "Pending",
                "timestamp": "2026-07-21T11:00:00+00:00",
                "details": "n/a",
            },
        ]
    )

    assert rows == [
        {
            "Event": "Review Executed",
            "Count": 2,
            "Latest": "2026-07-21T10:00:00+00:00",
            "Details": "B",
        }
    ]


def test_project_navigation_groups_are_operations_oriented() -> None:
    assert app._navigation_section_group("Projects", "active", "overview") == "Overview"
    assert (
        app._navigation_section_group("Projects", "active", "engineering_review")
        == "Engineering"
    )
    assert (
        app._navigation_section_group("Projects", "active", "estimate") == "Commercial"
    )
    assert (
        app._navigation_section_group("Projects", "active", "documents") == "Documents"
    )
    assert app._navigation_section_group("Projects", "active", "reports") == "Reporting"
    assert (
        app._navigation_section_group("Projects", "active", "project_settings")
        == "Settings"
    )


def test_project_navigation_contains_disabled_future_lifecycle_group() -> None:
    group_names = [name for name, _ in app.PROJECT_NAV_GROUPS]

    assert "Future Lifecycle (Disabled)" in group_names
    assert set(app.DISABLED_LIFECYCLE_PAGES) <= {
        page for _, entries in app.PROJECT_NAV_GROUPS for _, page in entries
    }


def test_build_workspace_service_runtime_path_exposes_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_root = tmp_path / "AtlasProjects"
    monkeypatch.setattr(app, "ensure_runtime_workspace_root", lambda: runtime_root)

    service = app._build_workspace_service()

    assert isinstance(service, ProjectWorkspaceService)
    assert callable(getattr(service, "preview_next_bid_id", None))
    assert callable(getattr(service.manager, "preview_next_bid_id", None))
    assert callable(
        getattr(service.manager.project_repository, "peek_next_bid_id", None)
    )


def test_create_project_primary_action_label_changes_with_selection() -> None:
    assert app._create_project_primary_action_label(False) == "Create Bid Workspace"
    assert app._create_project_primary_action_label(True) == "Create Bid Workspace"


def test_create_project_required_fields_only_name_and_client() -> None:
    assert app._create_project_missing_required_fields("", "") == [
        "Project Name",
        "Owner / Client",
    ]
    assert app._create_project_missing_required_fields("Project", "") == [
        "Owner / Client"
    ]
    assert app._create_project_missing_required_fields("Project", "Client") == []


def test_create_project_post_create_route_depends_on_upload_selection() -> None:
    assert app._create_project_post_create_page(False) == "Documents"
    assert app._create_project_post_create_page(True) == "Documents"


def test_create_project_effective_uploads_supports_individual_removal() -> None:
    uploads = [
        _FakeUploadedFile(name="a.pdf", data=b"a"),
        _FakeUploadedFile(name="b.pdf", data=b"b"),
        _FakeUploadedFile(name="c.pdf", data=b"c"),
    ]

    kept = app._create_project_effective_uploads(uploads, ["2. b.pdf"])
    kept_names = [item.name for item in kept]
    assert kept_names == ["a.pdf", "c.pdf"]


def test_create_project_clear_upload_state_resets_session_keys() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_create_project_uploads": ["x"],
            "atlas_create_project_remove_selection": ["1. x"],
            "atlas_create_project_uploads_token": 1,
        }
    )

    app._reset_create_project_upload_state(st)
    assert st.session_state["atlas_create_project_uploads"] == ["x"]
    assert st.session_state["atlas_create_project_uploads_token"] == 2
    assert "atlas_create_project_remove_selection" not in st.session_state


def test_create_project_upload_inspection_rows_include_required_columns() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="bid.pdf", data=b"pdf-bytes"),
        _FakeUploadedFile(name="bad.exe", data=b"x"),
    ]

    inspected = app._create_project_upload_inspection(service, uploads)

    assert inspected["total_selected_count"] == 2
    assert inspected["total_selected_size"] > 0
    assert inspected["accepted_count"] >= 1
    assert inspected["rejected_count"] >= 1
    assert inspected["has_any_selected_invalid"] is True
    assert inspected["all_selected_invalid"] is False
    assert inspected["accepted_payload"]
    assert inspected["rows"]

    row = inspected["rows"][0]
    assert set(
        [
            "Name",
            "Source Type",
            "File Size",
            "ZIP Source",
            "Duplicate",
            "Validation",
            "Messages",
        ]
    ) <= set(row.keys())


def test_create_project_upload_inspection_keeps_invalid_diagnostics_visible() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="empty.pdf", data=b""),
        _FakeUploadedFile(name="ok.jpg", data=b"img"),
    ]

    inspected = app._create_project_upload_inspection(service, uploads)

    rejected_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "rejected"
    ]
    accepted_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "accepted"
    ]
    assert rejected_rows
    assert accepted_rows
    assert any("empty file" in str(row.get("Messages", "")) for row in rejected_rows)


def test_create_project_upload_inspection_all_invalid_selection_is_blockable() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bad.exe", data=b"x")]
    inspected = app._create_project_upload_inspection(service, uploads)

    assert inspected["has_selected_files"] is True
    assert inspected["all_selected_invalid"] is True
    assert inspected["accepted_count"] == 0


def test_create_project_upload_inspection_zip_warnings_have_zip_indicator() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bad.zip", data=b"not-a-real-zip")]
    inspected = app._create_project_upload_inspection(service, uploads)

    warning_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "warning"
    ]
    assert warning_rows
    assert all(row.get("ZIP Source") == "Yes" for row in warning_rows)


def test_create_project_upload_inspection_marks_duplicate_state() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="dup.pdf", data=b"same"),
        _FakeUploadedFile(name="dup.pdf", data=b"same2"),
    ]
    inspected = app._create_project_upload_inspection(service, uploads)

    assert any(row.get("Duplicate") == "Yes" for row in inspected["rows"])


def test_preview_next_bid_id_helper_returns_value_when_supported() -> None:
    service = _CreatePageWorkspaceServiceWithPreview()

    assert app._preview_next_bid_id(service) == "BID-2099-0009"


def test_preview_next_bid_id_helper_returns_none_when_unsupported() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()

    assert app._preview_next_bid_id(service) is None


def test_create_project_page_renders_when_preview_unavailable() -> None:
    st = _CreatePageStreamlit(submit=False)
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert not st.errors
    assert any(
        "assigned when the workspace is created" in message for message in st.infos
    )


def test_create_project_page_owner_lookup_populates_existing_options() -> None:
    st = _CreatePageStreamlit(
        submit=False,
        client_name="Lookup Owner",
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.search_queries == ["Lookup Owner"]
    options = st.select_options.get("Select existing Owner / Client") or []
    assert "Lookup Owner LLC · org-lookup-owner" in options


def test_create_project_page_creation_still_works_without_preview() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create Without Preview",
        client_name="Client",
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_workspace_id"] == "BID-2099-0001"
    assert "atlas_header_project_selector" not in st.session_state
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.session_state["atlas_project_action_feedback"]["level"] == "success"
    assert st.rerun_called is True


def test_create_project_page_existing_owner_selection_uses_canonical_owner_and_links() -> (
    None
):
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create With Existing Owner",
        client_name="Lookup Owner",
        select_values={
            "Select existing Owner / Client": "Lookup Owner LLC · org-lookup-owner"
        },
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    created = service.created[-1]
    assert created.project.client == "Lookup Owner LLC"
    assert service.link_calls
    assert service.link_calls[-1]["organization_id"] == "org-lookup-owner"
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.rerun_called is True


def test_build_record_from_context_preserves_existing_identity_fields() -> None:
    existing = ProjectWorkspaceRecord(
        workspace_id="BID-2026-0005",
        project=Project(
            project_id="BID-2026-0005",
            name="X03 Validation Main",
            client="Northstar Owner Group",
            atlas_bid_id="BID-2026-0005",
            client_project_number="CLIENT-123",
            internal_project_number="INT-789",
            status=ProjectStatus.INTAKE,
        ),
        metadata={
            "project_name": "X03 Validation Main",
            "owner": "Northstar Owner Group",
            "atlas_bid_id": "BID-2026-0005",
            "client_project_number": "CLIENT-123",
            "internal_project_number": "INT-789",
        },
    )
    context = {
        "sample_project_id": "documents",
        "sample_project_name": "documents",
        "intake_snapshot": SimpleNamespace(
            metadata={
                "project_name": "documents",
                "atlas_bid_id": "documents",
                "owner": "documents",
                "client_project_number": "documents",
                "internal_project_number": "documents",
            }
        ),
    }

    rebuilt = app._build_record_from_context(context, existing_record=existing)

    assert rebuilt.project.project_id == "BID-2026-0005"
    assert rebuilt.project.name == "X03 Validation Main"
    assert rebuilt.project.atlas_bid_id == "BID-2026-0005"
    assert rebuilt.project.client_project_number == "CLIENT-123"
    assert rebuilt.project.internal_project_number == "INT-789"
    assert rebuilt.metadata["project_name"] == "X03 Validation Main"
    assert rebuilt.metadata["owner"] == "Northstar Owner Group"
    assert rebuilt.metadata["owner_client"] == "Northstar Owner Group"
    assert rebuilt.metadata["atlas_bid_id"] == "BID-2026-0005"


def test_build_record_from_context_rejects_generic_folder_identity() -> None:
    context = {
        "sample_project_id": "documents",
        "sample_project_name": "documents",
        "intake_snapshot": SimpleNamespace(
            metadata={
                "project_name": "documents",
                "atlas_bid_id": "documents",
                "owner": "documents",
            }
        ),
    }

    rebuilt = app._build_record_from_context(context)

    assert rebuilt.project.project_id == "atlas-project"
    assert rebuilt.project.name == "atlas-project"
    assert rebuilt.project.atlas_bid_id == "atlas-project"
    assert rebuilt.project.client == "atlas-project"


def test_create_project_upload_inspection_helper_uses_service_public_api() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bid.pdf", data=b"pdf")]

    _ = app._create_project_upload_inspection(service, uploads)

    assert service.inspect_calls == 1


def test_create_project_page_graceful_when_inspection_unavailable() -> None:
    st = _CreatePageStreamlit(
        submit=False,
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert not st.errors
    assert not st.warnings


def test_create_project_page_create_and_upload_with_valid_file() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create With File",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceWithPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert not service.import_calls
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.rerun_called is True


def test_create_project_page_inspection_failure_with_files_blocks_submission() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Blocked",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_page"] == "Documents"


def test_create_project_page_clear_files_allows_project_only_create() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Project Only",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
        button_presses={"Clear File Selection": True},
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_page"] == "Documents"


def test_create_project_page_project_only_create_succeeds_without_files() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Project Only",
        client_name="Client",
        uploaded_files=[],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert not service.import_calls
    assert st.session_state["atlas_active_page"] == "Documents"


def test_documents_pending_uploads_append_across_selections() -> None:
    st = _FakeStreamlit(session_state={})
    first = [_FakeUploadedFile(name="a.pdf", data=b"a")]
    second = [_FakeUploadedFile(name="b.csv", data=b"b")]

    first_added, _ = app._append_pending_upload_selection(st, "BID-1", first)
    second_added, _ = app._append_pending_upload_selection(st, "BID-1", second)
    pending = app._pending_upload_state(st, "BID-1")

    assert first_added == 1
    assert second_added == 1
    assert [item["name"] for item in pending] == ["a.pdf", "b.csv"]


def test_documents_pending_uploads_stream_file_without_getvalue() -> None:
    st = _FakeStreamlit(session_state={})
    uploaded = _StreamingUploadedFile(name="streamed.pdf", data=b"abcdef")

    added, duplicates = app._append_pending_upload_selection(
        st, "BID-STREAM", [uploaded]
    )
    pending = app._pending_upload_state(st, "BID-STREAM")

    assert added == 1
    assert duplicates == 0
    assert uploaded.read_calls > 1
    assert uploaded.getvalue_calls == 0
    assert pending[0]["size"] == 6
    assert Path(str(pending[0]["data_path"])).exists()

    app._clear_pending_uploads(st, "BID-STREAM")


def test_documents_pending_uploads_deduplicate_same_identity() -> None:
    st = _FakeStreamlit(session_state={})
    selection = [_FakeUploadedFile(name="a.pdf", data=b"same")]

    app._append_pending_upload_selection(st, "BID-1", selection)
    # Simulate a new event signature with identical file data.
    st.session_state["atlas_documents_pending_selection_signature"] = {}
    added, duplicates = app._append_pending_upload_selection(st, "BID-1", selection)

    pending = app._pending_upload_state(st, "BID-1")
    assert added == 0
    assert duplicates == 1
    assert len(pending) == 1


def test_documents_pending_uploads_remove_and_clear() -> None:
    st = _FakeStreamlit(session_state={})
    app._append_pending_upload_selection(
        st,
        "BID-1",
        [
            _FakeUploadedFile(name="a.pdf", data=b"a"),
            _FakeUploadedFile(name="b.pdf", data=b"b"),
        ],
    )
    pending = app._pending_upload_state(st, "BID-1")
    removed = app._remove_pending_uploads(
        st,
        "BID-1",
        [str(pending[0]["identity_key"])],
    )
    assert removed == 1
    assert len(app._pending_upload_state(st, "BID-1")) == 1

    app._clear_pending_uploads(st, "BID-1")
    assert app._pending_upload_state(st, "BID-1") == []


def test_documents_upload_panel_displays_batch_total_from_policy() -> None:
    record = _project_record("BID-1", "Batch Display")
    st = _HomeContractStreamlit()
    st.session_state["atlas_documents_pending_uploads"] = {
        "BID-1": [
            {
                "identity_key": "a",
                "name": "drawings.pdf",
                "size": 200 * 1024 * 1024,
            },
            {
                "identity_key": "b",
                "name": "specs.docx",
                "size": 25 * 1024 * 1024,
            },
        ]
    }
    service = _AsyncUploadWorkspaceService()

    app._render_upload_panel(st, service, record)  # type: ignore[arg-type]

    assert any("2 files selected · 225 MiB of 1 GiB" in item for item in st.captions)


def test_pending_identity_keys_to_remove_after_upload_keeps_rejected_pending() -> None:
    pending = [
        {
            "identity_key": app._pending_upload_identity("good.pdf", b"good"),
            "name": "good.pdf",
            "data": b"good",
            "size": 4,
        },
        {
            "identity_key": app._pending_upload_identity("bad.exe", b"bad"),
            "name": "bad.exe",
            "data": b"bad",
            "size": 3,
        },
    ]
    inspection = SimpleNamespace(
        accepted_files=[SimpleNamespace(name="good.pdf", data=b"good")],
        diagnostics=[
            {"name": "good.pdf", "accepted": True, "zip_source": False},
            {
                "name": "bad.exe",
                "accepted": False,
                "zip_source": False,
                "messages": ["unsupported extension"],
            },
        ],
    )

    removable = app._pending_identity_keys_to_remove_after_upload(pending, inspection)

    assert removable == {pending[0]["identity_key"]}


def test_pending_identity_keys_to_remove_after_upload_handles_zip_partitions() -> None:
    zip_pending = {
        "identity_key": app._pending_upload_identity("bundle.zip", b"zip-data"),
        "name": "bundle.zip",
        "data": b"zip-data",
        "size": 8,
    }

    all_accepted = SimpleNamespace(
        accepted_files=[],
        diagnostics=[
            {
                "name": "bundle.zip/nested/one.pdf",
                "accepted": True,
                "zip_source": True,
            },
            {
                "name": "bundle.zip/nested/two.csv",
                "accepted": True,
                "zip_source": True,
            },
        ],
    )
    mixed = SimpleNamespace(
        accepted_files=[],
        diagnostics=[
            {
                "name": "bundle.zip/nested/one.pdf",
                "accepted": True,
                "zip_source": True,
            },
            {
                "name": "bundle.zip/nested/two.exe",
                "accepted": False,
                "zip_source": True,
            },
        ],
    )

    removable_all = app._pending_identity_keys_to_remove_after_upload(
        [zip_pending],
        all_accepted,
    )
    removable_mixed = app._pending_identity_keys_to_remove_after_upload(
        [zip_pending],
        mixed,
    )

    assert removable_all == {zip_pending["identity_key"]}
    assert removable_mixed == set()


def test_documents_upload_picker_reset_increments_token_and_clears_signature() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_documents_upload_picker_tokens": {"BID-1": 2, "BID-2": 1},
            "atlas_documents_pending_selection_signature": {
                "BID-1": "abc",
                "BID-2": "xyz",
            },
        }
    )

    app._reset_documents_upload_picker(st, "BID-1")

    assert st.session_state["atlas_documents_upload_picker_tokens"]["BID-1"] == 3
    assert st.session_state["atlas_documents_upload_picker_tokens"]["BID-2"] == 1
    assert (
        "BID-1" not in st.session_state["atlas_documents_pending_selection_signature"]
    )
    assert (
        st.session_state["atlas_documents_pending_selection_signature"]["BID-2"]
        == "xyz"
    )


class _AsyncUploadWorkspaceService:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []

    def inspect_uploaded_documents(self, _uploaded_files: Any) -> None:
        raise AssertionError("upload rendering must not inspect files synchronously")

    def run_document_import_job(self, **_kwargs: Any) -> None:
        raise AssertionError("upload callback must not run document processing")

    def list_background_jobs(self, _workspace_id: str) -> list[dict[str, Any]]:
        return []

    def enqueue_document_processing(self, **kwargs: Any) -> dict[str, Any]:
        self.enqueued.append(dict(kwargs))
        return {
            "job_id": f"job-{len(self.enqueued)}",
            "project_id": kwargs["workspace_id"],
            "status": "queued",
        }


def test_documents_upload_pending_files_enqueues_without_expensive_processing() -> None:
    record = _project_record("BID-1", "Async Upload")
    upload_key = (
        "atlas_documents_upload_pending_BID-1_atlas_documents_upload_picker_BID-1_0"
    )
    pending = {
        "identity_key": app._pending_upload_identity("async.pdf", b"%PDF"),
        "name": "async.pdf",
        "data": b"%PDF",
        "size": 4,
    }
    st = _HomeContractStreamlit(pressed={upload_key})
    st.session_state["atlas_documents_pending_uploads"] = {"BID-1": [pending]}
    service = _AsyncUploadWorkspaceService()

    app._render_upload_panel(st, service, record)  # type: ignore[arg-type]

    assert len(service.enqueued) == 1
    assert service.enqueued[0]["uploaded_files"] == [("async.pdf", b"%PDF")]
    assert st.session_state["atlas_active_page"] == "Processing"
    assert app._pending_upload_state(st, "BID-1") == []
    assert st.rerun_called is True


class _ProcessingFragmentStreamlit(_HomeContractStreamlit):
    def __init__(self) -> None:
        super().__init__()
        self.fragment_intervals: list[str | None] = []

    def fragment(self, *, run_every: str | None = None) -> Any:
        self.fragment_intervals.append(run_every)

        def _decorator(func: Any) -> Any:
            return func

        return _decorator


class _ProcessingStatusWorkspaceService:
    def __init__(self, jobs: list[dict[str, Any]]) -> None:
        self.jobs = list(jobs)
        self.status_calls = 0
        self.bootstrap_calls = 0

    def load_workspace_bootstrap(self, _workspace_id: str) -> None:
        self.bootstrap_calls += 1
        raise AssertionError("processing status refresh must not reload bootstrap")

    def list_document_processing_statuses(
        self, _workspace_id: str, **_kwargs: Any
    ) -> list[dict[str, Any]]:
        self.status_calls += 1
        return list(self.jobs)


def _processing_job(
    *,
    job_id: str = "job-1",
    status: str = "running",
    step: str = "start",
    percent: int = 20,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "project_id": "BID-1",
        "request": {
            "category": "document_import",
            "input_payload": {"uploaded_files": [{"name": "active.pdf"}]},
        },
        "status": status,
        "progress": {
            "percent": percent,
            "message": "Inspecting",
            "step": step,
            "updated_at": "2026-07-20T10:00:00+00:00",
        },
        "diagnostics": [],
        "created_at": "2026-07-20T09:59:00+00:00",
        "started_at": "2026-07-20T10:00:00+00:00",
        "completed_at": None,
        "retry_available": False,
    }


def test_processing_status_fragment_refreshes_without_navigation_rerender() -> None:
    record = _project_record("BID-1", "Processing")
    st = _ProcessingFragmentStreamlit()
    st.session_state.update(
        {
            "atlas_active_workspace_id": "BID-1",
            "atlas_active_page": "Documents",
            "atlas_active_secondary_section": "documents",
            "atlas_documents_pending_uploads": {
                "BID-1": [{"identity_key": "file|1", "name": "pending.pdf"}]
            },
        }
    )
    service = _ProcessingStatusWorkspaceService([_processing_job()])

    app._render_processing_status_region(
        st,
        service,  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
        compact=True,
    )

    assert st.fragment_intervals == ["3s"]
    assert service.status_calls == 2
    assert service.bootstrap_calls == 0
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.session_state["atlas_active_secondary_section"] == "documents"
    assert (
        st.session_state["atlas_documents_pending_uploads"]["BID-1"][0]["name"]
        == "pending.pdf"
    )
    assert st.rerun_called is False


def test_processing_polling_stops_when_no_jobs_are_active() -> None:
    record = _project_record("BID-1", "Processing")
    st = _ProcessingFragmentStreamlit()
    service = _ProcessingStatusWorkspaceService(
        [_processing_job(status="succeeded", step="complete", percent=100)]
    )

    app._render_processing_status_region(
        st,
        service,  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
        compact=True,
    )

    assert st.fragment_intervals == [None]
    assert st.session_state["atlas_processing_auto_refresh"]["BID-1"] is False
    assert "Automatic processing refresh is stopped." in st.captions


def test_processing_status_uses_stale_cache_when_status_query_is_locked() -> None:
    record = _project_record("BID-1", "Processing")
    st = _HomeContractStreamlit()
    service = _ProcessingStatusWorkspaceService([_processing_job()])
    first = app._processing_status_snapshot(
        st,
        service,  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
    )

    class _LockedProcessingStatusService(_ProcessingStatusWorkspaceService):
        def list_document_processing_statuses(
            self, _workspace_id: str, **_kwargs: Any
        ) -> list[dict[str, Any]]:
            raise TimeoutError("jobs file is locked")

    stale = app._processing_status_snapshot(
        st,
        _LockedProcessingStatusService([]),  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
    )

    assert first["stale"] is False
    assert stale["stale"] is True
    assert stale["message"] == "Processing status is updating."
    assert stale["jobs"] == first["jobs"]
    assert stale["changed"] is False


def test_unchanged_processing_status_does_not_mark_snapshot_changed() -> None:
    record = _project_record("BID-1", "Processing")
    st = _HomeContractStreamlit()
    service = _ProcessingStatusWorkspaceService([_processing_job()])

    first = app._processing_status_snapshot(
        st,
        service,  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
    )
    second = app._processing_status_snapshot(
        st,
        service,  # type: ignore[arg-type]
        record,
        tenant_id="local",
        organization_id="atlas",
    )

    assert first["changed"] is True
    assert second["changed"] is False


def test_documents_upload_pending_files_queues_only_accepted_files() -> None:
    record = _project_record("BID-1", "Partial Batch Upload")
    upload_key = (
        "atlas_documents_upload_pending_BID-1_atlas_documents_upload_picker_BID-1_0"
    )
    valid = {
        "identity_key": app._pending_upload_identity("valid.pdf", b"%PDF"),
        "name": "valid.pdf",
        "data": b"%PDF",
        "size": 4,
    }
    invalid = {
        "identity_key": app._pending_upload_identity("invalid.json", b"{}"),
        "name": "invalid.json",
        "data": b"{}",
        "size": 2,
    }
    st = _HomeContractStreamlit(pressed={upload_key})
    st.session_state["atlas_documents_pending_uploads"] = {"BID-1": [valid, invalid]}
    service = _AsyncUploadWorkspaceService()

    app._render_upload_panel(st, service, record)  # type: ignore[arg-type]

    assert len(service.enqueued) == 1
    assert service.enqueued[0]["uploaded_files"] == [("valid.pdf", b"%PDF")]
    remaining = app._pending_upload_state(st, "BID-1")
    assert [item["name"] for item in remaining] == ["invalid.json"]
