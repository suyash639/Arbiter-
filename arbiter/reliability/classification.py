"""
arbiter/reliability/classification.py
-------------------------------------
Provider-aware error classification layer distinguishing retryable transient faults
from deterministic non-retryable errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from arbiter.observability.redaction import RedactionEngine


class ErrorCategory(str, Enum):
    """Categorized failure types for reliability and telemetry routing."""

    RETRYABLE_RATE_LIMIT = "retryable_rate_limit"          # HTTP 429, ResourceExhausted, Quota
    RETRYABLE_SERVER_ERROR = "retryable_server_error"      # HTTP 500, 502, 503, 504
    RETRYABLE_CONNECTION = "retryable_connection"          # ConnectError, ConnectionReset, DNS
    RETRYABLE_TIMEOUT = "retryable_timeout"                # APITimeout, ReadTimeout, socket.timeout
    NON_RETRYABLE_CLIENT_ERROR = "non_retryable_client"    # HTTP 400, 401, 403, 404, Auth
    NON_RETRYABLE_TOOL_ERROR = "non_retryable_tool"        # Scope violation, UnsupportedFilter
    NON_RETRYABLE_SCHEMA_ERROR = "non_retryable_schema"    # Unparseable output, malformed model JSON
    INTERNAL_ERROR = "internal_error"                      # Unclassified runtime errors


RETRY_AFTER_PATTERNS = [
    re.compile(r"retry\s+in\s+([0-9\.]+)\s*s", re.IGNORECASE),
    re.compile(r"retry-after[\s:=]+([0-9\.]+)", re.IGNORECASE),
    re.compile(r"retryDelay['\"]?:\s*['\"]?([0-9\.]+)s?", re.IGNORECASE),
]


@dataclass(frozen=True)
class ErrorClassification:
    """Classified error record with retryability determination and extracted backoff."""

    category: ErrorCategory
    retryable: bool
    retry_after_seconds: float | None = None
    status_code: int | None = None
    sanitized_message: str = ""


class ErrorClassifier:
    """Deterministic classifier inspecting exception types, HTTP status codes, and error strings."""

    @classmethod
    def extract_retry_after(cls, text: str) -> float | None:
        """Parse numeric retry delay from headers, exception strings, or quota messages."""
        if not text:
            return None
        for pattern in RETRY_AFTER_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    val = float(match.group(1))
                    if 0.0 < val <= 300.0:  # Cap reasonable ceiling
                        return val
                except (ValueError, IndexError):
                    pass
        return None

    @classmethod
    def classify(cls, error: Any) -> ErrorClassification:
        """Classify an exception or error payload into an ErrorClassification record."""
        if error is None:
            return ErrorClassification(
                category=ErrorCategory.INTERNAL_ERROR,
                retryable=False,
                sanitized_message="No error provided",
            )

        err_type = type(error).__name__
        raw_msg = str(error)
        msg_lower = raw_msg.lower()
        sanitized_msg = RedactionEngine.redact_text(raw_msg)

        # Extract status code if available
        status_code = getattr(error, "status_code", None) or getattr(error, "code", None)
        if status_code is None and hasattr(error, "response") and hasattr(error.response, "status_code"):
            status_code = error.response.status_code

        # Attempt to parse integer status code if string
        if isinstance(status_code, str):
            try:
                status_code = int(status_code)
            except ValueError:
                status_code = None

        retry_after = cls.extract_retry_after(raw_msg)

        # 1. Check Rate Limit / 429
        if (
            status_code == 429
            or "rate limit" in msg_lower
            or "resource_exhausted" in msg_lower
            or "quota exceeded" in msg_lower
            or "429" in raw_msg
            or "RateLimitError" in err_type
        ):
            return ErrorClassification(
                category=ErrorCategory.RETRYABLE_RATE_LIMIT,
                retryable=True,
                retry_after_seconds=retry_after,
                status_code=429,
                sanitized_message=sanitized_msg,
            )

        # 2. Check Server Errors (500, 502, 503, 504)
        if (
            status_code in (500, 502, 503, 504)
            or any(f"{code}" in raw_msg for code in (500, 502, 503, 504))
            or any(s in msg_lower for s in ("bad gateway", "service unavailable", "gateway timeout", "internal server error"))
            or "InternalServerError" in err_type
        ):
            return ErrorClassification(
                category=ErrorCategory.RETRYABLE_SERVER_ERROR,
                retryable=True,
                retry_after_seconds=retry_after,
                status_code=status_code or 500,
                sanitized_message=sanitized_msg,
            )

        # 3. Check Timeout
        if (
            isinstance(error, TimeoutError)
            or "timeout" in msg_lower
            or "timed out" in msg_lower
            or "TimeoutError" in err_type
            or "APITimeoutError" in err_type
        ):
            return ErrorClassification(
                category=ErrorCategory.RETRYABLE_TIMEOUT,
                retryable=True,
                retry_after_seconds=retry_after,
                status_code=408,
                sanitized_message=sanitized_msg,
            )

        # 4. Check Connection Failures
        if (
            isinstance(error, (ConnectionError, ConnectionResetError, BrokenPipeError, OSError))
            or "connection" in msg_lower
            or "network" in msg_lower
            or "connecterror" in msg_lower
            or "apiconnectionerror" in msg_lower
            or "connection refused" in msg_lower
            or "connection reset" in msg_lower
            or "broken pipe" in msg_lower
            or "network unreachable" in msg_lower
            or "dns" in msg_lower
            or "remote disconnected" in msg_lower
            or "APIConnectionError" in err_type
            or "ConnectError" in err_type
            or "ConnectionResetError" in err_type
        ):
            return ErrorClassification(
                category=ErrorCategory.RETRYABLE_CONNECTION,
                retryable=True,
                retry_after_seconds=retry_after,
                status_code=status_code,
                sanitized_message=sanitized_msg,
            )


        # 5. Check Non-retryable Deterministic Tool Errors & Scope Violations
        if (
            "scope violation" in msg_lower
            or "unsupportedfiltererror" in err_type.lower()
            or "booktoolerror" in err_type.lower()
            or "marketcoverageerror" in err_type.lower()
            or "nopricedataerror" in err_type.lower()
            or "nosuitabilityreviewerror" in err_type.lower()
        ):
            return ErrorClassification(
                category=ErrorCategory.NON_RETRYABLE_TOOL_ERROR,
                retryable=False,
                status_code=None,
                sanitized_message=sanitized_msg,
            )

        # 6. Check Non-retryable Client / Auth Errors (400, 401, 403, 404)
        if (
            status_code in (400, 401, 403, 404)
            or any(s in msg_lower for s in ("unauthorized", "invalid api key", "forbidden", "permission denied", "not found"))
            or any(k in err_type for k in ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError"))
        ):
            return ErrorClassification(
                category=ErrorCategory.NON_RETRYABLE_CLIENT_ERROR,
                retryable=False,
                status_code=status_code,
                sanitized_message=sanitized_msg,
            )

        # 7. Check Schema & Parsing Errors
        if "jsondecodeerror" in err_type.lower() or "validationerror" in err_type.lower() or "parsing" in msg_lower:
            return ErrorClassification(
                category=ErrorCategory.NON_RETRYABLE_SCHEMA_ERROR,
                retryable=False,
                status_code=None,
                sanitized_message=sanitized_msg,
            )

        # Default fallback
        return ErrorClassification(
            category=ErrorCategory.INTERNAL_ERROR,
            retryable=False,
            status_code=status_code,
            sanitized_message=sanitized_msg,
        )


def classify_error(error: Any) -> ErrorClassification:
    """Public helper to classify an error."""
    return ErrorClassifier.classify(error)
