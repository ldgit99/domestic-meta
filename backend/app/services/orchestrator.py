from app.core.constants import DECISION_EXCLUDE, DECISION_INCLUDE, DECISION_MAYBE, DECISION_REVIEW
from app.schemas.search import SearchRunResult
from app.services.connectors import KCIConnector, RISSConnector
from app.services.deduplication import DeduplicationService
from app.services.prisma import PrismaService
from app.services.screening import ScreeningService


class SearchOrchestrator:
    def __init__(self, store) -> None:
        self.store = store
        self.connectors = [KCIConnector(), RISSConnector()]
        self.deduplication = DeduplicationService()
        self.screening = ScreeningService()
        self.prisma = PrismaService()

    def run(self, search_request_id: str) -> SearchRunResult:
        request = self.store.get_search_request(search_request_id)
        if request is None:
            raise KeyError("Search request not found")

        self.store.update_search_request_status(search_request_id, "running")
        self._log(
            search_request_id,
            "search_run_started",
            "Search orchestration started.",
            stage="lifecycle",
            status="running",
        )

        try:
            self.store.reset_search_results(search_request_id)
            self._log(
                search_request_id,
                "search_results_reset",
                "Previous candidates, decisions, artifacts, and PRISMA counts were cleared before rerun.",
                stage="lifecycle",
                status="completed",
            )

            collected = []
            for connector in self.connectors:
                plan = connector.build_search_plan(request)
                connector_items = list(connector.collect(request))
                collected.extend(connector_items)
                source_name = getattr(connector, "source_name", connector.__class__.__name__.lower())
                mode = connector_items[0].raw_payload.get("source", "unknown") if connector_items else "none"
                self._log(
                    search_request_id,
                    "source_collection_completed",
                    f"Collected {len(connector_items)} candidate(s) from {source_name}.",
                    stage="collection",
                    status="completed",
                    metadata_json={
                        "source": source_name,
                        "count": len(connector_items),
                        "mode": mode,
                        "query_plan": plan.to_dict(),
                    },
                )

            collected, duplicates_removed = self.deduplication.deduplicate(collected)
            self.store.add_candidates(collected)
            self._log(
                search_request_id,
                "deduplication_completed",
                f"Deduplication kept {len(collected)} canonical-or-remaining candidates and removed {duplicates_removed} duplicates.",
                stage="deduplication",
                status="completed",
                metadata_json={
                    "remaining_candidates": len(collected),
                    "duplicates_removed": duplicates_removed,
                },
            )

            screened_count = 0
            for candidate in self.store.list_candidates(search_request_id):
                if candidate.canonical_record_id != candidate.id:
                    continue
                decision = self.screening.screen_title_abstract(candidate, request=request)
                self.store.save_decision(decision)
                candidate.status = self._status_for_screening(decision.decision)
                self.store.update_candidate(candidate)
                screened_count += 1

            self._log(
                search_request_id,
                "title_abstract_screening_completed",
                f"Completed title and abstract screening for {screened_count} canonical candidate(s).",
                stage="screening",
                status="completed",
                metadata_json={"screened_candidates": screened_count},
            )

            counts = self.store.get_prisma_counts(search_request_id)
            assert counts is not None
            updated = self.prisma.recalculate(
                counts=counts,
                collected_count=len(collected),
                duplicates_removed=duplicates_removed,
                decisions=self.store.list_decisions_for_search(search_request_id),
            )
            self.store.update_prisma_counts(updated)
            self._log(
                search_request_id,
                "prisma_recalculated",
                "PRISMA counts were recalculated after collection and screening.",
                stage="prisma",
                status="completed",
                metadata_json={
                    "identified_records": updated.identified_records,
                    "records_screened": updated.records_screened,
                    "studies_included_in_review": updated.studies_included_in_review,
                },
            )

            self.store.update_search_request_status(search_request_id, "completed")
            self._log(
                search_request_id,
                "search_run_completed",
                "Search orchestration completed successfully.",
                stage="lifecycle",
                status="completed",
                metadata_json={
                    "collected_candidates": len(collected),
                    "screened_candidates": screened_count,
                    "duplicates_removed": duplicates_removed,
                },
            )

            return SearchRunResult(
                search_request_id=search_request_id,
                status="completed",
                collected_candidates=len(collected),
                screened_candidates=screened_count,
                duplicates_removed=duplicates_removed,
            )
        except Exception as exc:
            self.store.update_search_request_status(search_request_id, "failed")
            self._log(
                search_request_id,
                "search_run_failed",
                f"Search orchestration failed: {exc}",
                stage="lifecycle",
                status="failed",
            )
            raise

    def _log(
        self,
        search_request_id: str,
        event_type: str,
        message: str,
        *,
        stage: str,
        status: str,
        metadata_json: dict | None = None,
    ) -> None:
        self.store.log_event(
            search_request_id,
            event_type,
            message,
            stage=stage,
            status=status,
            metadata_json=metadata_json or {},
        )

    def _status_for_screening(self, decision: str) -> str:
        if decision == DECISION_INCLUDE:
            return "selected_for_full_text"
        if decision == DECISION_EXCLUDE:
            return "excluded_title_abstract"
        if decision in {DECISION_MAYBE, DECISION_REVIEW}:
            return "needs_review_title_abstract"
        return "screened_title_abstract"
