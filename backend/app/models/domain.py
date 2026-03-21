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


@dataclass
class PipelineEvent:
    id: str
    search_request_id: str
    event_type: str
    status: str
    message: str
    stage: str | None
    candidate_id: str | None
    metadata_json: dict = field(default_factory=dict)
    created_at: str = ""


@dataclass
class FullTextArtifact:
    id: str
    candidate_record_id: str
    file_name: str
    source_url: str | None
    mime_type: str
    text_content: str
    text_extraction_status: str
    created_at: str
    stored_path: str | None = None


@dataclass
class ExtractionResult:
    id: str
    candidate_id: str
    status: str
    message: str
    fields_json: dict
    model_name: str | None
    raw_response: dict = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class ExtractionRevision:
    id: str
    extraction_result_id: str
    candidate_id: str
    search_request_id: str
    revision_index: int
    status: str
    message: str
    fields_json: dict
    model_name: str | None
    raw_response: dict = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class SourceCollectionResult:
    source: str
    backend: str
    query_mode: str
    query_plan: dict
    total_hits: int | None = None
    candidates: list[CandidateRecord] = field(default_factory=list)

