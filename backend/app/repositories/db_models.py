from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SearchRequestModel(Base):
    __tablename__ = "search_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    query_text: Mapped[str] = mapped_column(Text)
    expanded_keywords: Mapped[list] = mapped_column(JSON, default=list)
    year_from: Mapped[int] = mapped_column(Integer)
    year_to: Mapped[int] = mapped_column(Integer)
    include_theses: Mapped[bool] = mapped_column(Boolean, default=True)
    include_journal_articles: Mapped[bool] = mapped_column(Boolean, default=True)
    inclusion_rules: Mapped[list] = mapped_column(JSON, default=list)
    exclusion_rules: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String(64))


class CandidateRecordModel(Base):
    __tablename__ = "candidate_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_request_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(32))
    source_record_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    year: Mapped[int] = mapped_column(Integer)
    journal_or_school: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64))
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EligibilityDecisionModel(Base):
    __tablename__ = "eligibility_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_record_id: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32))
    reviewed_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(64))


class PrismaCountsModel(Base):
    __tablename__ = "prisma_counts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    identified_records: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records_removed: Mapped[int] = mapped_column(Integer, default=0)
    records_screened: Mapped[int] = mapped_column(Integer, default=0)
    records_excluded: Mapped[int] = mapped_column(Integer, default=0)
    reports_sought_for_retrieval: Mapped[int] = mapped_column(Integer, default=0)
    reports_not_retrieved: Mapped[int] = mapped_column(Integer, default=0)
    reports_assessed_for_eligibility: Mapped[int] = mapped_column(Integer, default=0)
    reports_excluded_with_reasons_json: Mapped[dict] = mapped_column(JSON, default=dict)
    studies_included_in_review: Mapped[int] = mapped_column(Integer, default=0)


class PipelineEventModel(Base):
    __tablename__ = "pipeline_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_request_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    candidate_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(64))


class FullTextArtifactModel(Base):
    __tablename__ = "full_text_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_record_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    text_content: Mapped[str] = mapped_column(Text)
    text_extraction_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String(64))
    stored_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExtractionResultModel(Base):
    __tablename__ = "extraction_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    fields_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ExtractionRevisionModel(Base):
    __tablename__ = "extraction_revisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    extraction_result_id: Mapped[str] = mapped_column(String(64), index=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True)
    search_request_id: Mapped[str] = mapped_column(String(64), index=True)
    revision_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    fields_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
