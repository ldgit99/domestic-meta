from app.services.effect_size import EffectSizeService


def test_effect_size_service_computes_hedges_g_from_group_statistics() -> None:
    fields = {
        "participants": {
            "sample_size_total": "120",
            "groups": [
                {"name": "실험집단", "n": "60", "mean": "82.4", "sd": "10.1", "timepoint": "post"},
                {"name": "통제집단", "n": "60", "mean": "75.2", "sd": "11.3", "timepoint": "post"},
            ],
        },
        "statistics": [],
        "effect_size_inputs": {
            "is_meta_analytic_ready": True,
            "effect_type_candidates": ["hedges_g"],
            "recommended_effect_type": "hedges_g",
            "computation_method": "two_group_posttest_smd",
            "correlation_coefficient": "",
            "missing_inputs": [],
        },
        "confidence": "medium",
    }

    summary = EffectSizeService().summarize(fields)

    assert summary["is_computable"] is True
    assert summary["recommended_effect_type"] == "hedges_g"
    assert summary["computed_effect_size"]["metric"] == "hedges_g"
    assert summary["computed_effect_size"]["value"] > 0.6
