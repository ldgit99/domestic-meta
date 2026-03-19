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
            [item for item in title_abstract if item.decision in {DECISION_INCLUDE}]
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
