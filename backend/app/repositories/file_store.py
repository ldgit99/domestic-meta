import json
from dataclasses import asdict
from pathlib import Path

from app.core.constants import TITLE_ABSTRACT_STAGE
from app.core.utils import generate_id, now_iso
from app.models.domain import (
    CandidateRecord,
    EligibilityDecision,
    ExtractionResult,
    ExtractionRevision,
    FullTextArtifact,
    PipelineEvent,
    PrismaCounts,
    SearchRequest,
)
from app.schemas.candidate import DecisionCreate, FullTextArtifactCreate
from app.schemas.search import SearchRequestCreate


class FileStore:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._save_raw(self._default_payload())

    def _default_payload(self) -> dict:
        return {
            "search_requests": {},
            "candidates": {},
            "decisions": {},
            "prisma_counts": {},
            "pipeline_events": {},
            "full_text_artifacts": {},
            "extraction_results": {},
            "extraction_revisions": {},
        }

    def _load_raw(self) -> dict:
        if not self.file_path.exists():
            payload = self._default_payload()
            self._save_raw(payload)
            return payload

        with self.file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        changed = False
        for key, default_value in self._default_payload().items():
            if key not in payload:
                payload[key] = default_value
                changed = True

        if changed:
            self._save_raw(payload)
        return payload

    def _save_raw(self, payload: dict) -> None:
        with self.file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _deserialize_search_request(self, payload: dict) -> SearchRequest:
        return SearchRequest(**payload)

    def _deserialize_candidate(self, payload: dict) -> CandidateRecord:
        return CandidateRecord(**payload)

    def _deserialize_decision(self, payload: dict) -> EligibilityDecision:
        return EligibilityDecision(**payload)

    def _deserialize_prisma(self, payload: dict) -> PrismaCounts:
        return PrismaCounts(**payload)

    def _deserialize_event(self, payload: dict) -> PipelineEvent:
        return PipelineEvent(**payload)

    def _deserialize_artifact(self, payload: dict) -> FullTextArtifact:
        return FullTextArtifact(**payload)

    def _deserialize_extraction(self, payload: dict) -> ExtractionResult:
        return ExtractionResult(**payload)

    def _deserialize_extraction_revision(self, payload: dict) -> ExtractionRevision:
        return ExtractionRevision(**payload)

    def list_search_requests(self) -> list[SearchRequest]:
        raw = self._load_raw()
        items = [self._deserialize_search_request(item) for item in raw["search_requests"].values()]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def create_search_request(self, payload: SearchRequestCreate) -> SearchRequest:
        raw = self._load_raw()
        item = SearchRequest(
            id=generate_id("search"),
            query_text=payload.query_text,
            expanded_keywords=payload.expanded_keywords,
            year_from=payload.year_from,
            year_to=payload.year_to,
            include_theses=payload.include_theses,
            include_journal_articles=payload.include_journal_articles,
            inclusion_rules=payload.inclusion_rules,
            exclusion_rules=payload.exclusion_rules,
            status="created",
            created_at=now_iso(),
        )
        raw["search_requests"][item.id] = asdict(item)
        raw["prisma_counts"][item.id] = asdict(
            PrismaCounts(
                id=generate_id("prisma"),
                search_request_id=item.id,
            )
        )
        self._save_raw(raw)
        return item

    def reset_search_results(self, search_request_id: str) -> None:
        raw = self._load_raw()
        candidate_ids = {
            candidate_id
            for candidate_id, item in raw["candidates"].items()
            if item["search_request_id"] == search_request_id
        }
        for candidate_id in candidate_ids:
            raw["candidates"].pop(candidate_id, None)
            raw["full_text_artifacts"].pop(candidate_id, None)
            raw["extraction_results"].pop(candidate_id, None)
        raw["decisions"] = {
            key: value
            for key, value in raw["decisions"].items()
            if value["candidate_record_id"] not in candidate_ids
        }
        raw["extraction_revisions"] = {
            key: value
            for key, value in raw["extraction_revisions"].items()
            if value["candidate_id"] not in candidate_ids
        }
        existing = raw["prisma_counts"].get(search_request_id)
        prisma_id = existing["id"] if existing else generate_id("prisma")
        raw["prisma_counts"][search_request_id] = asdict(
            PrismaCounts(id=prisma_id, search_request_id=search_request_id)
        )
        self._save_raw(raw)

    def get_search_request(self, search_request_id: str) -> SearchRequest | None:
        raw = self._load_raw()
        payload = raw["search_requests"].get(search_request_id)
        return self._deserialize_search_request(payload) if payload else None

    def update_search_request_status(self, search_request_id: str, status: str) -> None:
        raw = self._load_raw()
        raw["search_requests"][search_request_id]["status"] = status
        self._save_raw(raw)

    def add_candidates(self, items: list[CandidateRecord]) -> None:
        raw = self._load_raw()
        for item in items:
            raw["candidates"][item.id] = asdict(item)
        self._save_raw(raw)

    def list_candidates(self, search_request_id: str) -> list[CandidateRecord]:
        raw = self._load_raw()
        return [
            self._deserialize_candidate(item)
            for item in raw["candidates"].values()
            if item["search_request_id"] == search_request_id
        ]

    def get_candidate(self, candidate_id: str) -> CandidateRecord | None:
        raw = self._load_raw()
        payload = raw["candidates"].get(candidate_id)
        return self._deserialize_candidate(payload) if payload else None

    def update_candidate(self, item: CandidateRecord) -> None:
        raw = self._load_raw()
        raw["candidates"][item.id] = asdict(item)
        self._save_raw(raw)

    def save_decision(self, item: EligibilityDecision) -> EligibilityDecision:
        raw = self._load_raw()
        raw["decisions"][item.id] = asdict(item)
        self._save_raw(raw)
        return item

    def create_decision(self, candidate_id: str, payload: DecisionCreate) -> EligibilityDecision | None:
        raw = self._load_raw()
        candidate_payload = raw["candidates"].get(candidate_id)
        if candidate_payload is None:
            return None

        item = EligibilityDecision(
            id=generate_id("decision"),
            candidate_record_id=candidate_id,
            stage=payload.stage,
            decision=payload.decision,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            confidence=payload.confidence,
            reviewed_by=payload.reviewed_by,
            created_at=now_iso(),
        )
        raw["decisions"][item.id] = asdict(item)
        if payload.stage == TITLE_ABSTRACT_STAGE:
            candidate_payload["status"] = "screened_title_abstract"
        self._save_raw(raw)
        return item

    def list_decisions_for_search(self, search_request_id: str) -> list[EligibilityDecision]:
        raw = self._load_raw()
        candidate_ids = {
            item["id"]
            for item in raw["candidates"].values()
            if item["search_request_id"] == search_request_id
        }
        return [
            self._deserialize_decision(item)
            for item in raw["decisions"].values()
            if item["candidate_record_id"] in candidate_ids
        ]

    def get_prisma_counts(self, search_request_id: str) -> PrismaCounts | None:
        raw = self._load_raw()
        payload = raw["prisma_counts"].get(search_request_id)
        return self._deserialize_prisma(payload) if payload else None

    def update_prisma_counts(self, item: PrismaCounts) -> None:
        raw = self._load_raw()
        raw["prisma_counts"][item.search_request_id] = asdict(item)
        self._save_raw(raw)

    def log_event(
        self,
        search_request_id: str,
        event_type: str,
        message: str,
        *,
        stage: str | None = None,
        status: str = "info",
        candidate_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> PipelineEvent:
        raw = self._load_raw()
        item = PipelineEvent(
            id=generate_id("event"),
            search_request_id=search_request_id,
            event_type=event_type,
            status=status,
            message=message,
            stage=stage,
            candidate_id=candidate_id,
            metadata_json=metadata_json or {},
            created_at=now_iso(),
        )
        raw["pipeline_events"][item.id] = asdict(item)
        self._save_raw(raw)
        return item

    def list_events(self, search_request_id: str) -> list[PipelineEvent]:
        raw = self._load_raw()
        items = [
            self._deserialize_event(item)
            for item in raw["pipeline_events"].values()
            if item["search_request_id"] == search_request_id
        ]
        return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)

    def create_full_text_artifact(
        self,
        candidate_id: str,
        payload: FullTextArtifactCreate,
    ) -> FullTextArtifact | None:
        raw = self._load_raw()
        if candidate_id not in raw["candidates"]:
            return None

        item = FullTextArtifact(
            id=generate_id("artifact"),
            candidate_record_id=candidate_id,
            file_name=payload.file_name,
            source_url=payload.source_url,
            mime_type=payload.mime_type,
            text_content=payload.text_content,
            text_extraction_status=payload.text_extraction_status
            or ("available" if payload.text_content.strip() else "pending"),
            created_at=now_iso(),
            stored_path=payload.stored_path,
        )
        raw["full_text_artifacts"][candidate_id] = asdict(item)
        self._save_raw(raw)
        return item

    def get_full_text_artifact(self, candidate_id: str) -> FullTextArtifact | None:
        raw = self._load_raw()
        payload = raw["full_text_artifacts"].get(candidate_id)
        return self._deserialize_artifact(payload) if payload else None

    def save_extraction_result(self, item: ExtractionResult) -> ExtractionResult:
        raw = self._load_raw()
        if not item.id:
            item.id = generate_id("extract")
        if not item.created_at:
            item.created_at = now_iso()
        raw["extraction_results"][item.candidate_id] = asdict(item)
        revision = self._build_extraction_revision(raw, item)
        if revision is not None:
            raw["extraction_revisions"][revision.id] = asdict(revision)
        self._save_raw(raw)
        return item

    def get_extraction_result(self, candidate_id: str) -> ExtractionResult | None:
        raw = self._load_raw()
        payload = raw["extraction_results"].get(candidate_id)
        return self._deserialize_extraction(payload) if payload else None

    def list_extraction_results_for_search(self, search_request_id: str) -> list[ExtractionResult]:
        raw = self._load_raw()
        candidate_ids = {
            item["id"]
            for item in raw["candidates"].values()
            if item["search_request_id"] == search_request_id
        }
        return [
            self._deserialize_extraction(item)
            for key, item in raw["extraction_results"].items()
            if key in candidate_ids
        ]

    def list_extraction_revisions(self, candidate_id: str) -> list[ExtractionRevision]:
        raw = self._load_raw()
        items = [
            self._deserialize_extraction_revision(item)
            for item in raw["extraction_revisions"].values()
            if item["candidate_id"] == candidate_id
        ]
        return sorted(items, key=lambda item: (item.revision_index, item.created_at or "", item.id))

    def list_extraction_revisions_for_search(self, search_request_id: str) -> list[ExtractionRevision]:
        raw = self._load_raw()
        items = [
            self._deserialize_extraction_revision(item)
            for item in raw["extraction_revisions"].values()
            if item["search_request_id"] == search_request_id
        ]
        return sorted(items, key=lambda item: (item.candidate_id, item.revision_index, item.created_at or "", item.id))

    def _build_extraction_revision(self, raw: dict, item: ExtractionResult) -> ExtractionRevision | None:
        candidate = raw["candidates"].get(item.candidate_id)
        if candidate is None:
            return None
        revision_index = 1 + len(
            [
                value
                for value in raw["extraction_revisions"].values()
                if value["candidate_id"] == item.candidate_id
            ]
        )
        return ExtractionRevision(
            id=generate_id("revision"),
            extraction_result_id=item.id,
            candidate_id=item.candidate_id,
            search_request_id=candidate["search_request_id"],
            revision_index=revision_index,
            status=item.status,
            message=item.message,
            fields_json=item.fields_json,
            model_name=item.model_name,
            raw_response=item.raw_response,
            created_at=item.created_at or now_iso(),
        )
