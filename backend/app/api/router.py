from fastapi import APIRouter

from app.api.routes import candidates, exports, prisma, search_requests


api_router = APIRouter(prefix="/api")
api_router.include_router(search_requests.router)
api_router.include_router(candidates.router)
api_router.include_router(prisma.router)
api_router.include_router(exports.router)
