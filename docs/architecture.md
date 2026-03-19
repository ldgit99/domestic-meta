# Architecture Notes

## Current implemented slice

- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/repositories/file_store.py`: JSON file-backed repository
- `backend/app/repositories/sqlalchemy_store.py`: `SQLAlchemy` repository for `PostgreSQL` or `SQLite`
- `backend/alembic`: Alembic environment and initial relational migration
- `backend/app/repositories/db_models.py`: relational schema for searches, candidates, decisions, PRISMA, artifacts, and extraction results
- `backend/app/services/orchestrator.py`: collection, reset-on-rerun, deduplication, title and abstract screening, PRISMA recalculation
- `backend/app/services/search_management.py`: manual review and full-text registration with PRISMA refresh
- `backend/app/services/document_ingestion.py`: uploaded TXT and PDF persistence plus text extraction
- `backend/app/services/prisma.py`: PRISMA count recomputation and flow payload generation
- `backend/app/services/review.py`: candidate detail assembly and review queue generation
- `backend/app/services/extraction.py`: OpenAI `Responses API` extraction plus heuristic fallback
- `backend/app/services/extraction_workflow.py`: extraction execution and persistence
- `backend/app/services/effect_size.py`: effect-size-readiness summaries
- `backend/app/services/connectors.py`: `KCI` and `RISS` live-or-stub connectors
- `frontend/index.html`: static dashboard for search orchestration, review, PRISMA inspection, and extraction

## Exposed APIs

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `GET /api/search-requests/{id}/review-queue`
- `GET /api/candidates/{id}`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `POST /api/candidates/{id}/full-text-file`
- `POST /api/candidates/{id}/extract`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/prisma/flow`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/search-request.json`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`
- `GET /api/search-requests/{id}/exports/prisma-flow.json`
- `GET /api/search-requests/{id}/exports/extraction-results.json`
- `GET /api/search-requests/{id}/exports/meta-analysis-ready.csv`
- `GET /api/search-requests/{id}/exports/audit-report.md`

## Runtime behavior

- storage backend is selected by `REPOSITORY_BACKEND`
- `file` mode persists state under `backend/data/store.json`
- `sqlalchemy` mode persists state to `DATABASE_URL` and can auto-create tables when enabled
- `AUTO_CREATE_TABLES` controls whether `SQLAlchemyStore` calls `Base.metadata.create_all(...)`
- Alembic can manage the same schema through `backend/alembic` and `alembic upgrade head`
- uploaded files persist under `backend/uploads`
- rerunning a search clears prior candidates, decisions, PRISMA counts, artifacts, and extraction results for that search
- `KCI` live collection is attempted only when configured; otherwise the service falls back to stub data
- `RISS` live collection is attempted only when configured; otherwise the service falls back to stub data
- document ingestion extracts text from TXT directly and from PDF through `pypdf` when available
- manual screening immediately refreshes PRISMA counts and downstream review state
- PRISMA flow payloads are derived from persisted PRISMA counts plus exclusion reason counts
- extraction uses OpenAI only when configured and otherwise stores heuristic fallback output
- effect-size readiness is computed from extracted statistics and included in review outputs and exports

## Current dashboard behavior

- create and run a search request
- open recent searches from persisted storage
- inspect candidate lists and candidate detail payloads
- submit manual title and abstract decisions
- inspect PRISMA counts and a PRISMA flow payload view
- upload TXT or PDF full text
- run extraction and inspect extraction JSON
- preview export payloads for candidates, screening logs, PRISMA counts, PRISMA flow, meta-analysis CSV, and audit reports
- preview a reproducible search manifest export with criteria, counts, and PRISMA flow payload

## Next implementation targets

- production-safe `RISS` response mapping
- deployment validation and rollback procedures for Alembic-managed `PostgreSQL`
- OCR pipeline and stronger PDF parsing
- authentication and user-level isolation
