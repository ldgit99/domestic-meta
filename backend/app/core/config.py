from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseModel):
    app_name: str = "RISS Meta Agent API"
    environment: str = "development"
    uploads_dir: str = str(BASE_DIR / "uploads")
    exports_dir: str = str(BASE_DIR / "exports")
    data_dir: str = str(DATA_DIR)
    store_file: str = str(DATA_DIR / "store.json")


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
