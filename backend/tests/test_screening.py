from app.models.domain import CandidateRecord, SearchRequest
from app.services.screening import ScreeningService


def _candidate(**overrides) -> CandidateRecord:
    payload = {
        "id": "c1",
        "search_request_id": "s1",
        "source": "kci",
        "source_record_id": "k1",
        "title": "Self-directed learning and achievement",
        "authors": ["Kim"],
        "year": 2024,
        "journal_or_school": "Journal of Education",
        "abstract": "The intervention and control groups reported mean and standard deviation values.",
        "keywords": ["self-directed learning", "achievement"],
        "doi": None,
        "url": None,
        "document_type": "journal_article",
        "language": "ko",
        "raw_payload": {},
        "status": "collected",
        "duplicate_group_id": None,
        "canonical_record_id": "c1",
    }
    payload.update(overrides)
    return CandidateRecord(**payload)


def _request(**overrides) -> SearchRequest:
    payload = {
        "id": "s1",
        "query_text": "self-directed learning",
        "expanded_keywords": [],
        "year_from": 2010,
        "year_to": 2026,
        "include_theses": True,
        "include_journal_articles": True,
        "inclusion_rules": [],
        "exclusion_rules": [],
        "status": "created",
        "created_at": "now",
    }
    payload.update(overrides)
    return SearchRequest(**payload)


def test_screening_service_excludes_candidate_outside_date_range() -> None:
    decision = ScreeningService().screen_title_abstract(
        _candidate(year=2005),
        request=_request(year_from=2015, year_to=2026),
    )

    assert decision.decision == "exclude"
    assert decision.reason_code == "outside_date_range"


def test_screening_service_flags_missing_inclusion_rule_match() -> None:
    decision = ScreeningService().screen_title_abstract(
        _candidate(abstract="Quantitative study with mean scores and standard deviations."),
        request=_request(inclusion_rules=["online learning"]),
    )

    assert decision.decision == "maybe"
    assert decision.reason_text.startswith("No inclusion rule matched")


def test_screening_service_excludes_candidate_matching_exclusion_rule() -> None:
    decision = ScreeningService().screen_title_abstract(
        _candidate(title="Teacher interview study"),
        request=_request(exclusion_rules=["interview"]),
    )

    assert decision.decision == "exclude"
    assert decision.reason_code == "user_exclusion_rule_match"
