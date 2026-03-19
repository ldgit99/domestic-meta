from app.models.domain import PrismaCounts
from app.services.export import ExportService
from app.services.prisma import PrismaService


def test_prisma_flow_contains_expected_nodes_and_edges() -> None:
    counts = PrismaCounts(
        id="p1",
        search_request_id="s1",
        identified_records=20,
        duplicate_records_removed=4,
        records_screened=16,
        records_excluded=9,
        reports_sought_for_retrieval=7,
        reports_not_retrieved=1,
        reports_assessed_for_eligibility=6,
        reports_excluded_with_reasons_json={"not_quantitative": 5, "full_text_unavailable": 1},
        studies_included_in_review=3,
    )

    payload = PrismaService().build_flow("s1", counts)

    assert payload["search_request_id"] == "s1"
    assert any(node["id"] == "identified" and node["count"] == 20 for node in payload["nodes"])
    assert any(edge["source"] == "screened" and edge["target"] == "reports_sought" for edge in payload["edges"])
    assert any(reason["reason_code"] == "not_quantitative" for reason in payload["exclusion_reasons"])


def test_prisma_flow_export_returns_json_content() -> None:
    counts = PrismaCounts(
        id="p1",
        search_request_id="s1",
        identified_records=10,
        duplicate_records_removed=2,
        records_screened=8,
        records_excluded=3,
        reports_sought_for_retrieval=5,
        reports_not_retrieved=1,
        reports_assessed_for_eligibility=4,
        reports_excluded_with_reasons_json={"full_text_unavailable": 1},
        studies_included_in_review=2,
    )

    payload = ExportService().prisma_flow_json("s1", counts)

    assert payload["content_type"] == "application/json"
    assert "duplicates_removed" in payload["content"]
    assert "reports_sought" in payload["content"]
