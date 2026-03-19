from app.models.domain import CandidateRecord, EligibilityDecision, FullTextArtifact
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
        title="Effects of self-directed learning on achievement",
        authors=["Kim"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["self-directed learning"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="selected_for_full_text",
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


def test_review_queue_flags_missing_full_text_decision_after_artifact() -> None:
    store = MemoryStore()
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="riss",
        source_record_id="r1",
        title="Effects of formative feedback on learning outcomes",
        authors=["Lee"],
        year=2023,
        journal_or_school="Educational Review",
        abstract="",
        keywords=["feedback"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="full_text_available",
        canonical_record_id="c1",
    )
    title_decision = EligibilityDecision(
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
    artifact = FullTextArtifact(
        id="a1",
        candidate_record_id="c1",
        file_name="study.pdf",
        source_url=None,
        mime_type="application/pdf",
        text_content="Full text",
        text_extraction_status="available",
        created_at="now",
        stored_path=None,
    )
    store.candidates[candidate.id] = candidate
    store.decisions[title_decision.id] = title_decision
    store.full_text_artifacts[candidate.id] = artifact

    queue = ReviewService(store, EffectSizeService()).build_review_queue("s1")

    assert len(queue) == 1
    assert queue[0]["review_priority"] == "high"
    assert "full_text_decision_missing" in queue[0]["review_reasons"]
