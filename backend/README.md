# Backend

FastAPI backend for the domestic education meta-analysis prototype.

## Implemented capabilities

- search request creation and lookup
- file-backed persistence
- optional `SQLAlchemy` persistence for `PostgreSQL` or `SQLite`
- rerun-safe orchestration
- candidate listing and candidate detail APIs
- title and abstract screening plus manual review
- PRISMA counts lookup
- PRISMA flow payload generation
- configurable `KCI` live-or-stub connector
- configurable `RISS` live-or-stub connector
- full-text registration
- TXT and PDF text ingestion
- OCR-required detection for scanned or textless PDFs
- optional OCR retry through an external command template
- OpenAI `Responses API` extraction path with heuristic fallback
- effect-size readiness summaries
- extraction quality assessment with evidence coverage and sample-size checks
- extraction revision persistence for every saved extraction result
- extraction revision restore workflow with event logging
- extraction revision comparison against the current result
- manual extraction override persistence with event logging
- export endpoints including audit and PRISMA flow payloads
- pipeline event logging for collection, screening, OCR, and extraction actions
- search manifest export with search criteria, counts, and PRISMA flow payload

## Repository backend modes

- `REPOSITORY_BACKEND=file`: JSON persistence under `backend/data/store.json`
- `REPOSITORY_BACKEND=sqlalchemy`: relational persistence using `DATABASE_URL`
- `AUTO_CREATE_TABLES=true|false`: dev convenience toggle for `Base.metadata.create_all(...)`
- `CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:5500`

Example:

- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rissmeta`

`SQLAlchemy` mode can auto-create tables at startup, but Alembic is now included for explicit
schema management.

## Alembic migrations

Initial Alembic scaffolding and an initial schema migration are included under `backend/alembic`.

Common commands:

```bash
cd backend
alembic upgrade head
alembic downgrade -1
```

Recommended usage:

- keep `AUTO_CREATE_TABLES=true` for quick local prototypes
- set `AUTO_CREATE_TABLES=false` when schema should be managed only through Alembic

## KCI collection

Live collection is enabled only when configured. Otherwise the connector falls back to stub data.

- `KCI_LIVE_ENABLED=true`
- `KCI_API_URL`
- `KCI_API_KEY`
- `KCI_API_KEY_PARAM`
- `KCI_QUERY_PARAM`
- `KCI_COUNT_PARAM`
- `KCI_YEAR_FROM_PARAM`
- `KCI_YEAR_TO_PARAM`
- `KCI_RESPONSE_FORMAT`

## RISS collection

Live collection is enabled only when configured. Otherwise the connector falls back to stub data.

- `RISS_LIVE_ENABLED=true`
- `RISS_API_URL`
- `RISS_API_KEY`
- `RISS_API_KEY_PARAM`
- `RISS_QUERY_PARAM`
- `RISS_COUNT_PARAM`
- `RISS_QUERY_MODE`
- `RISS_RESPONSE_FORMAT`
- `RISS_DOCUMENT_TYPE_PARAM`
- `RISS_THESIS_VALUE`
- `RISS_JOURNAL_VALUE`

The current connector accepts JSON, XML, and SPARQL-style `results.bindings` JSON payloads.

Source-specific query plans are now generated before collection:

- `KCI`: field-oriented OpenAPI keyword plan with optional year-bound parameters
- `RISS`: integrated-search query plan, with detail-search syntax intentionally left configurable per endpoint

## PRISMA flow endpoints

- `GET /api/search-requests/{id}/prisma/flow`
- `GET /api/search-requests/{id}/events`
- `GET /api/search-requests/{id}/exports/prisma-flow.json`
- `GET /api/search-requests/{id}/exports/events.json`
- `GET /api/search-requests/{id}/exports/search-request.json`
- `PUT /api/candidates/{id}/extraction`
- `GET /api/candidates/{id}/extraction-history`
- `POST /api/candidates/{id}/extraction-history/{revision_id}/restore`
- `GET /api/candidates/{id}/extraction-history/{revision_id}/compare-current`
- `GET /api/search-requests/{id}/exports/extraction-revisions.json`

The flow payload includes:

- nodes for identified, duplicate-removed, screened, retrieval, eligibility, and included stages
- edges describing stage transitions
- exclusion-reason counts keyed by recorded `reason_code`

The search manifest export includes:

- original search request criteria
- candidate, decision, extraction, and extraction revision counts
- source and status distributions
- full-text text-status distributions
- extraction quality score distributions
- PRISMA counts plus PRISMA flow payload

## OpenAI extraction

When configured, the backend attempts `Responses API` extraction with structured JSON output.
Otherwise it stores a heuristic fallback extraction with an attached quality assessment payload. Every saved extraction result is also appended to a revision history so the dashboard and exports can audit automatic runs and later manual overrides. A prior revision can be restored into the current extraction result through the restore endpoint or dashboard action.

- `OPENAI_API_KEY`
- `OPENAI_MODEL_EXTRACTION`
- `OPENAI_RESPONSES_URL`
- `OCR_COMMAND_TEMPLATE`
- `OCR_TIMEOUT_SECONDS`
- `OCR_MIN_TEXT_LENGTH`

Quick manual checks after `uvicorn app.main:app --reload`:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/docs`

## Running tests

```bash
cd backend
pip install -e .[test]
pytest tests
```

## Containerized run

From repository root:

```bash
docker compose up --build
```

The provided compose stack uses:

- `postgres` for `DATABASE_URL`
- `backend` with `REPOSITORY_BACKEND=sqlalchemy`
- `frontend` with an Nginx reverse proxy from `/api` to the backend

## Full-text ingestion endpoints

- `POST /api/candidates/{id}/full-text`
- `POST /api/candidates/{id}/full-text-file`
- `POST /api/candidates/{id}/ocr`

Uploaded files are stored under `backend/uploads`. TXT is read directly. PDF text extraction uses
`pypdf` when available. When usable text is not extracted, the artifact is marked
`ocr_required` and extraction is blocked until text is supplied.
If `OCR_COMMAND_TEMPLATE` is configured, the OCR endpoint can retry extraction against the stored
file and update the artifact to `available` when usable text is returned.

## Next work items

- production-safe RISS field mapping
- deployment validation for Alembic migrations
- OCR execution pipeline and stronger PDF parsing


