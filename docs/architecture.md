# Architecture Notes

## Current implemented slice

- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/services/orchestrator.py`: collection, deduplication, title/abstract screening, PRISMA recalculation
- `backend/app/services/connectors.py`: KCI/RISS stub connectors
- `backend/app/repositories/memory.py`: in-memory store
- `frontend/index.html`: static prototype for triggering a search and viewing summary output

## Exposed APIs

- `POST /api/search-requests`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/exports/candidates.csv`

## Next implementation target

- PostgreSQL persistence
- real KCI Open API / OAI-PMH integration
- RISS Linked Data integration
- OpenAI Responses API + Structured Outputs extraction
- richer review UI
