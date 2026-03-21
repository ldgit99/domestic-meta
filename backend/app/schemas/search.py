from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_YEAR_FROM, DEFAULT_YEAR_TO
from app.schemas.prisma import PrismaCountsRead


class SearchRequestCreate(BaseModel):
    query_text: str = Field(min_length=2)
    expanded_keywords: list[str] = Field(default_factory=list)
    year_from: int = DEFAULT_YEAR_FROM
    year_to: int = DEFAULT_YEAR_TO
    include_theses: bool = True
    include_journal_articles: bool = True
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)


class SearchRequestRead(SearchRequestCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: str


class PipelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    search_request_id: str
    event_type: str
    status: str
    message: str
    stage: str | None = None
    candidate_id: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: str


class SearchSourceBreakdownRead(BaseModel):
    source: str
    label: str
    backend: str | None = None
    query_mode: str | None = None
    raw_total_hits: int | None = None
    fetched_candidates: int = 0
    canonical_candidates: int = 0
    duplicate_candidates: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    query_plan: dict = Field(default_factory=dict)


class ScreeningSequenceStepRead(BaseModel):
    order: int
    criterion_id: str
    label: str
    description: str
    evaluated_count: int = 0
    passed_count: int = 0
    excluded_count: int = 0
    review_count: int = 0
    included_count: int = 0
    outcome_counts: dict[str, int] = Field(default_factory=dict)


class SearchRequestSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query_text: str
    expanded_keywords: list[str] = Field(default_factory=list)
    year_from: int
    year_to: int
    include_theses: bool
    include_journal_articles: bool
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)
    status: str
    candidate_count: int
    canonical_candidate_count: int
    decision_count: int
    event_count: int = 0
    latest_event_at: str | None = None
    source_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    full_text_status_counts: dict[str, int] = Field(default_factory=dict)
    source_search_breakdown: list[SearchSourceBreakdownRead] = Field(default_factory=list)
    screening_sequence: list[ScreeningSequenceStepRead] = Field(default_factory=list)
    prisma: PrismaCountsRead | None = None


class SearchRunSourceRead(BaseModel):
    source: str
    label: str
    backend: str
    query_mode: str
    raw_total_hits: int | None = None
    fetched_candidates: int = 0


class SearchRunResult(BaseModel):
    search_request_id: str
    status: str
    collected_candidates: int
    screened_candidates: int
    duplicates_removed: int
    canonical_candidates: int
    source_runs: list[SearchRunSourceRead] = Field(default_factory=list)
