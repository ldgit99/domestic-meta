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
        text = self._extract_text(stored_path, content_type, content)
        status_text = text if text is not None else ""
        return FullTextArtifactCreate(
            file_name=file_name,
            mime_type=content_type or self._guess_mime(file_name),
            text_content=status_text,
            stored_path=str(stored_path),
        )

    def _guess_mime(self, file_name: str) -> str:
        lowered = file_name.lower()
        if lowered.endswith(".pdf"):
            return "application/pdf"
        if lowered.endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"

    def _extract_text(self, stored_path: Path, content_type: str, content: bytes) -> str:
        mime = content_type or self._guess_mime(stored_path.name)
        if mime.startswith("text/") or stored_path.suffix.lower() == ".txt":
            return content.decode("utf-8", errors="replace")

        if mime == "application/pdf" or stored_path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception:
                return ""

            try:
                reader = PdfReader(str(stored_path))
                return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                return ""

        return content.decode("utf-8", errors="replace")
