from app.services.document_ingestion import DocumentIngestionService


def test_document_ingestion_text_file_extracts_text() -> None:
    payload = DocumentIngestionService().ingest_bytes(
        candidate_id="c1",
        file_name="sample.txt",
        content_type="text/plain",
        content="연구대상은 120명이었다.".encode("utf-8"),
    )

    assert payload.text_content == "연구대상은 120명이었다."
    assert payload.stored_path is not None
    assert payload.mime_type == "text/plain"
