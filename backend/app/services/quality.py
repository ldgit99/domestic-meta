class QualityAssessmentService:
    def assess(self, fields_json: dict | None) -> dict:
        fields = fields_json or {}
        participants = fields.get("participants") or {}
        groups = [
            group
            for group in (self._normalize_group(item) for item in participants.get("groups") or [])
            if group is not None
        ]
        evidence_spans = [item for item in fields.get("evidence_spans") or [] if isinstance(item, dict)]
        effect_inputs = fields.get("effect_size_inputs") or {}
        statistics = fields.get("statistics") or []
        outcomes = [str(item).strip() for item in fields.get("outcomes") or [] if str(item).strip()]
        study_design = self._clean_text(fields.get("study_design"))
        confidence = (self._clean_text(fields.get("confidence")) or "low").lower()
        sample_size_total = self._to_int(participants.get("sample_size_total"))
        group_total = sum(group["n"] for group in groups if group["n"] is not None)
        complete_groups = [
            group for group in groups if group["n"] is not None and group["mean"] is not None and group["sd"] is not None
        ]
        correlation = self._extract_statistic(effect_inputs, statistics, {"correlation_r", "r"})
        t_value = self._extract_statistic(effect_inputs, statistics, {"t_value", "t"})
        effect_ready_from_values = len(complete_groups) >= 2 or correlation is not None or (
            t_value is not None and len([group for group in groups if group["n"] is not None]) >= 2
        )

        critical_present: list[str] = []
        critical_missing: list[str] = []
        warnings: list[str] = []

        if study_design and study_design != "unknown":
            critical_present.append("study_design")
        else:
            critical_missing.append("study_design")
            warnings.append("study_design_unknown")

        if sample_size_total is not None or any(group["n"] is not None for group in groups):
            critical_present.append("sample_size")
        else:
            critical_missing.append("sample_size")

        if outcomes:
            critical_present.append("outcomes")
        else:
            critical_missing.append("outcomes")
            warnings.append("outcomes_missing")

        if evidence_spans:
            critical_present.append("evidence_spans")
        else:
            critical_missing.append("evidence_spans")
            warnings.append("missing_evidence_spans")

        if effect_ready_from_values:
            critical_present.append("effect_inputs")
        else:
            critical_missing.append("effect_inputs")

        group_sample_size_total_matches = None
        if sample_size_total is not None and group_total > 0:
            group_sample_size_total_matches = sample_size_total == group_total
            if not group_sample_size_total_matches:
                warnings.append("sample_size_mismatch")

        if evidence_spans and len(evidence_spans) < max(1, len(critical_present) - 1):
            warnings.append("evidence_coverage_low")

        if confidence == "low":
            warnings.append("low_confidence_extraction")

        meta_ready_flag = bool(effect_inputs.get("is_meta_analytic_ready"))
        if meta_ready_flag and not effect_ready_from_values:
            warnings.append("meta_ready_without_sufficient_inputs")
        if not meta_ready_flag and effect_ready_from_values:
            warnings.append("effect_inputs_incomplete")
        if effect_ready_from_values and not evidence_spans:
            warnings.append("effect_inputs_without_evidence")

        score_value = 100
        penalties = {
            "missing_evidence_spans": 30,
            "sample_size_mismatch": 20,
            "low_confidence_extraction": 15,
            "meta_ready_without_sufficient_inputs": 15,
            "effect_inputs_incomplete": 12,
            "effect_inputs_without_evidence": 10,
            "study_design_unknown": 10,
            "outcomes_missing": 10,
            "evidence_coverage_low": 8,
        }
        for warning in self._dedupe(warnings):
            score_value -= penalties.get(warning, 5)
        score_value -= min(len(critical_missing) * 5, 20)
        score_value = max(score_value, 0)

        if score_value >= 80:
            score = "high"
        elif score_value >= 60:
            score = "medium"
        else:
            score = "low"

        return {
            "score": score,
            "warnings": self._dedupe(warnings),
            "evidence_count": len(evidence_spans),
            "group_sample_size_total_matches": group_sample_size_total_matches,
            "critical_fields_present": self._dedupe(critical_present),
            "critical_fields_missing": self._dedupe(critical_missing),
        }

    def _normalize_group(self, payload: dict) -> dict | None:
        if not isinstance(payload, dict):
            return None
        return {
            "n": self._to_int(payload.get("n")),
            "mean": self._to_float(payload.get("mean")),
            "sd": self._to_float(payload.get("sd")),
        }

    def _extract_statistic(self, effect_inputs: dict, statistics: list[dict], labels: set[str]) -> float | None:
        correlation_value = self._to_float(effect_inputs.get("correlation_coefficient"))
        if correlation_value is not None and labels & {"correlation_r", "r"}:
            return correlation_value
        for item in statistics:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip().lower()
            if label in labels:
                value = self._to_float(item.get("value"))
                if value is not None:
                    return value
        return None

    def _clean_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _to_int(self, value: object) -> int | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None

    def _to_float(self, value: object) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _dedupe(self, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            if not value or value in output:
                continue
            output.append(value)
        return output