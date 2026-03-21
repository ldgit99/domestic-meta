from app.repositories.memory import MemoryStore
from app.schemas.search import SearchRequestCreate
from app.services.orchestrator import SearchOrchestrator
from app.services.search_summary import SearchSummaryService


def test_orchestrator_returns_source_runs_and_summary_builds_source_and_sequence_views() -> None:
    store = MemoryStore()
    created = store.create_search_request(
        SearchRequestCreate(
            query_text="self-directed learning",
            expanded_keywords=["achievement", "motivation"],
            inclusion_rules=["achievement"],
            exclusion_rules=["qualitative"],
        )
    )

    result = SearchOrchestrator(store).run(created.id)

    assert result.status == "completed"
    assert result.collected_candidates == 4
    assert result.canonical_candidates == 4
    assert {item.source for item in result.source_runs} == {"kci", "riss"}
    assert all(item.query_mode for item in result.source_runs)

    summary = SearchSummaryService()
    candidates = store.list_candidates(created.id)
    events = store.list_events(created.id)

    source_breakdown = summary.build_source_breakdown(candidates, events)
    assert [item["source"] for item in source_breakdown] == ["riss", "kci"]

    riss_row = next(item for item in source_breakdown if item["source"] == "riss")
    kci_row = next(item for item in source_breakdown if item["source"] == "kci")
    assert riss_row["raw_total_hits"] == 2
    assert riss_row["fetched_candidates"] == 2
    assert kci_row["raw_total_hits"] == 2
    assert kci_row["query_mode"] == "kci_openapi_keyword"

    sequence = summary.build_screening_sequence(created, candidates)
    assert [item["criterion_id"] for item in sequence] == [
        "publication_year",
        "user_exclusion_rules",
        "user_inclusion_rules",
        "quantitative_signal",
    ]

    exclusion_step = next(item for item in sequence if item["criterion_id"] == "user_exclusion_rules")
    inclusion_step = next(item for item in sequence if item["criterion_id"] == "user_inclusion_rules")
    quantitative_step = next(item for item in sequence if item["criterion_id"] == "quantitative_signal")

    assert exclusion_step["evaluated_count"] == 4
    assert exclusion_step["excluded_count"] == 1
    assert inclusion_step["evaluated_count"] == 3
    assert inclusion_step["passed_count"] == 3
    assert quantitative_step["evaluated_count"] == 3
    assert quantitative_step["included_count"] == 2
    assert quantitative_step["review_count"] == 1
