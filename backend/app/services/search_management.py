from app.core.constants import (
    DECISION_EXCLUDE,
    DECISION_INCLUDE,
    DECISION_MAYBE,
    DECISION_REVIEW,
    FULL_TEXT_STAGE,
    TITLE_ABSTRACT_STAGE,
)
from app.models.domain import EligibilityDecision, FullTextArtifact
from app.schemas.candidate import DecisionCreate, FullTextArtifactCreate
from app.services.prisma import PrismaService


class SearchManagementService:
    def __init__(self, store, prisma_service: PrismaService) -> None:
        self.store = store
        self.prisma_service = prisma_service

    def create_manual_decision(
        self,
        candidate_id: str,
        payload: DecisionCreate,
    ) -> EligibilityDecision | None:
        decision = self.store.create_decision(candidate_id, payload)
        if decision is None:
            return None

        candidate = self.store.get_candidate(candidate_id)
        assert candidate is not None
        candidate.status = self._status_for_decision(
            current_status=candidate.status,
            stage=payload.stage,
            decision=payload.decision,
        )
        self.store.update_candidate(candidate)
        self.refresh_prisma(candidate.search_request_id)
        self.store.log_event(
            candidate.search_request_id,
            "manual_decision_recorded",
            f"Recorded {payload.stage} decision '{payload.decision}' for candidate '{candidate.title}'.",
            stage=payload.stage,
            status="completed",
            candidate_id=candidate_id,
            metadata_json={
                "decision": payload.decision,
                "reason_code": payload.reason_code,
                "reviewed_by": payload.reviewed_by,
                "candidate_status": candidate.status,
            },
        )
        return decision

    def register_full_text(
        self,
        candidate_id: str,
        payload: FullTextArtifactCreate,
    ) -> FullTextArtifact | None:
        artifact = self.store.create_full_text_artifact(candidate_id, payload)
        if artifact is None:
            return None

        candidate = self.store.get_candidate(candidate_id)
        assert candidate is not None
        candidate.status = self._status_for_artifact(artifact.text_extraction_status)
        self.store.update_candidate(candidate)
        self.refresh_prisma(candidate.search_request_id)
        self.store.log_event(
            candidate.search_request_id,
            "full_text_registered",
            f"Registered full text '{artifact.file_name}' with text status '{artifact.text_extraction_status}'.",
            stage="full_text",
            status="completed" if artifact.text_extraction_status == "available" else "attention",
            candidate_id=candidate_id,
            metadata_json={
                "file_name": artifact.file_name,
                "mime_type": artifact.mime_type,
                "text_extraction_status": artifact.text_extraction_status,
                "stored_path": artifact.stored_path,
                "candidate_status": candidate.status,
            },
        )
        return artifact

    def refresh_prisma(self, search_request_id: str) -> None:
        counts = self.store.get_prisma_counts(search_request_id)
        if counts is None:
            return

        candidates = self.store.list_candidates(search_request_id)
        decisions = self.store.list_decisions_for_search(search_request_id)
        duplicates_removed = len(
            [item for item in candidates if item.canonical_record_id and item.canonical_record_id != item.id]
        )

        updated = self.prisma_service.recalculate(
            counts=counts,
            collected_count=len(candidates),
            duplicates_removed=duplicates_removed,
            decisions=decisions,
        )
        self.store.update_prisma_counts(updated)

    def _status_for_decision(self, current_status: str, stage: str, decision: str) -> str:
        if stage == TITLE_ABSTRACT_STAGE:
            if decision == DECISION_INCLUDE:
                return "selected_for_full_text"
            if decision == DECISION_EXCLUDE:
                return "excluded_title_abstract"
            if decision in {DECISION_MAYBE, DECISION_REVIEW}:
                return "needs_review_title_abstract"
            return "screened_title_abstract"

        if stage == FULL_TEXT_STAGE:
            if decision == DECISION_INCLUDE:
                return "included_full_text"
            if decision == DECISION_EXCLUDE:
                return "excluded_full_text"
            if decision in {DECISION_MAYBE, DECISION_REVIEW}:
                return "needs_review_full_text"
            return "reviewed_full_text"

        return current_status

    def _status_for_artifact(self, text_extraction_status: str) -> str:
        if text_extraction_status == "available":
            return "full_text_available"
        if text_extraction_status in {"ocr_required", "ocr_failed", "no_text_extracted"}:
            return "full_text_needs_ocr"
        return "full_text_requested"
