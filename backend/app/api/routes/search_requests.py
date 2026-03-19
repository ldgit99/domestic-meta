from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_orchestrator, get_store
from app.repositories.memory import MemoryStore
from app.schemas.search import SearchRequestCreate, SearchRequestRead, SearchRunResult
from app.services.orchestrator import SearchOrchestrator


router = APIRouter(prefix="/search-requests", tags=["search-requests"])


@router.post("", response_model=SearchRequestRead)
def create_search_request(
    payload: SearchRequestCreate,
    store: MemoryStore = Depends(get_store),
) -> SearchRequestRead:
    created = store.create_search_request(payload)
    return SearchRequestRead.model_validate(created)


@router.get("/{search_request_id}", response_model=SearchRequestRead)
def get_search_request(
    search_request_id: str,
    store: MemoryStore = Depends(get_store),
) -> SearchRequestRead:
    result = store.get_search_request(search_request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    return SearchRequestRead.model_validate(result)


@router.get("/{search_request_id}/status")
def get_search_request_status(
    search_request_id: str,
    store: MemoryStore = Depends(get_store),
) -> dict[str, str]:
    result = store.get_search_request(search_request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    return {"id": result.id, "status": result.status}


@router.post("/{search_request_id}/run", response_model=SearchRunResult)
def run_search_request(
    search_request_id: str,
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> SearchRunResult:
    try:
        return orchestrator.run(search_request_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
