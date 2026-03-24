from fastapi.testclient import TestClient

from app.api.dependencies import get_orchestrator, get_store
from app.core.config import settings
from app.main import app
from app.repositories.memory import MemoryStore
from app.services.orchestrator import SearchOrchestrator


def test_search_run_and_summary_expose_source_breakdown_and_screening_sequence() -> None:
    store = MemoryStore()
    orchestrator = SearchOrchestrator(store=store)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    previous_riss_live_enabled = settings.riss_live_enabled
    settings.riss_live_enabled = False

    try:
        client = TestClient(app)
        created = client.post(
            "/api/search-requests",
            json={
                "query_text": "self-directed learning",
                "expanded_keywords": ["achievement", "motivation"],
                "year_from": 2018,
                "year_to": 2026,
                "include_theses": True,
                "include_journal_articles": True,
                "inclusion_rules": ["achievement"],
                "exclusion_rules": ["qualitative"],
            },
        )
        assert created.status_code == 200
        search_request_id = created.json()["id"]

        run = client.post(f"/api/search-requests/{search_request_id}/run")
        assert run.status_code == 200
        run_payload = run.json()
        assert run_payload["status"] == "completed"
        assert run_payload["collected_candidates"] == 4
        assert run_payload["canonical_candidates"] == 4
        assert {item["source"] for item in run_payload["source_runs"]} == {"riss", "kci"}

        summary = client.get(f"/api/search-requests/{search_request_id}/summary")
        assert summary.status_code == 200
        summary_payload = summary.json()

        riss_row = next(item for item in summary_payload["source_search_breakdown"] if item["source"] == "riss")
        kci_row = next(item for item in summary_payload["source_search_breakdown"] if item["source"] == "kci")
        exclusion_step = next(
            item for item in summary_payload["screening_sequence"] if item["criterion_id"] == "user_exclusion_rules"
        )
        quantitative_step = next(
            item for item in summary_payload["screening_sequence"] if item["criterion_id"] == "quantitative_signal"
        )

        assert riss_row["raw_total_hits"] == 2
        assert kci_row["raw_total_hits"] == 2
        assert kci_row["query_mode"] == "kci_openapi_keyword"
        assert exclusion_step["excluded_count"] == 1
        assert quantitative_step["included_count"] == 2
        assert quantitative_step["review_count"] == 1
    finally:
        settings.riss_live_enabled = previous_riss_live_enabled
        app.dependency_overrides.clear()
