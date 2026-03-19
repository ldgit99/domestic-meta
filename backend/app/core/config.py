from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "RISS Meta Agent API"
    environment: str = "development"
    uploads_dir: str = "uploads"
    exports_dir: str = "exports"


settings = Settings()
