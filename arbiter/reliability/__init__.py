"""
arbiter/reliability/__init__.py
-------------------------------
Arbiter Enterprise Reliability Subsystem.
"""

from __future__ import annotations

from arbiter.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from arbiter.reliability.classification import (
    ErrorCategory,
    ErrorClassification,
    ErrorClassifier,
    classify_error,
)
from arbiter.reliability.engine import ReliabilityEngine
from arbiter.reliability.fallback import build_reliability_fallback
from arbiter.reliability.retry import (
    RetryConfig,
    calculate_backoff_delay,
    execute_with_retry,
    execute_with_timeout,
)

__all__ = [
    "ReliabilityEngine",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "ErrorCategory",
    "ErrorClassification",
    "ErrorClassifier",
    "classify_error",
    "RetryConfig",
    "execute_with_retry",
    "execute_with_timeout",
    "calculate_backoff_delay",
    "build_reliability_fallback",
]
