from pydantic import BaseModel, ConfigDict, Field


class PrismaCountsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    search_request_id: str
    identified_records: int
    duplicate_records_removed: int
    records_screened: int
    records_excluded: int
    reports_sought_for_retrieval: int
    reports_not_retrieved: int
    reports_assessed_for_eligibility: int
    reports_excluded_with_reasons_json: dict[str, int] = Field(default_factory=dict)
    studies_included_in_review: int


class ExportPayloadRead(BaseModel):
    search_request_id: str
    content_type: str
    file_name: str
    content: str
