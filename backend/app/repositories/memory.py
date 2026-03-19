from app.core.constants import TITLE_ABSTRACT_STAGE
from app.core.utils import generate_id, now_iso
from app.models.domain import CandidateRecord, EligibilityDecision, PrismaCounts, SearchRequest
from app.schemas.candidate import DecisionCreate
from app.schemas.search import SearchRequestCreate


class MemoryStore:
    def __init__(self) -> None:
        self.search_requests: dict[str, SearchRequest] = {}
        self.candidates: dict[str, CandidateRecord] = {}
        self.decisions: dict[str, EligibilityDecision] = {}
        self.prisma_counts: dict[str, PrismaCounts] = {}

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
        self.decisions[item.id] = item
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
