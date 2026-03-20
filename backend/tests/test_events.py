from pathlib import Path

from app.models.domain import CandidateRecord, PipelineEvent, PrismaCounts, SearchRequest
from app.repositories.memory import MemoryStore
from app.repositories.sqlalchemy_store import SQLAlchemyStore
from app.schemas.candidate import DecisionCreate, FullTextArtifactCreate
from app.schemas.search import SearchRequestCreate
from app.services.export import ExportService
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


def _event(event_id: str = "e1") -> PipelineEvent:
    return PipelineEvent(
        id=event_id,
        search_request_id="s1",
        event_type="search_run_completed",
        status="completed",
        message="Search orchestration completed successfully.",
        stage="lifecycle",
        candidate_id=None,
        metadata_json={"collected_candidates": 2},
        created_at="2026-03-20T10:00:00",
    )


def _search_request() -> SearchRequest:
    return SearchRequest(
        id="s1",
        query_text="feedback",
        expanded_keywords=["achievement"],
        year_from=2018,
        year_to=2026,
        include_theses=True,
        include_journal_articles=True,
        inclusion_rules=["control group"],
        exclusion_rules=["qualitative"],
        status="completed",
        created_at="2026-03-20T09:00:00",
    )


def _counts() -> PrismaCounts:
    return PrismaCounts(
        id="p1",
        search_request_id="s1",
        identified_records=2,
        duplicate_records_removed=0,
        records_screened=2,
        records_excluded=0,
        reports_sought_for_retrieval=1,
        reports_not_retrieved=0,
        reports_assessed_for_eligibility=1,
        reports_excluded_with_reasons_json={},
        studies_included_in_review=1,
    )


def test_memory_store_logs_events_and_search_management_records_them() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    store.log_event(created.id, "search_request_created", "Created search request.", stage="lifecycle")
    service = SearchManagementService(store=store, prisma_service=PrismaService())

    candidate = CandidateRecord(
        id="c1",
        search_request_id=created.id,
        source="kci",
        source_record_id="k1",
        title="Feedback intervention effects",
        authors=["Park"],
        year=2024,
        journal_or_school="Education Studies",
        abstract="",
        keywords=["feedback"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="collected",
        canonical_record_id="c1",
    )
    store.add_candidates([candidate])

    service.create_manual_decision(
        candidate.id,
        DecisionCreate(stage="title_abstract", decision="include", reviewed_by="dashboard"),
    )
    service.register_full_text(
        candidate.id,
        FullTextArtifactCreate(
            file_name="study.txt",
            mime_type="text/plain",
            text_content="sample text for extraction",
            text_extraction_status="available",
        ),
    )

    events = store.list_events(created.id)

    assert any(item.event_type == "search_request_created" for item in events)
    assert any(item.event_type == "manual_decision_recorded" for item in events)
    assert any(item.event_type == "full_text_registered" for item in events)


def test_export_service_events_json_and_manifest_include_event_summary() -> None:
    service = ExportService()
    event = _event()
    payload = service.events_json("s1", [event])
    manifest = service.search_request_manifest_json(
        _search_request(),
        _counts(),
        [],
        [],
        [],
        [],
        [],
        [event],
    )

    assert '"event_type": "search_run_completed"' in payload["content"]
    assert '"created_at": "2026-03-20T10:00:00"' in payload["content"]
    assert '"event_count": 1' in manifest["content"]
    assert '"latest_event_at": "2026-03-20T10:00:00"' in manifest["content"]


def test_sqlalchemy_store_persists_pipeline_events(tmp_path: Path) -> None:
    db_path = tmp_path / "events.db"
    store = SQLAlchemyStore(f"sqlite:///{db_path}")
    created = store.create_search_request(SearchRequestCreate(query_text="self-directed learning"))

    logged = store.log_event(
        created.id,
        "search_request_created",
        "Created search request.",
        stage="lifecycle",
        status="completed",
        metadata_json={"query_text": created.query_text},
    )
    events = store.list_events(created.id)

    assert logged.id == events[0].id
    assert events[0].metadata_json["query_text"] == "self-directed learning"
