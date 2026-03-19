from fastapi import FastAPI

from app.api.router import api_router


app = FastAPI(
    title="RISS Meta Agent API",
    version="0.1.0",
    description="Education meta-analysis support API scaffold.",
)

app.include_router(api_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
