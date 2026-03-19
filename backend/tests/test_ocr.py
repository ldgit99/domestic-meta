from pathlib import Path
from types import SimpleNamespace

from app.models.domain import CandidateRecord
from app.repositories.memory import MemoryStore
from app.schemas.candidate import FullTextArtifactCreate
from app.schemas.search import SearchRequestCreate
from app.services.ocr import OCRService
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


def _prepare_candidate(tmp_path: Path) -> tuple[MemoryStore, SearchManagementService, CandidateRecord]:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="ocr"))
    candidate = CandidateRecord(
        id="c1",
        search_request_id=created.id,
        source="kci",
        source_record_id="k1",
        title="OCR Candidate",
        authors=["Kim"],
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
        canonical_record_id="c1",
    )
    store.add_candidates([candidate])
    service = SearchManagementService(store=store, prisma_service=PrismaService())
    stored_file = tmp_path / "scan.pdf"
    stored_file.write_bytes(b"%PDF-1.4 fake scan")
    artifact = service.register_full_text(
        candidate.id,
        FullTextArtifactCreate(
            file_name="scan.pdf",
            mime_type="application/pdf",
            text_content="",
            text_extraction_status="ocr_required",
            stored_path=str(stored_file),
        ),
    )
    assert artifact is not None
    return store, service, candidate


def test_ocr_service_updates_artifact_when_command_returns_text(tmp_path: Path, monkeypatch) -> None:
    store, search_management, candidate = _prepare_candidate(tmp_path)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="\ud45c\ubcf8\uc218 80\uba85 \uc2e4\ud5d8\uc9d1\ub2e8 40\uba85 \ud1b5\uc81c\uc9d1\ub2e8 40\uba85",
            stderr="",
        )

    monkeypatch.setattr("app.services.ocr.subprocess.run", fake_run)
    service = OCRService(
        store=store,
        search_management=search_management,
        command_template="tesseract {input_path} stdout -l kor+eng",
        timeout_seconds=30,
        min_text_length=20,
    )

    result = service.run(candidate.id)
    artifact = store.get_full_text_artifact(candidate.id)
    updated_candidate = store.get_candidate(candidate.id)

    assert result is not None
    assert result["status"] == "available"
    assert artifact is not None
    assert artifact.text_extraction_status == "available"
    assert artifact.text_content.startswith("\ud45c\ubcf8\uc218 80\uba85")
    assert updated_candidate is not None
    assert updated_candidate.status == "full_text_available"


def test_ocr_service_marks_failure_when_command_is_not_configured(tmp_path: Path) -> None:
    store, search_management, candidate = _prepare_candidate(tmp_path)
    service = OCRService(
        store=store,
        search_management=search_management,
        command_template=None,
        timeout_seconds=30,
        min_text_length=20,
    )

    result = service.run(candidate.id)
    artifact = store.get_full_text_artifact(candidate.id)
    updated_candidate = store.get_candidate(candidate.id)

    assert result is not None
    assert result["status"] == "ocr_failed"
    assert artifact is not None
    assert artifact.text_extraction_status == "ocr_failed"
    assert updated_candidate is not None
    assert updated_candidate.status == "full_text_needs_ocr"
