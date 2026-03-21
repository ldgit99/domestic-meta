from app.models.domain import CandidateRecord, PipelineEvent, SearchRequest
from app.services.screening import ScreeningService


class SearchSummaryService:
    def __init__(self) -> None:
        self.screening = ScreeningService()

    def build_source_breakdown(
        self,
        candidates: list[CandidateRecord],
        events: list[PipelineEvent],
    ) -> list[dict]:
        latest_source_events: dict[str, PipelineEvent] = {}
        for event in sorted(events, key=lambda item: (item.created_at, item.id)):
            if event.event_type != "source_collection_completed":
                continue
            source = str(event.metadata_json.get("source") or "").strip().lower()
            if source:
                latest_source_events[source] = event

        seen_sources: list[str] = []
        for source in ["riss", "kci"] + [candidate.source for candidate in candidates] + list(latest_source_events):
            normalized = str(source or "").strip().lower()
            if normalized and normalized not in seen_sources:
                seen_sources.append(normalized)

        rows: list[dict] = []
        for source in seen_sources:
            source_candidates = [item for item in candidates if item.source == source]
            event = latest_source_events.get(source)
            metadata = event.metadata_json if event is not None else {}
            query_plan = metadata.get("query_plan") or {}
            rows.append(
                {
                    "source": source,
                    "label": self._source_label(source),
                    "backend": metadata.get("backend") or self._infer_backend(source_candidates),
                    "query_mode": metadata.get("query_mode") or query_plan.get("mode"),
                    "raw_total_hits": metadata.get("raw_total_hits"),
                    "fetched_candidates": metadata.get("fetched_candidates", len(source_candidates)),
                    "canonical_candidates": len(
                        [item for item in source_candidates if item.canonical_record_id in {None, item.id}]
                    ),
                    "duplicate_candidates": len(
                        [item for item in source_candidates if item.canonical_record_id not in {None, item.id}]
                    ),
                    "status_counts": self._status_counts(source_candidates),
                    "query_plan": query_plan,
                }
            )
        return rows

    def build_screening_sequence(
        self,
        request: SearchRequest,
        candidates: list[CandidateRecord],
    ) -> list[dict]:
        canonical_candidates = [item for item in candidates if item.canonical_record_id in {None, item.id}]
        template = self.screening.sequence_template()
        aggregates = {
            item["criterion_id"]: {
                "order": index + 1,
                "criterion_id": item["criterion_id"],
                "label": item["label"],
                "description": item["description"],
                "evaluated_count": 0,
                "passed_count": 0,
                "excluded_count": 0,
                "review_count": 0,
                "included_count": 0,
                "outcome_counts": {},
            }
            for index, item in enumerate(template)
        }

        for candidate in canonical_candidates:
            evaluation = self.screening.evaluate_title_abstract(candidate, request=request)
            for step in evaluation.steps:
                aggregate = aggregates[step.criterion_id]
                aggregate["evaluated_count"] += 1
                aggregate["outcome_counts"][step.outcome] = aggregate["outcome_counts"].get(step.outcome, 0) + 1
                if step.outcome == "pass":
                    aggregate["passed_count"] += 1
                elif step.outcome == "exclude":
                    aggregate["excluded_count"] += 1
                elif step.outcome == "review":
                    aggregate["review_count"] += 1
                elif step.outcome == "include":
                    aggregate["included_count"] += 1

        return [aggregates[item["criterion_id"]] for item in template]

    def _source_label(self, source: str) -> str:
        labels = {
            "riss": "RISS",
            "kci": "KCI",
        }
        return labels.get(source, source.upper())

    def _status_counts(self, candidates: list[CandidateRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return counts

    def _infer_backend(self, candidates: list[CandidateRecord]) -> str | None:
        backends = {str(item.raw_payload.get("source") or "").strip() for item in candidates if item.raw_payload}
        backends.discard("")
        if len(backends) == 1:
            return next(iter(backends))
        return None
