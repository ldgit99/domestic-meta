from app.core.utils import generate_id, normalize_title
from app.models.domain import CandidateRecord


class DeduplicationService:
    def deduplicate(self, candidates: list[CandidateRecord]) -> tuple[list[CandidateRecord], int]:
        seen_doi: dict[str, CandidateRecord] = {}
        seen_title: dict[tuple[str, int], CandidateRecord] = {}
        duplicates_removed = 0

        for candidate in candidates:
            matched: CandidateRecord | None = None

            if candidate.doi and candidate.doi in seen_doi:
                matched = seen_doi[candidate.doi]
            else:
                title_key = (normalize_title(candidate.title), candidate.year)
                if title_key in seen_title:
                    matched = seen_title[title_key]

            if matched is None:
                if candidate.doi:
                    seen_doi[candidate.doi] = candidate
                seen_title[(normalize_title(candidate.title), candidate.year)] = candidate
                candidate.canonical_record_id = candidate.id
                continue

            duplicates_removed += 1
            group_id = matched.duplicate_group_id or generate_id("dup")
            matched.duplicate_group_id = group_id
            candidate.duplicate_group_id = group_id
            candidate.canonical_record_id = matched.id
            candidate.status = "deduplicated"

        return candidates, duplicates_removed
