from app.repositories.memory import MemoryStore
from app.services.orchestrator import SearchOrchestrator


_store = MemoryStore()
_orchestrator = SearchOrchestrator(store=_store)


def get_store() -> MemoryStore:
    return _store


def get_orchestrator() -> SearchOrchestrator:
    return _orchestrator
