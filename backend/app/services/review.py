from app.core.constants import (
    DECISION_EXCLUDE,
    DECISION_INCLUDE,
    DECISION_MAYBE,
    DECISION_REVIEW,
    FULL_TEXT_STAGE,
    TITLE_ABSTRACT_STAGE,
)
from app.services.effect_size import EffectSizeService


class ReviewService:
    def __init__(self, store, effect_size_service: EffectSizeService) -> None:
        self.store = store
        self.effect_size_service = effect_size_service

    def get_candidate_detail(self, candidate_id: str) -> dict | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None

        decisions = [
            item
            for item in self.store.list_decisions_for_search(candidate.search_request_id)
            if item.candidate_record_id == candidate_id
        ]
        title_decision = self._latest_decision(decisions, TITLE_ABSTRACT_STAGE)
        full_text_decision = self._latest_decision(decisions, FULL_TEXT_STAGE)
        artifact = self.store.get_full_text_artifact(candidate_id)
        extraction = self.store.get_extraction_result(candidate_id)
        effect_size_summary = self.effect_size_service.summarize(
            extraction.fields_json if extraction is not None else None
        )
        review_reasons = self._review_reasons(
            title_decision,
            full_text_decision,
            artifact,
            extraction,
            effect_size_summary,
        )

        return {
            "candidate": candidate,
            "latest_title_abstract_decision": title_decision,
            "latest_full_text_decision": full_text_decision,
            "full_text_artifact": artifact,
            "extraction_result": extraction,
            "effect_size_summary": effect_size_summary,
            "needs_manual_review": bool(review_reasons),
            "review_priority": self._review_priority(review_reasons),
            "review_reasons": review_reasons,
        }

    def build_review_queue(self, search_request_id: str) -> list[dict]:
        items: list[dict] = []
        candidates = sorted(
            self.store.list_candidates(search_request_id),
            key=lambda item: (item.year * -1, item.title),
        )
        for candidate in candidates:
            if candidate.canonical_record_id and candidate.canonical_record_id != candidate.id:
                continue

            detail = self.get_candidate_detail(candidate.id)
            if detail is None or not detail["needs_manual_review"]:
                continue

            latest_decision = detail["latest_full_text_decision"] or detail["latest_title_abstract_decision"]
            items.append(
                {
                    "candidate": detail["candidate"],
                    "latest_decision": latest_decision,
                    "full_text_status": (
                        detail["full_text_artifact"].text_extraction_status
                        if detail["full_text_artifact"]
                        else None
                    ),
                    "extraction_status": detail["extraction_result"].status if detail["extraction_result"] else None,
                    "effect_size_summary": detail["effect_size_summary"],
                    "review_priority": detail["review_priority"],
                    "review_reasons": detail["review_reasons"],
                }
            )

        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            items,
            key=lambda item: (
                priority_order.get(item["review_priority"], 9),
                item["candidate"].year * -1,
                item["candidate"].title,
            ),
        )

    def _latest_decision(self, decisions: list, stage: str):
        stage_items = [item for item in decisions if item.stage == stage]
        if not stage_items:
            return None
        return sorted(stage_items, key=lambda item: item.created_at)[-1]

    def _review_reasons(
        self,
        title_decision,
        full_text_decision,
        artifact,
        extraction,
        effect_size_summary: dict,
    ) -> list[str]:
        if full_text_decision and full_text_decision.decision == DECISION_EXCLUDE:
            return []
        if title_decision and title_decision.decision == DECISION_EXCLUDE and full_text_decision is None:
            return []

        reasons: list[str] = []
        artifact_status = artifact.text_extraction_status if artifact is not None else None
        artifact_has_text = self._artifact_has_text(artifact)

        if title_decision is None:
            reasons.append("title_abstract_decision_missing")
        elif title_decision.decision in {DECISION_MAYBE, DECISION_REVIEW}:
            reasons.append("title_abstract_review_needed")

        if full_text_decision and full_text_decision.decision in {DECISION_MAYBE, DECISION_REVIEW}:
            reasons.append("full_text_review_needed")

        include_for_full_text = False
        if full_text_decision is not None:
            include_for_full_text = full_text_decision.decision == DECISION_INCLUDE
        elif title_decision is not None:
            include_for_full_text = title_decision.decision == DECISION_INCLUDE

        if include_for_full_text and artifact is None:
            reasons.append("full_text_needed")

        if include_for_full_text and artifact_status in {"ocr_required", "no_text_extracted"}:
            reasons.append("ocr_required")
        elif include_for_full_text and artifact_status == "ocr_failed":
            reasons.append("ocr_failed")
        elif include_for_full_text and artifact_status == "pending":
            reasons.append("text_extraction_pending")

        if include_for_full_text and artifact_has_text and full_text_decision is None:
            reasons.append("full_text_decision_missing")

        if artifact_has_text and extraction is None:
            reasons.append("extraction_not_run")

        if extraction is not None:
            if extraction.status not in {"completed", "fallback_heuristic"}:
                reasons.append(f"extraction_status_{extraction.status}")
            if not effect_size_summary["is_computable"]:
                reasons.append("effect_size_not_computable")
            reasons.extend(effect_size_summary["review_flags"])

        return self._dedupe(reasons)

    def _review_priority(self, reasons: list[str]) -> str:
        if not reasons:
            return "low"

        high_priority = {
            "title_abstract_review_needed",
            "full_text_review_needed",
            "full_text_needed",
            "full_text_decision_missing",
            "effect_size_not_computable",
            "low_confidence_extraction",
            "ocr_required",
            "ocr_failed",
            "text_extraction_pending",
        }
        if any(reason in high_priority or reason.startswith("extraction_status_") for reason in reasons):
            return "high"
        return "medium"

    def _artifact_has_text(self, artifact) -> bool:
        if artifact is None:
            return False
        return artifact.text_extraction_status == "available" and bool((artifact.text_content or "").strip())

    def _dedupe(self, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            if value in output:
                continue
            output.append(value)
        return output
