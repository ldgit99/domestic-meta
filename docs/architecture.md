# Architecture Notes

## Current implemented slice

- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/repositories/file_store.py`: JSON file-backed repository
- `backend/app/services/orchestrator.py`: collection, rerun reset, deduplication, title/abstract screening, PRISMA recalculation
- `backend/app/services/search_management.py`: manual review and full-text registration with PRISMA refresh
- `backend/app/services/extraction.py`: OpenAI Responses API extraction plus heuristic fallback
- `backend/app/services/extraction_workflow.py`: extraction execution and persistence
- `backend/app/services/connectors.py`: KCI live-or-stub connector plus RISS stub connector
- `frontend/index.html`: persistent search list, summary, PRISMA, export, and demo extraction controls

## Exposed APIs

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `POST /api/candidates/{id}/extract`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`
- `GET /api/search-requests/{id}/exports/extraction-results.json`
- `GET /api/search-requests/{id}/exports/meta-analysis-ready.csv`

## Runtime behavior

- search requests persist to `backend/data/store.json`
- rerunning a search resets prior candidates, decisions, artifacts, PRISMA counts, and extraction results for that search
- KCI collection uses live mode only when configured; otherwise it falls back to stub data
- extraction uses OpenAI only when configured; otherwise it falls back to heuristics

## Next implementation target

- real RISS Linked Data integration
- PDF parsing / OCR pipeline
- PostgreSQL persistence replacing file store
- richer review UI
