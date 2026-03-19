from app.core.constants import (
    DECISION_EXCLUDE,
    DECISION_INCLUDE,
    DECISION_MAYBE,
    TITLE_ABSTRACT_STAGE,
)
from app.core.utils import now_iso
from app.models.domain import CandidateRecord, EligibilityDecision


class ScreeningService:
    def screen_title_abstract(self, candidate: CandidateRecord) -> EligibilityDecision:
        abstract = f"{candidate.title} {candidate.abstract}".lower()

        if "질적" in abstract or "면담" in abstract or "사례연구" in abstract:
            return EligibilityDecision(
                id=f"decision_stub_{candidate.id}",
                candidate_record_id=candidate.id,
                stage=TITLE_ABSTRACT_STAGE,
                decision=DECISION_EXCLUDE,
                reason_code="not_quantitative",
                reason_text="질적 연구 또는 사례연구로 판단됨",
                confidence="high",
                reviewed_by="screening_agent",
                created_at=now_iso(),
            )

        if "평균" in abstract or "표준편차" in abstract or "비교집단" in abstract or "실험" in abstract:
            return EligibilityDecision(
                id=f"decision_stub_{candidate.id}",
                candidate_record_id=candidate.id,
                stage=TITLE_ABSTRACT_STAGE,
                decision=DECISION_INCLUDE,
                reason_code=None,
                reason_text="양적 메타분석 후보로 판단됨",
                confidence="medium",
                reviewed_by="screening_agent",
                created_at=now_iso(),
            )

        return EligibilityDecision(
            id=f"decision_stub_{candidate.id}",
            candidate_record_id=candidate.id,
            stage=TITLE_ABSTRACT_STAGE,
            decision=DECISION_MAYBE,
            reason_code=None,
            reason_text="추가 검토 필요",
            confidence="low",
            reviewed_by="screening_agent",
            created_at=now_iso(),
        )
