"""FastAPI application entry point.

Run from the repository root so that ``risk_engine`` is importable::

    uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import api_router
from backend.app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        description=(
            "Research API for adaptive perpetual futures risk parameters, over "
            "synthetic data only. Two engines: `/risk/evaluate` is the v0 "
            "composite-score heuristic; `/risk/v1/evaluate` is the v1 "
            "five-dimension model, which can answer that a market supports no "
            "viable continuous perp at any margin level. Nothing here is "
            "calibrated to a real market."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
