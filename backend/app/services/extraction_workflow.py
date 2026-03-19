from app.models.domain import ExtractionResult
from app.services.extraction import ExtractionService


class ExtractionWorkflowService:
    def __init__(self, store, extraction_service: ExtractionService, ocr_service=None) -> None:
        self.store = store
        self.extraction_service = extraction_service
        self.ocr_service = ocr_service

    def run(self, candidate_id: str) -> ExtractionResult | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        artifact = self.store.get_full_text_artifact(candidate_id)
        if (
            artifact is not None
            and self.ocr_service is not None
            and self.ocr_service.is_configured()
            and (artifact.text_extraction_status != "available" or not artifact.text_content.strip())
        ):
            ocr_payload = self.ocr_service.run(candidate_id)
            if ocr_payload is not None and ocr_payload.get("full_text_artifact") is not None:
                artifact = ocr_payload["full_text_artifact"]

        result = self.extraction_service.run(candidate, artifact)
        self.store.save_extraction_result(result)

        if result.status in {"completed", "fallback_heuristic"}:
            candidate.status = "extracted"
        elif result.status in {"ocr_required", "ocr_failed", "text_extraction_pending", "text_not_available"}:
            candidate.status = "full_text_needs_ocr"

        self.store.update_candidate(candidate)
        return result
