from fastapi import APIRouter

from app.api.routes import candidates, prisma, search_requests


api_router = APIRouter(prefix="/api")
api_router.include_router(search_requests.router)
api_router.include_router(candidates.router)
api_router.include_router(prisma.router)
