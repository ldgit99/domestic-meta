from app.core.constants import DECISION_EXCLUDE, DECISION_INCLUDE, FULL_TEXT_STAGE, TITLE_ABSTRACT_STAGE
from app.models.domain import EligibilityDecision, PrismaCounts


class PrismaService:
    def recalculate(
        self,
        counts: PrismaCounts,
        collected_count: int,
        duplicates_removed: int,
        decisions: list[EligibilityDecision],
    ) -> PrismaCounts:
        counts.identified_records = collected_count
        counts.duplicate_records_removed = duplicates_removed

        title_abstract = [item for item in decisions if item.stage == TITLE_ABSTRACT_STAGE]
        full_text = [item for item in decisions if item.stage == FULL_TEXT_STAGE]

        counts.records_screened = len(title_abstract)
        counts.records_excluded = len([item for item in title_abstract if item.decision == DECISION_EXCLUDE])
        counts.reports_sought_for_retrieval = len(
            [item for item in title_abstract if item.decision == DECISION_INCLUDE]
        )
        counts.reports_assessed_for_eligibility = len(full_text)
        counts.studies_included_in_review = len(
            [item for item in full_text if item.decision == DECISION_INCLUDE]
        )

        reason_counts: dict[str, int] = {}
        for item in decisions:
            if item.decision != DECISION_EXCLUDE or not item.reason_code:
                continue
            reason_counts[item.reason_code] = reason_counts.get(item.reason_code, 0) + 1

        counts.reports_excluded_with_reasons_json = reason_counts
        counts.reports_not_retrieved = reason_counts.get("full_text_unavailable", 0)
        return counts

    def build_flow(self, search_request_id: str, counts: PrismaCounts) -> dict:
        full_text_excluded = max(
            counts.reports_assessed_for_eligibility - counts.studies_included_in_review,
            0,
        )

        nodes = [
            {
                "id": "identified",
                "label": "Records identified",
                "count": counts.identified_records,
                "stage": "identification",
                "description": "All records returned from source collection before deduplication.",
            },
            {
                "id": "duplicates_removed",
                "label": "Duplicate records removed",
                "count": counts.duplicate_records_removed,
                "stage": "identification",
                "description": "Records merged or removed during canonical deduplication.",
            },
            {
                "id": "screened",
                "label": "Records screened",
                "count": counts.records_screened,
                "stage": "screening",
                "description": "Records evaluated at the title and abstract stage.",
            },
            {
                "id": "title_excluded",
                "label": "Records excluded",
                "count": counts.records_excluded,
                "stage": "screening",
                "description": "Records excluded during title and abstract screening.",
            },
            {
                "id": "reports_sought",
                "label": "Reports sought for retrieval",
                "count": counts.reports_sought_for_retrieval,
                "stage": "retrieval",
                "description": "Studies moved forward for full-text retrieval.",
            },
            {
                "id": "reports_not_retrieved",
                "label": "Reports not retrieved",
                "count": counts.reports_not_retrieved,
                "stage": "retrieval",
                "description": "Studies that could not be retrieved at the full-text stage.",
            },
            {
                "id": "assessed",
                "label": "Reports assessed for eligibility",
                "count": counts.reports_assessed_for_eligibility,
                "stage": "eligibility",
                "description": "Reports reviewed with full-text evidence.",
            },
            {
                "id": "full_text_excluded",
                "label": "Reports excluded with reasons",
                "count": full_text_excluded,
                "stage": "eligibility",
                "description": "Reports excluded after full-text eligibility assessment.",
            },
            {
                "id": "included",
                "label": "Studies included in review",
                "count": counts.studies_included_in_review,
                "stage": "included",
                "description": "Final studies retained for synthesis or extraction.",
            },
        ]

        edges = [
            {
                "source": "identified",
                "target": "duplicates_removed",
                "count": counts.duplicate_records_removed,
                "label": "removed as duplicates",
            },
            {
                "source": "identified",
                "target": "screened",
                "count": counts.records_screened,
                "label": "moved to screening",
            },
            {
                "source": "screened",
                "target": "title_excluded",
                "count": counts.records_excluded,
                "label": "excluded at title or abstract",
            },
            {
                "source": "screened",
                "target": "reports_sought",
                "count": counts.reports_sought_for_retrieval,
                "label": "sent to full-text retrieval",
            },
            {
                "source": "reports_sought",
                "target": "reports_not_retrieved",
                "count": counts.reports_not_retrieved,
                "label": "not retrieved",
            },
            {
                "source": "reports_sought",
                "target": "assessed",
                "count": counts.reports_assessed_for_eligibility,
                "label": "assessed for eligibility",
            },
            {
                "source": "assessed",
                "target": "full_text_excluded",
                "count": full_text_excluded,
                "label": "excluded with reasons",
            },
            {
                "source": "assessed",
                "target": "included",
                "count": counts.studies_included_in_review,
                "label": "included in review",
            },
        ]

        exclusion_reasons = [
            {"reason_code": key, "count": value}
            for key, value in sorted(
                counts.reports_excluded_with_reasons_json.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        return {
            "search_request_id": search_request_id,
            "nodes": nodes,
            "edges": edges,
            "exclusion_reasons": exclusion_reasons,
        }
