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
    source_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    prisma: PrismaCountsRead | None = None


class SearchRunResult(BaseModel):
    search_request_id: str
    status: str
    collected_candidates: int
    screened_candidates: int
    duplicates_removed: int
