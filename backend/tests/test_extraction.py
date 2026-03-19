from app.models.domain import CandidateRecord, FullTextArtifact
from app.services.extraction import ExtractionService


def test_extraction_fallback_detects_group_statistics_and_meta_ready_signal() -> None:
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="kci",
        source_record_id="k1",
        title="Effects of self-directed learning on achievement",
        authors=["Kim"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="A group comparison study reported post-test means and standard deviations.",
        keywords=["self-directed learning"],
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
            "The study included 120 participants. The intervention group had 60 students. "
            "The control group had 60 students. The intervention group mean was 82.4 with "
            "a standard deviation of 10.1. The control group mean was 75.2 with a standard "
            "deviation of 11.3. The difference was statistically significant at p < .05."
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


def test_extraction_blocks_when_ocr_is_required() -> None:
    candidate = CandidateRecord(
        id="c2",
        search_request_id="s1",
        source="riss",
        source_record_id="r1",
        title="Scanned PDF study",
        authors=["Lee"],
        year=2024,
        journal_or_school="Graduate School",
        abstract="",
        keywords=["motivation"],
        doi=None,
        url=None,
        document_type="thesis",
        language="ko",
        raw_payload={},
        status="full_text_needs_ocr",
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
    )

    result = ExtractionService().run(candidate, artifact)

    assert result.status == "ocr_required"
    assert result.fields_json["effect_size_inputs"]["is_meta_analytic_ready"] is False


def test_extraction_supports_korean_group_labels() -> None:
    candidate = CandidateRecord(
        id="c3",
        search_request_id="s1",
        source="kci",
        source_record_id="k3",
        title="\uc790\uae30\uc8fc\ub3c4\ud559\uc2b5 \ud504\ub85c\uadf8\ub7a8 \ud6a8\uacfc",
        authors=["Choi"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["\uc790\uae30\uc8fc\ub3c4\ud559\uc2b5"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="full_text_available",
    )
    artifact = FullTextArtifact(
        id="a3",
        candidate_record_id="c3",
        file_name="demo.txt",
        source_url=None,
        mime_type="text/plain",
        text_content=(
            "\ud45c\ubcf8\uc218 80\uba85. \uc2e4\ud5d8\uc9d1\ub2e8 40\uba85, \ud1b5\uc81c\uc9d1\ub2e8 40\uba85. "
            "\uc2e4\ud5d8\uc9d1\ub2e8 \ud3c9\uade0 82.4 \ud45c\uc900\ud3b8\ucc28 10.1. "
            "\ud1b5\uc81c\uc9d1\ub2e8 \ud3c9\uade0 75.2 \ud45c\uc900\ud3b8\ucc28 11.3."
        ),
        text_extraction_status="available",
        created_at="now",
    )

    result = ExtractionService().run(candidate, artifact)

    assert result.fields_json["participants"]["sample_size_total"] == "80"
    assert result.fields_json["participants"]["groups"][0]["n"] == "40"
    assert result.fields_json["effect_size_inputs"]["recommended_effect_type"] == "hedges_g"
