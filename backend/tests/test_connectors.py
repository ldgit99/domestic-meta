import json

from app.core.config import settings
from app.models.domain import SearchRequest
from app.services.connectors import KCIStubConnector, RISSConnector, RISSLiveConnector


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


def test_riss_connector_falls_back_to_stub_when_live_disabled() -> None:
    previous_enabled = settings.riss_live_enabled
    previous_url = settings.riss_api_url
    settings.riss_live_enabled = False
    settings.riss_api_url = None
    try:
        items = list(RISSConnector().collect(_request()))
    finally:
        settings.riss_live_enabled = previous_enabled
        settings.riss_api_url = previous_url

    assert len(items) >= 1
    assert all(item.source == "riss" for item in items)


def test_riss_live_connector_parses_sparql_style_json_bindings() -> None:
    payload = json.dumps(
        {
            "results": {
                "bindings": [
                    {
                        "title": {"type": "literal", "value": "Self-directed learning effects"},
                        "author": {"type": "literal", "value": "Kim, Lee"},
                        "year": {"type": "literal", "value": "2023"},
                        "school": {"type": "literal", "value": "Seoul National University"},
                        "type": {"type": "literal", "value": "dissertation"},
                        "url": {"type": "uri", "value": "https://example.org/riss/live-1"},
                        "keyword": {"type": "literal", "value": "self-directed learning, achievement"},
                        "description": {"type": "literal", "value": "Reports means and standard deviations."},
                    }
                ]
            }
        }
    )

    items = RISSLiveConnector()._parse_json(payload)
    candidate = RISSLiveConnector()._candidate_from_mapping(items[0], _request())

    assert len(items) == 1
    assert candidate.title == "Self-directed learning effects"
    assert candidate.document_type == "thesis"
    assert candidate.journal_or_school == "Seoul National University"
    assert candidate.keywords == ["self-directed learning", "achievement"]


def test_stub_connectors_respect_year_range_and_document_flags() -> None:
    thesis_only = _request(include_journal_articles=False, include_theses=True, year_from=2022, year_to=2022)
    journal_only = _request(include_journal_articles=True, include_theses=False, year_from=2020, year_to=2020)

    riss_thesis_items = list(RISSConnector().collect(thesis_only))
    kci_items = list(KCIStubConnector().collect(journal_only))

    assert len(riss_thesis_items) == 1
    assert riss_thesis_items[0].document_type == "thesis"
    assert kci_items == []


def test_connector_query_text_uses_expanded_keywords() -> None:
    connector = KCIStubConnector()

    query = connector._build_query_text(
        _request(expanded_keywords=["achievement", "motivation", "achievement"])
    )

    assert query == "self-directed learning achievement motivation"
