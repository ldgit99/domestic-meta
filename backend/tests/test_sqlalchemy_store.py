from pathlib import Path

from sqlalchemy import inspect

from app.models.domain import CandidateRecord
from app.repositories.sqlalchemy_store import SQLAlchemyStore
from app.schemas.search import SearchRequestCreate


def test_sqlalchemy_store_persists_search_request_and_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    store = SQLAlchemyStore(f"sqlite:///{db_path}")

    created = store.create_search_request(SearchRequestCreate(query_text="self-directed learning"))
    candidate = CandidateRecord(
        id="c1",
        search_request_id=created.id,
        source="kci",
        source_record_id="k1",
        title="Effects of self-directed learning",
        authors=["Kim"],
        year=2024,
        journal_or_school="Journal of Education",
        abstract="Reports means and standard deviations for the intervention and control groups.",
        keywords=["self-directed learning"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="collected",
        canonical_record_id="c1",
    )

    store.add_candidates([candidate])

    loaded_request = store.get_search_request(created.id)
    loaded_candidates = store.list_candidates(created.id)

    assert loaded_request is not None
    assert loaded_request.query_text == "self-directed learning"
    assert len(loaded_candidates) == 1
    assert loaded_candidates[0].title == "Effects of self-directed learning"


def test_sqlalchemy_store_can_skip_auto_create(tmp_path: Path) -> None:
    db_path = tmp_path / "manual.db"
    store = SQLAlchemyStore(f"sqlite:///{db_path}", auto_create_tables=False)

    tables = inspect(store.engine).get_table_names()

    assert tables == []
