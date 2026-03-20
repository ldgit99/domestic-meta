from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import (
    get_document_ingestion,
    get_extraction_management,
    get_extraction_service,
    get_extraction_workflow,
    get_ocr_service,
    get_review_service,
    get_search_management,
    get_store,
)
from app.repositories.file_store import FileStore
from app.schemas.candidate import (
    CandidateDetailRead,
    CandidateQueueItemRead,
    CandidateRead,
    DecisionCreate,
    EligibilityDecisionRead,
    ExtractionResultRead,
    ExtractionResultUpdate,
    ExtractionRevisionRead,
    ExtractionRevisionRestoreCreate,
    FullTextArtifactCreate,
    FullTextArtifactRead,
    OCRRunRead,
)
from app.services.document_ingestion import DocumentIngestionService
from app.services.extraction import ExtractionService
from app.services.extraction_management import ExtractionManagementService
from app.services.extraction_workflow import ExtractionWorkflowService
from app.services.ocr import OCRService
from app.services.review import ReviewService
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


@router.get("/search-requests/{search_request_id}/review-queue", response_model=list[CandidateQueueItemRead])
def list_review_queue(
    search_request_id: str,
    store: FileStore = Depends(get_store),
    review_service: ReviewService = Depends(get_review_service),
) -> list[CandidateQueueItemRead]:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = review_service.build_review_queue(search_request_id)
    return [CandidateQueueItemRead.model_validate(item) for item in payload]


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailRead)
def get_candidate_detail(
    candidate_id: str,
    review_service: ReviewService = Depends(get_review_service),
) -> CandidateDetailRead:
    payload = review_service.get_candidate_detail(candidate_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateDetailRead.model_validate(payload)


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


@router.post("/candidates/{candidate_id}/full-text-file", response_model=FullTextArtifactRead)
async def upload_full_text_file(
    candidate_id: str,
    file: UploadFile = File(...),
    ingestion: DocumentIngestionService = Depends(get_document_ingestion),
    search_management: SearchManagementService = Depends(get_search_management),
) -> FullTextArtifactRead:
    content = await file.read()
    payload = ingestion.ingest_bytes(
        candidate_id=candidate_id,
        file_name=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    created = search_management.register_full_text(candidate_id, payload)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FullTextArtifactRead.model_validate(created)


@router.post("/candidates/{candidate_id}/ocr", response_model=OCRRunRead)
def run_ocr(
    candidate_id: str,
    ocr_service: OCRService = Depends(get_ocr_service),
) -> OCRRunRead:
    payload = ocr_service.run(candidate_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return OCRRunRead.model_validate(payload)


@router.post("/candidates/{candidate_id}/extract", response_model=ExtractionResultRead)
def run_extraction(
    candidate_id: str,
    extraction_workflow: ExtractionWorkflowService = Depends(get_extraction_workflow),
) -> ExtractionResultRead:
    created = extraction_workflow.run(candidate_id)
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return ExtractionResultRead.model_validate(created)


@router.put("/candidates/{candidate_id}/extraction", response_model=ExtractionResultRead)
def save_manual_extraction(
    candidate_id: str,
    payload: ExtractionResultUpdate,
    extraction_management: ExtractionManagementService = Depends(get_extraction_management),
) -> ExtractionResultRead:
    created = extraction_management.save_manual_result(candidate_id, payload)
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


@router.post("/candidates/{candidate_id}/extraction-history/{revision_id}/restore", response_model=ExtractionResultRead)
def restore_extraction_revision(
    candidate_id: str,
    revision_id: str,
    payload: ExtractionRevisionRestoreCreate,
    extraction_management: ExtractionManagementService = Depends(get_extraction_management),
) -> ExtractionResultRead:
    try:
        created = extraction_management.restore_revision(candidate_id, revision_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return ExtractionResultRead.model_validate(created)


@router.get("/candidates/{candidate_id}/extraction-history", response_model=list[ExtractionRevisionRead])
def get_extraction_history(
    candidate_id: str,
    store: FileStore = Depends(get_store),
) -> list[ExtractionRevisionRead]:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    payload = store.list_extraction_revisions(candidate_id)
    return [ExtractionRevisionRead.model_validate(item) for item in payload]
