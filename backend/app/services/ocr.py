import re
import subprocess
from pathlib import Path

from app.schemas.candidate import FullTextArtifactCreate


class OCRService:
    def __init__(
        self,
        store,
        search_management,
        command_template: str | None,
        timeout_seconds: int = 180,
        min_text_length: int = 20,
    ) -> None:
        self.store = store
        self.search_management = search_management
        self.command_template = command_template
        self.timeout_seconds = timeout_seconds
        self.min_text_length = min_text_length

    def is_configured(self) -> bool:
        return bool(self.command_template)

    def run(self, candidate_id: str) -> dict | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        artifact = self.store.get_full_text_artifact(candidate_id)
        if artifact is None:
            payload = {
                "candidate_id": candidate_id,
                "status": "missing_full_text",
                "message": "Full-text artifact is missing.",
                "full_text_artifact": None,
            }
            self._log(candidate, payload)
            return payload

        if artifact.text_extraction_status == "available" and artifact.text_content.strip():
            payload = {
                "candidate_id": candidate_id,
                "status": "already_available",
                "message": "Usable text already exists for this artifact.",
                "full_text_artifact": artifact,
            }
            self._log(candidate, payload)
            return payload

        if not artifact.stored_path:
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": "Stored file path is missing, so OCR cannot run.",
                "full_text_artifact": updated,
            }
            self._log(candidate, payload)
            return payload

        input_path = Path(artifact.stored_path)
        if not input_path.exists():
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": "Stored file was not found on disk.",
                "full_text_artifact": updated,
            }
            self._log(candidate, payload)
            return payload

        if not self.command_template:
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": "OCR_COMMAND_TEMPLATE is not configured.",
                "full_text_artifact": updated,
            }
            self._log(candidate, payload)
            return payload

        command = self.command_template.format(
            input_path=str(input_path),
            input_name=input_path.name,
        )
        self.store.log_event(
            candidate.search_request_id,
            "ocr_started",
            f"Starting OCR for candidate '{candidate.title}'.",
            stage="ocr",
            status="running",
            candidate_id=candidate_id,
            metadata_json={"stored_path": str(input_path), "file_name": artifact.file_name},
        )

        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": "OCR command timed out.",
                "full_text_artifact": updated,
            }
            self._log(candidate, payload)
            return payload
        except Exception as exc:
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": f"OCR command failed to start: {exc}",
                "full_text_artifact": updated,
            }
            self._log(candidate, payload)
            return payload

        output_text = (completed.stdout or "").strip()
        error_text = (completed.stderr or "").strip()

        if completed.returncode != 0:
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": self._error_message("OCR command returned a non-zero exit code.", error_text),
                "full_text_artifact": updated,
            }
            self._log(candidate, payload, return_code=completed.returncode)
            return payload

        if not self._has_usable_text(output_text):
            updated = self._update_artifact(candidate_id, artifact, artifact.text_content, "ocr_failed")
            payload = {
                "candidate_id": candidate_id,
                "status": "ocr_failed",
                "message": self._error_message("OCR completed, but usable text was not produced.", error_text),
                "full_text_artifact": updated,
            }
            self._log(candidate, payload, return_code=completed.returncode)
            return payload

        updated = self._update_artifact(candidate_id, artifact, output_text, "available")
        payload = {
            "candidate_id": candidate_id,
            "status": "available",
            "message": "OCR completed and usable text was stored.",
            "full_text_artifact": updated,
        }
        self._log(candidate, payload, return_code=completed.returncode)
        return payload

    def _update_artifact(self, candidate_id: str, artifact, text_content: str, status: str):
        payload = FullTextArtifactCreate(
            file_name=artifact.file_name,
            source_url=artifact.source_url,
            mime_type=artifact.mime_type,
            text_content=text_content,
            text_extraction_status=status,
            stored_path=artifact.stored_path,
        )
        updated = self.search_management.register_full_text(candidate_id, payload)
        assert updated is not None
        return updated

    def _has_usable_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        return len(normalized) >= self.min_text_length

    def _error_message(self, prefix: str, error_text: str) -> str:
        if not error_text:
            return prefix
        shortened = error_text[:200]
        return f"{prefix} stderr={shortened}"

    def _log(self, candidate, payload: dict, *, return_code: int | None = None) -> None:
        status = payload["status"]
        event_type = {
            "available": "ocr_completed",
            "already_available": "ocr_skipped",
            "missing_full_text": "ocr_failed",
            "ocr_failed": "ocr_failed",
        }.get(status, "ocr_completed")
        event_status = {
            "available": "completed",
            "already_available": "skipped",
            "missing_full_text": "failed",
            "ocr_failed": "failed",
        }.get(status, "completed")
        artifact = payload.get("full_text_artifact")
        self.store.log_event(
            candidate.search_request_id,
            event_type,
            payload["message"],
            stage="ocr",
            status=event_status,
            candidate_id=candidate.id,
            metadata_json={
                "ocr_status": status,
                "return_code": return_code,
                "text_extraction_status": getattr(artifact, "text_extraction_status", None),
                "stored_path": getattr(artifact, "stored_path", None),
            },
        )
