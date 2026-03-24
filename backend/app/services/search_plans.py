from dataclasses import asdict, dataclass, field

from app.core.config import settings
from app.core.constants import SOURCE_KCI, SOURCE_RISS
from app.models.domain import SearchRequest


@dataclass
class SourceSearchPlan:
    source: str
    mode: str
    query_text: str
    terms: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def dedupe_terms(request: SearchRequest) -> list[str]:
    values = [request.query_text, *request.expanded_keywords]
    deduped: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
    return deduped


def _normalized_riss_web_page_scale() -> int:
    configured = settings.riss_web_page_scale
    return configured if configured > 0 else 100


def _build_riss_web_params(query_text: str) -> dict[str, str]:
    return {
        "isDetailSearch": "N",
        "searchGubun": "true",
        "viewYn": "OP",
        "query": query_text,
        "queryText": "",
        "iStartCount": "0",
        "iGroupView": "5",
        "icate": "all",
        "colName": "all",
        "exQuery": "",
        "exQueryText": "",
        "order": "/DESC",
        "onHanja": "false",
        "strSort": "RANK",
        "pageScale": str(_normalized_riss_web_page_scale()),
        "orderBy": "",
        "fsearchMethod": "search",
        "isFDetailSearch": "N",
        "sflag": "1",
        "searchQuery": query_text,
        "fsearchSort": "",
        "fsearchOrder": "",
        "limiterList": "",
        "limiterListText": "",
        "facetList": "",
        "facetListText": "",
        "fsearchDB": "",
        "resultKeyword": query_text,
        "pageNumber": "1",
    }


def _escape_sparql_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_riss_keyword_filter(terms: list[str]) -> str:
    if not terms:
        return ""

    variable_names = [
        "title",
        "subjectLabel",
        "authorTitle",
        "authorLabel",
        "publisherTitle",
        "publisherLabel",
        "journalTitle",
    ]
    conditions: list[str] = []
    for term in terms:
        escaped = _escape_sparql_literal(term.lower())
        matches = [
            f'(BOUND(?{name}) && CONTAINS(LCASE(STR(?{name})), "{escaped}"))'
            for name in variable_names
        ]
        conditions.append(f"({' || '.join(matches)})")
    return f"FILTER ({' || '.join(conditions)})"


def _build_riss_year_filter(request: SearchRequest) -> str:
    return (
        'FILTER (!BOUND(?year) || '
        f'(SUBSTR(STR(?year), 1, 4) >= "{request.year_from}" '
        f'&& SUBSTR(STR(?year), 1, 4) <= "{request.year_to}"))'
    )


def _build_riss_sparql_query(request: SearchRequest, terms: list[str]) -> str:
    keyword_filter = _build_riss_keyword_filter(terms)
    year_filter = _build_riss_year_filter(request)
    blocks: list[str] = []

    if request.include_theses:
        blocks.append(
            """
  {
    ?uri a <http://purl.org/ontology/bibo/Thesis> .
    BIND("thesis" AS ?recordType)
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/title> ?title . }
    OPTIONAL { ?uri <http://purl.org/dc/terms/issued> ?year . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/creator> ?authorNode . ?authorNode <http://purl.org/dc/elements/1.1/title> ?authorTitle . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/creator> ?authorNode2 . ?authorNode2 <http://www.w3.org/2004/02/skos/core#prefLabel> ?authorLabel . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/publisher> ?publisherNode . ?publisherNode <http://purl.org/dc/elements/1.1/title> ?publisherTitle . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/publisher> ?publisherNode2 . ?publisherNode2 <http://www.w3.org/2004/02/skos/core#prefLabel> ?publisherLabel . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/subject> ?subjectNode . ?subjectNode <http://www.w3.org/2004/02/skos/core#prefLabel> ?subjectLabel . }
    OPTIONAL { ?uri <http://purl.org/dc/terms/description> ?abstract . }
    YEAR_FILTER
    KEYWORD_FILTER
  }
            """.strip()
            .replace("YEAR_FILTER", year_filter)
            .replace("KEYWORD_FILTER", keyword_filter)
        )

    if request.include_journal_articles:
        blocks.append(
            """
  {
    ?journal <http://data.riss.kr/ontology/hasArticle> ?uri .
    BIND("journal_article" AS ?recordType)
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/title> ?title . }
    OPTIONAL { ?uri <http://purl.org/dc/terms/issued> ?year . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/creator> ?authorNode . ?authorNode <http://purl.org/dc/elements/1.1/title> ?authorTitle . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/creator> ?authorNode2 . ?authorNode2 <http://www.w3.org/2004/02/skos/core#prefLabel> ?authorLabel . }
    OPTIONAL { ?journal <http://purl.org/dc/elements/1.1/title> ?journalTitle . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/publisher> ?publisherNode . ?publisherNode <http://purl.org/dc/elements/1.1/title> ?publisherTitle . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/publisher> ?publisherNode2 . ?publisherNode2 <http://www.w3.org/2004/02/skos/core#prefLabel> ?publisherLabel . }
    OPTIONAL { ?uri <http://purl.org/dc/elements/1.1/subject> ?subjectNode . ?subjectNode <http://www.w3.org/2004/02/skos/core#prefLabel> ?subjectLabel . }
    OPTIONAL { ?uri <http://purl.org/dc/terms/description> ?abstract . }
    YEAR_FILTER
    KEYWORD_FILTER
  }
            """.strip()
            .replace("YEAR_FILTER", year_filter)
            .replace("KEYWORD_FILTER", keyword_filter)
        )

    if not blocks:
        blocks.append('  { BIND("unsupported" AS ?recordType) FILTER(false) }')

    union_block = "\n  UNION\n".join(blocks)
    return (
        "SELECT DISTINCT ?uri ?title ?authorTitle ?authorLabel ?year ?publisherTitle ?publisherLabel "
        "?journalTitle ?subjectLabel ?abstract ?recordType WHERE {\n"
        f"{union_block}\n"
        "}\n"
        "ORDER BY DESC(?year)\n"
        "LIMIT 20"
    )


def build_kci_search_plan(request: SearchRequest) -> SourceSearchPlan:
    terms = dedupe_terms(request)
    query_text = " ".join(terms)
    params: dict[str, str] = {}
    notes = [
        "KCI search uses field-based OpenAPI parameters.",
        "Keyword terms are sent through the configured KCI keyword parameter.",
    ]

    if settings.kci_query_param:
        params[settings.kci_query_param] = query_text
    if settings.kci_count_param:
        params[settings.kci_count_param] = "20"
    if settings.kci_year_from_param:
        params[settings.kci_year_from_param] = str(request.year_from)
        notes.append("KCI year lower bound is applied through the configured year-from parameter.")
    if settings.kci_year_to_param:
        params[settings.kci_year_to_param] = str(request.year_to)
        notes.append("KCI year upper bound is applied through the configured year-to parameter.")

    return SourceSearchPlan(
        source=SOURCE_KCI,
        mode="kci_openapi_keyword",
        query_text=query_text,
        terms=terms,
        params=params,
        notes=notes,
    )


def build_riss_search_plan(request: SearchRequest) -> SourceSearchPlan:
    terms = dedupe_terms(request)
    configured_mode = (settings.riss_query_mode or "web").lower()
    query_text = " ".join(terms)

    if configured_mode == "web":
        return SourceSearchPlan(
            source=SOURCE_RISS,
            mode="riss_web_full_search",
            query_text=query_text,
            terms=terms,
            params=_build_riss_web_params(query_text),
            notes=[
                "RISS search uses the real www.riss.kr web search result pages.",
                "The connector paginates with iStartCount and collects the full thesis and journal result sets.",
                f"pageScale is set to {_normalized_riss_web_page_scale()} per request.",
            ],
        )

    if configured_mode == "sparql":
        query = _build_riss_sparql_query(request, terms)
        return SourceSearchPlan(
            source=SOURCE_RISS,
            mode="riss_sparql_keyword_search",
            query_text=query_text,
            terms=terms,
            params={"query": query, "type": "Xml", "flag": "none"},
            notes=[
                "RISS search uses the official data.riss.kr SPARQL endpoint.",
                "Keyword matches are applied across title, subject, author, and publisher labels.",
            ],
        )

    mode = configured_mode if configured_mode == "integrated" else "integrated"
    params: dict[str, str] = {}
    notes = [
        "RISS search defaults to the integrated search query parameter.",
        "Detailed field syntax varies by endpoint and should be configured separately before live rollout.",
    ]
    if configured_mode != mode:
        notes.append(
            f"Unsupported RISS query mode '{configured_mode}' was configured; falling back to integrated search."
        )

    if settings.riss_query_param:
        params[settings.riss_query_param] = query_text
    if settings.riss_count_param:
        params[settings.riss_count_param] = "20"

    return SourceSearchPlan(
        source=SOURCE_RISS,
        mode="riss_integrated_search",
        query_text=query_text,
        terms=terms,
        params=params,
        notes=notes,
    )
