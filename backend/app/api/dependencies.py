from app.core.config import settings
from app.repositories.file_store import FileStore
from app.services.orchestrator import SearchOrchestrator
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


_store = FileStore(settings.store_file)
_prisma_service = PrismaService()
_orchestrator = SearchOrchestrator(store=_store)
_search_management = SearchManagementService(store=_store, prisma_service=_prisma_service)


def get_store() -> FileStore:
    return _store


def get_orchestrator() -> SearchOrchestrator:
    return _orchestrator


def get_search_management() -> SearchManagementService:
    return _search_management
