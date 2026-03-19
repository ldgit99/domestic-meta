from app.models.domain import CandidateRecord, ExtractionResult
from app.services.export import ExportService


def test_meta_analysis_ready_csv_contains_extraction_rows() -> None:
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
            "participants": {"population": "", "sample_size_total": "120", "groups": []},
            "intervention_or_predictor": "협동학습",
            "comparison": "강의식 수업",
            "outcomes": [],
            "statistics": [],
            "effect_size_inputs": {"is_meta_analytic_ready": True, "effect_type_candidates": ["standardized_mean_difference"]},
            "evidence_spans": [],
            "confidence": "medium",
        },
        model_name="gpt-4o-mini",
        raw_response={},
        created_at="now",
    )

    payload = ExportService().meta_analysis_ready_csv("s1", [candidate], [extraction])

    assert "candidate_id,title,year" in payload["content"]
    assert "c1" in payload["content"]
    assert "group_comparison" in payload["content"]
