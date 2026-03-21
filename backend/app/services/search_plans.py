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
    configured_mode = settings.riss_query_mode or "integrated"
    mode = configured_mode if configured_mode == "integrated" else "integrated"
    query_text = " ".join(terms)
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
