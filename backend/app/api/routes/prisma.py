from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.schemas.prisma import PrismaCountsRead, PrismaFlowRead
from app.services.prisma import PrismaService


router = APIRouter(tags=["prisma"])
service = PrismaService()


@router.get("/search-requests/{search_request_id}/prisma", response_model=PrismaCountsRead)
def get_prisma_counts(
    search_request_id: str,
    store=Depends(get_store),
) -> PrismaCountsRead:
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    return PrismaCountsRead.model_validate(counts)


@router.get("/search-requests/{search_request_id}/prisma/flow", response_model=PrismaFlowRead)
def get_prisma_flow(
    search_request_id: str,
    store=Depends(get_store),
) -> PrismaFlowRead:
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    payload = service.build_flow(search_request_id, counts)
    return PrismaFlowRead.model_validate(payload)
