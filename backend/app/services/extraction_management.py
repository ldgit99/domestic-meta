import copy

from app.core.utils import generate_id, now_iso
from app.models.domain import ExtractionResult
from app.schemas.candidate import ExtractionResultUpdate
from app.services.quality import QualityAssessmentService


class ExtractionManagementService:
    def __init__(self, store, quality_service: QualityAssessmentService) -> None:
        self.store = store
        self.quality_service = quality_service

    def save_manual_result(
        self,
        candidate_id: str,
        payload: ExtractionResultUpdate,
    ) -> ExtractionResult | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        existing = self.store.get_extraction_result(candidate_id)
        fields = self._build_fields(payload, existing)
        timestamp = now_iso()
        raw_response = self._raw_response(existing, payload, timestamp)
        item = ExtractionResult(
            id=existing.id if existing and existing.id else generate_id("extract"),
            candidate_id=candidate_id,
            status=payload.status,
            message=payload.message,
            fields_json=fields,
            model_name="manual_override",
            raw_response=raw_response,
            created_at=timestamp,
        )
        self.store.save_extraction_result(item)

        candidate.status = "extracted"
        self.store.update_candidate(candidate)

        self.store.log_event(
            candidate.search_request_id,
            "manual_extraction_saved",
            f"Saved manual extraction override for candidate '{candidate.title}'.",
            stage="extraction",
            status="completed",
            candidate_id=candidate.id,
            metadata_json={
                "result_status": item.status,
                "reviewed_by": payload.reviewed_by,
                "notes": payload.notes,
                "quality_score": fields.get("quality_assessment", {}).get("score"),
                "candidate_status": candidate.status,
            },
        )
        return item

    def _build_fields(
        self,
        payload: ExtractionResultUpdate,
        existing: ExtractionResult | None,
    ) -> dict:
        if payload.fields_json:
            fields = copy.deepcopy(payload.fields_json)
        elif existing is not None:
            fields = copy.deepcopy(existing.fields_json or {})
        else:
            fields = {}
        fields["quality_assessment"] = self.quality_service.assess(fields)
        return fields

    def _raw_response(
        self,
        existing: ExtractionResult | None,
        payload: ExtractionResultUpdate,
        timestamp: str,
    ) -> dict:
        raw_response: dict = {}
        if existing is not None and isinstance(existing.raw_response, dict):
            raw_response = copy.deepcopy(existing.raw_response)
        raw_response["manual_override"] = {
            "reviewed_by": payload.reviewed_by,
            "notes": payload.notes,
            "updated_at": timestamp,
            "previous_status": existing.status if existing else None,
            "previous_model_name": existing.model_name if existing else None,
        }
        return raw_response