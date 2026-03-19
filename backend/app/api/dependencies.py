from app.repositories.memory import MemoryStore
from app.services.orchestrator import SearchOrchestrator
from app.services.prisma import PrismaService
from app.services.search_management import SearchManagementService


_store = MemoryStore()
_prisma_service = PrismaService()
_orchestrator = SearchOrchestrator(store=_store)
_search_management = SearchManagementService(store=_store, prisma_service=_prisma_service)


def get_store() -> MemoryStore:
    return _store


def get_orchestrator() -> SearchOrchestrator:
    return _orchestrator


def get_search_management() -> SearchManagementService:
    return _search_management
