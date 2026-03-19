import math


class EffectSizeService:
    def summarize(self, fields_json: dict | None) -> dict:
        fields = fields_json or {}
        participants = fields.get("participants") or {}
        statistics = fields.get("statistics") or []
        effect_inputs = fields.get("effect_size_inputs") or {}
        groups = participants.get("groups") or []

        normalized_groups = [
            group for group in (self._normalize_group(item) for item in groups) if group is not None
        ]
        group_sizes = [group for group in normalized_groups if group["n"] is not None]
        complete_groups = [
            group
            for group in normalized_groups
            if group["n"] is not None and group["mean"] is not None and group["sd"] is not None
        ]

        recommended = self._clean_text(effect_inputs.get("recommended_effect_type"))
        if recommended is None:
            candidates = effect_inputs.get("effect_type_candidates") or []
            recommended = self._clean_text(candidates[0]) if candidates else None

        method = self._clean_text(effect_inputs.get("computation_method"))
        available_inputs: list[str] = []
        missing_inputs = list(effect_inputs.get("missing_inputs") or [])
        review_flags: list[str] = []
        computed_effect_size: dict | None = None

        if len(group_sizes) >= 2:
            available_inputs.append("group_sample_sizes")
        if any(group["mean"] is not None for group in normalized_groups):
            available_inputs.append("group_means")
        if any(group["sd"] is not None for group in normalized_groups):
            available_inputs.append("group_standard_deviations")

        correlation = self._extract_correlation(effect_inputs, statistics)
        if correlation is not None:
            available_inputs.append("correlation_coefficient")

        t_value = self._extract_statistic(statistics, {"t_value", "t"})
        if t_value is not None:
            available_inputs.append("t_value")

        if len(complete_groups) >= 2:
            value, variance = self._compute_hedges_g(complete_groups[0], complete_groups[1])
            if value is not None:
                computed_effect_size = {
                    "metric": "hedges_g",
                    "value": round(value, 4),
                    "variance": round(variance, 6) if variance is not None else None,
                }
                recommended = recommended or "hedges_g"
                method = method or "two_group_posttest_smd"

        if computed_effect_size is None and correlation is not None:
            sample_size = self._to_int(participants.get("sample_size_total"))
            if sample_size is not None and sample_size > 3 and abs(correlation) < 1:
                fisher_z = 0.5 * math.log((1 + correlation) / (1 - correlation))
                variance = 1 / (sample_size - 3)
                computed_effect_size = {
                    "metric": "fisher_z",
                    "value": round(fisher_z, 4),
                    "variance": round(variance, 6),
                }
                recommended = recommended or "fisher_z"
                method = method or "correlation_to_fisher_z"

        if computed_effect_size is None and t_value is not None and len(group_sizes) >= 2:
            value, variance = self._compute_hedges_g_from_t(
                t_value,
                group_sizes[0]["n"],
                group_sizes[1]["n"],
            )
            if value is not None:
                computed_effect_size = {
                    "metric": "hedges_g",
                    "value": round(value, 4),
                    "variance": round(variance, 6) if variance is not None else None,
                }
                recommended = recommended or "hedges_g"
                method = method or "independent_t_to_smd"

        if computed_effect_size is None:
            missing_inputs.extend(
                self._infer_missing_inputs(normalized_groups, participants, correlation, t_value)
            )

        if fields.get("confidence") == "low":
            review_flags.append("low_confidence_extraction")

        if computed_effect_size is None and effect_inputs.get("is_meta_analytic_ready"):
            review_flags.append("ready_flag_without_computed_effect")

        if recommended in {"hedges_g", "standardized_mean_difference"} and len(complete_groups) < 2:
            review_flags.append("group_statistics_missing")

        return {
            "is_computable": computed_effect_size is not None,
            "recommended_effect_type": recommended,
            "computation_method": method,
            "computed_effect_size": computed_effect_size,
            "available_inputs": self._dedupe(available_inputs),
            "missing_inputs": self._dedupe(missing_inputs),
            "review_flags": self._dedupe(review_flags),
        }

    def _normalize_group(self, payload: dict) -> dict | None:
        if not isinstance(payload, dict):
            return None

        name = self._clean_text(payload.get("name")) or "group"
        return {
            "name": name,
            "n": self._to_int(payload.get("n")),
            "mean": self._to_float(payload.get("mean")),
            "sd": self._to_float(payload.get("sd")),
            "timepoint": self._clean_text(payload.get("timepoint")),
        }

    def _extract_correlation(self, effect_inputs: dict, statistics: list[dict]) -> float | None:
        direct = self._to_float(effect_inputs.get("correlation_coefficient"))
        if direct is not None:
            return direct
        return self._extract_statistic(statistics, {"correlation_r", "r"})

    def _extract_statistic(self, statistics: list[dict], labels: set[str]) -> float | None:
        for item in statistics:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip().lower()
            if label in labels:
                value = self._to_float(item.get("value"))
                if value is not None:
                    return value
        return None

    def _infer_missing_inputs(
        self,
        groups: list[dict],
        participants: dict,
        correlation: float | None,
        t_value: float | None,
    ) -> list[str]:
        missing: list[str] = []

        if len(groups) >= 2:
            if not all(group["n"] is not None for group in groups[:2]):
                missing.append("group_sample_sizes")
            if not all(group["mean"] is not None for group in groups[:2]):
                missing.append("group_means")
            if not all(group["sd"] is not None for group in groups[:2]):
                missing.append("group_standard_deviations")
            if t_value is None and correlation is None and (
                not all(group["mean"] is not None for group in groups[:2])
                or not all(group["sd"] is not None for group in groups[:2])
            ):
                missing.append("effect_statistic")
            return missing

        if correlation is not None:
            if self._to_int(participants.get("sample_size_total")) is None:
                missing.append("sample_size_total")
            return missing

        if t_value is not None:
            missing.append("group_sample_sizes")
            return missing

        missing.extend(["effect_statistic", "sample_size_total"])
        return missing

    def _compute_hedges_g(self, group_a: dict, group_b: dict) -> tuple[float | None, float | None]:
        n1 = group_a["n"]
        n2 = group_b["n"]
        mean1 = group_a["mean"]
        mean2 = group_b["mean"]
        sd1 = group_a["sd"]
        sd2 = group_b["sd"]
        if None in {n1, n2, mean1, mean2, sd1, sd2}:
            return None, None
        if n1 <= 1 or n2 <= 1:
            return None, None

        pooled_denom = n1 + n2 - 2
        if pooled_denom <= 0:
            return None, None

        pooled_variance = (((n1 - 1) * (sd1**2)) + ((n2 - 1) * (sd2**2))) / pooled_denom
        if pooled_variance <= 0:
            return None, None

        pooled_sd = math.sqrt(pooled_variance)
        if pooled_sd == 0:
            return None, None

        cohen_d = (mean1 - mean2) / pooled_sd
        correction = 1 - (3 / ((4 * (n1 + n2)) - 9)) if (4 * (n1 + n2) - 9) > 0 else 1
        hedges_g = correction * cohen_d
        variance = ((n1 + n2) / (n1 * n2)) + ((hedges_g**2) / (2 * pooled_denom))
        return hedges_g, variance

    def _compute_hedges_g_from_t(
        self,
        t_value: float,
        n1: int | None,
        n2: int | None,
    ) -> tuple[float | None, float | None]:
        if n1 is None or n2 is None or n1 <= 0 or n2 <= 0:
            return None, None

        cohen_d = t_value * math.sqrt((1 / n1) + (1 / n2))
        correction = 1 - (3 / ((4 * (n1 + n2)) - 9)) if (4 * (n1 + n2) - 9) > 0 else 1
        hedges_g = correction * cohen_d
        pooled_denom = n1 + n2 - 2
        variance = ((n1 + n2) / (n1 * n2)) + ((hedges_g**2) / (2 * pooled_denom)) if pooled_denom > 0 else None
        return hedges_g, variance

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

    def _clean_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _dedupe(self, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            if not value or value in output:
                continue
            output.append(value)
        return output
