from app.models.domain import CandidateRecord, ExtractionResult
from app.repositories.memory import MemoryStore
from app.schemas.candidate import ExtractionResultUpdate
from app.schemas.search import SearchRequestCreate
from app.services.extraction_management import ExtractionManagementService
from app.services.quality import QualityAssessmentService


def _candidate(search_request_id: str) -> CandidateRecord:
    return CandidateRecord(
        id="c1",
        search_request_id=search_request_id,
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
        status="included_full_text",
        canonical_record_id="c1",
    )


def test_manual_extraction_save_updates_quality_candidate_status_and_events() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="self-directed learning"))
    candidate = _candidate(created.id)
    store.add_candidates([candidate])
    service = ExtractionManagementService(store=store, quality_service=QualityAssessmentService())

    result = service.save_manual_result(
        candidate.id,
        ExtractionResultUpdate(
            reviewed_by="dashboard",
            notes="Corrected group means from the full text table.",
            fields_json={
                "study_design": "group_comparison",
                "participants": {
                    "sample_size_total": "120",
                    "groups": [
                        {"name": "intervention", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                        {"name": "control", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
                    ],
                },
                "intervention_or_predictor": "self-directed learning",
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
                    {"field": "participants.sample_size_total", "evidence_text": "N=120", "location": "manual"},
                    {"field": "participants.groups.intervention", "evidence_text": "n=60 mean=82.4 sd=10.1", "location": "manual"},
                    {"field": "participants.groups.control", "evidence_text": "n=60 mean=75.2 sd=11.3", "location": "manual"},
                    {"field": "outcomes.0", "evidence_text": "achievement", "location": "manual"},
                ],
                "confidence": "high",
            },
        ),
    )

    assert result is not None
    assert result.status == "manual_override"
    assert result.model_name == "manual_override"
    assert result.fields_json["quality_assessment"]["score"] == "high"

    updated_candidate = store.get_candidate(candidate.id)
    assert updated_candidate is not None
    assert updated_candidate.status == "extracted"

    saved = store.get_extraction_result(candidate.id)
    assert saved is not None
    assert saved.raw_response["manual_override"]["reviewed_by"] == "dashboard"
    assert saved.raw_response["manual_override"]["notes"] == "Corrected group means from the full text table."

    events = store.list_events(created.id)
    assert events
    assert events[0].event_type == "manual_extraction_saved"
    assert events[0].metadata_json["quality_score"] == "high"


def test_manual_extraction_save_can_reuse_existing_fields_when_payload_is_empty() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    candidate = _candidate(created.id)
    store.add_candidates([candidate])
    store.save_extraction_result(
        ExtractionResult(
            id="e1",
            candidate_id=candidate.id,
            status="fallback_heuristic",
            message="heuristic",
            fields_json={
                "study_design": "group_comparison",
                "participants": {
                    "sample_size_total": "80",
                    "groups": [
                        {"name": "intervention", "n": "40", "mean": "80.0", "sd": "10.0", "timepoint": "post"},
                        {"name": "control", "n": "40", "mean": "75.0", "sd": "9.0", "timepoint": "post"},
                    ],
                },
                "intervention_or_predictor": "feedback",
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
                    {"field": "participants.sample_size_total", "evidence_text": "N=80", "location": "heuristic"},
                    {"field": "participants.groups.intervention", "evidence_text": "n=40 mean=80.0 sd=10.0", "location": "heuristic"},
                    {"field": "participants.groups.control", "evidence_text": "n=40 mean=75.0 sd=9.0", "location": "heuristic"},
                    {"field": "outcomes.0", "evidence_text": "achievement", "location": "heuristic"},
                ],
                "confidence": "medium",
            },
            model_name=None,
            raw_response={"source": "heuristic"},
            created_at="now",
        )
    )

    service = ExtractionManagementService(store=store, quality_service=QualityAssessmentService())
    result = service.save_manual_result(
        candidate.id,
        ExtractionResultUpdate(
            reviewed_by="dashboard",
            notes="Kept extracted values but approved them manually.",
            fields_json={},
        ),
    )

    assert result is not None
    assert result.fields_json["study_design"] == "group_comparison"
    assert result.fields_json["quality_assessment"]["score"] in {"high", "medium"}
    assert result.raw_response["source"] == "heuristic"
    assert result.raw_response["manual_override"]["previous_status"] == "fallback_heuristic"