from pathlib import Path

from app.models.domain import CandidateRecord, ExtractionResult
from app.repositories.file_store import FileStore
from app.repositories.memory import MemoryStore
from app.repositories.sqlalchemy_store import SQLAlchemyStore
from app.schemas.search import SearchRequestCreate


def _candidate(search_request_id: str) -> CandidateRecord:
    return CandidateRecord(
        id="c1",
        search_request_id=search_request_id,
        source="kci",
        source_record_id="k1",
        title="Effects of self-directed learning",
        authors=["Kim"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="",
        keywords=["self-directed learning"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="included_full_text",
        canonical_record_id="c1",
    )


def _result(status: str, message: str, created_at: str) -> ExtractionResult:
    return ExtractionResult(
        id="e1",
        candidate_id="c1",
        status=status,
        message=message,
        fields_json={
            "study_design": "group_comparison",
            "participants": {
                "sample_size_total": "120",
                "groups": [
                    {"name": "intervention", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                    {"name": "control", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
                ],
            },
            "outcomes": ["achievement"],
            "effect_size_inputs": {
                "is_meta_analytic_ready": True,
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
                "missing_inputs": [],
            },
            "evidence_spans": [
                {"field": "participants.sample_size_total", "evidence_text": "N=120", "location": "heuristic"},
                {"field": "participants.groups.intervention", "evidence_text": "n=60 mean=82.4 sd=10.1", "location": "heuristic"},
                {"field": "participants.groups.control", "evidence_text": "n=60 mean=75.2 sd=11.3", "location": "heuristic"},
                {"field": "outcomes.0", "evidence_text": "achievement", "location": "heuristic"},
            ],
            "confidence": "medium",
        },
        model_name="manual_override" if status == "manual_override" else "gpt",
        raw_response={"status": status},
        created_at=created_at,
    )


def test_memory_store_persists_extraction_revisions() -> None:
    store = MemoryStore()
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    store.add_candidates([_candidate(created.id)])

    store.save_extraction_result(_result("completed", "Initial extraction", "2026-03-20T10:00:00"))
    store.save_extraction_result(_result("manual_override", "Manual correction", "2026-03-20T10:10:00"))

    revisions = store.list_extraction_revisions("c1")
    search_revisions = store.list_extraction_revisions_for_search(created.id)

    assert len(revisions) == 2
    assert revisions[0].revision_index == 1
    assert revisions[1].revision_index == 2
    assert revisions[1].status == "manual_override"
    assert len(search_revisions) == 2


def test_file_store_persists_extraction_revisions(tmp_path: Path) -> None:
    store = FileStore(str(tmp_path / "store.json"))
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    store.add_candidates([_candidate(created.id)])

    store.save_extraction_result(_result("completed", "Initial extraction", "2026-03-20T10:00:00"))
    store.save_extraction_result(_result("manual_override", "Manual correction", "2026-03-20T10:10:00"))

    revisions = store.list_extraction_revisions("c1")

    assert len(revisions) == 2
    assert revisions[0].revision_index == 1
    assert revisions[1].message == "Manual correction"


def test_sqlalchemy_store_persists_extraction_revisions(tmp_path: Path) -> None:
    db_path = tmp_path / "revisions.db"
    store = SQLAlchemyStore(f"sqlite:///{db_path}")
    created = store.create_search_request(SearchRequestCreate(query_text="feedback"))
    store.add_candidates([_candidate(created.id)])

    store.save_extraction_result(_result("completed", "Initial extraction", "2026-03-20T10:00:00"))
    store.save_extraction_result(_result("manual_override", "Manual correction", "2026-03-20T10:10:00"))

    revisions = store.list_extraction_revisions("c1")
    search_revisions = store.list_extraction_revisions_for_search(created.id)

    assert len(revisions) == 2
    assert revisions[0].revision_index == 1
    assert revisions[1].revision_index == 2
    assert revisions[1].model_name == "manual_override"
    assert len(search_revisions) == 2
