# domestic-meta

Prototype repository for a domestic education meta-analysis agent built around `RISS`, `KCI`,
`PRISMA 2020`, and OpenAI-assisted extraction workflows.

The repository already includes research and planning documents plus a working prototype slice:

- `research.md`: Korean research memo for the product and feasibility study
- `plan.md`: implementation plan and execution roadmap
- `docs/architecture.md`: current architecture notes
- `backend`: FastAPI API, orchestration, storage, screening, export, and extraction services
- `frontend`: static dashboard for search, review, PRISMA inspection, and extraction

## Current prototype scope

- search request creation, rerun-safe execution, and summary APIs
- file-backed repository plus optional `SQLAlchemy` persistence for `PostgreSQL` or `SQLite`
- configurable live-or-stub collection for `KCI`
- configurable live-or-stub collection for `RISS`
- deduplication and canonical record management
- title and abstract screening plus manual review actions
- PRISMA counts recalculation
- PRISMA flow payload generation and export
- candidate detail view and review queue assembly
- TXT and PDF full-text ingestion
- OCR-required detection when PDF text extraction yields no usable text
- optional OCR retry through a configurable external command
- OpenAI `Responses API` extraction path with heuristic fallback
- effect-size readiness summaries, extraction quality assessment, manual extraction overrides, and meta-analysis-ready CSV export
- pipeline event logging, timeline inspection, and events export
- export endpoints for search manifests, candidates, screening, PRISMA, extraction, meta-analysis, and audit reports

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

Default API base: `http://127.0.0.1:8000`

The file-backed repository persists under `backend/data/store.json`.
Uploaded full-text artifacts persist under `backend/uploads`.

### Configuration

Use `backend/.env.example` as the starting point for:

- repository backend selection
- `KCI` live collection settings
- `RISS` live collection settings
- OpenAI extraction settings

Key settings:

- `REPOSITORY_BACKEND=file|sqlalchemy`
- `DATABASE_URL=postgresql+psycopg://...`
- `AUTO_CREATE_TABLES=true|false`
- `KCI_LIVE_ENABLED=true`
- `RISS_LIVE_ENABLED=true`
- `OPENAI_API_KEY=...`
- `OCR_COMMAND_TEMPLATE=tesseract {input_path} stdout -l kor+eng`
- `CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:5500`

When live collection or OpenAI extraction is not configured, the prototype falls back to local
stub data or heuristic extraction.
If uploaded PDF text extraction fails or returns no usable text, the candidate remains in an
OCR-needed state until manual text or an OCR-derived text file is supplied.

If you are using `REPOSITORY_BACKEND=sqlalchemy` for a persistent relational database, prefer:

- `alembic upgrade head` to create or advance schema
- `AUTO_CREATE_TABLES=false` in shared or production environments

### Frontend

Open `frontend/index.html` in a browser while the backend is running.
When the page is served through a web server, it defaults to `window.location.origin + "/api"`.
When opened from `file://`, it falls back to `http://127.0.0.1:8000/api`.

The dashboard currently supports:

- running a search request
- opening recent searches
- inspecting candidates and review queues
- submitting manual screening decisions
- rendering PRISMA counts and PRISMA flow payloads
- uploading TXT or PDF full text
- surfacing `full_text_needs_ocr` and `ocr_required` states in review flows
- rerunning OCR on stored PDF files when an external OCR command is configured
- running extraction
- surfacing extraction quality scores and review warnings in candidate detail and exports
- editing and saving manual extraction overrides from the dashboard
- previewing export content
- exporting a reproducible search manifest with criteria and PRISMA flow payloads

## Key API endpoints

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

## Docker

Run the full stack with:

```bash
docker compose up --build
```

Services:

- `frontend`: `http://127.0.0.1:8080`
- `backend`: internal API served behind the frontend reverse proxy
- `postgres`: persistent relational database for `SQLAlchemy` mode

The bundled frontend container proxies `/api` to the backend container, so no manual API base
override is needed in that setup.

## CI

GitHub Actions now runs backend tests on pushes and pull requests with:

```bash
cd backend
pip install -e .[test]
pytest tests
```

## Open items

- production validation of `RISS` endpoint mapping
- deployment pipeline validation for Alembic-based `PostgreSQL` upgrades
- OCR execution pipeline and stronger PDF parsing
- authentication and multi-user separation