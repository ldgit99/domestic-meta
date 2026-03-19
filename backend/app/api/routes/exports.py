from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_store
from app.schemas.prisma import ExportPayloadRead
from app.services.export import ExportService


router = APIRouter(tags=["exports"])
service = ExportService()


@router.get("/search-requests/{search_request_id}/exports/candidates.csv", response_model=ExportPayloadRead)
def export_candidates_csv(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = service.candidates_csv(search_request_id, store.list_candidates(search_request_id))
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/screening-log.json", response_model=ExportPayloadRead)
def export_screening_log_json(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = service.screening_log_json(
        search_request_id,
        store.list_candidates(search_request_id),
        store.list_decisions_for_search(search_request_id),
    )
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/search-request.json", response_model=ExportPayloadRead)
def export_search_request_manifest_json(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    search_request = store.get_search_request(search_request_id)
    if search_request is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    payload = service.search_request_manifest_json(
        search_request,
        counts,
        store.list_candidates(search_request_id),
        store.list_decisions_for_search(search_request_id),
        store.list_extraction_results_for_search(search_request_id),
    )
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/prisma-counts.json", response_model=ExportPayloadRead)
def export_prisma_json(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    payload = service.prisma_json(search_request_id, counts)
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/prisma-flow.json", response_model=ExportPayloadRead)
def export_prisma_flow_json(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    payload = service.prisma_flow_json(search_request_id, counts)
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/extraction-results.json", response_model=ExportPayloadRead)
def export_extraction_results_json(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = service.extraction_results_json(
        search_request_id,
        store.list_extraction_results_for_search(search_request_id),
    )
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/meta-analysis-ready.csv", response_model=ExportPayloadRead)
def export_meta_analysis_ready_csv(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    if store.get_search_request(search_request_id) is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    payload = service.meta_analysis_ready_csv(
        search_request_id,
        store.list_candidates(search_request_id),
        store.list_decisions_for_search(search_request_id),
        store.list_extraction_results_for_search(search_request_id),
    )
    return ExportPayloadRead.model_validate(payload)


@router.get("/search-requests/{search_request_id}/exports/audit-report.md", response_model=ExportPayloadRead)
def export_audit_report(
    search_request_id: str,
    store=Depends(get_store),
) -> ExportPayloadRead:
    search_request = store.get_search_request(search_request_id)
    if search_request is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    counts = store.get_prisma_counts(search_request_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="PRISMA counts not found")
    payload = service.audit_report_markdown(
        search_request,
        counts,
        store.list_candidates(search_request_id),
        store.list_decisions_for_search(search_request_id),
        store.list_extraction_results_for_search(search_request_id),
    )
    return ExportPayloadRead.model_validate(payload)
