from app.models.domain import CandidateRecord
from app.services.screening import ScreeningService


def test_screening_excludes_qualitative_study() -> None:
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="kci",
        source_record_id="k1",
        title="협동학습 질적 사례연구",
        authors=["홍길동"],
        year=2023,
        journal_or_school="교육연구",
        abstract="면담 중심 질적 사례연구이다.",
        keywords=["질적연구"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="collected",
    )

    result = ScreeningService().screen_title_abstract(candidate)

    assert result.decision == "exclude"
    assert result.reason_code == "not_quantitative"
