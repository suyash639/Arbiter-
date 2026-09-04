"""
arbiter/api/dependencies.py
---------------------------
FastAPI dependency injection providers for configuration, data store, and orchestrator.
"""

from __future__ import annotations

from typing import Optional
from fastapi import Request

from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.orchestrator import ArbiterOrchestrator


def get_config(request: Request) -> Config:
    """Retrieve Config instance from application state."""
    return request.app.state.config


def get_store(request: Request) -> DataStore:
    """Retrieve DataStore instance from application state."""
    return request.app.state.store


def get_orchestrator(request: Request) -> ArbiterOrchestrator:
    """Retrieve ArbiterOrchestrator instance from application state."""
    return request.app.state.orchestrator


def get_observability(request: Request) -> ObservabilityManager:
    """Retrieve ObservabilityManager instance from application state."""
    return getattr(request.app.state, "observability", None) or get_observability_manager()


def get_request_id(request: Request) -> str:
    """Extract request correlation ID from request state."""
    return getattr(request.state, "request_id", "req_unknown")
