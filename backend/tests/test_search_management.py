from app.models.domain import CandidateRecord
from app.repositories.memory import MemoryStore
from app.schemas.candidate import DecisionCreate
from app.schemas.search import SearchRequestCreate
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


def test_search_management_updates_candidate_status_and_prisma_by_stage() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    candidate = CandidateRecord(
        id="c1",
        search_request_id=created.id,
        source="kci",
        source_record_id="k1",
        title="Feedback intervention effects",
        authors=["Park"],
        year=2024,
        journal_or_school="Education Studies",
        abstract="",
        keywords=["feedback"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="collected",
        canonical_record_id="c1",
    )
    store.add_candidates([candidate])
    service = SearchManagementService(store=store, prisma_service=PrismaService())

    title_decision = service.create_manual_decision(
        candidate.id,
        DecisionCreate(stage="title_abstract", decision="include", reviewed_by="dashboard"),
    )
    full_text_decision = service.create_manual_decision(
        candidate.id,
        DecisionCreate(stage="full_text", decision="include", reviewed_by="dashboard"),
    )

    updated_candidate = store.get_candidate(candidate.id)
    counts = store.get_prisma_counts(created.id)

    assert title_decision is not None
    assert full_text_decision is not None
    assert updated_candidate is not None
    assert updated_candidate.status == "included_full_text"
    assert counts is not None
    assert counts.records_screened == 1
    assert counts.reports_sought_for_retrieval == 1
    assert counts.reports_assessed_for_eligibility == 1
    assert counts.studies_included_in_review == 1
