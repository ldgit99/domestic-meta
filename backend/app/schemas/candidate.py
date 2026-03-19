from pydantic import BaseModel, Field


class CandidateRead(BaseModel):
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
    id: str
    candidate_record_id: str
    created_at: str
