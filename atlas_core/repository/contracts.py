"""Repository contracts for Atlas Project persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_core.contracts.commercial_spine_contracts import (
        CatalogItem,
        ChangeOrder,
        CustomerAccount,
        CustomerInvoice,
        Estimate,
        InventoryLocation,
        InventoryPosition,
        InventoryReservation,
        Opportunity,
        ProcurementNeed,
        Proposal,
        QuickBooksSyncReference,
        SalesOrder,
        VendorBill,
    )

JsonDict = dict[str, Any]


class ProjectRepository(ABC):
    """Persistence contract for project-level records and lifecycle actions."""

    @abstractmethod
    def create(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def save(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self, project_ref: str) -> tuple[JsonDict, JsonDict, JsonDict, str]:
        raise NotImplementedError

    @abstractmethod
    def list_projects(
        self,
        include_archived: bool = False,
    ) -> list[tuple[str, JsonDict, JsonDict, JsonDict, str]]:
        raise NotImplementedError

    @abstractmethod
    def rename(self, project_id: str, new_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def archive(self, project_id: str, archived: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, project_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def duplicate(
        self,
        project_id: str,
        new_project_id: str,
        new_name: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_pinned(self, project_id: str, pinned: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_reference(self, project_id: str, reference: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def project_location(self, project_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_manifest(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def refresh_manifest(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def export_bundle(self, project_id: str, out_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def import_bundle(self, bundle_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def health_check(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def allocate_bid_id(self, year: int | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def peek_next_bid_id(self, year: int | None = None) -> str:
        raise NotImplementedError


class WorkspaceRepository(ABC):
    """Persistence contract for workspace-view and UI state."""

    @abstractmethod
    def load_state(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def save_state(self, project_id: str, state: JsonDict) -> None:
        raise NotImplementedError


class DocumentRepository(ABC):
    """Persistence contract for project documents and import intake."""

    @abstractmethod
    def import_uploads(
        self,
        project_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> JsonDict:
        raise NotImplementedError

    def save_commercial_document(
        self,
        tenant_id: str,
        organization_id: str,
        payload: JsonDict,
    ) -> None:
        """Optional hook for commercial-document persistence using existing repositories."""
        raise NotImplementedError

    def load_commercial_document(
        self,
        tenant_id: str,
        organization_id: str,
        document_id: str,
    ) -> JsonDict | None:
        """Optional hook for loading a commercial-document payload by identity."""
        return None

    def list_commercial_documents(
        self,
        tenant_id: str,
        organization_id: str,
        document_type: str | None = None,
    ) -> list[JsonDict]:
        """Optional hook for listing commercial-document payloads by scope."""
        return []


class ReviewRepository(ABC):
    """Persistence contract for review result artifacts."""

    @abstractmethod
    def save_artifact(
        self, project_id: str, artifact_name: str, payload: JsonDict
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_artifact(self, project_id: str, artifact_name: str) -> JsonDict | None:
        raise NotImplementedError

    def save_transaction_document(self, project_id: str, payload: JsonDict) -> None:
        """Optional hook for persisted commercial transaction documents."""
        raise NotImplementedError

    def load_transaction_documents(self, project_id: str) -> list[JsonDict]:
        """Optional hook for loading persisted commercial transaction documents."""
        return []


class KnowledgeRepository(ABC):
    """Persistence contract for graph/knowledge artifacts."""

    @abstractmethod
    def save_knowledge_graph(self, project_id: str, payload: JsonDict) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_knowledge_graph(self, project_id: str) -> JsonDict | None:
        raise NotImplementedError

    @abstractmethod
    def save_engineering_intelligence(self, project_id: str, payload: JsonDict) -> None:
        raise NotImplementedError


class HistoryRepository(ABC):
    """Persistence contract for simple project timeline events."""

    @abstractmethod
    def append_event(self, project_id: str, event_type: str, payload: JsonDict) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, project_id: str, limit: int = 100) -> list[JsonDict]:
        raise NotImplementedError


class JobRepository(ABC):
    """Persistence contract for background jobs and immutable attempt history."""

    @abstractmethod
    def save_job(self, project_id: str, job_payload: JsonDict) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_job(self, project_id: str, job_id: str) -> JsonDict | None:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self, project_id: str, limit: int = 200) -> list[JsonDict]:
        raise NotImplementedError


class AttachmentRepository(ABC):
    """Persistence contract for unified tenant-scoped attachments."""

    @abstractmethod
    def save_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_payload: JsonDict,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
    ) -> JsonDict | None:
        raise NotImplementedError

    @abstractmethod
    def list_attachments(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[JsonDict]:
        raise NotImplementedError

    @abstractmethod
    def find_attachment_by_hash(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        file_hash: str,
        size_bytes: int,
    ) -> JsonDict | None:
        raise NotImplementedError

    @abstractmethod
    def write_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str,
        version_id: str,
        filename: str,
        data: bytes,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        storage_reference: str,
    ) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def save_link(
        self,
        tenant_id: str,
        organization_id: str,
        link_payload: JsonDict,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_links(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str | None = None,
        object_type: str | None = None,
        object_id: str | None = None,
        include_inactive: bool = False,
        limit: int = 5000,
    ) -> list[JsonDict]:
        raise NotImplementedError

    @abstractmethod
    def save_activity(
        self,
        tenant_id: str,
        organization_id: str,
        activity_payload: JsonDict,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_activity(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str | None = None,
        limit: int = 200,
    ) -> list[JsonDict]:
        raise NotImplementedError


class CommercialRepository(ABC):
    """Persistence contract for tenant-scoped commercial records."""

    @abstractmethod
    def save_customer_account(self, record: CustomerAccount) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_customer_account(self, customer_id: str) -> CustomerAccount | None:
        raise NotImplementedError

    @abstractmethod
    def list_customer_accounts(self) -> list[CustomerAccount]:
        raise NotImplementedError

    @abstractmethod
    def save_opportunity(self, record: Opportunity) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_opportunity(self, opportunity_id: str) -> Opportunity | None:
        raise NotImplementedError

    @abstractmethod
    def list_opportunities(self) -> list[Opportunity]:
        raise NotImplementedError

    @abstractmethod
    def save_proposal(self, record: Proposal) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_proposal(self, proposal_id: str) -> Proposal | None:
        raise NotImplementedError

    @abstractmethod
    def list_proposals(self) -> list[Proposal]:
        raise NotImplementedError

    @abstractmethod
    def save_estimate(self, record: Estimate) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_estimate(self, estimate_id: str) -> Estimate | None:
        raise NotImplementedError

    @abstractmethod
    def list_estimates(self) -> list[Estimate]:
        raise NotImplementedError

    @abstractmethod
    def save_sales_order(self, record: SalesOrder) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_sales_order(self, sales_order_id: str) -> SalesOrder | None:
        raise NotImplementedError

    @abstractmethod
    def list_sales_orders(self) -> list[SalesOrder]:
        raise NotImplementedError

    @abstractmethod
    def save_change_order(self, record: ChangeOrder) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_change_order(self, change_order_id: str) -> ChangeOrder | None:
        raise NotImplementedError

    @abstractmethod
    def list_change_orders(self) -> list[ChangeOrder]:
        raise NotImplementedError

    @abstractmethod
    def save_catalog_item(self, record: CatalogItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_catalog_item(self, catalog_item_id: str) -> CatalogItem | None:
        raise NotImplementedError

    @abstractmethod
    def list_catalog_items(self) -> list[CatalogItem]:
        raise NotImplementedError

    @abstractmethod
    def save_inventory_location(self, record: InventoryLocation) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_inventory_location(self, location_id: str) -> InventoryLocation | None:
        raise NotImplementedError

    @abstractmethod
    def list_inventory_locations(self) -> list[InventoryLocation]:
        raise NotImplementedError

    @abstractmethod
    def save_inventory_position(self, record: InventoryPosition) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_inventory_position(self, position_id: str) -> InventoryPosition | None:
        raise NotImplementedError

    @abstractmethod
    def list_inventory_positions(self) -> list[InventoryPosition]:
        raise NotImplementedError

    @abstractmethod
    def save_inventory_reservation(self, record: InventoryReservation) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_inventory_reservation(
        self, reservation_id: str
    ) -> InventoryReservation | None:
        raise NotImplementedError

    @abstractmethod
    def list_inventory_reservations(self) -> list[InventoryReservation]:
        raise NotImplementedError

    @abstractmethod
    def save_procurement_need(self, record: ProcurementNeed) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_procurement_need(self, procurement_need_id: str) -> ProcurementNeed | None:
        raise NotImplementedError

    @abstractmethod
    def list_procurement_needs(self) -> list[ProcurementNeed]:
        raise NotImplementedError

    @abstractmethod
    def save_customer_invoice(self, record: CustomerInvoice) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_customer_invoice(self, customer_invoice_id: str) -> CustomerInvoice | None:
        raise NotImplementedError

    @abstractmethod
    def list_customer_invoices(self) -> list[CustomerInvoice]:
        raise NotImplementedError

    @abstractmethod
    def save_vendor_bill(self, record: VendorBill) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_vendor_bill(self, vendor_bill_id: str) -> VendorBill | None:
        raise NotImplementedError

    @abstractmethod
    def list_vendor_bills(self) -> list[VendorBill]:
        raise NotImplementedError

    @abstractmethod
    def save_quickbooks_sync_reference(self, record: QuickBooksSyncReference) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_quickbooks_sync_reference(
        self, sync_reference_id: str
    ) -> QuickBooksSyncReference | None:
        raise NotImplementedError

    @abstractmethod
    def list_quickbooks_sync_references(self) -> list[QuickBooksSyncReference]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class RepositoryBundle:
    """Complete repository composition for a project runtime."""

    project_repository: ProjectRepository
    workspace_repository: WorkspaceRepository
    document_repository: DocumentRepository
    review_repository: ReviewRepository
    knowledge_repository: KnowledgeRepository
    history_repository: HistoryRepository
    job_repository: JobRepository
    attachment_repository: AttachmentRepository
    commercial_repository: CommercialRepository | None = None
    tenant_id: str | None = None
    tenant_root: Path | None = None

    def __post_init__(self) -> None:
        if self.tenant_id is not None:
            normalized_tenant_id = self.tenant_id.strip()
            object.__setattr__(self, "tenant_id", normalized_tenant_id or None)
        if self.tenant_root is not None and not isinstance(self.tenant_root, Path):
            object.__setattr__(self, "tenant_root", Path(self.tenant_root))
