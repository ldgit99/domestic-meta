import copy

from app.core.utils import generate_id, now_iso
from app.models.domain import ExtractionResult
from app.schemas.candidate import ExtractionResultUpdate, ExtractionRevisionRestoreCreate
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
        fields = self._build_fields(payload.fields_json, existing)
        timestamp = now_iso()
        item = ExtractionResult(
            id=existing.id if existing and existing.id else generate_id("extract"),
            candidate_id=candidate_id,
            status=payload.status,
            message=payload.message,
            fields_json=fields,
            model_name="manual_override",
            raw_response=self._manual_override_raw_response(existing, payload, timestamp),
            created_at=timestamp,
        )
        return self._persist_result(
            candidate,
            item,
            event_type="manual_extraction_saved",
            event_message=f"Saved manual extraction override for candidate '{candidate.title}'.",
            metadata={
                "result_status": item.status,
                "reviewed_by": payload.reviewed_by,
                "notes": payload.notes,
            },
        )

    def restore_revision(
        self,
        candidate_id: str,
        revision_id: str,
        payload: ExtractionRevisionRestoreCreate,
    ) -> ExtractionResult | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        revision = self._get_revision(candidate_id, revision_id)
        existing = self.store.get_extraction_result(candidate_id)
        fields = self._build_fields(revision.fields_json, existing=None)
        timestamp = now_iso()
        message = payload.message or f"Restored extraction revision {revision.revision_index}."
        item = ExtractionResult(
            id=existing.id if existing and existing.id else revision.extraction_result_id or generate_id("extract"),
            candidate_id=candidate_id,
            status=payload.status,
            message=message,
            fields_json=fields,
            model_name="manual_restore",
            raw_response=self._restore_raw_response(existing, revision, payload, timestamp),
            created_at=timestamp,
        )
        return self._persist_result(
            candidate,
            item,
            event_type="extraction_revision_restored",
            event_message=(
                f"Restored extraction revision {revision.revision_index} for candidate '{candidate.title}'."
            ),
            metadata={
                "result_status": item.status,
                "reviewed_by": payload.reviewed_by,
                "notes": payload.notes,
                "restored_revision_id": revision.id,
                "restored_revision_index": revision.revision_index,
                "restored_revision_status": revision.status,
                "restored_revision_model_name": revision.model_name,
            },
        )

    def compare_revision_to_current(self, candidate_id: str, revision_id: str) -> dict | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        current = self.store.get_extraction_result(candidate_id)
        if current is None:
            raise LookupError("Current extraction result not found")

        revision = self._get_revision(candidate_id, revision_id)
        differences = self._diff_result(current, revision)
        return {
            "candidate_id": candidate_id,
            "current_extraction_id": current.id,
            "revision_id": revision.id,
            "revision_index": revision.revision_index,
            "changed_field_count": len(differences),
            "differences": differences,
        }

    def _get_revision(self, candidate_id: str, revision_id: str):
        revision = next(
            (item for item in self.store.list_extraction_revisions(candidate_id) if item.id == revision_id),
            None,
        )
        if revision is None:
            raise LookupError("Extraction revision not found")
        return revision

    def _persist_result(
        self,
        candidate,
        item: ExtractionResult,
        event_type: str,
        event_message: str,
        metadata: dict,
    ) -> ExtractionResult:
        self.store.save_extraction_result(item)

        candidate.status = "extracted"
        self.store.update_candidate(candidate)

        event_metadata = dict(metadata)
        event_metadata["quality_score"] = item.fields_json.get("quality_assessment", {}).get("score")
        event_metadata["candidate_status"] = candidate.status
        self.store.log_event(
            candidate.search_request_id,
            event_type,
            event_message,
            stage="extraction",
            status="completed",
            candidate_id=candidate.id,
            metadata_json=event_metadata,
        )
        return item

    def _build_fields(
        self,
        fields_json: dict,
        existing: ExtractionResult | None,
    ) -> dict:
        if fields_json:
            fields = copy.deepcopy(fields_json)
        elif existing is not None:
            fields = copy.deepcopy(existing.fields_json or {})
        else:
            fields = {}
        fields["quality_assessment"] = self.quality_service.assess(fields)
        return fields

    def _manual_override_raw_response(
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

    def _restore_raw_response(
        self,
        existing: ExtractionResult | None,
        revision,
        payload: ExtractionRevisionRestoreCreate,
        timestamp: str,
    ) -> dict:
        raw_response: dict = {}
        if existing is not None and isinstance(existing.raw_response, dict):
            raw_response = copy.deepcopy(existing.raw_response)
        raw_response["restored_revision"] = {
            "revision_id": revision.id,
            "revision_index": revision.revision_index,
            "restored_at": timestamp,
            "reviewed_by": payload.reviewed_by,
            "notes": payload.notes,
            "source_status": revision.status,
            "source_model_name": revision.model_name,
            "source_created_at": revision.created_at,
            "previous_status": existing.status if existing else None,
            "previous_model_name": existing.model_name if existing else None,
        }
        return raw_response

    def _diff_result(self, current: ExtractionResult, revision) -> list[dict]:
        current_map = self._flatten_value(current.fields_json or {})
        revision_map = self._flatten_value(revision.fields_json or {})
        current_map.update(
            {
                "meta.status": current.status,
                "meta.message": current.message,
                "meta.model_name": current.model_name,
            }
        )
        revision_map.update(
            {
                "meta.status": revision.status,
                "meta.message": revision.message,
                "meta.model_name": revision.model_name,
            }
        )

        output: list[dict] = []
        for path in sorted(set(current_map) | set(revision_map)):
            current_value = current_map.get(path)
            revision_value = revision_map.get(path)
            if path not in revision_map:
                output.append(
                    {
                        "field_path": path,
                        "change_type": "added_in_current",
                        "current_value": current_value,
                        "revision_value": None,
                    }
                )
                continue
            if path not in current_map:
                output.append(
                    {
                        "field_path": path,
                        "change_type": "missing_in_current",
                        "current_value": None,
                        "revision_value": revision_value,
                    }
                )
                continue
            if current_value != revision_value:
                output.append(
                    {
                        "field_path": path,
                        "change_type": "changed",
                        "current_value": current_value,
                        "revision_value": revision_value,
                    }
                )
        return output

    def _flatten_value(self, payload: object, prefix: str = "") -> dict[str, object]:
        if isinstance(payload, dict):
            if not payload and prefix:
                return {prefix: {}}
            output: dict[str, object] = {}
            for key in sorted(payload):
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                output.update(self._flatten_value(payload[key], child_prefix))
            return output
        if isinstance(payload, list):
            if not payload and prefix:
                return {prefix: []}
            output: dict[str, object] = {}
            for index, item in enumerate(payload):
                child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
                output.update(self._flatten_value(item, child_prefix))
            return output
        return {prefix: payload}
