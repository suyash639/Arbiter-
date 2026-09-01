"""
arbiter/reliability/circuit_breaker.py
--------------------------------------
Thread-safe, three-state Circuit Breaker protecting upstream LLM backends
from cascade failures and excessive quota depletion.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    """Operational states of the circuit breaker."""

    CLOSED = "CLOSED"        # Normal execution
    OPEN = "OPEN"            # Fail fast, upstream blocked
    HALF_OPEN = "HALF_OPEN"  # Testing recovery probe


class CircuitBreakerOpenError(RuntimeError):
    """Raised when an operation is rejected because the circuit breaker is OPEN."""

    def __init__(self, message: str = "Circuit breaker is OPEN. Fast-failing upstream call.", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CircuitBreaker:
    """Thread-safe circuit breaker with automatic state transitions and recovery probing."""

    def __init__(
        self,
        name: str = "llm_upstream",
        failure_threshold: int = 3,
        recovery_seconds: float = 30.0,
        half_open_success_threshold: int = 1,
        on_state_change: Optional[Callable[[CircuitState, CircuitState, str], None]] = None,
    ) -> None:
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_seconds = max(0.001, recovery_seconds)
        self.half_open_success_threshold = max(1, half_open_success_threshold)
        self.on_state_change = on_state_change

        self._lock = threading.RLock()
        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._half_open_successes: int = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current state of the circuit breaker with automated recovery timeout evaluation."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.perf_counter() - self._opened_at
                if elapsed >= self.recovery_seconds:
                    self._transition_to(CircuitState.HALF_OPEN, f"Recovery timeout ({self.recovery_seconds}s) elapsed")
            return self._state

    def _transition_to(self, new_state: CircuitState, reason: str) -> None:
        """Internal helper to mutate state and invoke state change listeners."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        if new_state == CircuitState.OPEN:
            self._opened_at = time.perf_counter()
            self._half_open_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._half_open_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state, reason)
            except Exception:
                pass

    def can_execute(self) -> bool:
        """Check whether a request is permitted to execute without raising."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def check_execution(self) -> None:
        """Raise CircuitBreakerOpenError if the circuit is OPEN."""
        with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                remaining = max(0.0, self.recovery_seconds - (time.perf_counter() - self._opened_at))
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Fast-failing upstream call (retry in {remaining:.1f}s).",
                    retry_after=round(remaining, 2),
                )

    def record_success(self) -> None:
        """Record a successful upstream execution."""
        with self._lock:
            current_state = self.state
            if current_state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_success_threshold:
                    self._transition_to(CircuitState.CLOSED, "Probe request succeeded")
            elif current_state == CircuitState.CLOSED:
                self._consecutive_failures = 0

    def record_failure(self, error: Any = None) -> None:
        """Record an upstream failure."""
        with self._lock:
            current_state = self.state
            if current_state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN, f"Probe request failed: {error}")
            elif current_state == CircuitState.CLOSED:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.failure_threshold:
                    self._transition_to(
                        CircuitState.OPEN,
                        f"Consecutive failures ({self._consecutive_failures}) reached threshold ({self.failure_threshold})"
                    )

    def reset(self) -> None:
        """Reset the circuit breaker back to initial CLOSED state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED, "Manual reset")
            self._consecutive_failures = 0
            self._half_open_successes = 0
            self._opened_at = 0.0
