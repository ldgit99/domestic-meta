import os
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseModel):
    app_name: str = "RISS Meta Agent API"
    environment: str = os.getenv("APP_ENV", "development")
    cors_allow_origins: list[str] = [
        item.strip()
        for item in os.getenv("CORS_ALLOW_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5500,http://localhost:5500").split(",")
        if item.strip()
    ]
    uploads_dir: str = str(BASE_DIR / "uploads")
    exports_dir: str = str(BASE_DIR / "exports")
    data_dir: str = str(DATA_DIR)
    store_file: str = str(DATA_DIR / "store.json")
    repository_backend: str = os.getenv("REPOSITORY_BACKEND", "file").lower()
    database_url: str | None = os.getenv("DATABASE_URL")
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
    kci_live_enabled: bool = os.getenv("KCI_LIVE_ENABLED", "false").lower() == "true"
    kci_api_url: str | None = os.getenv("KCI_API_URL")
    kci_api_key: str | None = os.getenv("KCI_API_KEY")
    kci_api_key_param: str = os.getenv("KCI_API_KEY_PARAM", "apiKey")
    kci_query_param: str = os.getenv("KCI_QUERY_PARAM", "keyword")
    kci_count_param: str = os.getenv("KCI_COUNT_PARAM", "displayCount")
    kci_year_from_param: str | None = os.getenv("KCI_YEAR_FROM_PARAM")
    kci_year_to_param: str | None = os.getenv("KCI_YEAR_TO_PARAM")
    kci_response_format: str = os.getenv("KCI_RESPONSE_FORMAT", "xml")
    riss_live_enabled: bool = os.getenv("RISS_LIVE_ENABLED", "false").lower() == "true"
    riss_api_url: str | None = os.getenv("RISS_API_URL")
    riss_api_key: str | None = os.getenv("RISS_API_KEY")
    riss_api_key_param: str = os.getenv("RISS_API_KEY_PARAM", "apiKey")
    riss_query_param: str = os.getenv("RISS_QUERY_PARAM", "keyword")
    riss_count_param: str = os.getenv("RISS_COUNT_PARAM", "count")
    riss_query_mode: str = os.getenv("RISS_QUERY_MODE", "integrated").lower()
    riss_response_format: str = os.getenv("RISS_RESPONSE_FORMAT", "json")
    riss_document_type_param: str | None = os.getenv("RISS_DOCUMENT_TYPE_PARAM")
    riss_thesis_value: str = os.getenv("RISS_THESIS_VALUE", "thesis")
    riss_journal_value: str = os.getenv("RISS_JOURNAL_VALUE", "journal")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model_extraction: str = os.getenv("OPENAI_MODEL_EXTRACTION", "gpt-4o-mini")
    openai_responses_url: str = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
    ocr_command_template: str | None = os.getenv("OCR_COMMAND_TEMPLATE")
    ocr_timeout_seconds: int = int(os.getenv("OCR_TIMEOUT_SECONDS", "180"))
    ocr_min_text_length: int = int(os.getenv("OCR_MIN_TEXT_LENGTH", "20"))


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
