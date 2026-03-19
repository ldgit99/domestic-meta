from app.models.domain import EligibilityDecision, PrismaCounts
from app.services.prisma import PrismaService


def test_prisma_recalculate_counts() -> None:
    service = PrismaService()
    counts = PrismaCounts(id="p1", search_request_id="s1")
    decisions = [
        EligibilityDecision(
            id="d1",
            candidate_record_id="c1",
            stage="title_abstract",
            decision="include",
            reason_code=None,
            reason_text=None,
            confidence="medium",
            reviewed_by="agent",
            created_at="now",
        ),
        EligibilityDecision(
            id="d2",
            candidate_record_id="c2",
            stage="title_abstract",
            decision="exclude",
            reason_code="not_quantitative",
            reason_text="x",
            confidence="high",
            reviewed_by="agent",
            created_at="now",
        ),
    ]

    result = service.recalculate(counts, collected_count=3, duplicates_removed=1, decisions=decisions)

    assert result.identified_records == 3
    assert result.duplicate_records_removed == 1
    assert result.records_screened == 2
    assert result.records_excluded == 1
    assert result.reports_sought_for_retrieval == 1
    assert result.reports_excluded_with_reasons_json["not_quantitative"] == 1
