"""
arbiter/api/routes/health.py
----------------------------
Health and readiness probe endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from arbiter.api.dependencies import get_config, get_store
from arbiter.api.schemas import HealthResponse, ReadinessResponse
from arbiter.config import Config
from arbiter.data_store import DataStore

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
async def health_check() -> HealthResponse:
    """Lightweight liveness probe checking whether the application process is running."""
    return HealthResponse(status="ok", service="arbiter")


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness Probe")
async def readiness_check(
    store: DataStore = Depends(get_store),
    config: Config = Depends(get_config),
) -> ReadinessResponse:
    """Readiness probe checking that datasets and model configuration are properly loaded."""
    client_count = len(store.client_ids) if hasattr(store, "client_ids") else 0
    instrument_count = len(store.covered_symbols) if hasattr(store, "covered_symbols") else 0

    return ReadinessResponse(
        status="ready",
        clients_loaded=client_count,
        instruments_loaded=instrument_count,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
    )
