# Architecture Notes

## Current implemented slice

- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/repositories/file_store.py`: JSON file-backed repository
- `backend/app/services/orchestrator.py`: collection, deduplication, title/abstract screening, PRISMA recalculation
- `backend/app/services/search_management.py`: manual review and full-text registration with PRISMA refresh
- `backend/app/services/connectors.py`: KCI/RISS stub connectors
- `frontend/index.html`: persistent search list, summary, PRISMA, and export viewing

## Exposed APIs

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`

## Next implementation target

- real KCI Open API / OAI-PMH integration
- RISS Linked Data integration
- OpenAI Responses API + Structured Outputs extraction
- PostgreSQL persistence replacing file store
- richer review UI
