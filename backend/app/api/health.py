"""Liveness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.config import Settings, get_settings
from backend.app.models import HealthResponse
from risk_engine import ENGINE_VERSION

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Report service liveness and the versions in use."""
    return HealthResponse(
        status="ok",
        api_version=settings.api_version,
        engine_version=ENGINE_VERSION,
    )
