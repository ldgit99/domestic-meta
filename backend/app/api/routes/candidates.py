from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.repositories.memory import MemoryStore
from app.schemas.candidate import CandidateRead, DecisionCreate, EligibilityDecisionRead


router = APIRouter(tags=["candidates"])


@router.get("/search-requests/{search_request_id}/candidates", response_model=list[CandidateRead])
def list_candidates(
    search_request_id: str,
    store: MemoryStore = Depends(get_store),
) -> list[CandidateRead]:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    return [CandidateRead.model_validate(item) for item in store.list_candidates(search_request_id)]


@router.post("/candidates/{candidate_id}/decision", response_model=EligibilityDecisionRead)
def create_decision(
    candidate_id: str,
    payload: DecisionCreate,
    store: MemoryStore = Depends(get_store),
) -> EligibilityDecisionRead:
    created = store.create_decision(candidate_id, payload)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return EligibilityDecisionRead.model_validate(created)
