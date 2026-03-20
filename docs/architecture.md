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
- `backend/app/services/ocr.py`: optional OCR retry runner for stored artifacts
- `backend/app/services/prisma.py`: PRISMA count recomputation and flow payload generation
- `backend/app/services/review.py`: candidate detail assembly and review queue generation
- `backend/app/services/extraction.py`: OpenAI `Responses API` extraction plus heuristic fallback
- `backend/app/services/extraction_workflow.py`: extraction execution and persistence
- `backend/app/services/extraction_management.py`: manual extraction override persistence and audit logging
- `backend/app/services/effect_size.py`: effect-size-readiness summaries
- `backend/app/services/quality.py`: extraction quality scoring, evidence coverage checks, and sample-size consistency checks
- `backend/app/services/connectors.py`: `KCI` and `RISS` live-or-stub connectors
- `frontend/index.html`: static dashboard for search orchestration, review, PRISMA inspection, and extraction

## Exposed APIs

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `GET /api/search-requests/{id}/events`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `GET /api/search-requests/{id}/review-queue`
- `GET /api/candidates/{id}`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `POST /api/candidates/{id}/full-text-file`
- `POST /api/candidates/{id}/ocr`
- `POST /api/candidates/{id}/extract`
- `PUT /api/candidates/{id}/extraction`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/prisma/flow`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/search-request.json`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`
- `GET /api/search-requests/{id}/exports/prisma-flow.json`
- `GET /api/search-requests/{id}/exports/events.json`
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
- failed or empty PDF extraction is persisted as `ocr_required`, which keeps the candidate in review until usable text exists
- a configurable OCR command can be invoked later to update the stored artifact and candidate status
- manual screening immediately refreshes PRISMA counts and downstream review state
- pipeline events are persisted for search creation, orchestration, manual review, OCR, and extraction transitions
- PRISMA flow payloads are derived from persisted PRISMA counts plus exclusion reason counts
- extraction uses OpenAI only when configured and otherwise stores heuristic fallback output
- effect-size readiness is computed from extracted statistics and included in review outputs and exports
- extraction results carry a `quality_assessment` payload that feeds review priority, manifests, audit reports, and meta-analysis exports
- reviewed extraction JSON can be manually overridden without losing audit metadata, and the override is logged as a pipeline event

## Current dashboard behavior

- create and run a search request
- open recent searches from persisted storage
- inspect candidate lists and candidate detail payloads
- review a search activity timeline with recent pipeline events
- submit manual title and abstract decisions
- inspect PRISMA counts and a PRISMA flow payload view
- upload TXT or PDF full text
- surface OCR-needed states through candidate detail, review queue, summary payloads, and exports
- trigger OCR retries against stored full-text files
- run extraction and inspect extraction JSON
- edit extraction JSON for the selected candidate and save a manual override back to the backend
- surface extraction quality scores and warnings in candidate detail and review outputs
- preview export payloads for candidates, screening logs, PRISMA counts, PRISMA flow, meta-analysis CSV, and audit reports
- preview a reproducible search manifest export with criteria, counts, and PRISMA flow payload

## Deployment and verification slice

- `docker-compose.yml` runs `frontend`, `backend`, and `postgres` as a local integration stack
- `backend/Dockerfile` packages the FastAPI service and is paired with `alembic upgrade head` in compose startup
- `frontend/Dockerfile` and `frontend/nginx.conf` serve the static dashboard and reverse-proxy `/api` to the backend container
- `.github/workflows/ci.yml` runs backend tests inside the `backend` working directory with editable installs
- the dashboard now resolves its API base from same-origin hosting by default and falls back to `http://127.0.0.1:8000/api` only under `file://`
## Next implementation targets

- production-safe `RISS` response mapping
- deployment validation and rollback procedures for Alembic-managed `PostgreSQL`
- OCR pipeline and stronger PDF parsing
- authentication and user-level isolation