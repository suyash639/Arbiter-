"""
arbiter/api/app.py
------------------
FastAPI application factory, middleware configuration, and lifecycle management.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from arbiter.api.errors import register_error_handlers
from arbiter.api.routes.health import router as health_router
from arbiter.api.routes.metadata import router as metadata_router
from arbiter.api.routes.query import router as query_router
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.orchestrator import ArbiterOrchestrator


class SecurityHeadersAndCorrelationMiddleware(BaseHTTPMiddleware):
    """Injects correlation request ID, sets security headers, and tracks HTTP latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Establish Request ID
        client_req_id = request.headers.get("X-Request-ID")
        if client_req_id and len(client_req_id.strip()) <= 64:
            request_id = client_req_id.strip()
        else:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        request.state.request_id = request_id

        # 2. Process Request
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        # 3. Attach Security & Tracing Headers
        if "X-Request-ID" not in response.headers:
            response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        return response


def create_app(
    store: Optional[DataStore] = None,
    config: Optional[Config] = None,
    orchestrator: Optional[ArbiterOrchestrator] = None,
    observability: Optional[ObservabilityManager] = None,
) -> FastAPI:
    """Application factory initializing FastAPI with dependencies and routing."""
    app = FastAPI(
        title="Arbiter AI Financial Operations API",
        description="Production-grade multi-agent financial intelligence and operations engine.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Add Security & Correlation Middleware
    app.add_middleware(SecurityHeadersAndCorrelationMiddleware)

    # 3. Register Standardized Error Handlers
    register_error_handlers(app)

    # 4. Initialize State and Dependencies
    cfg = config or (Config.from_env() if store is None else None)
    app.state.config = cfg
    if store is not None:
        app.state.store = store
    elif cfg is not None:
        app.state.store = DataStore.load(cfg.book_path, cfg.market_path)
    else:
        app.state.store = None

    if orchestrator is not None:
        app.state.orchestrator = orchestrator
    elif app.state.store is not None and app.state.config is not None:
        app.state.orchestrator = ArbiterOrchestrator(app.state.store, app.state.config)
    else:
        app.state.orchestrator = None

    app.state.observability = observability or get_observability_manager()

    # 5. Include API Routers
    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(metadata_router)

    return app
