from app.models.domain import CandidateRecord, EligibilityDecision
from app.repositories.memory import MemoryStore
from app.services.effect_size import EffectSizeService
from app.services.review import ReviewService


def test_review_queue_flags_included_candidate_without_full_text() -> None:
    store = MemoryStore()
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="kci",
        source_record_id="k1",
        title="협동학습이 학업성취도에 미치는 효과",
        authors=["홍길동"],
        year=2024,
        journal_or_school="교육연구",
        abstract="",
        keywords=["협동학습"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="screened_title_abstract",
        canonical_record_id="c1",
    )
    decision = EligibilityDecision(
        id="d1",
        candidate_record_id="c1",
        stage="title_abstract",
        decision="include",
        reason_code=None,
        reason_text=None,
        confidence="medium",
        reviewed_by="agent",
        created_at="now",
    )
    store.candidates[candidate.id] = candidate
    store.decisions[decision.id] = decision

    queue = ReviewService(store, EffectSizeService()).build_review_queue("s1")

    assert len(queue) == 1
    assert queue[0]["review_priority"] == "high"
    assert "full_text_needed" in queue[0]["review_reasons"]
