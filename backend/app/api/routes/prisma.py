from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.repositories.file_store import FileStore
from app.schemas.prisma import PrismaCountsRead


router = APIRouter(tags=["prisma"])


@router.get("/search-requests/{search_request_id}/prisma", response_model=PrismaCountsRead)
def get_prisma_counts(
    search_request_id: str,
    store: FileStore = Depends(get_store),
) -> PrismaCountsRead:
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    return PrismaCountsRead.model_validate(counts)
