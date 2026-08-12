from fastapi import APIRouter

from . import health, risk

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(risk.router)

__all__ = ["api_router"]
