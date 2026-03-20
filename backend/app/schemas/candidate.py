from typing import Any

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
    text_extraction_status: str | None = None
    stored_path: str | None = None


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


class ExtractionRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    extraction_result_id: str
    candidate_id: str
    search_request_id: str
    revision_index: int
    status: str
    message: str
    fields_json: dict = Field(default_factory=dict)
    model_name: str | None = None
    raw_response: dict = Field(default_factory=dict)
    created_at: str | None = None


class ExtractionDiffEntryRead(BaseModel):
    field_path: str
    change_type: str
    current_value: Any | None = None
    revision_value: Any | None = None


class ExtractionRevisionComparisonRead(BaseModel):
    candidate_id: str
    current_extraction_id: str
    revision_id: str
    revision_index: int
    changed_field_count: int
    differences: list[ExtractionDiffEntryRead] = Field(default_factory=list)


class ExtractionResultUpdate(BaseModel):
    fields_json: dict = Field(default_factory=dict)
    status: str = Field(default="manual_override")
    message: str = Field(default="Manual extraction override saved.")
    reviewed_by: str = Field(default="human")
    notes: str | None = None


class ExtractionRevisionRestoreCreate(BaseModel):
    status: str = Field(default="manual_override")
    message: str | None = None
    reviewed_by: str = Field(default="human")
    notes: str | None = None


class OCRRunRead(BaseModel):
    candidate_id: str
    status: str
    message: str
    full_text_artifact: FullTextArtifactRead | None = None


class EffectSizeComputedRead(BaseModel):
    metric: str
    value: float
    variance: float | None = None


class EffectSizeSummaryRead(BaseModel):
    is_computable: bool = False
    recommended_effect_type: str | None = None
    computation_method: str | None = None
    computed_effect_size: EffectSizeComputedRead | None = None
    available_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)


class QualityAssessmentRead(BaseModel):
    score: str = "low"
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    group_sample_size_total_matches: bool | None = None
    critical_fields_present: list[str] = Field(default_factory=list)
    critical_fields_missing: list[str] = Field(default_factory=list)


class CandidateDetailRead(BaseModel):
    candidate: CandidateRead
    latest_title_abstract_decision: EligibilityDecisionRead | None = None
    latest_full_text_decision: EligibilityDecisionRead | None = None
    full_text_artifact: FullTextArtifactRead | None = None
    extraction_result: ExtractionResultRead | None = None
    effect_size_summary: EffectSizeSummaryRead = Field(default_factory=EffectSizeSummaryRead)
    quality_assessment: QualityAssessmentRead = Field(default_factory=QualityAssessmentRead)
    needs_manual_review: bool = False
    review_priority: str = "low"
    review_reasons: list[str] = Field(default_factory=list)


class CandidateQueueItemRead(BaseModel):
    candidate: CandidateRead
    latest_decision: EligibilityDecisionRead | None = None
    full_text_status: str | None = None
    extraction_status: str | None = None
    effect_size_summary: EffectSizeSummaryRead = Field(default_factory=EffectSizeSummaryRead)
    quality_assessment: QualityAssessmentRead = Field(default_factory=QualityAssessmentRead)
    review_priority: str
    review_reasons: list[str] = Field(default_factory=list)
