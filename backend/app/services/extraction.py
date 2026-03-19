import copy
import json
import re
import urllib.request

from app.core.config import settings
from app.core.utils import generate_id, now_iso
from app.models.domain import CandidateRecord, ExtractionResult, FullTextArtifact
from app.services.quality import QualityAssessmentService


class ExtractionService:
    GROUP_ALIASES = {
        "intervention": [
            "intervention group",
            "experimental group",
            "treatment group",
            "실험집단",
            "처치집단",
        ],
        "control": [
            "control group",
            "comparison group",
            "비교집단",
            "대조집단",
            "통제집단",
        ],
    }

    def __init__(self) -> None:
        self.quality = QualityAssessmentService()

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
                "fields_json": self._with_quality_assessment(existing.fields_json),
                "model_name": existing.model_name,
                "created_at": existing.created_at,
            }

        if artifact is None:
            return {
                "id": None,
                "candidate_id": candidate.id,
                "status": "missing_full_text",
                "message": "Full text is missing, so extraction preview cannot run yet.",
                "fields_json": self._empty_fields(),
                "model_name": None,
                "created_at": None,
            }

        if self._artifact_needs_text(artifact):
            status = self._artifact_blocking_status(artifact)
            return {
                "id": None,
                "candidate_id": candidate.id,
                "status": status,
                "message": self._artifact_blocking_message(status),
                "fields_json": self._empty_fields(),
                "model_name": None,
                "created_at": None,
            }

        heuristic = self._heuristic_fields(candidate, artifact)
        return {
            "id": None,
            "candidate_id": candidate.id,
            "status": "preview_ready",
            "message": "Heuristic preview is ready. Live extraction will use OpenAI when configured and fall back otherwise.",
            "fields_json": self._with_quality_assessment(heuristic),
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
                message="Full text is missing, so extraction cannot run.",
                fields_json=self._empty_fields(),
                model_name=None,
                raw_response={},
                created_at=now_iso(),
            )

        if self._artifact_needs_text(artifact):
            status = self._artifact_blocking_status(artifact)
            return ExtractionResult(
                id=generate_id("extract"),
                candidate_id=candidate.id,
                status=status,
                message=self._artifact_blocking_message(status),
                fields_json=self._empty_fields(),
                model_name=None,
                raw_response={"text_extraction_status": artifact.text_extraction_status},
                created_at=now_iso(),
            )

        if settings.openai_api_key:
            live_result = self._run_openai(candidate, artifact)
            if live_result is not None:
                return live_result

        heuristic = self._with_quality_assessment(self._heuristic_fields(candidate, artifact))
        return ExtractionResult(
            id=generate_id("extract"),
            candidate_id=candidate.id,
            status="fallback_heuristic",
            message="OpenAI extraction was unavailable, so heuristic extraction was saved instead.",
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
            message="OpenAI Responses API extraction completed.",
            fields_json=self._with_quality_assessment(parsed),
            model_name=raw_response.get("model") or settings.openai_model_extraction,
            raw_response=raw_response,
            created_at=now_iso(),
        )

    def _build_prompt(self, candidate: CandidateRecord, artifact: FullTextArtifact) -> str:
        text = artifact.text_content[:12000]
        return (
            f"Paper title: {candidate.title}\n"
            f"Year: {candidate.year}\n"
            f"Abstract: {candidate.abstract}\n"
            "Extract meta-analysis-ready data for an education study.\n"
            "Return study design, participants, group statistics, outcomes, timepoints, statistics, "
            "effect size inputs, evidence spans, and confidence.\n"
            "Use empty strings or empty arrays for missing values and do not infer missing numbers.\n"
            f"Paper text:\n{text}"
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
        sample_size, sample_evidence = self._extract_sample_size(text)
        groups = self._extract_groups(text)
        if not sample_size:
            group_total = sum(int(group["n"]) for group in groups if group.get("n"))
            if group_total:
                sample_size = str(group_total)

        study_design = self._detect_study_design(text)
        statistics = self._extract_statistics(text)
        effect_inputs = self._infer_effect_inputs(groups, sample_size, statistics)
        timepoints = self._extract_timepoints(text)

        evidence = []
        if sample_evidence:
            evidence.append(
                {
                    "field": "participants.sample_size_total",
                    "evidence_text": sample_evidence,
                    "location": "heuristic",
                }
            )
        for group in groups:
            if group["mean"] and group["sd"]:
                evidence.append(
                    {
                        "field": f"participants.groups.{group['name']}",
                        "evidence_text": f"{group['name']} n={group['n']} mean={group['mean']} sd={group['sd']}",
                        "location": "heuristic",
                    }
                )

        return {
            "study_design": study_design,
            "participants": {
                "population": "",
                "sample_size_total": sample_size,
                "groups": groups,
            },
            "intervention_or_predictor": self._detect_intervention(text),
            "comparison": self._detect_comparison(groups),
            "outcomes": self._detect_outcomes(text),
            "timepoints": timepoints,
            "statistics": statistics,
            "effect_size_inputs": effect_inputs,
            "evidence_spans": evidence,
            "confidence": "low",
        }

    def _extract_sample_size(self, text: str) -> tuple[str, str]:
        patterns = [
            r"(\d+)\s*(?:participants|students|people)\b",
            r"N\s*=\s*(\d+)",
            r"표본\s*(?:수|수는)?\s*(\d+)",
            r"(\d+)\s*명",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1), match.group(0)
        return "", ""

    def _detect_study_design(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ["quasi-experimental", "quasi experimental", "준실험"]):
            return "quasi_experimental"
        if any(
            token in lowered
            for token in [
                "intervention group",
                "control group",
                "experimental group",
                "comparison group",
                "실험집단",
                "통제집단",
                "비교집단",
                "대조집단",
            ]
        ):
            return "group_comparison"
        if any(token in lowered for token in ["correlation", "correlational", "상관"]):
            return "correlational"
        if any(token in lowered for token in ["regression", "회귀"]):
            return "regression"
        return "unknown"

    def _extract_groups(self, text: str) -> list[dict]:
        groups: list[dict] = []
        for canonical_name, aliases in self.GROUP_ALIASES.items():
            group = self._extract_group(text, canonical_name, aliases)
            if group is not None:
                groups.append(group)
        return groups

    def _extract_group(self, text: str, canonical_name: str, aliases: list[str]) -> dict | None:
        number_pattern = r"-?(?:\d+(?:\.\d+)?|\.\d+)"
        for alias in aliases:
            escaped = re.escape(alias)
            n_match = re.search(
                rf"{escaped}[\s\S]{{0,60}}?(?:n\s*=\s*|had\s*|with\s*|was\s*|were\s*)?(\d+)\s*(?:participants|students|people|명)?",
                text,
                re.IGNORECASE,
            )
            mean_sd_match = re.search(
                rf"{escaped}[\s\S]{{0,140}}?(?:mean|평균)\s*(?:=|:|was)?\s*({number_pattern})[\s\S]{{0,60}}?(?:sd|standard deviation|표준편차)\s*(?:=|:|was|of)?\s*({number_pattern})",
                text,
                re.IGNORECASE,
            )
            if not mean_sd_match:
                mean_sd_match = re.search(
                    rf"{escaped}[\s\S]{{0,140}}?M\s*=\s*({number_pattern})[\s\S]{{0,40}}?SD\s*=\s*({number_pattern})",
                    text,
                    re.IGNORECASE,
                )

            group = {
                "name": canonical_name,
                "n": n_match.group(1) if n_match else "",
                "mean": mean_sd_match.group(1) if mean_sd_match else "",
                "sd": mean_sd_match.group(2) if mean_sd_match else "",
                "timepoint": "post",
            }
            if group["n"] or group["mean"] or group["sd"]:
                return group
        return None

    def _extract_statistics(self, text: str) -> list[dict]:
        stats: list[dict] = []
        number_pattern = r"-?(?:\d+(?:\.\d+)?|\.\d+)"
        t_match = re.search(rf"\bt\s*[=\(]?\s*({number_pattern})", text, re.IGNORECASE)
        f_match = re.search(rf"\bf\s*[=\(]?\s*({number_pattern})", text, re.IGNORECASE)
        r_match = re.search(rf"\br\s*=\s*({number_pattern})", text, re.IGNORECASE)
        p_match = re.search(r"\bp\s*([<=>])\s*(\.?\d+)", text, re.IGNORECASE)
        beta_match = re.search(rf"(?:beta|β)\s*=\s*({number_pattern})", text, re.IGNORECASE)

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
        if beta_match:
            stats.append({"label": "beta", "value": beta_match.group(1), "location": "heuristic"})

        return stats

    def _extract_timepoints(self, text: str) -> list[str]:
        lowered = text.lower()
        values: list[str] = []
        pairs = [
            ("pretest", "pretest"),
            ("posttest", "posttest"),
            ("pre-test", "pretest"),
            ("post-test", "posttest"),
            ("사전", "pretest"),
            ("사후", "posttest"),
            ("추후", "follow_up"),
            ("follow-up", "follow_up"),
        ]
        for token, normalized in pairs:
            if token in lowered or token in text:
                values.append(normalized)
        return self._dedupe(values)

    def _detect_comparison(self, groups: list[dict]) -> str:
        if any(group["name"] == "control" for group in groups):
            return "control"
        if len(groups) >= 2:
            return groups[1]["name"]
        return ""

    def _detect_intervention(self, text: str) -> str:
        lowered = text.lower()
        if "self-directed learning" in lowered or "자기주도학습" in text:
            return "self-directed learning"
        if "program" in lowered or "프로그램" in text:
            return "program"
        if "regression" in lowered or "회귀" in text:
            return "regression_predictor"
        return ""

    def _detect_outcomes(self, text: str) -> list[str]:
        outcomes: list[str] = []
        lowered = text.lower()
        pairs = [
            ("achievement", "achievement"),
            ("motivation", "motivation"),
            ("academic achievement", "academic achievement"),
            ("engagement", "engagement"),
            ("성취", "achievement"),
            ("동기", "motivation"),
            ("참여", "engagement"),
        ]
        for token, label in pairs:
            if token in lowered or token in text:
                outcomes.append(label)
        return self._dedupe(outcomes)

    def _infer_effect_inputs(
        self,
        groups: list[dict],
        sample_size: str,
        statistics: list[dict],
    ) -> dict:
        complete_groups = [
            group for group in groups if group.get("n") and group.get("mean") and group.get("sd")
        ]
        t_value = next((item for item in statistics if item["label"] == "t_value"), None)
        r_value = next((item for item in statistics if item["label"] == "correlation_r"), None)

        if len(complete_groups) >= 2:
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

    def _with_quality_assessment(self, fields: dict) -> dict:
        payload = copy.deepcopy(fields)
        payload["quality_assessment"] = self.quality.assess(payload)
        return payload

    def _dedupe(self, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            if value and value not in output:
                output.append(value)
        return output

    def _artifact_needs_text(self, artifact: FullTextArtifact) -> bool:
        return artifact.text_extraction_status != "available" or not artifact.text_content.strip()

    def _artifact_blocking_status(self, artifact: FullTextArtifact) -> str:
        if artifact.text_extraction_status in {"ocr_required", "no_text_extracted"}:
            return "ocr_required"
        if artifact.text_extraction_status == "ocr_failed":
            return "ocr_failed"
        if artifact.text_extraction_status == "pending":
            return "text_extraction_pending"
        return "text_not_available"

    def _artifact_blocking_message(self, status: str) -> str:
        messages = {
            "ocr_required": "Text extraction did not produce usable text. OCR or manual text entry is required.",
            "ocr_failed": "OCR or text extraction failed. Re-upload the document or provide manual text.",
            "text_extraction_pending": "Full text is registered, but usable text has not been extracted yet.",
            "text_not_available": "Usable text is not available for extraction yet.",
        }
        return messages.get(status, "Usable text is not available for extraction yet.")

    def _empty_fields(self) -> dict:
        payload = {
            "study_design": "",
            "participants": {
                "population": "",
                "sample_size_total": "",
                "groups": [],
            },
            "intervention_or_predictor": "",
            "comparison": "",
            "outcomes": [],
            "timepoints": [],
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
        return self._with_quality_assessment(payload)

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
                "timepoints": {
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
                "timepoints",
                "statistics",
                "effect_size_inputs",
                "evidence_spans",
                "confidence",
            ],
        }