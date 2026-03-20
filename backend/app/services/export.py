import json

from app.core.constants import FULL_TEXT_STAGE, TITLE_ABSTRACT_STAGE
from app.models.domain import (
    CandidateRecord,
    EligibilityDecision,
    ExtractionResult,
    ExtractionRevision,
    FullTextArtifact,
    PipelineEvent,
    PrismaCounts,
    SearchRequest,
)
from app.services.effect_size import EffectSizeService
from app.services.prisma import PrismaService
from app.services.quality import QualityAssessmentService


class ExportService:
    def __init__(self) -> None:
        self.effect_sizes = EffectSizeService()
        self.prisma = PrismaService()
        self.quality = QualityAssessmentService()

    def candidates_csv(self, search_request_id: str, candidates: list[CandidateRecord]) -> dict:
        lines = [
            "id,source,document_type,title,authors,year,journal_or_school,status,doi,url,keywords,canonical_record_id,duplicate_group_id"
        ]
        for item in candidates:
            lines.append(
                self._csv_line(
                    [
                        item.id,
                        item.source,
                        item.document_type,
                        item.title,
                        "|".join(item.authors),
                        item.year,
                        item.journal_or_school,
                        item.status,
                        item.doi or "",
                        item.url or "",
                        "|".join(item.keywords),
                        item.canonical_record_id or "",
                        item.duplicate_group_id or "",
                    ]
                )
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
        candidates: list[CandidateRecord],
        decisions: list[EligibilityDecision],
    ) -> dict:
        candidate_map = {item.id: item for item in candidates}
        payload = []
        for item in sorted(decisions, key=lambda decision: (decision.created_at, decision.stage, decision.id)):
            candidate = candidate_map.get(item.candidate_record_id)
            payload.append(
                {
                    "id": item.id,
                    "candidate_record_id": item.candidate_record_id,
                    "candidate_title": candidate.title if candidate else None,
                    "candidate_source": candidate.source if candidate else None,
                    "candidate_year": candidate.year if candidate else None,
                    "candidate_document_type": candidate.document_type if candidate else None,
                    "candidate_status": candidate.status if candidate else None,
                    "stage": item.stage,
                    "decision": item.decision,
                    "reason_code": item.reason_code,
                    "reason_text": item.reason_text,
                    "confidence": item.confidence,
                    "reviewed_by": item.reviewed_by,
                    "created_at": item.created_at,
                }
            )
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_screening_log.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    def search_request_manifest_json(
        self,
        search_request: SearchRequest,
        counts: PrismaCounts,
        candidates: list[CandidateRecord],
        decisions: list[EligibilityDecision],
        results: list[ExtractionResult],
        revisions: list[ExtractionRevision],
        artifacts: list[FullTextArtifact],
        events: list[PipelineEvent],
    ) -> dict:
        payload = {
            "search_request": {
                "id": search_request.id,
                "query_text": search_request.query_text,
                "expanded_keywords": search_request.expanded_keywords,
                "year_from": search_request.year_from,
                "year_to": search_request.year_to,
                "include_theses": search_request.include_theses,
                "include_journal_articles": search_request.include_journal_articles,
                "inclusion_rules": search_request.inclusion_rules,
                "exclusion_rules": search_request.exclusion_rules,
                "status": search_request.status,
                "created_at": search_request.created_at,
            },
            "summary": {
                "candidate_count": len(candidates),
                "canonical_candidate_count": len(
                    [item for item in candidates if item.canonical_record_id in {None, item.id}]
                ),
                "decision_count": len(decisions),
                "extraction_count": len(results),
                "extraction_revision_count": len(revisions),
                "event_count": len(events),
                "latest_event_at": events[0].created_at if events else None,
                "source_counts": self._source_counts(candidates),
                "status_counts": self._status_counts(candidates),
                "full_text_status_counts": self._full_text_status_counts(artifacts),
                "quality_score_counts": self._quality_score_counts(results),
            },
            "prisma_counts": {
                "identified_records": counts.identified_records,
                "duplicate_records_removed": counts.duplicate_records_removed,
                "records_screened": counts.records_screened,
                "records_excluded": counts.records_excluded,
                "reports_sought_for_retrieval": counts.reports_sought_for_retrieval,
                "reports_not_retrieved": counts.reports_not_retrieved,
                "reports_assessed_for_eligibility": counts.reports_assessed_for_eligibility,
                "reports_excluded_with_reasons_json": counts.reports_excluded_with_reasons_json,
                "studies_included_in_review": counts.studies_included_in_review,
            },
            "prisma_flow": self.prisma.build_flow(search_request.id, counts),
        }
        return {
            "search_request_id": search_request.id,
            "content_type": "application/json",
            "file_name": f"{search_request.id}_search_request.json",
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

    def prisma_flow_json(self, search_request_id: str, counts: PrismaCounts) -> dict:
        payload = self.prisma.build_flow(search_request_id, counts)
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_prisma_flow.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    def events_json(
        self,
        search_request_id: str,
        events: list[PipelineEvent],
    ) -> dict:
        payload = [
            {
                "id": item.id,
                "search_request_id": item.search_request_id,
                "event_type": item.event_type,
                "status": item.status,
                "message": item.message,
                "stage": item.stage,
                "candidate_id": item.candidate_id,
                "metadata_json": item.metadata_json,
                "created_at": item.created_at,
            }
            for item in sorted(events, key=lambda event: (event.created_at, event.id))
        ]
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_events.json",
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

    def extraction_revisions_json(
        self,
        search_request_id: str,
        revisions: list[ExtractionRevision],
    ) -> dict:
        payload = [
            {
                "id": item.id,
                "extraction_result_id": item.extraction_result_id,
                "candidate_id": item.candidate_id,
                "search_request_id": item.search_request_id,
                "revision_index": item.revision_index,
                "status": item.status,
                "message": item.message,
                "fields_json": item.fields_json,
                "model_name": item.model_name,
                "raw_response": item.raw_response,
                "created_at": item.created_at,
            }
            for item in revisions
        ]
        return {
            "search_request_id": search_request_id,
            "content_type": "application/json",
            "file_name": f"{search_request_id}_extraction_revisions.json",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    def meta_analysis_ready_csv(
        self,
        search_request_id: str,
        candidates: list[CandidateRecord],
        decisions: list[EligibilityDecision],
        results: list[ExtractionResult],
    ) -> dict:
        result_map = {item.candidate_id: item for item in results}
        latest_decision_map = self._latest_decision_map(decisions)
        lines = [
            "candidate_id,source,document_type,title,year,latest_decision_stage,latest_decision,study_design,is_meta_analytic_ready,recommended_effect_type,computation_method,computed_metric,computed_value,computed_variance,sample_size_total,intervention_or_predictor,comparison,confidence,status,qa_score,qa_warnings,qa_evidence_count,missing_inputs,review_flags"
        ]
        for candidate in candidates:
            result = result_map.get(candidate.id)
            if result is None:
                continue

            latest_decision = latest_decision_map.get(candidate.id)
            fields = result.fields_json or {}
            participants = fields.get("participants", {})
            effect = fields.get("effect_size_inputs", {})
            summary = self.effect_sizes.summarize(fields)
            computed = summary.get("computed_effect_size") or {}
            quality = self._quality_payload(fields)
            lines.append(
                self._csv_line(
                    [
                        candidate.id,
                        candidate.source,
                        candidate.document_type,
                        candidate.title,
                        candidate.year,
                        latest_decision.stage if latest_decision else "",
                        latest_decision.decision if latest_decision else "",
                        fields.get("study_design", ""),
                        effect.get("is_meta_analytic_ready", False),
                        summary.get("recommended_effect_type") or "",
                        summary.get("computation_method") or "",
                        computed.get("metric", ""),
                        computed.get("value", ""),
                        computed.get("variance", ""),
                        participants.get("sample_size_total", ""),
                        fields.get("intervention_or_predictor", ""),
                        fields.get("comparison", ""),
                        fields.get("confidence", ""),
                        result.status,
                        quality.get("score", ""),
                        "|".join(quality.get("warnings") or []),
                        quality.get("evidence_count", 0),
                        "|".join(summary.get("missing_inputs", [])),
                        "|".join(summary.get("review_flags", [])),
                    ]
                )
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
        revisions: list[ExtractionRevision],
        artifacts: list[FullTextArtifact],
        events: list[PipelineEvent],
    ) -> dict:
        result_map = {item.candidate_id: item for item in results}
        artifact_map = {item.candidate_record_id: item for item in artifacts}
        title_decision_map = self._latest_decision_map(decisions, stage=TITLE_ABSTRACT_STAGE)
        full_text_decision_map = self._latest_decision_map(decisions, stage=FULL_TEXT_STAGE)
        lines = [
            f"# Audit Report: {search_request.query_text}",
            "",
            "## Search Criteria",
            "",
            f"- Search Request ID: `{search_request.id}`",
            f"- Status: `{search_request.status}`",
            f"- Created At: `{search_request.created_at}`",
            f"- Query Text: `{search_request.query_text}`",
            f"- Expanded Keywords: {', '.join(search_request.expanded_keywords) if search_request.expanded_keywords else 'None'}",
            f"- Year Range: {search_request.year_from} to {search_request.year_to}",
            f"- Include Theses: `{search_request.include_theses}`",
            f"- Include Journal Articles: `{search_request.include_journal_articles}`",
            f"- Inclusion Rules: {', '.join(search_request.inclusion_rules) if search_request.inclusion_rules else 'None'}",
            f"- Exclusion Rules: {', '.join(search_request.exclusion_rules) if search_request.exclusion_rules else 'None'}",
            "",
            "## Search Inventory",
            "",
            f"- Candidate count: {len(candidates)}",
            f"- Canonical candidate count: {len([item for item in candidates if item.canonical_record_id in {None, item.id}])}",
            f"- Decision count: {len(decisions)}",
            f"- Extraction count: {len(results)}",
            f"- Extraction revision count: {len(revisions)}",
            f"- Event count: {len(events)}",
            f"- Latest event at: {events[0].created_at if events else 'None'}",
            f"- Source counts: {self._format_mapping(self._source_counts(candidates))}",
            f"- Status counts: {self._format_mapping(self._status_counts(candidates))}",
            f"- Full-text status counts: {self._format_mapping(self._full_text_status_counts(artifacts))}",
            f"- Quality score counts: {self._format_mapping(self._quality_score_counts(results))}",
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
            "| Candidate | Source | Year | Status | FT Text Status | TA Decision | FT Decision | Extraction | Effect | QA Score | Revisions | QA Warnings | Review Flags |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]

        revision_counts = self._revision_counts(revisions)
        for candidate in candidates:
            extraction = result_map.get(candidate.id)
            artifact = artifact_map.get(candidate.id)
            fields = extraction.fields_json if extraction else None
            summary = self.effect_sizes.summarize(fields)
            quality = self._quality_payload(fields)
            computed = summary.get("computed_effect_size") or {}
            effect_label = ""
            if computed:
                effect_label = f"{computed.get('metric')}={computed.get('value')}"
            elif summary.get("recommended_effect_type"):
                effect_label = str(summary.get("recommended_effect_type"))

            lines.append(
                f"| {candidate.title} | {candidate.source} | {candidate.year} | {candidate.status} | {artifact.text_extraction_status if artifact else ''} | {title_decision_map.get(candidate.id).decision if title_decision_map.get(candidate.id) else ''} | {full_text_decision_map.get(candidate.id).decision if full_text_decision_map.get(candidate.id) else ''} | {extraction.status if extraction else ''} | {effect_label} | {quality.get('score', '')} | {revision_counts.get(candidate.id, 0)} | {'; '.join(quality.get('warnings') or [])} | {'; '.join(summary.get('review_flags', []))} |"
            )

        lines.extend(["", "## Recent Activity", ""])
        if events:
            for item in sorted(events, key=lambda event: (event.created_at, event.id), reverse=True)[:10]:
                candidate_label = f" candidate={item.candidate_id}" if item.candidate_id else ""
                lines.append(
                    f"- {item.created_at} | {item.status} | {item.event_type}{candidate_label} | {item.message}"
                )
        else:
            lines.append("- None")

        lines.extend(["", "## Exclusion Reasons", ""])
        if counts.reports_excluded_with_reasons_json:
            for key, value in sorted(
                counts.reports_excluded_with_reasons_json.items(),
                key=lambda item: (-item[1], item[0]),
            ):
                lines.append(f"- `{key}`: {value}")
        else:
            lines.append("- None")

        return {
            "search_request_id": search_request.id,
            "content_type": "text/markdown",
            "file_name": f"{search_request.id}_audit_report.md",
            "content": "\n".join(lines),
        }

    def _source_counts(self, candidates: list[CandidateRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.source] = counts.get(candidate.source, 0) + 1
        return counts

    def _status_counts(self, candidates: list[CandidateRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return counts

    def _full_text_status_counts(self, artifacts: list[FullTextArtifact]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for artifact in artifacts:
            counts[artifact.text_extraction_status] = counts.get(artifact.text_extraction_status, 0) + 1
        return counts

    def _quality_score_counts(self, results: list[ExtractionResult]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in results:
            quality = self._quality_payload(result.fields_json)
            score = str(quality.get("score") or "unknown")
            counts[score] = counts.get(score, 0) + 1
        return counts

    def _revision_counts(self, revisions: list[ExtractionRevision]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for revision in revisions:
            counts[revision.candidate_id] = counts.get(revision.candidate_id, 0) + 1
        return counts

    def _quality_payload(self, fields: dict | None) -> dict:
        payload = fields or {}
        existing = payload.get("quality_assessment")
        if isinstance(existing, dict) and existing.get("score"):
            return existing
        return self.quality.assess(payload)

    def _latest_decision_map(
        self,
        decisions: list[EligibilityDecision],
        stage: str | None = None,
    ) -> dict[str, EligibilityDecision]:
        output: dict[str, EligibilityDecision] = {}
        for item in sorted(decisions, key=lambda decision: (decision.created_at, decision.id)):
            if stage is not None and item.stage != stage:
                continue
            output[item.candidate_record_id] = item
        return output

    def _format_mapping(self, values: dict[str, int]) -> str:
        if not values:
            return "None"
        return ", ".join(f"{key}={value}" for key, value in sorted(values.items()))

    def _csv_line(self, values: list[object]) -> str:
        return ",".join(self._csv_value(value) for value in values)

    def _csv_value(self, value: object) -> str:
        text = "" if value is None else str(value)
        return f'"{text.replace(chr(34), chr(39))}"'
