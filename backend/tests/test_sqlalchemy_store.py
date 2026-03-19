from pathlib import Path

from app.models.domain import CandidateRecord
from app.repositories.sqlalchemy_store import SQLAlchemyStore
from app.schemas.search import SearchRequestCreate


def test_sqlalchemy_store_persists_search_request_and_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    store = SQLAlchemyStore(f"sqlite:///{db_path}")

    created = store.create_search_request(SearchRequestCreate(query_text="협동학습"))
    candidate = CandidateRecord(
        id="c1",
        search_request_id=created.id,
        source="kci",
        source_record_id="k1",
        title="협동학습의 효과",
        authors=["홍길동"],
        year=2024,
        journal_or_school="교육연구",
        abstract="평균과 표준편차를 보고하였다.",
        keywords=["협동학습"],
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
    assert loaded_request.query_text == "협동학습"
    assert len(loaded_candidates) == 1
    assert loaded_candidates[0].title == "협동학습의 효과"
