"""
arbiter/observability/context.py
--------------------------------
Thread-safe and async-safe request context propagation via contextvars.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

_current_request_id: ContextVar[str | None] = ContextVar("arbiter_current_request_id", default=None)


def generate_request_id() -> str:
    """Generate a unique request correlation ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def set_current_request_id(request_id: str) -> Token[str | None]:
    """Bind a request_id to the current execution context."""
    return _current_request_id.set(request_id)


def get_current_request_id() -> str | None:
    """Retrieve the request_id associated with the current execution context."""
    return _current_request_id.get()


def reset_current_request_id(token: Token[str | None]) -> None:
    """Reset the current request_id context to its previous state."""
    _current_request_id.reset(token)
