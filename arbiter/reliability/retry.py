"""
arbiter/reliability/retry.py
----------------------------
Centralized exponential backoff with jitter and timeout control.
"""

from __future__ import annotations

import concurrent.futures
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

from arbiter.reliability.classification import ErrorClassification, classify_error

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    """Configuration governing exponential backoff retry policies."""

    max_attempts: int = 3
    initial_backoff: float = 0.5
    max_backoff: float = 10.0
    jitter: bool = True
    respect_retry_after: bool = True
    per_attempt_timeout_seconds: float | None = 15.0


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: float | None = None,
) -> float:
    """Calculate exponential backoff delay with randomized jitter and Retry-After constraints."""
    base_delay = config.initial_backoff * (2 ** max(0, attempt - 1))
    capped_delay = min(config.max_backoff, base_delay)

    if config.jitter:
        # Full jitter between 50% and 100% of capped delay
        delay = random.uniform(capped_delay * 0.5, capped_delay)
    else:
        delay = capped_delay

    if config.respect_retry_after and retry_after is not None and retry_after > 0:
        delay = max(delay, retry_after)

    return round(min(config.max_backoff, delay), 4)


def execute_with_timeout(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
) -> T:
    """Execute a callable with strict wall-clock timeout protection.

    Uses ThreadPoolExecutor with shutdown(wait=False, cancel_futures=True) so the caller
    returns immediately upon timeout expiration without blocking on worker thread completion.
    (Note: Synchronously executing blocking I/O inside Python worker threads cannot be forcefully
    killed from outside, but the caller thread is never blocked waiting for them).
    """
    kw = kwargs or {}
    if timeout_seconds is None or timeout_seconds <= 0:
        return func(*args, **kw)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kw)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        raise TimeoutError(f"Operation timed out after {timeout_seconds:.1f}s") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)




default_sleep: Callable[[float], None] = time.sleep


def execute_with_retry(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: dict[str, Any] | None = None,
    config: RetryConfig | None = None,
    on_retry: Optional[Callable[[int, float, ErrorClassification], None]] = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> T:
    """Execute callable with exponential backoff, jitter, and classification-aware retries."""
    cfg = config or RetryConfig()
    kw = kwargs or {}
    sleeper = sleep_fn if sleep_fn is not None else default_sleep
    last_error: Exception | None = None


    for attempt in range(1, cfg.max_attempts + 1):
        try:
            return execute_with_timeout(
                func,
                args=args,
                kwargs=kw,
                timeout_seconds=cfg.per_attempt_timeout_seconds,
            )
        except Exception as exc:
            last_error = exc
            classification = classify_error(exc)

            # If not retryable or final attempt reached, fail immediately
            if not classification.retryable or attempt >= cfg.max_attempts:
                raise exc

            delay = calculate_backoff_delay(attempt, cfg, classification.retry_after_seconds)

            if on_retry:
                try:
                    on_retry(attempt, delay, classification)
                except Exception:
                    pass

            sleeper(delay)


    if last_error:
        raise last_error
    raise RuntimeError("Retry loop exited unexpectedly without result or exception.")
