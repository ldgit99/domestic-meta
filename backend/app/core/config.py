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
    riss_live_enabled: bool = os.getenv("RISS_LIVE_ENABLED", "false").lower() == "true"
    riss_api_url: str | None = os.getenv("RISS_API_URL")
    riss_api_key: str | None = os.getenv("RISS_API_KEY")
    riss_api_key_param: str = os.getenv("RISS_API_KEY_PARAM", "apiKey")
    riss_query_param: str = os.getenv("RISS_QUERY_PARAM", "keyword")
    riss_count_param: str = os.getenv("RISS_COUNT_PARAM", "count")
    riss_response_format: str = os.getenv("RISS_RESPONSE_FORMAT", "json")
    riss_document_type_param: str | None = os.getenv("RISS_DOCUMENT_TYPE_PARAM")
    riss_thesis_value: str = os.getenv("RISS_THESIS_VALUE", "thesis")
    riss_journal_value: str = os.getenv("RISS_JOURNAL_VALUE", "journal")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model_extraction: str = os.getenv("OPENAI_MODEL_EXTRACTION", "gpt-4o-mini")
    openai_responses_url: str = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
