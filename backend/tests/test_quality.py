from app.services.quality import QualityAssessmentService


service = QualityAssessmentService()


def test_quality_assessment_returns_high_for_well_evidenced_complete_inputs() -> None:
    result = service.assess(
        {
            "study_design": "group_comparison",
            "participants": {
                "sample_size_total": "120",
                "groups": [
                    {"name": "intervention", "n": "60", "mean": "82.4", "sd": "10.1"},
                    {"name": "control", "n": "60", "mean": "75.2", "sd": "11.3"},
                ],
            },
            "outcomes": ["achievement"],
            "statistics": [],
            "effect_size_inputs": {
                "is_meta_analytic_ready": True,
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
            },
            "evidence_spans": [
                {"field": "participants.sample_size_total", "evidence_text": "N=120", "location": "heuristic"},
                {"field": "participants.groups.intervention", "evidence_text": "n=60 mean=82.4 sd=10.1", "location": "heuristic"},
                {"field": "participants.groups.control", "evidence_text": "n=60 mean=75.2 sd=11.3", "location": "heuristic"},
                {"field": "outcomes.0", "evidence_text": "achievement", "location": "heuristic"},
            ],
            "confidence": "high",
        }
    )

    assert result["score"] == "high"
    assert result["warnings"] == []
    assert result["group_sample_size_total_matches"] is True
    assert result["evidence_count"] == 4


def test_quality_assessment_returns_low_for_mismatch_and_missing_evidence() -> None:
    result = service.assess(
        {
            "study_design": "group_comparison",
            "participants": {
                "sample_size_total": "100",
                "groups": [
                    {"name": "intervention", "n": "60", "mean": "82.4", "sd": "10.1"},
                    {"name": "control", "n": "60", "mean": "75.2", "sd": "11.3"},
                ],
            },
            "outcomes": ["achievement"],
            "statistics": [],
            "effect_size_inputs": {
                "is_meta_analytic_ready": True,
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
            },
            "evidence_spans": [
                {"field": "participants.sample_size_total", "evidence_text": "N=100", "location": "heuristic"}
            ],
            "confidence": "low",
        }
    )

    assert result["score"] == "low"
    assert "sample_size_mismatch" in result["warnings"]
    assert "low_confidence_extraction" in result["warnings"]
    assert "evidence_coverage_low" in result["warnings"]
    assert result["group_sample_size_total_matches"] is False