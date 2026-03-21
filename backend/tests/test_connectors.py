import json

from app.core.config import settings
from app.models.domain import SearchRequest
from app.services.connectors import KCIConnector, KCIStubConnector, RISSConnector, RISSLiveConnector


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

    connector = RISSLiveConnector()
    items = connector._parse_json(payload)
    candidate = connector._candidate_from_mapping(items[0], _request(), connector.build_search_plan(_request()))

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


def test_kci_search_plan_uses_fielded_api_params() -> None:
    connector = KCIConnector()
    previous_year_from = settings.kci_year_from_param
    previous_year_to = settings.kci_year_to_param
    settings.kci_year_from_param = "dateFrom"
    settings.kci_year_to_param = "dateTo"
    try:
        plan = connector.build_search_plan(
            _request(expanded_keywords=["achievement", "motivation", "achievement"], year_from=2018, year_to=2024)
        )
    finally:
        settings.kci_year_from_param = previous_year_from
        settings.kci_year_to_param = previous_year_to

    assert plan.source == "kci"
    assert plan.mode == "kci_openapi_keyword"
    assert plan.terms == ["self-directed learning", "achievement", "motivation"]
    assert plan.params[settings.kci_query_param] == "self-directed learning achievement motivation"
    assert plan.params["dateFrom"] == "2018"
    assert plan.params["dateTo"] == "2024"


def test_riss_search_plan_uses_integrated_query_mode() -> None:
    connector = RISSConnector()
    previous_mode = settings.riss_query_mode
    settings.riss_query_mode = "integrated"
    try:
        plan = connector.build_search_plan(
            _request(expanded_keywords=["achievement", "motivation", "achievement"])
        )
    finally:
        settings.riss_query_mode = previous_mode

    assert plan.source == "riss"
    assert plan.mode == "riss_integrated_search"
    assert plan.terms == ["self-directed learning", "achievement", "motivation"]
    assert plan.params[settings.riss_query_param] == "self-directed learning achievement motivation"
    assert any("Detailed field syntax" in note for note in plan.notes)
