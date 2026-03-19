from pathlib import Path
from types import SimpleNamespace

from app.models.domain import CandidateRecord, FullTextArtifact
from app.repositories.memory import MemoryStore
from app.schemas.search import SearchRequestCreate
from app.schemas.candidate import FullTextArtifactCreate
from app.services.extraction import ExtractionService
from app.services.extraction_workflow import ExtractionWorkflowService
from app.services.ocr import OCRService
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


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
    assert fields["quality_assessment"]["score"] == "medium"
    assert "low_confidence_extraction" in fields["quality_assessment"]["warnings"]
    assert fields["quality_assessment"]["evidence_count"] >= 3


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
    assert result.fields_json["quality_assessment"]["score"] == "low"
    assert "missing_evidence_spans" in result.fields_json["quality_assessment"]["warnings"]


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
            "\ud1b5\uc81c\uc9d1\ub2e8 \ud3c9\uade0 75.2 \ud45c\uc900\ud3b8\ucc28 11.3. \uc0ac\ud6c4 \uc131\ucde8\ub3c4\ub97c \ube44\uad50\ud588\ub2e4."
        ),
        text_extraction_status="available",
        created_at="now",
    )

    result = ExtractionService().run(candidate, artifact)

    assert result.fields_json["participants"]["sample_size_total"] == "80"
    assert result.fields_json["participants"]["groups"][0]["n"] == "40"
    assert result.fields_json["effect_size_inputs"]["recommended_effect_type"] == "hedges_g"
    assert "posttest" in result.fields_json["timepoints"]
    assert result.fields_json["quality_assessment"]["score"] in {"medium", "high"}


def test_extraction_workflow_attempts_ocr_before_extracting(tmp_path: Path, monkeypatch) -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="ocr workflow"))
    candidate = CandidateRecord(
        id="c4",
        search_request_id=created.id,
        source="kci",
        source_record_id="k4",
        title="OCR workflow candidate",
        authors=["Han"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["ocr"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="selected_for_full_text",
        canonical_record_id="c4",
    )
    store.add_candidates([candidate])
    search_management = SearchManagementService(store=store, prisma_service=PrismaService())
    stored_file = tmp_path / "scan.pdf"
    stored_file.write_bytes(b"%PDF-1.4 fake scan")
    search_management.register_full_text(
        candidate.id,
        FullTextArtifactCreate(
            file_name="scan.pdf",
            mime_type="application/pdf",
            text_content="",
            text_extraction_status="ocr_required",
            stored_path=str(stored_file),
        ),
    )

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="The study included 80 participants. The intervention group had 40 students. The control group had 40 students. The intervention group mean was 82.4 with a standard deviation of 10.1. The control group mean was 75.2 with a standard deviation of 11.3.",
            stderr="",
        )

    monkeypatch.setattr("app.services.ocr.subprocess.run", fake_run)
    ocr_service = OCRService(
        store=store,
        search_management=search_management,
        command_template="tesseract {input_path} stdout -l kor+eng",
        timeout_seconds=30,
        min_text_length=20,
    )
    workflow = ExtractionWorkflowService(
        store=store,
        extraction_service=ExtractionService(),
        ocr_service=ocr_service,
    )

    result = workflow.run(candidate.id)
    artifact = store.get_full_text_artifact(candidate.id)
    updated_candidate = store.get_candidate(candidate.id)

    assert result is not None
    assert result.status in {"fallback_heuristic", "completed"}
    assert result.fields_json["quality_assessment"]["score"] in {"medium", "high"}
    assert artifact is not None
    assert artifact.text_extraction_status == "available"
    assert updated_candidate is not None
    assert updated_candidate.status == "extracted"