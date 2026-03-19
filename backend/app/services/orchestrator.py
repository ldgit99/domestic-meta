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
        self.store.reset_search_results(search_request_id)

        collected = []
        for connector in self.connectors:
            collected.extend(connector.collect(request))

        collected, duplicates_removed = self.deduplication.deduplicate(collected)
        self.store.add_candidates(collected)

        screened_count = 0
        for candidate in self.store.list_candidates(search_request_id):
            if candidate.canonical_record_id != candidate.id:
                continue
            decision = self.screening.screen_title_abstract(candidate)
            self.store.save_decision(decision)
            candidate.status = "screened_title_abstract"
            self.store.update_candidate(candidate)
            screened_count += 1

        counts = self.store.get_prisma_counts(search_request_id)
        assert counts is not None
        updated = self.prisma.recalculate(
            counts=counts,
            collected_count=len(collected),
            duplicates_removed=duplicates_removed,
            decisions=self.store.list_decisions_for_search(search_request_id),
        )
        self.store.update_prisma_counts(updated)
        self.store.update_search_request_status(search_request_id, "completed")

        return SearchRunResult(
            search_request_id=search_request_id,
            status="completed",
            collected_candidates=len(collected),
            screened_candidates=screened_count,
            duplicates_removed=duplicates_removed,
        )
