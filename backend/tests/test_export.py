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
from app.services.export import ExportService


def _search_request() -> SearchRequest:
    return SearchRequest(
        id="s1",
        query_text="self-directed learning",
        expanded_keywords=["achievement", "motivation"],
        year_from=2018,
        year_to=2026,
        include_theses=True,
        include_journal_articles=True,
        inclusion_rules=["achievement"],
        exclusion_rules=["qualitative"],
        status="completed",
        created_at="now",
    )


def _counts() -> PrismaCounts:
    return PrismaCounts(
        id="p1",
        search_request_id="s1",
        identified_records=5,
        duplicate_records_removed=1,
        records_screened=4,
        records_excluded=1,
        reports_sought_for_retrieval=3,
        reports_not_retrieved=0,
        reports_assessed_for_eligibility=2,
        reports_excluded_with_reasons_json={"not_quantitative": 1},
        studies_included_in_review=2,
    )


def _candidate() -> CandidateRecord:
    return CandidateRecord(
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
        status="included_full_text",
        duplicate_group_id=None,
        canonical_record_id="c1",
    )


def _decisions() -> list[EligibilityDecision]:
    return [
        EligibilityDecision(
            id="d1",
            candidate_record_id="c1",
            stage="title_abstract",
            decision="include",
            reason_code=None,
            reason_text=None,
            confidence="medium",
            reviewed_by="agent",
            created_at="2026-03-19T00:00:00",
        ),
        EligibilityDecision(
            id="d2",
            candidate_record_id="c1",
            stage="full_text",
            decision="include",
            reason_code=None,
            reason_text=None,
            confidence="medium",
            reviewed_by="agent",
            created_at="2026-03-19T00:10:00",
        ),
    ]


def _extraction() -> ExtractionResult:
    return ExtractionResult(
        id="e1",
        candidate_id="c1",
        status="completed",
        message="ok",
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
                {"field": "participants.sample_size_total", "evidence_text": "N=120", "location": "heuristic"},
                {"field": "participants.groups.intervention", "evidence_text": "intervention n=60 mean=82.4 sd=10.1", "location": "heuristic"},
                {"field": "participants.groups.control", "evidence_text": "control n=60 mean=75.2 sd=11.3", "location": "heuristic"},
                {"field": "outcomes.0", "evidence_text": "achievement", "location": "heuristic"},
            ],
            "confidence": "high",
            "quality_assessment": {
                "score": "high",
                "warnings": [],
                "evidence_count": 4,
                "group_sample_size_total_matches": True,
                "critical_fields_present": ["study_design", "sample_size", "outcomes", "evidence_spans", "effect_inputs"],
                "critical_fields_missing": [],
            },
        },
        model_name=None,
        raw_response={},
        created_at="now",
    )


def _revisions() -> list[ExtractionRevision]:
    extraction = _extraction()
    return [
        ExtractionRevision(
            id="r1",
            extraction_result_id=extraction.id,
            candidate_id=extraction.candidate_id,
            search_request_id="s1",
            revision_index=1,
            status="completed",
            message="Initial extraction",
            fields_json=extraction.fields_json,
            model_name="gpt",
            raw_response={"source": "openai"},
            created_at="2026-03-20T10:00:00",
        ),
        ExtractionRevision(
            id="r2",
            extraction_result_id=extraction.id,
            candidate_id=extraction.candidate_id,
            search_request_id="s1",
            revision_index=2,
            status="manual_override",
            message="Manual correction",
            fields_json=extraction.fields_json,
            model_name="manual_override",
            raw_response={"manual_override": {"reviewed_by": "dashboard"}},
            created_at="2026-03-20T10:10:00",
        ),
    ]


def _artifact() -> FullTextArtifact:
    return FullTextArtifact(
        id="a1",
        candidate_record_id="c1",
        file_name="study.pdf",
        source_url=None,
        mime_type="application/pdf",
        text_content="Full text",
        text_extraction_status="available",
        created_at="now",
        stored_path="study.pdf",
    )


def _event() -> PipelineEvent:
    return PipelineEvent(
        id="ev1",
        search_request_id="s1",
        event_type="search_run_completed",
        status="completed",
        message="Search orchestration completed successfully.",
        stage="lifecycle",
        candidate_id=None,
        metadata_json={"collected_candidates": 1},
        created_at="2026-03-20T10:00:00",
    )


def test_audit_report_contains_search_criteria_stage_decisions_quality_summary_and_revision_count() -> None:
    payload = ExportService().audit_report_markdown(
        _search_request(),
        _counts(),
        [_candidate()],
        _decisions(),
        [_extraction()],
        _revisions(),
        [_artifact()],
        [_event()],
    )

    assert "# Audit Report: self-directed learning" in payload["content"]
    assert "Expanded Keywords: achievement, motivation" in payload["content"]
    assert "Status counts: included_full_text=1" in payload["content"]
    assert "Full-text status counts: available=1" in payload["content"]
    assert "Quality score counts: high=1" in payload["content"]
    assert "Extraction revision count: 2" in payload["content"]
    assert "## Recent Activity" in payload["content"]
    assert "QA Score | Revisions | QA Warnings" in payload["content"]
    assert "| high | 2 |" in payload["content"]


def test_meta_analysis_ready_csv_contains_decision_and_quality_columns() -> None:
    payload = ExportService().meta_analysis_ready_csv(
        "s1",
        [_candidate()],
        _decisions(),
        [_extraction()],
    )

    assert "latest_decision_stage" in payload["content"]
    assert "qa_score" in payload["content"]
    assert "qa_warnings" in payload["content"]
    assert "qa_evidence_count" in payload["content"]
    assert "full_text" in payload["content"]
    assert "hedges_g" in payload["content"]
    assert "two_group_posttest_smd" in payload["content"]
    assert "high" in payload["content"]


def test_extraction_revisions_json_contains_revision_metadata() -> None:
    payload = ExportService().extraction_revisions_json("s1", _revisions())

    assert '"revision_index": 1' in payload["content"]
    assert '"revision_index": 2' in payload["content"]
    assert '"model_name": "manual_override"' in payload["content"]
    assert '"candidate_id": "c1"' in payload["content"]


def test_screening_log_json_contains_candidate_metadata() -> None:
    payload = ExportService().screening_log_json("s1", [_candidate()], _decisions())

    assert '"candidate_title": "Effects of self-directed learning on achievement"' in payload["content"]
    assert '"candidate_status": "included_full_text"' in payload["content"]
    assert '"stage": "full_text"' in payload["content"]


def test_search_request_manifest_json_contains_summary_prisma_flow_event_counts_quality_counts_and_revision_counts() -> None:
    payload = ExportService().search_request_manifest_json(
        _search_request(),
        _counts(),
        [_candidate()],
        _decisions(),
        [_extraction()],
        _revisions(),
        [_artifact()],
        [_event()],
    )

    assert '"expanded_keywords": [' in payload["content"]
    assert '"source_counts": {' in payload["content"]
    assert '"full_text_status_counts": {' in payload["content"]
    assert '"quality_score_counts": {' in payload["content"]
    assert '"extraction_revision_count": 2' in payload["content"]
    assert '"high": 1' in payload["content"]
    assert '"prisma_flow": {' in payload["content"]
    assert '"studies_included_in_review": 2' in payload["content"]
    assert '"event_count": 1' in payload["content"]
