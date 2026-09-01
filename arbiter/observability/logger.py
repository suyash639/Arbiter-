"""
arbiter/observability/logger.py
-------------------------------
Structured logger with automatic request_id correlation and PII sanitization.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from arbiter.observability.context import get_current_request_id
from arbiter.observability.redaction import RedactionEngine


class StructuredLogger:
    """Structured event logger wrapping Python standard logging."""

    def __init__(self, name: str = "arbiter") -> None:
        self.logger = logging.getLogger(name)

    def _log_event(self, level: int, event: str, **kwargs: Any) -> None:
        """Sanitize and format structured event record."""
        if not self.logger.isEnabledFor(level):
            return

        request_id = kwargs.pop("request_id", None) or get_current_request_id() or "no_request_context"
        sanitized_payload = RedactionEngine.redact_value(kwargs)

        record = {
            "event": event,
            "request_id": request_id,
            **sanitized_payload,
        }

        # Format as compact JSON message
        try:
            msg = json.dumps(record, default=str)
        except Exception:
            msg = f"event={event} request_id={request_id} payload={sanitized_payload}"

        self.logger.log(level, msg)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log_event(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log_event(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log_event(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log_event(logging.ERROR, event, **kwargs)


def get_logger(name: str = "arbiter") -> StructuredLogger:
    """Factory helper to obtain a StructuredLogger instance."""
    return StructuredLogger(name)
