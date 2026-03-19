from app.models.domain import CandidateRecord, EligibilityDecision, ExtractionResult, PrismaCounts, SearchRequest
from app.services.export import ExportService


def test_audit_report_contains_prisma_and_candidate_rows() -> None:
    search_request = SearchRequest(
        id="s1",
        query_text="협동학습",
        expanded_keywords=[],
        year_from=2010,
        year_to=2026,
        include_theses=True,
        include_journal_articles=True,
        inclusion_rules=[],
        exclusion_rules=[],
        status="completed",
        created_at="now",
    )
    counts = PrismaCounts(id="p1", search_request_id="s1", identified_records=3, records_screened=2)
    candidate = CandidateRecord(
        id="c1",
        search_request_id="s1",
        source="kci",
        source_record_id="k1",
        title="협동학습이 학업성취도에 미치는 효과",
        authors=["홍길동"],
        year=2024,
        journal_or_school="교육연구",
        abstract="",
        keywords=["협동학습"],
        doi=None,
        url=None,
        document_type="journal_article",
        language="ko",
        raw_payload={},
        status="extracted",
    )
    decision = EligibilityDecision(
        id="d1",
        candidate_record_id="c1",
        stage="title_abstract",
        decision="include",
        reason_code=None,
        reason_text=None,
        confidence="medium",
        reviewed_by="agent",
        created_at="now",
    )
    extraction = ExtractionResult(
        id="e1",
        candidate_id="c1",
        status="completed",
        message="ok",
        fields_json={},
        model_name=None,
        raw_response={},
        created_at="now",
    )

    payload = ExportService().audit_report_markdown(search_request, counts, [candidate], [decision], [extraction])

    assert "# Audit Report: 협동학습" in payload["content"]
    assert "Identified records: 3" in payload["content"]
    assert "협동학습이 학업성취도에 미치는 효과" in payload["content"]
