import json

from app.core.config import settings
from app.models.domain import SearchRequest
from app.services.connectors import RISSConnector, RISSLiveConnector


def _request() -> SearchRequest:
    return SearchRequest(
        id="s1",
        query_text="협동학습",
        expanded_keywords=[],
        year_from=2010,
        year_to=2026,
        include_theses=True,
        include_journal_articles=True,
        inclusion_rules=[],
        exclusion_rules=[],
        status="created",
        created_at="now",
    )


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
                        "title": {"type": "literal", "value": "협동학습의 효과"},
                        "author": {"type": "literal", "value": "홍길동;김연구"},
                        "year": {"type": "literal", "value": "2023"},
                        "school": {"type": "literal", "value": "서울대학교"},
                        "type": {"type": "literal", "value": "dissertation"},
                        "url": {"type": "uri", "value": "https://example.org/riss/live-1"},
                        "keyword": {"type": "literal", "value": "협동학습;학업성취도"},
                        "description": {"type": "literal", "value": "평균과 표준편차를 보고한 학위논문"},
                    }
                ]
            }
        }
    )

    items = RISSLiveConnector()._parse_json(payload)
    candidate = RISSLiveConnector()._candidate_from_mapping(items[0], _request())

    assert len(items) == 1
    assert candidate.title == "협동학습의 효과"
    assert candidate.document_type == "thesis"
    assert candidate.journal_or_school == "서울대학교"
    assert candidate.keywords == ["협동학습", "학업성취도"]
