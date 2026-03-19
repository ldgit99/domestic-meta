import json
import re
import urllib.request

from app.core.config import settings
from app.core.utils import generate_id, now_iso
from app.models.domain import CandidateRecord, ExtractionResult, FullTextArtifact


class ExtractionService:
    def preview(
        self,
        candidate: CandidateRecord,
        artifact: FullTextArtifact | None,
        existing: ExtractionResult | None = None,
    ) -> dict:
        if existing is not None:
            return {
                "id": existing.id,
                "candidate_id": existing.candidate_id,
                "status": existing.status,
                "message": existing.message,
                "fields_json": existing.fields_json,
                "model_name": existing.model_name,
                "created_at": existing.created_at,
            }

        if artifact is None:
            return {
                "id": None,
                "candidate_id": candidate.id,
                "status": "missing_full_text",
                "message": "원문이 없어 추출 프리뷰를 생성할 수 없습니다.",
                "fields_json": self._empty_fields(),
                "model_name": None,
                "created_at": None,
            }

        heuristic = self._heuristic_fields(candidate, artifact)
        return {
            "id": None,
            "candidate_id": candidate.id,
            "status": "preview_ready",
            "message": "원문 기반 휴리스틱 프리뷰입니다. 추출 실행 시 OpenAI 또는 fallback 로직이 저장됩니다.",
            "fields_json": heuristic,
            "model_name": None,
            "created_at": None,
        }

    def run(
        self,
        candidate: CandidateRecord,
        artifact: FullTextArtifact | None,
    ) -> ExtractionResult:
        if artifact is None:
            return ExtractionResult(
                id=generate_id("extract"),
                candidate_id=candidate.id,
                status="missing_full_text",
                message="원문이 없어 추출을 실행할 수 없습니다.",
                fields_json=self._empty_fields(),
                model_name=None,
                raw_response={},
                created_at=now_iso(),
            )

        if settings.openai_api_key:
            live_result = self._run_openai(candidate, artifact)
            if live_result is not None:
                return live_result

        heuristic = self._heuristic_fields(candidate, artifact)
        return ExtractionResult(
            id=generate_id("extract"),
            candidate_id=candidate.id,
            status="fallback_heuristic",
            message="OpenAI 설정이 없거나 응답 파싱에 실패하여 휴리스틱 추출 결과를 저장했습니다.",
            fields_json=heuristic,
            model_name=None,
            raw_response={},
            created_at=now_iso(),
        )

    def _run_openai(
        self,
        candidate: CandidateRecord,
        artifact: FullTextArtifact,
    ) -> ExtractionResult | None:
        prompt = self._build_prompt(candidate, artifact)
        schema = self._response_schema()
        payload = {
            "model": settings.openai_model_extraction,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You extract meta-analysis-ready fields from Korean education papers. "
                                "Return JSON only and do not invent missing values."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "meta_analysis_extraction",
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        request = urllib.request.Request(
            settings.openai_responses_url,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8"),
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        parsed = self._parse_response_text(raw_response)
        if parsed is None:
            return None

        return ExtractionResult(
            id=generate_id("extract"),
            candidate_id=candidate.id,
            status="completed",
            message="OpenAI Responses API 기반 구조화 추출을 완료했습니다.",
            fields_json=parsed,
            model_name=raw_response.get("model") or settings.openai_model_extraction,
            raw_response=raw_response,
            created_at=now_iso(),
        )

    def _build_prompt(self, candidate: CandidateRecord, artifact: FullTextArtifact) -> str:
        text = artifact.text_content[:12000]
        return (
            f"논문 제목: {candidate.title}\n"
            f"연도: {candidate.year}\n"
            f"초록: {candidate.abstract}\n"
            "다음 원문 텍스트에서 교육학 메타분석에 필요한 구조화 데이터를 추출하라.\n"
            "집단별 n, 평균, 표준편차, timepoint, t/F/p/r 통계, 권장 효과크기 유형, 계산 방식, 누락 입력을 함께 채워라.\n"
            "모르는 값은 빈 문자열 또는 빈 배열로 두고 추정하지 말라.\n"
            f"원문 텍스트:\n{text}"
        )

    def _parse_response_text(self, payload: dict) -> dict | None:
        text = payload.get("output_text")
        if isinstance(text, str) and text.strip():
            return self._json_or_none(text)

        for item in payload.get("output", []):
            for content in item.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    parsed = self._json_or_none(content["text"])
                    if parsed is not None:
                        return parsed
        return None

    def _json_or_none(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _heuristic_fields(self, candidate: CandidateRecord, artifact: FullTextArtifact) -> dict:
        text = f"{candidate.title}\n{candidate.abstract}\n{artifact.text_content}"
        sample_size = ""
        sample_match = re.search(r"(\d+)\s*명", text)
        if sample_match:
            sample_size = sample_match.group(1)

        groups = self._extract_groups(text)
        if not sample_size:
            group_total = sum(int(group["n"]) for group in groups if group.get("n"))
            if group_total:
                sample_size = str(group_total)

        study_design = "unknown"
        if "준실험" in text:
            study_design = "quasi_experimental"
        elif "실험집단" in text or "통제집단" in text or "비교집단" in text:
            study_design = "group_comparison"
        elif "상관" in text:
            study_design = "correlational"
        elif "회귀" in text:
            study_design = "regression"

        statistics = self._extract_statistics(text)
        effect_inputs = self._infer_effect_inputs(groups, sample_size, statistics)
        evidence = []
        if sample_size and sample_match is not None:
            evidence.append(
                {
                    "field": "participants.sample_size_total",
                    "evidence_text": sample_match.group(0),
                    "location": "heuristic",
                }
            )
        for group in groups:
            if group["mean"] and group["sd"]:
                evidence.append(
                    {
                        "field": f"participants.groups.{group['name']}",
                        "evidence_text": f"{group['name']} 평균 {group['mean']} 표준편차 {group['sd']}",
                        "location": "heuristic",
                    }
                )

        comparison = ""
        if any(group["name"] in {"통제집단", "대조집단", "비교집단"} for group in groups):
            comparison = next(
                group["name"]
                for group in groups
                if group["name"] in {"통제집단", "대조집단", "비교집단"}
            )

        intervention = ""
        if "협동학습" in text:
            intervention = "협동학습"
        elif "프로그램" in text:
            intervention = "프로그램 개입"
        elif "회귀" in text:
            intervention = "회귀모형 예측변수"

        return {
            "study_design": study_design,
            "participants": {
                "population": "",
                "sample_size_total": sample_size,
                "groups": groups,
            },
            "intervention_or_predictor": intervention,
            "comparison": comparison,
            "outcomes": [],
            "statistics": statistics,
            "effect_size_inputs": effect_inputs,
            "evidence_spans": evidence,
            "confidence": "low",
        }

    def _extract_groups(self, text: str) -> list[dict]:
        group_labels = ["실험집단", "통제집단", "비교집단", "처치집단", "대조집단"]
        groups: list[dict] = []
        number_pattern = r"-?(?:\d+(?:\.\d+)?|\.\d+)"

        for label in group_labels:
            n_match = re.search(rf"{label}\s*(?:은|는|이|가)?\s*(\d+)\s*명", text)
            mean_sd_match = re.search(
                rf"{label}[\s\S]{{0,100}}?평균(?:은|는|:)?\s*({number_pattern})[\s\S]{{0,30}}?표준편차(?:은|는|:)?\s*({number_pattern})",
                text,
            )
            if not mean_sd_match:
                mean_sd_match = re.search(
                    rf"{label}[\s\S]{{0,100}}?M\s*=\s*({number_pattern})[\s\S]{{0,20}}?SD\s*=\s*({number_pattern})",
                    text,
                    re.IGNORECASE,
                )

            group = {
                "name": label,
                "n": n_match.group(1) if n_match else "",
                "mean": mean_sd_match.group(1) if mean_sd_match else "",
                "sd": mean_sd_match.group(2) if mean_sd_match else "",
                "timepoint": "post",
            }
            if group["n"] or group["mean"] or group["sd"]:
                groups.append(group)

        return groups

    def _extract_statistics(self, text: str) -> list[dict]:
        stats: list[dict] = []
        number_pattern = r"-?(?:\d+(?:\.\d+)?|\.\d+)"
        t_match = re.search(rf"\bt\s*[=\(]?\s*({number_pattern})", text, re.IGNORECASE)
        f_match = re.search(rf"\bf\s*[=\(]?\s*({number_pattern})", text, re.IGNORECASE)
        r_match = re.search(rf"\br\s*=\s*({number_pattern})", text, re.IGNORECASE)
        p_match = re.search(r"\bp\s*([<=>])\s*(\.?\d+)", text, re.IGNORECASE)

        if t_match:
            stats.append({"label": "t_value", "value": t_match.group(1), "location": "heuristic"})
        if f_match:
            stats.append({"label": "f_value", "value": f_match.group(1), "location": "heuristic"})
        if r_match:
            stats.append({"label": "correlation_r", "value": r_match.group(1), "location": "heuristic"})
        if p_match:
            stats.append(
                {
                    "label": "p_value",
                    "value": f"{p_match.group(1)}{p_match.group(2)}",
                    "location": "heuristic",
                }
            )

        return stats

    def _infer_effect_inputs(
        self,
        groups: list[dict],
        sample_size: str,
        statistics: list[dict],
    ) -> dict:
        has_complete_groups = len(
            [
                group
                for group in groups
                if group.get("n") and group.get("mean") and group.get("sd")
            ]
        ) >= 2
        t_value = next((item for item in statistics if item["label"] == "t_value"), None)
        r_value = next((item for item in statistics if item["label"] == "correlation_r"), None)

        if has_complete_groups:
            return {
                "is_meta_analytic_ready": True,
                "effect_type_candidates": ["hedges_g", "standardized_mean_difference"],
                "recommended_effect_type": "hedges_g",
                "computation_method": "two_group_posttest_smd",
                "correlation_coefficient": "",
                "missing_inputs": [],
            }

        if r_value and sample_size:
            return {
                "is_meta_analytic_ready": True,
                "effect_type_candidates": ["fisher_z", "correlation"],
                "recommended_effect_type": "fisher_z",
                "computation_method": "correlation_to_fisher_z",
                "correlation_coefficient": r_value["value"],
                "missing_inputs": [],
            }

        if t_value and len([group for group in groups if group.get("n")]) >= 2:
            return {
                "is_meta_analytic_ready": True,
                "effect_type_candidates": ["hedges_g", "standardized_mean_difference"],
                "recommended_effect_type": "hedges_g",
                "computation_method": "independent_t_to_smd",
                "correlation_coefficient": "",
                "missing_inputs": [],
            }

        missing_inputs = ["effect_statistic"]
        if len(groups) >= 2:
            if not all(group.get("n") for group in groups[:2]):
                missing_inputs.append("group_sample_sizes")
            if not all(group.get("mean") for group in groups[:2]):
                missing_inputs.append("group_means")
            if not all(group.get("sd") for group in groups[:2]):
                missing_inputs.append("group_standard_deviations")
        elif not sample_size:
            missing_inputs.append("sample_size_total")

        return {
            "is_meta_analytic_ready": False,
            "effect_type_candidates": [],
            "recommended_effect_type": "",
            "computation_method": "",
            "correlation_coefficient": r_value["value"] if r_value else "",
            "missing_inputs": self._dedupe(missing_inputs),
        }

    def _dedupe(self, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            if value and value not in output:
                output.append(value)
        return output

    def _empty_fields(self) -> dict:
        return {
            "study_design": "",
            "participants": {
                "population": "",
                "sample_size_total": "",
                "groups": [],
            },
            "intervention_or_predictor": "",
            "comparison": "",
            "outcomes": [],
            "statistics": [],
            "effect_size_inputs": {
                "is_meta_analytic_ready": False,
                "effect_type_candidates": [],
                "recommended_effect_type": "",
                "computation_method": "",
                "correlation_coefficient": "",
                "missing_inputs": [],
            },
            "evidence_spans": [],
            "confidence": "low",
        }

    def _response_schema(self) -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "study_design": {"type": "string"},
                "participants": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "population": {"type": "string"},
                        "sample_size_total": {"type": "string"},
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "n": {"type": "string"},
                                    "mean": {"type": "string"},
                                    "sd": {"type": "string"},
                                    "timepoint": {"type": "string"},
                                },
                                "required": ["name", "n", "mean", "sd", "timepoint"],
                            },
                        },
                    },
                    "required": ["population", "sample_size_total", "groups"],
                },
                "intervention_or_predictor": {"type": "string"},
                "comparison": {"type": "string"},
                "outcomes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "statistics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "location": {"type": "string"},
                        },
                        "required": ["label", "value", "location"],
                    },
                },
                "effect_size_inputs": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "is_meta_analytic_ready": {"type": "boolean"},
                        "effect_type_candidates": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "recommended_effect_type": {"type": "string"},
                        "computation_method": {"type": "string"},
                        "correlation_coefficient": {"type": "string"},
                        "missing_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "is_meta_analytic_ready",
                        "effect_type_candidates",
                        "recommended_effect_type",
                        "computation_method",
                        "correlation_coefficient",
                        "missing_inputs",
                    ],
                },
                "evidence_spans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "field": {"type": "string"},
                            "evidence_text": {"type": "string"},
                            "location": {"type": "string"},
                        },
                        "required": ["field", "evidence_text", "location"],
                    },
                },
                "confidence": {"type": "string"},
            },
            "required": [
                "study_design",
                "participants",
                "intervention_or_predictor",
                "comparison",
                "outcomes",
                "statistics",
                "effect_size_inputs",
                "evidence_spans",
                "confidence",
            ],
        }
