from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_orchestrator, get_store
from app.repositories.file_store import FileStore
from app.schemas.search import (
    SearchRequestCreate,
    SearchRequestRead,
    SearchRequestSummaryRead,
    SearchRunResult,
)
from app.services.orchestrator import SearchOrchestrator


router = APIRouter(prefix="/search-requests", tags=["search-requests"])


@router.get("", response_model=list[SearchRequestRead])
def list_search_requests(store: FileStore = Depends(get_store)) -> list[SearchRequestRead]:
    return [SearchRequestRead.model_validate(item) for item in store.list_search_requests()]


@router.post("", response_model=SearchRequestRead)
def create_search_request(
    payload: SearchRequestCreate,
    store: FileStore = Depends(get_store),
) -> SearchRequestRead:
    created = store.create_search_request(payload)
    return SearchRequestRead.model_validate(created)


@router.get("/{search_request_id}", response_model=SearchRequestRead)
def get_search_request(
    search_request_id: str,
    store: FileStore = Depends(get_store),
) -> SearchRequestRead:
    result = store.get_search_request(search_request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    return SearchRequestRead.model_validate(result)


@router.get("/{search_request_id}/summary", response_model=SearchRequestSummaryRead)
def get_search_request_summary(
    search_request_id: str,
    store: FileStore = Depends(get_store),
) -> SearchRequestSummaryRead:
    result = store.get_search_request(search_request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Search request not found")

    candidates = store.list_candidates(search_request_id)
    decisions = store.list_decisions_for_search(search_request_id)
    canonical_count = len([item for item in candidates if item.canonical_record_id == item.id])
    prisma = store.get_prisma_counts(search_request_id)
    source_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for candidate in candidates:
        source_counts[candidate.source] = source_counts.get(candidate.source, 0) + 1
        status_counts[candidate.status] = status_counts.get(candidate.status, 0) + 1

    return SearchRequestSummaryRead(
        id=result.id,
        query_text=result.query_text,
        expanded_keywords=result.expanded_keywords,
        year_from=result.year_from,
        year_to=result.year_to,
        include_theses=result.include_theses,
        include_journal_articles=result.include_journal_articles,
        inclusion_rules=result.inclusion_rules,
        exclusion_rules=result.exclusion_rules,
        status=result.status,
        candidate_count=len(candidates),
        canonical_candidate_count=canonical_count,
        decision_count=len(decisions),
        source_counts=source_counts,
        status_counts=status_counts,
        prisma=prisma,
    )


@router.get("/{search_request_id}/status")
def get_search_request_status(
    search_request_id: str,
    store: FileStore = Depends(get_store),
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
