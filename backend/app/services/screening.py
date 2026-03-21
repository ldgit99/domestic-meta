from dataclasses import dataclass, field

from app.core.constants import (
    DECISION_EXCLUDE,
    DECISION_INCLUDE,
    DECISION_MAYBE,
    TITLE_ABSTRACT_STAGE,
)
from app.core.utils import now_iso
from app.models.domain import CandidateRecord, EligibilityDecision, SearchRequest


@dataclass
class ScreeningEvaluationStep:
    criterion_id: str
    label: str
    description: str
    outcome: str
    detail: str


@dataclass
class ScreeningEvaluation:
    decision: str
    reason_code: str | None
    reason_text: str
    confidence: str
    steps: list[ScreeningEvaluationStep] = field(default_factory=list)


class ScreeningService:
    def sequence_template(self) -> list[dict[str, str]]:
        return [
            {
                "criterion_id": "publication_year",
                "label": "연도 범위",
                "description": "사용자가 지정한 시작/종료 연도 범위를 충족하는지 확인합니다.",
            },
            {
                "criterion_id": "user_exclusion_rules",
                "label": "사용자 제외 기준",
                "description": "제목·초록·키워드가 사용자가 입력한 제외 기준과 일치하는지 확인합니다.",
            },
            {
                "criterion_id": "user_inclusion_rules",
                "label": "사용자 포함 기준",
                "description": "사용자가 입력한 포함 기준이 제목·초록·키워드에서 확인되는지 살펴봅니다.",
            },
            {
                "criterion_id": "quantitative_signal",
                "label": "양적연구 및 통계 신호",
                "description": "평균, 표준편차, 비교집단, 상관계수 같은 메타분석용 통계 신호를 찾습니다.",
            },
        ]

    def evaluate_title_abstract(
        self,
        candidate: CandidateRecord,
        request: SearchRequest | None = None,
    ) -> ScreeningEvaluation:
        text = self._search_text(candidate)
        steps: list[ScreeningEvaluationStep] = []

        if request is not None:
            if candidate.year and (candidate.year < request.year_from or candidate.year > request.year_to):
                steps.append(
                    self._step(
                        "publication_year",
                        "exclude",
                        f"출판 연도 {candidate.year}가 요청 범위 {request.year_from}-{request.year_to}를 벗어났습니다.",
                    )
                )
                return ScreeningEvaluation(
                    decision=DECISION_EXCLUDE,
                    reason_code="outside_date_range",
                    reason_text="Excluded because the publication year is outside the requested range.",
                    confidence="high",
                    steps=steps,
                )

            steps.append(
                self._step(
                    "publication_year",
                    "pass",
                    f"출판 연도 {candidate.year or '-'}가 요청 범위 안에 있습니다.",
                )
            )

            matched_exclusion = self._first_matching_rule(text, request.exclusion_rules)
            if matched_exclusion:
                steps.append(
                    self._step(
                        "user_exclusion_rules",
                        "exclude",
                        f"제외 기준 '{matched_exclusion}'과 일치했습니다.",
                    )
                )
                return ScreeningEvaluation(
                    decision=DECISION_EXCLUDE,
                    reason_code="user_exclusion_rule_match",
                    reason_text=f"Matched exclusion rule: {matched_exclusion}",
                    confidence="high",
                    steps=steps,
                )

            steps.append(
                self._step(
                    "user_exclusion_rules",
                    "pass",
                    "제외 기준과 일치하는 항목이 없습니다." if request.exclusion_rules else "사용자 제외 기준이 없어 통과했습니다.",
                )
            )

            if request.inclusion_rules:
                matched_inclusion = self._first_matching_rule(text, request.inclusion_rules)
                if not matched_inclusion:
                    steps.append(
                        self._step(
                            "user_inclusion_rules",
                            "review",
                            "포함 기준과 일치하는 신호가 없어 수동 검토가 필요합니다.",
                        )
                    )
                    return ScreeningEvaluation(
                        decision=DECISION_MAYBE,
                        reason_code=None,
                        reason_text="No inclusion rule matched automatically; manual review is required.",
                        confidence="low",
                        steps=steps,
                    )

                steps.append(
                    self._step(
                        "user_inclusion_rules",
                        "pass",
                        f"포함 기준 '{matched_inclusion}'과 일치했습니다.",
                    )
                )
            else:
                steps.append(
                    self._step(
                        "user_inclusion_rules",
                        "pass",
                        "사용자 포함 기준이 없어 자동 포함 판단 단계로 진행합니다.",
                    )
                )

        if any(keyword in text for keyword in ["qualitative", "interview", "case study", "focus group"]):
            steps.append(
                self._step(
                    "quantitative_signal",
                    "exclude",
                    "질적연구 신호가 감지되어 자동 제외되었습니다.",
                )
            )
            return ScreeningEvaluation(
                decision=DECISION_EXCLUDE,
                reason_code="not_quantitative",
                reason_text="Excluded because the title or abstract suggests a qualitative design.",
                confidence="high",
                steps=steps,
            )

        if any(
            keyword in text
            for keyword in ["mean", "standard deviation", "control group", "intervention group", "correlation"]
        ):
            steps.append(
                self._step(
                    "quantitative_signal",
                    "include",
                    "메타분석에 필요한 양적 통계 신호가 확인되었습니다.",
                )
            )
            return ScreeningEvaluation(
                decision=DECISION_INCLUDE,
                reason_code=None,
                reason_text="Included as a likely quantitative study with extractable statistics.",
                confidence="medium",
                steps=steps,
            )

        steps.append(
            self._step(
                "quantitative_signal",
                "review",
                "통계 신호가 충분하지 않아 수동 검토가 필요합니다.",
            )
        )
        return ScreeningEvaluation(
            decision=DECISION_MAYBE,
            reason_code=None,
            reason_text="Automatic title and abstract screening was inconclusive.",
            confidence="low",
            steps=steps,
        )

    def screen_title_abstract(
        self,
        candidate: CandidateRecord,
        request: SearchRequest | None = None,
    ) -> EligibilityDecision:
        evaluation = self.evaluate_title_abstract(candidate, request=request)
        return self._decision(
            candidate,
            evaluation.decision,
            evaluation.reason_code,
            evaluation.reason_text,
            evaluation.confidence,
        )

    def _search_text(self, candidate: CandidateRecord) -> str:
        values = [
            candidate.title,
            candidate.abstract,
            candidate.journal_or_school,
            " ".join(candidate.keywords),
        ]
        return " ".join(value for value in values if value).lower()

    def _first_matching_rule(self, text: str, rules: list[str]) -> str | None:
        for rule in rules:
            normalized = rule.strip().lower()
            if normalized and normalized in text:
                return rule.strip()
        return None

    def _step(self, criterion_id: str, outcome: str, detail: str) -> ScreeningEvaluationStep:
        template = next(
            item for item in self.sequence_template() if item["criterion_id"] == criterion_id
        )
        return ScreeningEvaluationStep(
            criterion_id=criterion_id,
            label=template["label"],
            description=template["description"],
            outcome=outcome,
            detail=detail,
        )

    def _decision(
        self,
        candidate: CandidateRecord,
        decision: str,
        reason_code: str | None,
        reason_text: str,
        confidence: str,
    ) -> EligibilityDecision:
        return EligibilityDecision(
            id=f"decision_stub_{candidate.id}",
            candidate_record_id=candidate.id,
            stage=TITLE_ABSTRACT_STAGE,
            decision=decision,
            reason_code=reason_code,
            reason_text=reason_text,
            confidence=confidence,
            reviewed_by="screening_agent",
            created_at=now_iso(),
        )
