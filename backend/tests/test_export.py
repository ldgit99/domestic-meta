from app.models.domain import CandidateRecord, EligibilityDecision, ExtractionResult, PrismaCounts, SearchRequest
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
            "comparison": "control group",
            "statistics": [],
            "effect_size_inputs": {
                "is_meta_analytic_ready": True,
                "effect_type_candidates": ["hedges_g"],
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
                "correlation_coefficient": "",
                "missing_inputs": [],
            },
            "confidence": "medium",
        },
        model_name=None,
        raw_response={},
        created_at="now",
    )


def test_audit_report_contains_search_criteria_and_stage_decisions() -> None:
    payload = ExportService().audit_report_markdown(
        _search_request(),
        _counts(),
        [_candidate()],
        _decisions(),
        [_extraction()],
    )

    assert "# Audit Report: self-directed learning" in payload["content"]
    assert "Expanded Keywords: achievement, motivation" in payload["content"]
    assert "Status counts: included_full_text=1" in payload["content"]
    assert "| Effects of self-directed learning on achievement | kci | 2024 | included_full_text | include | include | completed |" in payload["content"]


def test_meta_analysis_ready_csv_contains_decision_columns() -> None:
    payload = ExportService().meta_analysis_ready_csv(
        "s1",
        [_candidate()],
        _decisions(),
        [_extraction()],
    )

    assert "latest_decision_stage" in payload["content"]
    assert "full_text" in payload["content"]
    assert "hedges_g" in payload["content"]
    assert "two_group_posttest_smd" in payload["content"]


def test_screening_log_json_contains_candidate_metadata() -> None:
    payload = ExportService().screening_log_json("s1", [_candidate()], _decisions())

    assert '"candidate_title": "Effects of self-directed learning on achievement"' in payload["content"]
    assert '"candidate_status": "included_full_text"' in payload["content"]
    assert '"stage": "full_text"' in payload["content"]


def test_search_request_manifest_json_contains_summary_and_prisma_flow() -> None:
    payload = ExportService().search_request_manifest_json(
        _search_request(),
        _counts(),
        [_candidate()],
        _decisions(),
        [_extraction()],
    )

    assert '"expanded_keywords": [' in payload["content"]
    assert '"source_counts": {' in payload["content"]
    assert '"prisma_flow": {' in payload["content"]
    assert '"studies_included_in_review": 2' in payload["content"]
