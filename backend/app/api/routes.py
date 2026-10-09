from fastapi import APIRouter

from app.api import compilation, health, toolchain

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(toolchain.router)
api_router.include_router(compilation.router)
