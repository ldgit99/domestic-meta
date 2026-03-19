from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_extraction_service, get_extraction_workflow, get_search_management, get_store
from app.repositories.file_store import FileStore
from app.schemas.candidate import (
    CandidateRead,
    DecisionCreate,
    EligibilityDecisionRead,
    ExtractionResultRead,
    FullTextArtifactCreate,
    FullTextArtifactRead,
)
from app.services.extraction import ExtractionService
from app.services.extraction_workflow import ExtractionWorkflowService
from app.services.search_management import SearchManagementService


router = APIRouter(tags=["candidates"])


@router.get("/search-requests/{search_request_id}/candidates", response_model=list[CandidateRead])
def list_candidates(
    search_request_id: str,
    store: FileStore = Depends(get_store),
) -> list[CandidateRead]:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    items = sorted(
        store.list_candidates(search_request_id),
        key=lambda item: (item.canonical_record_id != item.id, item.year * -1, item.title),
    )
    return [CandidateRead.model_validate(item) for item in items]


@router.post("/candidates/{candidate_id}/decision", response_model=EligibilityDecisionRead)
def create_decision(
    candidate_id: str,
    payload: DecisionCreate,
    search_management: SearchManagementService = Depends(get_search_management),
) -> EligibilityDecisionRead:
    created = search_management.create_manual_decision(candidate_id, payload)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return EligibilityDecisionRead.model_validate(created)


@router.post("/candidates/{candidate_id}/full-text", response_model=FullTextArtifactRead)
def upload_full_text(
    candidate_id: str,
    payload: FullTextArtifactCreate,
    search_management: SearchManagementService = Depends(get_search_management),
) -> FullTextArtifactRead:
    created = search_management.register_full_text(candidate_id, payload)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FullTextArtifactRead.model_validate(created)


@router.post("/candidates/{candidate_id}/extract", response_model=ExtractionResultRead)
def run_extraction(
    candidate_id: str,
    extraction_workflow: ExtractionWorkflowService = Depends(get_extraction_workflow),
) -> ExtractionResultRead:
    created = extraction_workflow.run(candidate_id)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return ExtractionResultRead.model_validate(created)


@router.get("/candidates/{candidate_id}/extraction", response_model=ExtractionResultRead)
def preview_extraction(
    candidate_id: str,
    store: FileStore = Depends(get_store),
    extraction_service: ExtractionService = Depends(get_extraction_service),
) -> ExtractionResultRead:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    existing = store.get_extraction_result(candidate_id)
    artifact = store.get_full_text_artifact(candidate_id)
    payload = extraction_service.preview(candidate, artifact, existing=existing)
    return ExtractionResultRead.model_validate(payload)
