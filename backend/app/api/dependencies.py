from app.core.config import settings
from app.repositories.file_store import FileStore
from app.repositories.sqlalchemy_store import SQLAlchemyStore
from app.services.document_ingestion import DocumentIngestionService
from app.services.effect_size import EffectSizeService
from app.services.extraction import ExtractionService
from app.services.extraction_workflow import ExtractionWorkflowService
from app.services.ocr import OCRService
from app.services.orchestrator import SearchOrchestrator
from app.services.prisma import PrismaService
from app.services.quality import QualityAssessmentService
from app.services.review import ReviewService
from app.services.search_management import SearchManagementService


def _build_store():
    if settings.repository_backend == "file":
        return FileStore(settings.store_file)
    if settings.repository_backend == "sqlalchemy":
        if not settings.database_url:
            raise ValueError("DATABASE_URL must be set when REPOSITORY_BACKEND=sqlalchemy")
        return SQLAlchemyStore(
            settings.database_url,
            auto_create_tables=settings.auto_create_tables,
        )
    raise ValueError(f"Unsupported REPOSITORY_BACKEND: {settings.repository_backend}")


_store = _build_store()
_prisma_service = PrismaService()
_document_ingestion = DocumentIngestionService()
_effect_size_service = EffectSizeService()
_quality_service = QualityAssessmentService()
_extraction_service = ExtractionService()
_orchestrator = SearchOrchestrator(store=_store)
_search_management = SearchManagementService(store=_store, prisma_service=_prisma_service)
_ocr_service = OCRService(
    store=_store,
    search_management=_search_management,
    command_template=settings.ocr_command_template,
    timeout_seconds=settings.ocr_timeout_seconds,
    min_text_length=settings.ocr_min_text_length,
)
_extraction_workflow = ExtractionWorkflowService(
    store=_store,
    extraction_service=_extraction_service,
    ocr_service=_ocr_service,
)
_review_service = ReviewService(
    store=_store,
    effect_size_service=_effect_size_service,
    quality_service=_quality_service,
)


def get_store():
    return _store


def get_orchestrator() -> SearchOrchestrator:
    return _orchestrator


def get_search_management() -> SearchManagementService:
    return _search_management


def get_document_ingestion() -> DocumentIngestionService:
    return _document_ingestion


def get_effect_size_service() -> EffectSizeService:
    return _effect_size_service


def get_quality_service() -> QualityAssessmentService:
    return _quality_service


def get_extraction_service() -> ExtractionService:
    return _extraction_service


def get_extraction_workflow() -> ExtractionWorkflowService:
    return _extraction_workflow


def get_ocr_service() -> OCRService:
    return _ocr_service


def get_review_service() -> ReviewService:
    return _review_service