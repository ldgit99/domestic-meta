from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.repositories.memory import MemoryStore
from app.schemas.prisma import CandidatesExportRead
from app.services.export import ExportService


router = APIRouter(tags=["exports"])
service = ExportService()


@router.get("/search-requests/{search_request_id}/exports/candidates.csv", response_model=CandidatesExportRead)
def export_candidates_csv(
    search_request_id: str,
    store: MemoryStore = Depends(get_store),
) -> CandidatesExportRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = service.candidates_csv(search_request_id, store.list_candidates(search_request_id))
    return CandidatesExportRead.model_validate(payload)
