from pydantic import BaseModel, ConfigDict, Field


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class DecisionCreate(BaseModel):
    stage: str
    decision: str
    reason_code: str | None = None
    reason_text: str | None = None
    confidence: str = Field(default="medium")
    reviewed_by: str = Field(default="human")


class EligibilityDecisionRead(DecisionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_record_id: str
    created_at: str


class FullTextArtifactCreate(BaseModel):
    file_name: str
    source_url: str | None = None
    mime_type: str = "application/pdf"
    text_content: str = ""


class FullTextArtifactRead(FullTextArtifactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_record_id: str
    text_extraction_status: str
    created_at: str


class ExtractionResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    candidate_id: str
    status: str
    message: str
    fields_json: dict = Field(default_factory=dict)
    model_name: str | None = None
    created_at: str | None = None
