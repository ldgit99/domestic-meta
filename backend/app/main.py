from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title="RISS Meta Agent API",
    version="0.1.0",
    description="Education meta-analysis support API scaffold.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_INDEX = _REPO_ROOT / "frontend" / "index.html"


def _service_index(base_path: str = "") -> dict[str, object]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "api_base": f"{base_path}/api" if base_path else "/api",
        "dashboard_url": "/dashboard",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_urls": ["/health", "/api/health"],
        "key_endpoints": [
            "/api/search-requests",
            "/api/search-requests/{id}/run",
            "/api/search-requests/{id}/summary",
            "/api/search-requests/{id}/candidates",
            "/api/candidates/{id}",
            "/api/candidates/{id}/extract",
        ],
    }


@app.get("/")
def root() -> dict[str, object]:
    return _service_index()


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    if not _FRONTEND_INDEX.exists():
        raise HTTPException(status_code=503, detail="Dashboard frontend is not available")
    return FileResponse(_FRONTEND_INDEX)


@app.get("/api")
def api_root() -> dict[str, object]:
    payload = _service_index()
    payload["message"] = "Use /docs for interactive API docs, /dashboard for the web UI, or call the listed /api endpoints directly."
    return payload


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
def api_healthcheck() -> dict[str, str]:
    return {"status": "ok"}
