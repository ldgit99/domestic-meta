import os
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseModel):
    app_name: str = "RISS Meta Agent API"
    environment: str = os.getenv("APP_ENV", "development")
    uploads_dir: str = str(BASE_DIR / "uploads")
    exports_dir: str = str(BASE_DIR / "exports")
    data_dir: str = str(DATA_DIR)
    store_file: str = str(DATA_DIR / "store.json")
    kci_live_enabled: bool = os.getenv("KCI_LIVE_ENABLED", "false").lower() == "true"
    kci_api_url: str | None = os.getenv("KCI_API_URL")
    kci_api_key: str | None = os.getenv("KCI_API_KEY")
    kci_api_key_param: str = os.getenv("KCI_API_KEY_PARAM", "apiKey")
    kci_query_param: str = os.getenv("KCI_QUERY_PARAM", "keyword")
    kci_count_param: str = os.getenv("KCI_COUNT_PARAM", "displayCount")
    kci_response_format: str = os.getenv("KCI_RESPONSE_FORMAT", "xml")


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
