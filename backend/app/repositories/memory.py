from app.core.constants import TITLE_ABSTRACT_STAGE
from app.core.utils import generate_id, now_iso
from app.models.domain import (
    CandidateRecord,
    EligibilityDecision,
    ExtractionResult,
    ExtractionRevision,
    FullTextArtifact,
    PipelineEvent,
    PrismaCounts,
    SearchRequest,
)
from app.schemas.candidate import DecisionCreate, FullTextArtifactCreate
from app.schemas.search import SearchRequestCreate


class MemoryStore:
    def __init__(self) -> None:
        self.search_requests: dict[str, SearchRequest] = {}
        self.candidates: dict[str, CandidateRecord] = {}
        self.decisions: dict[str, EligibilityDecision] = {}
        self.prisma_counts: dict[str, PrismaCounts] = {}
        self.pipeline_events: dict[str, PipelineEvent] = {}
        self.full_text_artifacts: dict[str, FullTextArtifact] = {}
        self.extraction_results: dict[str, ExtractionResult] = {}
        self.extraction_revisions: dict[str, ExtractionRevision] = {}

    def list_search_requests(self) -> list[SearchRequest]:
        return sorted(self.search_requests.values(), key=lambda item: item.created_at, reverse=True)

    def create_search_request(self, payload: SearchRequestCreate) -> SearchRequest:
        item = SearchRequest(
            id=generate_id("search"),
            query_text=payload.query_text,
            expanded_keywords=payload.expanded_keywords,
            year_from=payload.year_from,
            year_to=payload.year_to,
            include_theses=payload.include_theses,
            include_journal_articles=payload.include_journal_articles,
            inclusion_rules=payload.inclusion_rules,
            exclusion_rules=payload.exclusion_rules,
            status="created",
            created_at=now_iso(),
        )
        self.search_requests[item.id] = item
        self.prisma_counts[item.id] = PrismaCounts(
            id=generate_id("prisma"),
            search_request_id=item.id,
        )
        return item

    def reset_search_results(self, search_request_id: str) -> None:
        candidate_ids = {item.id for item in self.list_candidates(search_request_id)}
        for candidate_id in candidate_ids:
            self.candidates.pop(candidate_id, None)
            self.full_text_artifacts.pop(candidate_id, None)
            self.extraction_results.pop(candidate_id, None)
        self.decisions = {
            key: value
            for key, value in self.decisions.items()
            if value.candidate_record_id not in candidate_ids
        }
        self.extraction_revisions = {
            key: value
            for key, value in self.extraction_revisions.items()
            if value.candidate_id not in candidate_ids
        }
        existing = self.prisma_counts.get(search_request_id)
        prisma_id = existing.id if existing else generate_id("prisma")
        self.prisma_counts[search_request_id] = PrismaCounts(id=prisma_id, search_request_id=search_request_id)

    def get_search_request(self, search_request_id: str) -> SearchRequest | None:
        return self.search_requests.get(search_request_id)

    def update_search_request_status(self, search_request_id: str, status: str) -> None:
        self.search_requests[search_request_id].status = status

    def add_candidates(self, items: list[CandidateRecord]) -> None:
        for item in items:
            self.candidates[item.id] = item

    def list_candidates(self, search_request_id: str) -> list[CandidateRecord]:
        return [item for item in self.candidates.values() if item.search_request_id == search_request_id]

    def get_candidate(self, candidate_id: str) -> CandidateRecord | None:
        return self.candidates.get(candidate_id)

    def update_candidate(self, item: CandidateRecord) -> None:
        self.candidates[item.id] = item

    def save_decision(self, item: EligibilityDecision) -> EligibilityDecision:
        self.decisions[item.id] = item
        return item

    def create_decision(self, candidate_id: str, payload: DecisionCreate) -> EligibilityDecision | None:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            return None

        item = EligibilityDecision(
            id=generate_id("decision"),
            candidate_record_id=candidate_id,
            stage=payload.stage,
            decision=payload.decision,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            confidence=payload.confidence,
            reviewed_by=payload.reviewed_by,
            created_at=now_iso(),
        )
        self.save_decision(item)
        if payload.stage == TITLE_ABSTRACT_STAGE:
            candidate.status = "screened_title_abstract"
        return item

    def list_decisions_for_search(self, search_request_id: str) -> list[EligibilityDecision]:
        candidate_ids = {item.id for item in self.list_candidates(search_request_id)}
        return [item for item in self.decisions.values() if item.candidate_record_id in candidate_ids]

    def get_prisma_counts(self, search_request_id: str) -> PrismaCounts | None:
        return self.prisma_counts.get(search_request_id)

    def update_prisma_counts(self, item: PrismaCounts) -> None:
        self.prisma_counts[item.search_request_id] = item

    def log_event(
        self,
        search_request_id: str,
        event_type: str,
        message: str,
        *,
        stage: str | None = None,
        status: str = "info",
        candidate_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> PipelineEvent:
        item = PipelineEvent(
            id=generate_id("event"),
            search_request_id=search_request_id,
            event_type=event_type,
            status=status,
            message=message,
            stage=stage,
            candidate_id=candidate_id,
            metadata_json=metadata_json or {},
            created_at=now_iso(),
        )
        self.pipeline_events[item.id] = item
        return item

    def list_events(self, search_request_id: str) -> list[PipelineEvent]:
        items = [item for item in self.pipeline_events.values() if item.search_request_id == search_request_id]
        return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)

    def create_full_text_artifact(
        self,
        candidate_id: str,
        payload: FullTextArtifactCreate,
    ) -> FullTextArtifact | None:
        if self.get_candidate(candidate_id) is None:
            return None

        item = FullTextArtifact(
            id=generate_id("artifact"),
            candidate_record_id=candidate_id,
            file_name=payload.file_name,
            source_url=payload.source_url,
            mime_type=payload.mime_type,
            text_content=payload.text_content,
            text_extraction_status=payload.text_extraction_status
            or ("available" if payload.text_content.strip() else "pending"),
            created_at=now_iso(),
            stored_path=payload.stored_path,
        )
        self.full_text_artifacts[candidate_id] = item
        return item

    def get_full_text_artifact(self, candidate_id: str) -> FullTextArtifact | None:
        return self.full_text_artifacts.get(candidate_id)

    def save_extraction_result(self, item: ExtractionResult) -> ExtractionResult:
        if not item.id:
            item.id = generate_id("extract")
        if not item.created_at:
            item.created_at = now_iso()
        self.extraction_results[item.candidate_id] = item
        self._record_extraction_revision(item)
        return item

    def get_extraction_result(self, candidate_id: str) -> ExtractionResult | None:
        return self.extraction_results.get(candidate_id)

    def list_extraction_results_for_search(self, search_request_id: str) -> list[ExtractionResult]:
        candidate_ids = {item.id for item in self.list_candidates(search_request_id)}
        return [item for item in self.extraction_results.values() if item.candidate_id in candidate_ids]

    def list_extraction_revisions(self, candidate_id: str) -> list[ExtractionRevision]:
        items = [item for item in self.extraction_revisions.values() if item.candidate_id == candidate_id]
        return sorted(items, key=lambda item: (item.revision_index, item.created_at or "", item.id))

    def list_extraction_revisions_for_search(self, search_request_id: str) -> list[ExtractionRevision]:
        items = [
            item
            for item in self.extraction_revisions.values()
            if item.search_request_id == search_request_id
        ]
        return sorted(items, key=lambda item: (item.candidate_id, item.revision_index, item.created_at or "", item.id))

    def _record_extraction_revision(self, item: ExtractionResult) -> None:
        candidate = self.get_candidate(item.candidate_id)
        if candidate is None:
            return
        existing = self.list_extraction_revisions(item.candidate_id)
        revision = ExtractionRevision(
            id=generate_id("revision"),
            extraction_result_id=item.id,
            candidate_id=item.candidate_id,
            search_request_id=candidate.search_request_id,
            revision_index=len(existing) + 1,
            status=item.status,
            message=item.message,
            fields_json=item.fields_json,
            model_name=item.model_name,
            raw_response=item.raw_response,
            created_at=item.created_at or now_iso(),
        )
        self.extraction_revisions[revision.id] = revision
