from app.models.domain import CandidateRecord, FullTextArtifact


class ExtractionService:
    def preview(
        self,
        candidate: CandidateRecord,
        artifact: FullTextArtifact | None,
    ) -> dict:
        if artifact is None:
            return {
                "candidate_id": candidate.id,
                "status": "missing_full_text",
                "message": "원문이 없어 추출 프리뷰를 생성할 수 없습니다.",
                "fields": {
                    "study_design": None,
                    "participants": None,
                    "statistics": [],
                    "effect_size_inputs": None,
                },
            }

        return {
            "candidate_id": candidate.id,
            "status": "preview_ready",
            "message": "후속 단계에서 OpenAI Responses API와 Structured Outputs로 연결할 추출 프리뷰입니다.",
            "fields": {
                "study_design": "unknown",
                "participants": {
                    "sample_size_total": None,
                    "groups": [],
                },
                "statistics": [],
                "effect_size_inputs": {
                    "is_meta_analytic_ready": False,
                },
                "text_excerpt_length": len(artifact.text_content),
            },
        }
