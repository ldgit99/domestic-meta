from app.core.constants import (
    DECISION_EXCLUDE,
    DECISION_INCLUDE,
    DECISION_MAYBE,
    TITLE_ABSTRACT_STAGE,
)
from app.core.utils import now_iso
from app.models.domain import CandidateRecord, EligibilityDecision, SearchRequest


class ScreeningService:
    def screen_title_abstract(
        self,
        candidate: CandidateRecord,
        request: SearchRequest | None = None,
    ) -> EligibilityDecision:
        text = self._search_text(candidate)

        if request is not None:
            if candidate.year and (candidate.year < request.year_from or candidate.year > request.year_to):
                return self._decision(
                    candidate,
                    DECISION_EXCLUDE,
                    "outside_date_range",
                    "Excluded because the publication year is outside the requested range.",
                    "high",
                )

            matched_exclusion = self._first_matching_rule(text, request.exclusion_rules)
            if matched_exclusion:
                return self._decision(
                    candidate,
                    DECISION_EXCLUDE,
                    "user_exclusion_rule_match",
                    f"Matched exclusion rule: {matched_exclusion}",
                    "high",
                )

            if request.inclusion_rules:
                matched_inclusion = self._first_matching_rule(text, request.inclusion_rules)
                if not matched_inclusion:
                    return self._decision(
                        candidate,
                        DECISION_MAYBE,
                        None,
                        "No inclusion rule matched automatically; manual review is required.",
                        "low",
                    )

        if any(keyword in text for keyword in ["qualitative", "interview", "case study", "focus group"]):
            return self._decision(
                candidate,
                DECISION_EXCLUDE,
                "not_quantitative",
                "Excluded because the title or abstract suggests a qualitative design.",
                "high",
            )

        if any(
            keyword in text
            for keyword in ["mean", "standard deviation", "control group", "intervention group", "correlation"]
        ):
            return self._decision(
                candidate,
                DECISION_INCLUDE,
                None,
                "Included as a likely quantitative study with extractable statistics.",
                "medium",
            )

        return self._decision(
            candidate,
            DECISION_MAYBE,
            None,
            "Automatic title and abstract screening was inconclusive.",
            "low",
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
