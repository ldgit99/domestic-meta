from app.core.config import settings
from app.repositories.file_store import FileStore
from app.services.document_ingestion import DocumentIngestionService
from app.services.effect_size import EffectSizeService
from app.services.extraction import ExtractionService
from app.services.extraction_workflow import ExtractionWorkflowService
from app.services.orchestrator import SearchOrchestrator
from app.services.prisma import PrismaService
from app.services.review import ReviewService
from app.services.search_management import SearchManagementService


_store = FileStore(settings.store_file)
_prisma_service = PrismaService()
_document_ingestion = DocumentIngestionService()
_effect_size_service = EffectSizeService()
_extraction_service = ExtractionService()
_orchestrator = SearchOrchestrator(store=_store)
_search_management = SearchManagementService(store=_store, prisma_service=_prisma_service)
_extraction_workflow = ExtractionWorkflowService(store=_store, extraction_service=_extraction_service)
_review_service = ReviewService(store=_store, effect_size_service=_effect_size_service)


def get_store() -> FileStore:
    return _store


def get_orchestrator() -> SearchOrchestrator:
    return _orchestrator


def get_search_management() -> SearchManagementService:
    return _search_management


def get_document_ingestion() -> DocumentIngestionService:
    return _document_ingestion


def get_effect_size_service() -> EffectSizeService:
    return _effect_size_service


def get_extraction_service() -> ExtractionService:
    return _extraction_service


def get_extraction_workflow() -> ExtractionWorkflowService:
    return _extraction_workflow


def get_review_service() -> ReviewService:
    return _review_service
