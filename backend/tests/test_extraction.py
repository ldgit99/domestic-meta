from app.models.domain import CandidateRecord, FullTextArtifact
from app.services.extraction import ExtractionService


def test_extraction_fallback_detects_meta_ready_signal() -> None:
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="kci",
        source_record_id="k1",
        title="협동학습이 학업성취도에 미치는 효과",
        authors=["홍길동"],
        year=2024,
        journal_or_school="교육연구",
        abstract="비교집단 연구로 평균과 표준편차를 보고하였다.",
        keywords=["협동학습"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="full_text_available",
    )
    artifact = FullTextArtifact(
        id="a1",
        candidate_record_id="c1",
        file_name="demo.txt",
        source_url=None,
        mime_type="text/plain",
        text_content="연구대상은 120명이었다. 실험집단과 통제집단의 평균과 표준편차를 보고하였다.",
        text_extraction_status="available",
        created_at="now",
    )

    result = ExtractionService().run(candidate, artifact)

    assert result.status in {"fallback_heuristic", "completed"}
    assert result.fields_json["effect_size_inputs"]["is_meta_analytic_ready"] is True
    assert result.fields_json["participants"]["sample_size_total"] == "120"
