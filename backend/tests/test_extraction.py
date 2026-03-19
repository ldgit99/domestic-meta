from app.models.domain import CandidateRecord, FullTextArtifact
from app.services.extraction import ExtractionService


def test_extraction_fallback_detects_group_statistics_and_meta_ready_signal() -> None:
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
        text_content=(
            "연구대상은 120명이었다. 실험집단 60명과 통제집단 60명으로 구성하였다. "
            "실험집단 평균은 82.4, 표준편차는 10.1이었고 통제집단 평균은 75.2, 표준편차는 11.3이었다. "
            "두 집단 간 차이는 통계적으로 유의하였다(p < .05)."
        ),
        text_extraction_status="available",
        created_at="now",
    )

    result = ExtractionService().run(candidate, artifact)
    fields = result.fields_json

    assert result.status in {"fallback_heuristic", "completed"}
    assert fields["effect_size_inputs"]["is_meta_analytic_ready"] is True
    assert fields["effect_size_inputs"]["recommended_effect_type"] == "hedges_g"
    assert fields["participants"]["sample_size_total"] == "120"
    assert fields["participants"]["groups"][0]["n"] == "60"
    assert fields["participants"]["groups"][0]["mean"] == "82.4"
