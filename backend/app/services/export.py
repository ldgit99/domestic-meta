import json

from app.models.domain import CandidateRecord, EligibilityDecision, ExtractionResult, PrismaCounts, SearchRequest


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

    def extraction_results_json(
        self,
        search_request_id: str,
        results: list[ExtractionResult],
    ) -> dict:
        payload = [
            {
                "id": item.id,
                "candidate_id": item.candidate_id,
                "status": item.status,
                "message": item.message,
                "fields_json": item.fields_json,
                "model_name": item.model_name,
                "created_at": item.created_at,
            }
            for item in results
        ]
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_extraction_results.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    def meta_analysis_ready_csv(
        self,
        search_request_id: str,
        candidates: list[CandidateRecord],
        results: list[ExtractionResult],
    ) -> dict:
        result_map = {item.candidate_id: item for item in results}
        lines = [
            "candidate_id,title,year,study_design,is_meta_analytic_ready,sample_size_total,intervention_or_predictor,comparison,confidence,status"
        ]
        for candidate in candidates:
            result = result_map.get(candidate.id)
            if result is None:
                continue
            fields = result.fields_json or {}
            participants = fields.get("participants", {})
            effect = fields.get("effect_size_inputs", {})
            title = candidate.title.replace('"', "'")
            intervention = str(fields.get("intervention_or_predictor", "")).replace('"', "'")
            comparison = str(fields.get("comparison", "")).replace('"', "'")
            lines.append(
                f'{candidate.id},"{title}",{candidate.year},{fields.get("study_design","")},{effect.get("is_meta_analytic_ready", False)},{participants.get("sample_size_total","")},"{intervention}","{comparison}",{fields.get("confidence","")},{result.status}'
            )

        return {
            "search_request_id": search_request_id,
            "content_type": "text/csv",
            "file_name": f"{search_request_id}_meta_analysis_ready.csv",
            "content": "\n".join(lines),
        }

    def audit_report_markdown(
        self,
        search_request: SearchRequest,
        counts: PrismaCounts,
        candidates: list[CandidateRecord],
        decisions: list[EligibilityDecision],
        results: list[ExtractionResult],
    ) -> dict:
        result_map = {item.candidate_id: item for item in results}
        decision_map = {item.candidate_record_id: item for item in decisions}
        lines = [
            f"# Audit Report: {search_request.query_text}",
            "",
            f"- Search Request ID: `{search_request.id}`",
            f"- Status: `{search_request.status}`",
            f"- Created At: `{search_request.created_at}`",
            "",
            "## PRISMA Summary",
            "",
            f"- Identified records: {counts.identified_records}",
            f"- Duplicate records removed: {counts.duplicate_records_removed}",
            f"- Records screened: {counts.records_screened}",
            f"- Records excluded: {counts.records_excluded}",
            f"- Reports sought for retrieval: {counts.reports_sought_for_retrieval}",
            f"- Reports not retrieved: {counts.reports_not_retrieved}",
            f"- Reports assessed for eligibility: {counts.reports_assessed_for_eligibility}",
            f"- Studies included in review: {counts.studies_included_in_review}",
            "",
            "## Candidate Snapshot",
            "",
            "| Candidate | Source | Status | Decision | Extraction |",
            "| --- | --- | --- | --- | --- |",
        ]

        for candidate in candidates:
            decision = decision_map.get(candidate.id)
            extraction = result_map.get(candidate.id)
            lines.append(
                f"| {candidate.title} | {candidate.source} | {candidate.status} | {decision.decision if decision else ''} | {extraction.status if extraction else ''} |"
            )

        lines.extend(["", "## Exclusion Reasons", ""])
        if counts.reports_excluded_with_reasons_json:
            for key, value in counts.reports_excluded_with_reasons_json.items():
                lines.append(f"- `{key}`: {value}")
        else:
            lines.append("- 없음")

        return {
            "search_request_id": search_request.id,
            "content_type": "text/markdown",
            "file_name": f"{search_request.id}_audit_report.md",
            "content": "\n".join(lines),
        }
