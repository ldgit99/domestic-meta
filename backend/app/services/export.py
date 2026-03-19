from app.models.domain import CandidateRecord


class ExportService:
    def candidates_csv(self, search_request_id: str, candidates: list[CandidateRecord]) -> dict:
        lines = [
            "id,source,title,year,document_type,status,canonical_record_id,duplicate_group_id"
        ]
        for item in candidates:
            title = item.title.replace('"', "'")
            lines.append(
                f'{item.id},{item.source},"{title}",{item.year},{item.document_type},{item.status},{item.canonical_record_id or ""},{item.duplicate_group_id or ""}'
            )

        return {
            "search_request_id": search_request_id,
            "content_type": "text/csv",
            "file_name": f"{search_request_id}_candidates.csv",
            "content": "\n".join(lines),
        }
