import json

from app.models.domain import CandidateRecord, EligibilityDecision, PrismaCounts


class ExportService:
    def candidates_csv(self, search_request_id: str, candidates: list[CandidateRecord]) -> dict:
        lines = [
            "id,source,title,year,document_type,status,canonical_record_id,duplicate_group_id"
        ]
        for item in candidates:
            title = item.title.replace('"', "'")
            lines.append(
                f'{item.id},{item.source},"{title}",{item.year},{item.document_type},{item.status},{item.canonical_record_id or ""},{item.duplicate_group_id or ""}'
            )

        return {
            "search_request_id": search_request_id,
            "content_type": "text/csv",
            "file_name": f"{search_request_id}_candidates.csv",
            "content": "\n".join(lines),
        }

    def screening_log_json(
        self,
        search_request_id: str,
        decisions: list[EligibilityDecision],
    ) -> dict:
        payload = [
            {
                "id": item.id,
                "candidate_record_id": item.candidate_record_id,
                "stage": item.stage,
                "decision": item.decision,
                "reason_code": item.reason_code,
                "reason_text": item.reason_text,
                "confidence": item.confidence,
                "reviewed_by": item.reviewed_by,
                "created_at": item.created_at,
            }
            for item in decisions
        ]
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_screening_log.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    def prisma_json(self, search_request_id: str, counts: PrismaCounts) -> dict:
        payload = {
            "id": counts.id,
            "search_request_id": counts.search_request_id,
            "identified_records": counts.identified_records,
            "duplicate_records_removed": counts.duplicate_records_removed,
            "records_screened": counts.records_screened,
            "records_excluded": counts.records_excluded,
            "reports_sought_for_retrieval": counts.reports_sought_for_retrieval,
            "reports_not_retrieved": counts.reports_not_retrieved,
            "reports_assessed_for_eligibility": counts.reports_assessed_for_eligibility,
            "reports_excluded_with_reasons_json": counts.reports_excluded_with_reasons_json,
            "studies_included_in_review": counts.studies_included_in_review,
        }
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_prisma_counts.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }
