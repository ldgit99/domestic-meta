from app.services.document_ingestion import DocumentIngestionService


def test_document_ingestion_text_file_extracts_text() -> None:
    payload = DocumentIngestionService().ingest_bytes(
        candidate_id="c1",
        file_name="sample.txt",
        content_type="text/plain",
        content="The study included 120 participants.".encode("utf-8"),
    )

    assert payload.text_content == "The study included 120 participants."
    assert payload.stored_path is not None
    assert payload.mime_type == "text/plain"
    assert payload.text_extraction_status == "available"


def test_document_ingestion_pdf_without_usable_text_marks_ocr_required() -> None:
    payload = DocumentIngestionService().ingest_bytes(
        candidate_id="c2",
        file_name="scan.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
    )

    assert payload.mime_type == "application/pdf"
    assert payload.text_content == ""
    assert payload.text_extraction_status == "ocr_required"
