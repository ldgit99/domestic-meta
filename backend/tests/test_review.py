from app.models.domain import CandidateRecord, EligibilityDecision, ExtractionResult, FullTextArtifact
from app.repositories.memory import MemoryStore
from app.services.effect_size import EffectSizeService
from app.services.quality import QualityAssessmentService
from app.services.review import ReviewService


def _review_service(store: MemoryStore) -> ReviewService:
    return ReviewService(store, EffectSizeService(), QualityAssessmentService())


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

    queue = _review_service(store).build_review_queue("s1")

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

    queue = _review_service(store).build_review_queue("s1")

    assert len(queue) == 1
    assert queue[0]["review_priority"] == "high"
    assert "full_text_decision_missing" in queue[0]["review_reasons"]


def test_review_queue_flags_ocr_required_before_extraction() -> None:
    store = MemoryStore()
    candidate = CandidateRecord(
        id="c2",
        search_request_id="s1",
        source="kci",
        source_record_id="k2",
        title="Effects of tutoring on mathematics achievement",
        authors=["Park"],
        year=2025,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["tutoring"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="full_text_needs_ocr",
        canonical_record_id="c2",
    )
    title_decision = EligibilityDecision(
        id="d2",
        candidate_record_id="c2",
        stage="title_abstract",
        decision="include",
        reason_code=None,
        reason_text=None,
        confidence="medium",
        reviewed_by="agent",
        created_at="now",
    )
    artifact = FullTextArtifact(
        id="a2",
        candidate_record_id="c2",
        file_name="scan.pdf",
        source_url=None,
        mime_type="application/pdf",
        text_content="",
        text_extraction_status="ocr_required",
        created_at="now",
        stored_path="scan.pdf",
    )
    store.candidates[candidate.id] = candidate
    store.decisions[title_decision.id] = title_decision
    store.full_text_artifacts[candidate.id] = artifact

    queue = _review_service(store).build_review_queue("s1")

    assert len(queue) == 1
    assert queue[0]["full_text_status"] == "ocr_required"
    assert queue[0]["review_priority"] == "high"
    assert "ocr_required" in queue[0]["review_reasons"]
    assert "extraction_not_run" not in queue[0]["review_reasons"]


def test_review_queue_uses_quality_assessment_for_priority_and_reasons() -> None:
    store = MemoryStore()
    candidate = CandidateRecord(
        id="c3",
        search_request_id="s1",
        source="kci",
        source_record_id="k3",
        title="Effects of mentoring on achievement",
        authors=["Cho"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["mentoring"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="extracted",
        canonical_record_id="c3",
    )
    title_decision = EligibilityDecision(
        id="d3",
        candidate_record_id="c3",
        stage="title_abstract",
        decision="include",
        reason_code=None,
        reason_text=None,
        confidence="medium",
        reviewed_by="agent",
        created_at="2026-03-20T10:00:00",
    )
    full_text_decision = EligibilityDecision(
        id="d4",
        candidate_record_id="c3",
        stage="full_text",
        decision="include",
        reason_code=None,
        reason_text=None,
        confidence="medium",
        reviewed_by="agent",
        created_at="2026-03-20T10:05:00",
    )
    artifact = FullTextArtifact(
        id="a3",
        candidate_record_id="c3",
        file_name="study.txt",
        source_url=None,
        mime_type="text/plain",
        text_content="full text available",
        text_extraction_status="available",
        created_at="now",
        stored_path=None,
    )
    extraction = ExtractionResult(
        id="e3",
        candidate_id="c3",
        status="fallback_heuristic",
        message="heuristic",
        fields_json={
            "study_design": "group_comparison",
            "participants": {
                "sample_size_total": "100",
                "groups": [
                    {"name": "intervention", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                    {"name": "control", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
                ],
            },
            "intervention_or_predictor": "mentoring",
            "comparison": "control",
            "outcomes": ["achievement"],
            "timepoints": ["posttest"],
            "statistics": [],
            "effect_size_inputs": {
                "is_meta_analytic_ready": True,
                "effect_type_candidates": ["hedges_g"],
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
                "correlation_coefficient": "",
                "missing_inputs": [],
            },
            "evidence_spans": [
                {"field": "participants.sample_size_total", "evidence_text": "N=100", "location": "heuristic"}
            ],
            "confidence": "low",
        },
        model_name=None,
        raw_response={},
        created_at="now",
    )
    store.candidates[candidate.id] = candidate
    store.decisions[title_decision.id] = title_decision
    store.decisions[full_text_decision.id] = full_text_decision
    store.full_text_artifacts[candidate.id] = artifact
    store.extraction_results[candidate.id] = extraction

    detail = _review_service(store).get_candidate_detail(candidate.id)
    queue = _review_service(store).build_review_queue("s1")

    assert detail is not None
    assert detail["quality_assessment"]["score"] == "low"
    assert "sample_size_mismatch" in detail["review_reasons"]
    assert "quality_assessment_low" in detail["review_reasons"]
    assert len(queue) == 1
    assert queue[0]["review_priority"] == "high"
    assert "sample_size_mismatch" in queue[0]["review_reasons"]