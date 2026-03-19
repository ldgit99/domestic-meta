import re
from pathlib import Path

from app.core.config import settings
from app.schemas.candidate import FullTextArtifactCreate


class DocumentIngestionService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.uploads_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def ingest_bytes(
        self,
        candidate_id: str,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> FullTextArtifactCreate:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file_name) or "upload.bin"
        stored_path = self.upload_dir / f"{candidate_id}_{safe_name}"
        stored_path.write_bytes(content)
        text_content, text_status = self._extract_text(stored_path, content_type, content)
        return FullTextArtifactCreate(
            file_name=file_name,
            mime_type=content_type or self._guess_mime(file_name),
            text_content=text_content,
            text_extraction_status=text_status,
            stored_path=str(stored_path),
        )

    def _guess_mime(self, file_name: str) -> str:
        lowered = file_name.lower()
        if lowered.endswith(".pdf"):
            return "application/pdf"
        if lowered.endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"

    def _extract_text(self, stored_path: Path, content_type: str, content: bytes) -> tuple[str, str]:
        mime = content_type or self._guess_mime(stored_path.name)
        if mime.startswith("text/") or stored_path.suffix.lower() == ".txt":
            text = content.decode("utf-8", errors="replace").strip()
            return text, self._status_for_text(text)

        if mime == "application/pdf" or stored_path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception:
                return "", "ocr_required"

            try:
                reader = PdfReader(str(stored_path))
                text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                return "", "ocr_required"

            if self._has_usable_text(text):
                return text, "available"
            return "", "ocr_required"

        text = content.decode("utf-8", errors="replace").strip()
        return text, self._status_for_text(text)

    def _status_for_text(self, text: str) -> str:
        return "available" if self._has_usable_text(text) else "no_text_extracted"

    def _has_usable_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        return len(normalized) >= settings.ocr_min_text_length
