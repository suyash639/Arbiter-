"""
arbiter/reliability/engine.py
-----------------------------
Centralized Reliability Engine coordinating retries, exponential backoff,
circuit breaker fail-fast, timeout controls, and observability integration.
"""

from __future__ import annotations

import time
from typing import Any, Callable, List, Optional, TypeVar

from arbiter.config import Config
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from arbiter.reliability.classification import ErrorClassification, classify_error
from arbiter.reliability.fallback import build_reliability_fallback
from arbiter.reliability.retry import RetryConfig, execute_with_retry

T = TypeVar("T")


class ReliabilityEngine:
    """Enterprise reliability coordinator managing resilient LLM and gateway execution."""

    def __init__(
        self,
        config: Config | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_config: RetryConfig | None = None,
        observability: ObservabilityManager | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config
        self.obs = observability or get_observability_manager()
        self.sleep_fn = sleep_fn


        # Initialize Circuit Breaker with observability callbacks
        if circuit_breaker is not None:
            self.circuit_breaker = circuit_breaker
        else:
            cb_threshold = getattr(config, "circuit_breaker_failure_threshold", 3) if config else 3
            cb_recovery = getattr(config, "circuit_breaker_recovery_seconds", 30.0) if config else 30.0
            self.circuit_breaker = CircuitBreaker(
                name="llm_upstream",
                failure_threshold=cb_threshold,
                recovery_seconds=cb_recovery,
                on_state_change=self._on_circuit_state_change,
            )

        # Initialize Retry Configuration
        if retry_config is not None:
            self.retry_config = retry_config
        else:
            max_attempts = getattr(config, "reliability_max_attempts", 3) if config else 3
            init_backoff = getattr(config, "reliability_initial_backoff", 0.5) if config else 0.5
            max_backoff = getattr(config, "reliability_max_backoff", 10.0) if config else 10.0
            jitter = getattr(config, "reliability_jitter", True) if config else True
            timeout = getattr(config, "llm_timeout_seconds", None) if config else None
            self.retry_config = RetryConfig(
                max_attempts=max_attempts,
                initial_backoff=init_backoff,
                max_backoff=max_backoff,
                jitter=jitter,
                per_attempt_timeout_seconds=timeout,
            )


    def _on_circuit_state_change(self, old_state: CircuitState, new_state: CircuitState, reason: str) -> None:
        """Log structured event to observability subsystem when circuit breaker changes state."""
        self.obs.logger.warning(
            "circuit_state_changed",
            circuit_name=self.circuit_breaker.name,
            old_state=old_state.value,
            new_state=new_state.value,
            reason=reason,
        )

    def execute(
        self,
        func: Callable[..., T],
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        question_id: str = "unknown",
        client_id: str | None = None,
        agents: List[str] | None = None,
        operation_name: str = "llm_execution",
        request_id: str | None = None,
    ) -> T | dict[str, Any]:
        """Execute callable protected by circuit breaker, timeout, and exponential backoff retry.

        If execution fails after retries or circuit is open, returns a safe abstention envelope.
        """
        kw = kwargs or {}
        agent_path = list(agents) if agents else ["router"]

        # 1. Circuit Breaker Check (fail-fast)
        try:
            self.circuit_breaker.check_execution()
        except CircuitBreakerOpenError as cb_err:
            self.obs.logger.warning(
                "circuit_open_rejected",
                operation=operation_name,
                request_id=request_id,
                reason=str(cb_err),
                retry_after=cb_err.retry_after,
            )
            return build_reliability_fallback(
                question_id=question_id,
                client_id=client_id,
                agents=agent_path,
                reason=f"Circuit breaker is OPEN. Upstream LLM call fast-failed: {cb_err}",
                flags=["upstream_issue"],
            )

        # 2. Retry listener
        def _handle_retry(attempt: int, delay: float, classification: ErrorClassification) -> None:
            self.obs.logger.info(
                "retry_attempt",
                operation=operation_name,
                request_id=request_id,
                attempt=attempt,
                delay_ms=round(delay * 1000.0, 2),
                category=classification.category.value,
                reason=classification.sanitized_message[:150],
            )

        # 3. Execute with Retry & Timeout
        try:
            result = execute_with_retry(
                func,
                args=args,
                kwargs=kw,
                config=self.retry_config,
                on_retry=_handle_retry,
                sleep_fn=self.sleep_fn,
            )

            # Check if result was returned as raw error string (e.g. 429 quota error message from LLM)
            if isinstance(result, dict) and result.get("abstained") and "upstream_issue" in result.get("flags", []):
                # If specialist returned an upstream issue directly
                self.circuit_breaker.record_failure(result.get("reason"))
            else:
                self.circuit_breaker.record_success()

            return result

        except Exception as exc:
            classification = classify_error(exc)
            self.circuit_breaker.record_failure(exc)

            self.obs.logger.error(
                "upstream_failure",
                operation=operation_name,
                request_id=request_id,
                category=classification.category.value,
                error_type=type(exc).__name__,
                reason=classification.sanitized_message[:150],
            )

            return build_reliability_fallback(
                question_id=question_id,
                client_id=client_id,
                agents=agent_path,
                reason=f"Upstream failure ({classification.category.value}): {classification.sanitized_message}",
                flags=["upstream_issue"],
            )

    def reset(self) -> None:
        """Reset the reliability engine and underlying circuit breaker."""
        self.circuit_breaker.reset()
