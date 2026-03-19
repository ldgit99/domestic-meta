from app.models.domain import CandidateRecord, EligibilityDecision, ExtractionResult, PrismaCounts, SearchRequest
from app.services.export import ExportService


def test_audit_report_contains_prisma_and_candidate_rows() -> None:
    search_request = SearchRequest(
        id="s1",
        query_text="협동학습",
        expanded_keywords=[],
        year_from=2010,
        year_to=2026,
        include_theses=True,
        include_journal_articles=True,
        inclusion_rules=[],
        exclusion_rules=[],
        status="completed",
        created_at="now",
    )
    counts = PrismaCounts(id="p1", search_request_id="s1", identified_records=3, records_screened=2)
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
        status="extracted",
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
    extraction = ExtractionResult(
        id="e1",
        candidate_id="c1",
        status="completed",
        message="ok",
        fields_json={
            "participants": {
                "sample_size_total": "120",
                "groups": [
                    {"name": "실험집단", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                    {"name": "통제집단", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
                ],
            },
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

    payload = ExportService().audit_report_markdown(search_request, counts, [candidate], [decision], [extraction])

    assert "# Audit Report: 협동학습" in payload["content"]
    assert "Identified records: 3" in payload["content"]
    assert "협동학습이 학업성취도에 미치는 효과" in payload["content"]
    assert "hedges_g" in payload["content"]


def test_meta_analysis_ready_csv_contains_effect_summary_columns() -> None:
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
        status="extracted",
    )
    extraction = ExtractionResult(
        id="e1",
        candidate_id="c1",
        status="completed",
        message="ok",
        fields_json={
            "study_design": "group_comparison",
            "participants": {
                "sample_size_total": "120",
                "groups": [
                    {"name": "실험집단", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                    {"name": "통제집단", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
                ],
            },
            "intervention_or_predictor": "협동학습",
            "comparison": "통제집단",
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

    payload = ExportService().meta_analysis_ready_csv("s1", [candidate], [extraction])

    assert "recommended_effect_type" in payload["content"]
    assert "hedges_g" in payload["content"]
    assert "two_group_posttest_smd" in payload["content"]
