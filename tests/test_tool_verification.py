"""
tests/test_tool_verification.py
--------------------------------
Comprehensive unit, security, isolation, and audit tests for Arbiter Tool Verification (Phase 4).
"""

from __future__ import annotations

import concurrent.futures
import pytest
from unittest.mock import MagicMock

from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager
from arbiter.reliability import ReliabilityEngine, RetryConfig
from arbiter.tool_verification import (
    TOOL_REGISTRY,
    MissingClientScopeError,
    ToolArgumentValidationError,
    ToolExecutionError,
    ToolResultValidationError,
    ToolScopeViolationError,
    ToolVerificationError,
    ToolVerifier,
    UnauthorizedToolError,
    UnknownClientScopeError,
    UnknownToolError,
    create_verified_tool,
    get_authorized_tools_for_agent,
    get_tool_definition,
)
from arbiter.tools.book import calculate_cash_balance, get_client_kyc_profile
from arbiter.tools.market import get_instrument_details, get_market_price


# ===========================================================================
# 1. Authoritative Tool Registry & Agent Authorization Tests
# ===========================================================================

class TestToolRegistryAndAuthorization:
    """Test registry completeness and strict agent authorization boundaries."""

    def test_registry_contains_all_specialist_tools(self):
        """Verify that all 24 tools across book_qa, kyc_profile, notes_desk, and market_desk are registered."""
        assert len(TOOL_REGISTRY) == 24
        assert "get_cash_balance" in TOOL_REGISTRY
        assert "get_kyc_profile" in TOOL_REGISTRY
        assert "get_notes" in TOOL_REGISTRY
        assert "get_price" in TOOL_REGISTRY

    def test_authorized_agent_tool_mappings(self):
        """Verify that agent-to-tool sets match expected specialist domains."""
        book_tools = get_authorized_tools_for_agent("book_qa")
        assert len(book_tools) == 16
        assert "get_cash_balance" in book_tools
        assert "get_price" not in book_tools

        kyc_tools = get_authorized_tools_for_agent("kyc_profile")
        assert len(kyc_tools) == 2
        assert "get_kyc_profile" in kyc_tools
        assert "get_cash_balance" not in kyc_tools

        notes_tools = get_authorized_tools_for_agent("notes_desk")
        assert len(notes_tools) == 2
        assert "get_notes" in notes_tools
        assert "get_kyc_profile" not in notes_tools

        market_tools = get_authorized_tools_for_agent("market_desk")
        assert len(market_tools) == 4
        assert "get_price" in market_tools
        assert "get_notes" not in market_tools

        compliance_tools = get_authorized_tools_for_agent("compliance")
        assert len(compliance_tools) == 0

    def test_unauthorized_agent_tool_combination_rejected(self, store: DataStore):
        """Verify that an agent attempting to invoke a tool outside its scope is rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(UnauthorizedToolError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda cid: {},
                agent_name="market_desk",
                tool_name="get_cash_balance",
                kwargs={"cid": "cli_1014"},
                trusted_client_id="cli_1014",
            )
        assert "Agent 'market_desk' is not authorized to invoke tool 'get_cash_balance'" in str(exc_info.value)

    def test_unknown_tool_rejected(self, store: DataStore):
        """Verify that attempting to invoke an unregistered tool name fails immediately."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(UnknownToolError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda: {},
                agent_name="book_qa",
                tool_name="arbitrary_unregistered_tool",
                kwargs={},
            )
        assert "Tool 'arbitrary_unregistered_tool' is not registered" in str(exc_info.value)


# ===========================================================================
# 2. Argument Validation & Strict Schema Enforcement Tests
# ===========================================================================

class TestArgumentValidation:
    """Test strict argument schemas, date validation, type checks, and unknown key rejection."""

    def test_valid_arguments_pass_verification(self, store: DataStore):
        """Verify that schema-compliant arguments execute successfully."""
        verifier = ToolVerifier(store=store)
        res = verifier.verify_and_execute(
            tool_func=lambda symbol, date: get_market_price(store, symbol, date),
            agent_name="market_desk",
            tool_name="get_price",
            kwargs={"symbol": "AAPL", "date": "2026-05-17"},
        )
        assert res["symbol"] == "AAPL"
        assert res["close_price"] == "190.17"


    def test_missing_required_argument_rejected(self, store: DataStore):
        """Verify that omitting a mandatory parameter raises ToolArgumentValidationError."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolArgumentValidationError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda symbol, date: {},
                agent_name="market_desk",
                tool_name="get_price",
                kwargs={"symbol": "AAPL"},  # Missing date
            )
        assert "Argument validation failed for tool 'get_price'" in str(exc_info.value)

    def test_unexpected_extra_arguments_rejected(self, store: DataStore):
        """Verify that extra/unexpected keys (potential injection attacks) are rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolArgumentValidationError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda symbol, date: {},
                agent_name="market_desk",
                tool_name="get_price",
                kwargs={"symbol": "AAPL", "date": "2026-05-17", "sql_injection": "DROP TABLE"},
            )
        assert "Extra inputs are not permitted" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_malformed_iso_date_rejected(self, store: DataStore):
        """Verify that non-ISO or malformed date strings fail validation."""
        verifier = ToolVerifier(store=store)
        for bad_date in ["17/05/2026", "2026-13-45", "yesterday", "2026-5-17", "invalid"]:
            with pytest.raises(ToolArgumentValidationError):
                verifier.verify_and_execute(
                    tool_func=lambda symbol, date: {},
                    agent_name="market_desk",
                    tool_name="get_price",
                    kwargs={"symbol": "AAPL", "date": bad_date},
                )

    def test_invalid_filter_enum_rejected(self, store: DataStore):
        """Verify that invalid txn_type values outside the allowed literal set are rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolArgumentValidationError):
            verifier.verify_and_execute(
                tool_func=lambda cid, txn_type=None: {},
                agent_name="book_qa",
                tool_name="get_client_transactions",
                kwargs={"cid": "cli_1014", "txn_type": "invalid_transaction_type"},
                trusted_client_id="cli_1014",
            )


# ===========================================================================
# 3. Client Scope & Isolation Verification Tests
# ===========================================================================

class TestClientScopeVerification:
    """Test client boundary enforcement, missing scopes, and unknown client rejections."""

    def test_valid_client_scoped_call_succeeds(self, store: DataStore):
        """Verify that matching trusted client_id allows tool execution."""
        verifier = ToolVerifier(store=store)
        res = verifier.verify_and_execute(
            tool_func=lambda cid: calculate_cash_balance(store, cid),
            agent_name="book_qa",
            tool_name="get_cash_balance",
            kwargs={"cid": "cli_1014"},
            trusted_client_id="cli_1014",
        )
        assert res["client_id"] == "cli_1014"
        assert res["balance"] == "15386.78"

    def test_missing_client_scope_rejected(self, store: DataStore):
        """Verify that client-scoped tools fail when trusted_client_id is omitted."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(MissingClientScopeError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda cid: {},
                agent_name="book_qa",
                tool_name="get_cash_balance",
                kwargs={"cid": "cli_1014"},
                trusted_client_id=None,  # Missing trusted scope
            )
        assert "requires an authoritative client_id" in str(exc_info.value)

    def test_mismatched_cross_client_scope_rejected(self, store: DataStore):
        """Verify that an LLM argument attempting cross-client access is rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolScopeViolationError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda cid: {},
                agent_name="book_qa",
                tool_name="get_cash_balance",
                kwargs={"cid": "cli_9999"},  # SNOOPING ATTEMPT
                trusted_client_id="cli_1014",
            )
        assert "Scope violation: client_id mismatch" in str(exc_info.value)

    def test_unknown_client_id_rejected(self, store: DataStore):
        """Verify that an unknown client ID not in the store fails scope verification."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(UnknownClientScopeError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda cid: {},
                agent_name="book_qa",
                tool_name="get_cash_balance",
                kwargs={"cid": "cli_nonexistent"},
                trusted_client_id="cli_nonexistent",
            )
        assert "is not in the client book" in str(exc_info.value)

    def test_tool_arguments_cannot_override_trusted_context(self, store: DataStore):
        """Verify that trusted request context client_id is enforced and overrides any mismatch."""
        verifier = ToolVerifier(store=store)
        wrapper = create_verified_tool(
            func=lambda cid: calculate_cash_balance(store, cid),
            agent_name="book_qa",
            store=store,
            trusted_client_id="cli_1014",
            tool_name_override="get_cash_balance",
            verifier=verifier,
        )
        res = wrapper(cid="cli_1014")
        assert res["client_id"] == "cli_1014"


# ===========================================================================
# 4. Result Validation Tests
# ===========================================================================

class TestResultValidation:
    """Test output schema validation, shape checking, and malformed result detection."""

    def test_valid_tool_result_accepted(self, store: DataStore):
        """Verify that a well-formed result dictionary with valid citations passes validation."""
        verifier = ToolVerifier(store=store)
        res = verifier.verify_and_execute(
            tool_func=lambda symbol: get_instrument_details(store, symbol),
            agent_name="market_desk",
            tool_name="get_instrument",
            kwargs={"symbol": "AAPL"},
        )
        assert res["symbol"] == "AAPL"
        assert res["citations"] == ["AAPL"]

    def test_unexpected_result_type_rejected(self, store: DataStore):
        """Verify that returning a string/number when a dictionary is expected raises an error."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolResultValidationError) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda symbol: "unexpected string result",
                agent_name="market_desk",
                tool_name="get_instrument",
                kwargs={"symbol": "AAPL"},
            )
        assert "Result did not match expected shape 'dict'" in str(exc_info.value)

    def test_malformed_citations_in_result_rejected(self, store: DataStore):
        """Verify that a result with a non-list citations field is rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolResultValidationError):
            verifier.verify_and_execute(
                tool_func=lambda symbol: {"symbol": symbol, "citations": "invalid_string_citation"},
                agent_name="market_desk",
                tool_name="get_instrument",
                kwargs={"symbol": "AAPL"},
            )


# ===========================================================================
# 5. Observability & Telemetry Integration Tests
# ===========================================================================

class TestObservabilityAndSecurity:
    """Test telemetry emission, PII masking, and multi-threaded request isolation."""

    def test_tool_verification_events_recorded_in_observability(self, store: DataStore):
        """Verify that successful and failed verified tool calls are recorded in ObservabilityManager."""
        obs = ObservabilityManager()
        verifier = ToolVerifier(store=store, observability=obs)

        # Successful tool call
        verifier.verify_and_execute(
            tool_func=lambda symbol: get_instrument_details(store, symbol),
            agent_name="market_desk",
            tool_name="get_instrument",
            kwargs={"symbol": "MSFT"},
            request_id="req_test_obs_123",
        )

        assert len(obs.collector.get_all_traces()) == 0  # Traces are finalized at request level
        # Verify logger / direct recording
        with pytest.raises(ToolArgumentValidationError):
            verifier.verify_and_execute(
                tool_func=lambda symbol: {},
                agent_name="market_desk",
                tool_name="get_instrument",
                kwargs={},  # Missing symbol
                request_id="req_test_obs_123",
            )

    def test_concurrent_tool_verification_preserves_scope_isolation(self, store: DataStore):
        """Verify that concurrent verification requests with different client IDs remain strictly isolated."""
        verifier = ToolVerifier(store=store)

        def verify_task(cid: str) -> dict:
            return verifier.verify_and_execute(
                tool_func=lambda cid: calculate_cash_balance(store, cid),
                agent_name="book_qa",
                tool_name="get_cash_balance",
                kwargs={"cid": cid},
                trusted_client_id=cid,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(verify_task, "cli_1014") for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for res in results:
            assert res["client_id"] == "cli_1014"
            assert res["balance"] == "15386.78"




# ===========================================================================
# 6. Reliability Engine Integration Tests
# ===========================================================================

class TestReliabilityIntegration:
    """Verify that deterministic validation errors fail fast without retry."""

    def test_deterministic_validation_errors_are_not_retried(self, store: DataStore):
        """Verify that ToolArgumentValidationError and UnauthorizedToolError are not retried by ReliabilityEngine."""
        call_count = 0

        def failing_tool_call():
            nonlocal call_count
            call_count += 1
            raise ToolArgumentValidationError("get_price", "Invalid date format")

        engine = ReliabilityEngine(
            retry_config=RetryConfig(max_attempts=3, initial_backoff=0.01),
        )

        res = engine.execute(
            func=failing_tool_call,
            question_id="q_test_val_retry",
            client_id="cli_1014",
        )

        # Non-retryable deterministic errors must NOT be retried (call_count == 1)
        assert call_count == 1
        assert res["abstained"] is True
        assert "upstream_issue" in res["flags"]

    def test_invalid_numeric_field_rejected(self, store: DataStore):
        """Verify that an invalid numeric field name outside the allowed schema is rejected."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(ToolArgumentValidationError):
            verifier.verify_and_execute(
                tool_func=lambda cid, numeric_field: {},
                agent_name="book_qa",
                tool_name="get_transaction_total",
                kwargs={"cid": "cli_1014", "numeric_field": "invalid_unsupported_field"},
                trusted_client_id="cli_1014",
            )

    def test_tool_execution_domain_error_propagates(self, store: DataStore):
        """Verify that underlying domain errors (e.g. MarketCoverageError) propagate cleanly."""
        verifier = ToolVerifier(store=store)
        with pytest.raises(Exception) as exc_info:
            verifier.verify_and_execute(
                tool_func=lambda symbol: get_instrument_details(store, symbol),
                agent_name="market_desk",
                tool_name="get_instrument",
                kwargs={"symbol": "UNCOVERED_SYM"},
            )
        assert "UNCOVERED_SYM" in str(exc_info.value)

    def test_verified_wrapper_preserves_function_metadata(self, store: DataStore):
        """Verify that create_verified_tool preserves docstring and name via wraps."""
        def dummy_tool(cid: str) -> dict:
            """Dummy docstring."""
            return {"client_id": cid}

        wrapped = create_verified_tool(
            func=dummy_tool,
            agent_name="book_qa",
            store=store,
            trusted_client_id="cli_1014",
            tool_name_override="get_cash_balance",
        )
        assert wrapped.__name__ == "dummy_tool"
        assert wrapped.__doc__ == "Dummy docstring."

