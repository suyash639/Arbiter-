"""
arbiter/api/errors.py
---------------------
Standardized exception handlers and error normalization for FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from arbiter.observability.redaction import RedactionEngine
from arbiter.security.errors import InputValidationError, SecurityError

logger = logging.getLogger("arbiter.api.errors")


from fastapi.encoders import jsonable_encoder


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform, safe exception handlers on the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        sanitized_errors = RedactionEngine.redact_value(jsonable_encoder(exc.errors()))
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Invalid request payload format or parameters.",
                "request_id": rid,
                "details": sanitized_errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": str(exc.detail),
                "request_id": rid,
                "details": None,
            },
        )

    @app.exception_handler(InputValidationError)
    async def input_validation_exception_handler(request: Request, exc: InputValidationError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "bad_request",
                "message": str(exc),
                "request_id": rid,
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        logger.error(f"Unhandled API exception on request {rid}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while processing the request.",
                "request_id": rid,
                "details": None,
            },
        )
