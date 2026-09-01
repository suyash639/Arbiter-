"""
tests/test_reliability.py
-------------------------
Comprehensive unit and fault-injection test suite for the Arbiter Reliability Subsystem.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.orchestrator import ArbiterOrchestrator
from arbiter.reliability import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    ErrorCategory,
    ErrorClassification,
    ErrorClassifier,
    ReliabilityEngine,
    RetryConfig,
    calculate_backoff_delay,
    classify_error,
    execute_with_retry,
    execute_with_timeout,
)

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# 1. Error Classification & Regex Extraction Tests
# ---------------------------------------------------------------------------
class TestErrorClassification:
    def test_classify_rate_limit_429(self):
        class Mock429(Exception):
            status_code = 429

        err = Mock429("Rate limit exceeded. Please retry in 8.5s.")
        cls = classify_error(err)
        assert cls.category == ErrorCategory.RETRYABLE_RATE_LIMIT
        assert cls.retryable is True
        assert cls.status_code == 429
        assert cls.retry_after_seconds == 8.5

    def test_classify_server_errors_5xx(self):
        for code in (500, 502, 503, 504):
            class Mock5xx(Exception):
                status_code = code

            cls = classify_error(Mock5xx(f"Gateway failure HTTP {code}"))
            assert cls.category == ErrorCategory.RETRYABLE_SERVER_ERROR
            assert cls.retryable is True

    def test_classify_connection_and_timeout_errors(self):
        cls_conn = classify_error(ConnectionResetError("Connection reset by peer"))
        assert cls_conn.category == ErrorCategory.RETRYABLE_CONNECTION
        assert cls_conn.retryable is True

        cls_timeout = classify_error(TimeoutError("Read timed out"))
        assert cls_timeout.category == ErrorCategory.RETRYABLE_TIMEOUT
        assert cls_timeout.retryable is True

    def test_classify_non_retryable_client_errors(self):
        class Mock401(Exception):
            status_code = 401

        cls = classify_error(Mock401("Unauthorized: Invalid API key"))
        assert cls.category == ErrorCategory.NON_RETRYABLE_CLIENT_ERROR
        assert cls.retryable is False

    def test_classify_deterministic_tool_errors(self):
        cls = classify_error(ValueError("Scope violation: client_id mismatch."))
        assert cls.category == ErrorCategory.NON_RETRYABLE_TOOL_ERROR
        assert cls.retryable is False

    def test_retry_after_parsing_variants(self):
        assert ErrorClassifier.extract_retry_after("retry in 12.3s") == 12.3
        assert ErrorClassifier.extract_retry_after("Retry-After: 4.5") == 4.5
        assert ErrorClassifier.extract_retry_after("retryDelay': '7s'") == 7.0
        assert ErrorClassifier.extract_retry_after("No delay mentioned") is None

    def test_error_message_sanitization_masks_secrets(self):
        raw_msg = "Error using key AIzaSyD1234567890123456789012345678901 for client PAN ABCDE1234F"
        cls = classify_error(RuntimeError(raw_msg))
        assert "AIzaSyD" not in cls.sanitized_message
        assert "[REDACTED_SECRET]" in cls.sanitized_message
        assert "ABCDE1234F" not in cls.sanitized_message
        assert "****234F" in cls.sanitized_message


# ---------------------------------------------------------------------------
# 2. Circuit Breaker State Machine Tests
# ---------------------------------------------------------------------------
class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=1.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_trips_to_open_after_threshold_failures(self):
        state_changes = []
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_seconds=1.0,
            on_state_change=lambda old, new, r: state_changes.append((old, new)),
        )

        cb.record_failure("error 1")
        assert cb.state == CircuitState.CLOSED
        cb.record_failure("error 2")
        assert cb.state == CircuitState.CLOSED
        cb.record_failure("error 3")
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False
        assert state_changes == [(CircuitState.CLOSED, CircuitState.OPEN)]

    def test_open_circuit_fails_fast_with_exception(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=10.0)
        cb.record_failure("error")
        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.check_execution()
        assert "is OPEN" in str(exc_info.value)
        assert exc_info.value.retry_after is not None

    def test_recovery_transition_to_half_open_and_closed(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05, half_open_success_threshold=1)
        cb.record_failure("error")
        assert cb.state == CircuitState.OPEN

        time.sleep(0.06)
        # Automatic transition on evaluation
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

        # Successful probe resets to CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failed_probe_in_half_open_re_trips_to_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        cb.record_failure("error")
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

        # Failed probe trips back to OPEN
        cb.record_failure("probe error")
        assert cb.state == CircuitState.OPEN

    def test_concurrency_safety_under_multithreaded_failures(self):
        cb = CircuitBreaker(failure_threshold=10, recovery_seconds=1.0)

        def worker():
            for _ in range(5):
                cb.record_failure("concurrent error")

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# 3. Retry Engine & Exponential Backoff Tests
# ---------------------------------------------------------------------------
class TestRetryEngine:
    def test_calculate_backoff_delay(self):
        cfg = RetryConfig(initial_backoff=1.0, max_backoff=10.0, jitter=False)
        assert calculate_backoff_delay(1, cfg) == 1.0
        assert calculate_backoff_delay(2, cfg) == 2.0
        assert calculate_backoff_delay(3, cfg) == 4.0
        assert calculate_backoff_delay(4, cfg) == 8.0
        assert calculate_backoff_delay(5, cfg) == 10.0  # Capped

    def test_respects_larger_retry_after(self):
        cfg = RetryConfig(initial_backoff=0.5, max_backoff=10.0, jitter=False, respect_retry_after=True)
        delay = calculate_backoff_delay(1, cfg, retry_after=5.0)
        assert delay == 5.0

    def test_transient_error_retries_and_succeeds(self):
        attempts = 0
        mock_sleep = MagicMock()
        retries_recorded = []

        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionResetError("Temporary network reset")
            return "SUCCESS"

        def on_retry(att, d, c):
            retries_recorded.append((att, d, c.category))

        res = execute_with_retry(
            flaky_function,
            config=RetryConfig(max_attempts=3, initial_backoff=0.1, jitter=False),
            on_retry=on_retry,
            sleep_fn=mock_sleep,
        )

        assert res == "SUCCESS"
        assert attempts == 2
        assert mock_sleep.call_count == 1
        assert len(retries_recorded) == 1
        assert retries_recorded[0][0] == 1
        assert retries_recorded[0][2] == ErrorCategory.RETRYABLE_CONNECTION

    def test_non_retryable_error_fails_immediately_without_retry(self):
        attempts = 0
        mock_sleep = MagicMock()

        def client_error_function():
            nonlocal attempts
            attempts += 1
            raise ValueError("Scope violation: client_id mismatch.")

        with pytest.raises(ValueError) as exc:
            execute_with_retry(
                client_error_function,
                config=RetryConfig(max_attempts=3),
                sleep_fn=mock_sleep,
            )

        assert attempts == 1
        assert mock_sleep.call_count == 0
        assert "Scope violation" in str(exc.value)

    def test_exhaustion_of_retries_raises_last_exception(self):
        attempts = 0
        mock_sleep = MagicMock()

        def always_fails():
            nonlocal attempts
            attempts += 1
            raise TimeoutError("Persistent upstream timeout")

        with pytest.raises(TimeoutError):
            execute_with_retry(
                always_fails,
                config=RetryConfig(max_attempts=3, initial_backoff=0.01),
                sleep_fn=mock_sleep,
            )

        assert attempts == 3
        assert mock_sleep.call_count == 2

    def test_timeout_execution_terminates_hung_function(self):
        def hung_function():
            time.sleep(0.5)
            return "DONE"

        with pytest.raises(TimeoutError) as exc_info:
            execute_with_timeout(hung_function, timeout_seconds=0.05)
        assert "timed out after 0.1s" in str(exc_info.value) or "timed out" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Reliability Engine Integration & Fault Injection Tests
# ---------------------------------------------------------------------------
class TestReliabilityEngineIntegration:
    @pytest.fixture
    def store(self):
        return DataStore.load(DATA_DIR / "client_book.json", DATA_DIR / "market_data.json")

    @pytest.fixture
    def config(self):
        return Config(
            book_path=DATA_DIR / "client_book.json",
            market_path=DATA_DIR / "market_data.json",
            llm_base_url="http://localhost:8600/v1",
            _llm_api_key="test-key",
            llm_provider="gemini",
            llm_model="gemini-3.6-flash",
            reliability_max_attempts=3,
            reliability_initial_backoff=0.01,
            circuit_breaker_failure_threshold=2,
            circuit_breaker_recovery_seconds=0.1,
        )

    def test_orchestrator_recovers_from_transient_failure(self, store, config):
        obs = ObservabilityManager()
        engine = ReliabilityEngine(config=config, observability=obs, sleep_fn=lambda _: None)
        orch = ArbiterOrchestrator(store, config, reliability=engine)
        orch.obs = obs

        call_count = 0

        def flaky_specialist_answer(qid, cid, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                class QuotaError(Exception):
                    status_code = 429
                raise QuotaError("Rate limit exceeded 429. Please retry in 1s.")
            return {
                "question_id": qid,
                "answer": "Recovered answer",
                "answer_value": "15386.78",
                "abstained": False,
                "refused": False,
                "citations": [cid],
                "confidence": 1.0,
                "flags": [],
                "agents": ["router", "book_qa"],
            }

        orch.specialists["book_qa"].answer = flaky_specialist_answer

        res = orch.answer({
            "question_id": "q_transient",
            "client_id": "cli_1014",
            "prompt": "What is the cash balance for cli_1014?"
        })

        assert res["answer_value"] == "15386.78"
        assert res["abstained"] is False
        assert call_count == 2
        assert engine.circuit_breaker.state == CircuitState.CLOSED

    def test_exhausted_retries_produces_safe_abstention_envelope(self, store, config):
        obs = ObservabilityManager()
        engine = ReliabilityEngine(config=config, observability=obs, sleep_fn=lambda _: None)
        orch = ArbiterOrchestrator(store, config, reliability=engine)
        orch.obs = obs

        def always_failing_answer(qid, cid, prompt):
            raise ConnectionResetError("Gateway completely down")

        orch.specialists["book_qa"].answer = always_failing_answer

        res = orch.answer({
            "question_id": "q_exhausted",
            "client_id": "cli_1014",
            "prompt": "What is the cash balance for cli_1014?"
        })

        assert res["abstained"] is True
        assert res["answer_value"] is None
        assert "upstream_issue" in res["flags"]
        assert res["confidence"] == 0.0
        assert "Gateway completely down" in res["reason"] or "retryable_connection" in res["reason"]

    def test_circuit_breaker_trips_and_fails_fast(self, store, config):
        obs = ObservabilityManager()
        engine = ReliabilityEngine(
            config=config,
            observability=obs,
            sleep_fn=lambda _: None,
        )
        orch = ArbiterOrchestrator(store, config, reliability=engine)
        orch.obs = obs
        orch.route_question = MagicMock(return_value="book_qa")

        fail_count = 0

        def failing_answer(qid, cid, prompt):
            nonlocal fail_count
            fail_count += 1
            raise TimeoutError("Upstream timeout")

        orch.specialists["book_qa"].answer = failing_answer

        # Request 1 fails after 3 retries -> records failure 1 on circuit
        res1 = orch.answer({"question_id": "q_cb_1", "client_id": "cli_1014", "prompt": "Prompt 1"})
        assert res1["abstained"] is True
        assert engine.circuit_breaker.state == CircuitState.CLOSED

        # Request 2 fails after 3 retries -> trips circuit breaker to OPEN (threshold = 2)
        res2 = orch.answer({"question_id": "q_cb_2", "client_id": "cli_1014", "prompt": "Prompt 2"})
        assert res2["abstained"] is True
        assert engine.circuit_breaker.state == CircuitState.OPEN

        # Request 3 should FAIL FAST without invoking specialist or sleeping
        invocations_before = fail_count
        res3 = orch.answer({"question_id": "q_cb_3", "client_id": "cli_1014", "prompt": "Prompt 3"})
        assert res3["abstained"] is True
        assert "Circuit breaker is OPEN" in res3["reason"]
        assert fail_count == invocations_before  # No new specialist calls were made!

    def test_no_retry_on_policy_refusal_or_validation_errors(self, store, config):
        """Verifies policy refusal and validation checks execute once without retrying."""
        obs = ObservabilityManager()
        engine = ReliabilityEngine(config=config, observability=obs, sleep_fn=lambda _: None)
        orch = ArbiterOrchestrator(store, config, reliability=engine)
        orch.obs = obs

        compliance_invocations = 0

        def refusal_answer(qid, cid, prompt):
            nonlocal compliance_invocations
            compliance_invocations += 1
            return {
                "question_id": qid,
                "answer": "",
                "answer_value": None,
                "abstained": False,
                "refused": True,
                "reason": "I cannot provide investment advice.",
                "citations": [],
                "confidence": 1.0,
                "flags": [],
                "agents": ["router", "compliance"],
            }

        orch.specialists["compliance"].answer = refusal_answer

        res = orch.answer({
            "question_id": "q_refusal",
            "client_id": "cli_1014",
            "prompt": "Should cli_1014 buy more AAPL?"
        })

        assert res["refused"] is True
        assert compliance_invocations == 1  # Exactly 1 call, zero retries

    def test_zero_unintended_network_calls_during_pytest(self):
        """Verifies that un-mocked OpenAIChat calls are intercepted by conftest isolation."""
        from agno.models.openai import OpenAIChat
        import openai

        model = OpenAIChat(id="test-model", base_url="http://localhost:8600/v1")
        client = model.get_client()

        # Calling create on unmocked client raises APIConnectionError instantly without network timeout
        t0 = time.perf_counter()
        with pytest.raises(openai.APIConnectionError) as exc_info:
            client.chat.completions.create(messages=[{"role": "user", "content": "hi"}], model="test")
        duration = time.perf_counter() - t0

        assert duration < 0.05  # Instantaneous fail-fast (< 50ms)
        assert "Fast test isolation" in str(exc_info.value)


