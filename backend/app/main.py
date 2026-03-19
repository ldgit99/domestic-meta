from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router


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


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
