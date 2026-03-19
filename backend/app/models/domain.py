from dataclasses import dataclass, field


@dataclass
class SearchRequest:
    id: str
    query_text: str
    expanded_keywords: list[str]
    year_from: int
    year_to: int
    include_theses: bool
    include_journal_articles: bool
    inclusion_rules: list[str]
    exclusion_rules: list[str]
    status: str
    created_at: str


@dataclass
class CandidateRecord:
    id: str
    search_request_id: str
    source: str
    source_record_id: str
    title: str
    authors: list[str]
    year: int
    journal_or_school: str
    abstract: str
    keywords: list[str]
    doi: str | None
    url: str | None
    document_type: str
    language: str
    raw_payload: dict
    status: str
    duplicate_group_id: str | None = None
    canonical_record_id: str | None = None


@dataclass
class EligibilityDecision:
    id: str
    candidate_record_id: str
    stage: str
    decision: str
    reason_code: str | None
    reason_text: str | None
    confidence: str
    reviewed_by: str
    created_at: str


@dataclass
class PrismaCounts:
    id: str
    search_request_id: str
    identified_records: int = 0
    duplicate_records_removed: int = 0
    records_screened: int = 0
    records_excluded: int = 0
    reports_sought_for_retrieval: int = 0
    reports_not_retrieved: int = 0
    reports_assessed_for_eligibility: int = 0
    reports_excluded_with_reasons_json: dict[str, int] = field(default_factory=dict)
    studies_included_in_review: int = 0
