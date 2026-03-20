from app.models.domain import CandidateRecord, ExtractionResult
from app.repositories.memory import MemoryStore
from app.schemas.candidate import ExtractionResultUpdate, ExtractionRevisionRestoreCreate
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


def _fields(total: str, intervention_mean: str, control_mean: str, evidence_location: str, confidence: str) -> dict:
    return {
        "study_design": "group_comparison",
        "participants": {
            "sample_size_total": total,
            "groups": [
                {"name": "intervention", "n": "60" if total == "120" else "40", "mean": intervention_mean, "sd": "10.1", "timepoint": "post"},
                {"name": "control", "n": "60" if total == "120" else "40", "mean": control_mean, "sd": "11.3" if total == "120" else "9.0", "timepoint": "post"},
            ],
        },
        "intervention_or_predictor": "self-directed learning" if total == "120" else "feedback",
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
            {"field": "participants.sample_size_total", "evidence_text": f"N={total}", "location": evidence_location},
            {"field": "participants.groups.intervention", "evidence_text": f"mean={intervention_mean}", "location": evidence_location},
            {"field": "participants.groups.control", "evidence_text": f"mean={control_mean}", "location": evidence_location},
            {"field": "outcomes.0", "evidence_text": "achievement", "location": evidence_location},
        ],
        "confidence": confidence,
    }


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
            fields_json=_fields("120", "82.4", "75.2", "manual", "high"),
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
            fields_json=_fields("80", "80.0", "75.0", "heuristic", "medium"),
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


def test_restore_revision_restores_previous_fields_and_appends_a_new_revision() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    candidate = _candidate(created.id)
    store.add_candidates([candidate])
    service = ExtractionManagementService(store=store, quality_service=QualityAssessmentService())

    store.save_extraction_result(
        ExtractionResult(
            id="e1",
            candidate_id=candidate.id,
            status="completed",
            message="initial extraction",
            fields_json=_fields("80", "80.0", "75.0", "heuristic", "medium"),
            model_name="gpt",
            raw_response={"source": "openai"},
            created_at="2026-03-20T10:00:00",
        )
    )
    store.save_extraction_result(
        ExtractionResult(
            id="e1",
            candidate_id=candidate.id,
            status="manual_override",
            message="corrected extraction",
            fields_json=_fields("120", "82.4", "75.2", "manual", "high"),
            model_name="manual_override",
            raw_response={"manual_override": {"reviewed_by": "dashboard"}},
            created_at="2026-03-20T10:10:00",
        )
    )

    revisions = store.list_extraction_revisions(candidate.id)
    restored = service.restore_revision(
        candidate.id,
        revisions[0].id,
        ExtractionRevisionRestoreCreate(reviewed_by="dashboard", notes="Rollback to the earlier extraction."),
    )

    assert restored is not None
    assert restored.status == "manual_override"
    assert restored.model_name == "manual_restore"
    assert restored.message == "Restored extraction revision 1."
    assert restored.fields_json["participants"]["sample_size_total"] == "80"
    assert restored.raw_response["restored_revision"]["revision_id"] == revisions[0].id
    assert restored.raw_response["restored_revision"]["source_model_name"] == "gpt"

    all_revisions = store.list_extraction_revisions(candidate.id)
    assert len(all_revisions) == 3
    assert all_revisions[-1].model_name == "manual_restore"

    events = store.list_events(created.id)
    assert events[0].event_type == "extraction_revision_restored"
    assert events[0].metadata_json["restored_revision_index"] == 1


def test_restore_revision_raises_for_missing_revision() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    candidate = _candidate(created.id)
    store.add_candidates([candidate])
    service = ExtractionManagementService(store=store, quality_service=QualityAssessmentService())

    try:
        service.restore_revision(
            candidate.id,
            "missing-revision",
            ExtractionRevisionRestoreCreate(reviewed_by="dashboard"),
        )
    except LookupError as exc:
        assert str(exc) == "Extraction revision not found"
    else:
        raise AssertionError("Expected LookupError for a missing extraction revision")
def test_compare_revision_to_current_reports_field_differences() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    candidate = _candidate(created.id)
    store.add_candidates([candidate])
    service = ExtractionManagementService(store=store, quality_service=QualityAssessmentService())

    store.save_extraction_result(
        ExtractionResult(
            id="e1",
            candidate_id=candidate.id,
            status="completed",
            message="initial extraction",
            fields_json=_fields("80", "80.0", "75.0", "heuristic", "medium"),
            model_name="gpt",
            raw_response={"source": "openai"},
            created_at="2026-03-20T10:00:00",
        )
    )
    store.save_extraction_result(
        ExtractionResult(
            id="e1",
            candidate_id=candidate.id,
            status="manual_override",
            message="corrected extraction",
            fields_json=_fields("120", "82.4", "75.2", "manual", "high"),
            model_name="manual_override",
            raw_response={"manual_override": {"reviewed_by": "dashboard"}},
            created_at="2026-03-20T10:10:00",
        )
    )

    revisions = store.list_extraction_revisions(candidate.id)
    comparison = service.compare_revision_to_current(candidate.id, revisions[0].id)

    assert comparison is not None
    assert comparison["revision_index"] == 1
    assert comparison["changed_field_count"] >= 4
    paths = {item["field_path"]: item for item in comparison["differences"]}
    assert paths["meta.status"]["current_value"] == "manual_override"
    assert paths["meta.status"]["revision_value"] == "completed"
    assert paths["participants.sample_size_total"]["current_value"] == "120"
    assert paths["participants.sample_size_total"]["revision_value"] == "80"