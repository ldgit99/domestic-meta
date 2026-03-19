from pydantic import BaseModel, Field


class PrismaCountsRead(BaseModel):
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
