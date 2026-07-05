"""Application service for plan review requests."""

from __future__ import annotations

from atlas_core.contracts import PlanReviewRequest, PlanReviewResponse
from atlas_core.services import DocumentClassifierService, PlanReviewWorkflowService


class PlanReviewApplicationService:
    def __init__(
        self,
        workflow_service: PlanReviewWorkflowService | None = None,
        document_classifier_service: DocumentClassifierService | None = None,
    ) -> None:
        self.workflow_service = workflow_service or PlanReviewWorkflowService()
        self.document_classifier_service = (
            document_classifier_service or DocumentClassifierService()
        )

    def run(self, request: PlanReviewRequest) -> PlanReviewResponse:
        if request.raw_pages:
            self.document_classifier_service.classify(request.raw_pages)

        result = self.workflow_service.run_review(
            review_id=request.review_id,
            project_id=request.project_id,
            name=request.name,
            raw_sheets=request.raw_sheets,
            raw_sections=request.raw_sections,
            raw_device_schedules=request.raw_device_schedules,
        )

        return PlanReviewResponse(result=result)
