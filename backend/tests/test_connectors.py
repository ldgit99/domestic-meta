import json
from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.models.domain import SearchRequest
from app.services.connectors import KCIConnector, KCIStubConnector, RISSConnector, RISSLiveConnector, RISSStubConnector


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


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


def _web_item(control_no: str, p_mat_type: str, title: str, etc_spans: list[tuple[str, str]], abstract: str = "") -> str:
    rendered_spans = []
    for role, text in etc_spans:
        class_attr = ""
        if role != "value":
            class_attr = f' class="{role}"'
        rendered_spans.append(f"<span{class_attr}>{text}</span>")
    abstract_html = f'<p class="preAbstract">{abstract}</p>' if abstract else ""
    return f'''
<li>
  <span style="display:none;"><input name="p_control_no" value="{control_no}|{p_mat_type}" type="checkbox" /></span>
  <div class="cont">
    <p class="title"><a href="/search/detail/DetailView.do?p_mat_type={p_mat_type}&control_no={control_no}">{title}</a></p>
    <p class="etc">{"".join(rendered_spans)}</p>
    {abstract_html}
  </div>
</li>
'''


def _web_page(total_hits: int, items: list[str]) -> str:
    return f'''
<div class="searchBox pd">
  <dl>
    <dd>query<span>(<span class="num">{total_hits}</span>)</span></dd>
  </dl>
</div>
<div class="srchResultListW">
  <ul>
    {"".join(items)}
  </ul>
</div>
'''


def test_riss_connector_falls_back_to_stub_when_live_disabled() -> None:
    previous_enabled = settings.riss_live_enabled
    previous_url = settings.riss_api_url
    settings.riss_live_enabled = False
    settings.riss_api_url = None
    try:
        result = RISSConnector().collect(_request())
    finally:
        settings.riss_live_enabled = previous_enabled
        settings.riss_api_url = previous_url

    assert result.backend == "stub"
    assert result.source == "riss"
    assert len(result.candidates) >= 1
    assert all(item.source == "riss" for item in result.candidates)


def test_riss_connector_surfaces_live_misconfiguration_without_stub_fallback() -> None:
    previous_enabled = settings.riss_live_enabled
    previous_url = settings.riss_api_url
    previous_mode = settings.riss_query_mode
    settings.riss_live_enabled = True
    settings.riss_api_url = None
    settings.riss_query_mode = "integrated"
    try:
        result = RISSConnector().collect(_request())
    finally:
        settings.riss_live_enabled = previous_enabled
        settings.riss_api_url = previous_url
        settings.riss_query_mode = previous_mode

    assert result.backend == "live_misconfigured"
    assert result.source == "riss"
    assert result.total_hits == 0
    assert result.candidates == []
    assert "RISS_API_URL" in result.query_plan["notes"][-1]


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
            },
            "totalCount": 17,
        }
    )

    connector = RISSLiveConnector()
    items, total_hits = connector._parse_json(payload)
    candidate = connector._candidate_from_mapping(items[0], _request(), connector.build_search_plan(_request()))

    assert len(items) == 1
    assert total_hits == 17
    assert candidate.title == "Self-directed learning effects"
    assert candidate.document_type == "thesis"
    assert candidate.journal_or_school == "Seoul National University"
    assert candidate.keywords == ["self-directed learning", "achievement"]


def test_riss_live_connector_parses_sparql_xml_results() -> None:
    payload = """<?xml version='1.0'?><sparql xmlns='http://www.w3.org/2005/sparql-results#'>
    <head>
        <variable name='uri'/>
        <variable name='title'/>
        <variable name='authorLabel'/>
        <variable name='subjectLabel'/>
        <variable name='recordType'/>
    </head>
    <results>
        <result>
            <binding name='uri'><uri>https://data.riss.kr/resource/Thesis/1</uri></binding>
            <binding name='title'><literal>XML thesis title</literal></binding>
            <binding name='authorLabel'><literal>Kim</literal></binding>
            <binding name='subjectLabel'><literal>learning motivation</literal></binding>
            <binding name='recordType'><literal>thesis</literal></binding>
        </result>
    </results>
</sparql>"""

    connector = RISSLiveConnector()
    items, total_hits = connector._parse_xml_records(payload)
    candidate = connector._candidate_from_mapping(items[0], _request(), connector.build_search_plan(_request()))

    assert total_hits is None
    assert items[0]["uri"] == "https://data.riss.kr/resource/Thesis/1"
    assert candidate.title == "XML thesis title"
    assert candidate.document_type == "thesis"
    assert candidate.keywords == ["learning motivation"]


def test_riss_live_connector_collects_paginated_web_results(monkeypatch) -> None:
    requested_urls: list[str] = []
    pages = {
        ("bib_t", "0"): _web_page(
            3,
            [
                _web_item(
                    "thesis-1",
                    "bib-t",
                    "AI chatbot education in higher education",
                    [("writer", "Kim"), ("assigned", "Seoul University"), ("value", "2024"), ("value", "국내석사")],
                    "Reports quantitative outcomes.",
                ),
                _web_item(
                    "thesis-2",
                    "bib-t",
                    "Teacher support for AI chatbot education",
                    [("writer", "Lee"), ("assigned", "Korea University"), ("value", "2023"), ("value", "국내박사")],
                ),
            ],
        ),
        ("bib_t", "2"): _web_page(
            3,
            [
                _web_item(
                    "thesis-3",
                    "bib-t",
                    "AI chatbot education self-efficacy study",
                    [("writer", "Park"), ("assigned", "Yonsei University"), ("value", "2022"), ("value", "국내석사")],
                )
            ],
        ),
        ("re_a_kor", "0"): _web_page(
            2,
            [
                _web_item(
                    "article-1",
                    "re-a",
                    "AI chatbot education intervention effects",
                    [("writer", "Choi"), ("assigned", "Korean AI Education Society"), ("value", "2025"), ("value", "Journal of AI Education"), ("value", "Vol.3 No.1")],
                    "Controlled classroom experiment.",
                ),
                _web_item(
                    "article-2",
                    "re-a",
                    "Prompt design for AI chatbot education",
                    [("writer", "Han"), ("assigned", "EdTech Association"), ("value", "2024"), ("value", "Educational Technology Review"), ("value", "Vol.8 No.2")],
                ),
            ],
        ),
    }

    def fake_urlopen(request, timeout=0):
        url = request.full_url if hasattr(request, "full_url") else request.get_full_url()
        requested_urls.append(url)
        query = parse_qs(urlparse(url).query)
        key = (query["colName"][0], query["iStartCount"][0])
        return _FakeResponse(pages[key])

    previous_values = {
        "riss_live_enabled": settings.riss_live_enabled,
        "riss_query_mode": settings.riss_query_mode,
        "riss_api_url": settings.riss_api_url,
        "riss_web_page_scale": settings.riss_web_page_scale,
        "riss_thesis_collection": settings.riss_thesis_collection,
        "riss_journal_collection": settings.riss_journal_collection,
    }
    settings.riss_live_enabled = True
    settings.riss_query_mode = "web"
    settings.riss_api_url = "https://www.riss.kr/search/Search.do"
    settings.riss_web_page_scale = 2
    settings.riss_thesis_collection = "bib_t"
    settings.riss_journal_collection = "re_a_kor"
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    try:
        result = RISSConnector().collect(_request(query_text="ai chatbot education", expanded_keywords=["classroom"]))
    finally:
        for key, value in previous_values.items():
            setattr(settings, key, value)

    assert result.backend == "live"
    assert result.total_hits == 5
    assert len(result.candidates) == 5
    assert sum(1 for item in result.candidates if item.document_type == "thesis") == 3
    assert sum(1 for item in result.candidates if item.document_type == "journal_article") == 2
    assert any(item.journal_or_school == "Journal of AI Education" for item in result.candidates)
    assert any("Total RISS web page requests: 3." in note for note in result.query_plan["notes"])
    assert any("iStartCount=2" in url and "colName=bib_t" in url for url in requested_urls)
    assert any("colName=re_a_kor" in url for url in requested_urls)


def test_stub_connectors_respect_year_range_and_document_flags() -> None:
    thesis_only = _request(include_journal_articles=False, include_theses=True, year_from=2022, year_to=2022)
    journal_only = _request(include_journal_articles=True, include_theses=False, year_from=2020, year_to=2020)

    riss_result = RISSStubConnector().collect(thesis_only)
    kci_result = KCIStubConnector().collect(journal_only)

    assert len(riss_result.candidates) == 1
    assert riss_result.candidates[0].document_type == "thesis"
    assert kci_result.candidates == []
    assert kci_result.total_hits == 0


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


def test_riss_search_plan_uses_web_query_mode() -> None:
    connector = RISSConnector()
    previous_mode = settings.riss_query_mode
    previous_page_scale = settings.riss_web_page_scale
    settings.riss_query_mode = "web"
    settings.riss_web_page_scale = 50
    try:
        plan = connector.build_search_plan(
            _request(expanded_keywords=["achievement", "motivation", "achievement"])
        )
    finally:
        settings.riss_query_mode = previous_mode
        settings.riss_web_page_scale = previous_page_scale

    assert plan.source == "riss"
    assert plan.mode == "riss_web_full_search"
    assert plan.terms == ["self-directed learning", "achievement", "motivation"]
    assert plan.params["query"] == "self-directed learning achievement motivation"
    assert plan.params["pageScale"] == "50"
    assert any("real www.riss.kr web search result pages" in note for note in plan.notes)


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


def test_riss_search_plan_uses_sparql_keyword_mode() -> None:
    connector = RISSConnector()
    previous_mode = settings.riss_query_mode
    settings.riss_query_mode = "sparql"
    try:
        plan = connector.build_search_plan(
            _request(expanded_keywords=["achievement", "motivation"], include_journal_articles=False)
        )
    finally:
        settings.riss_query_mode = previous_mode

    assert plan.source == "riss"
    assert plan.mode == "riss_sparql_keyword_search"
    assert plan.terms == ["self-directed learning", "achievement", "motivation"]
    assert plan.params["type"] == "Xml"
    assert plan.params["flag"] == "none"
    assert "<http://purl.org/ontology/bibo/Thesis>" in plan.params["query"]
    assert any("official data.riss.kr SPARQL endpoint" in note for note in plan.notes)