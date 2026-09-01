"""
tests/test_observability.py
---------------------------
Comprehensive unit and integration test suite for the Arbiter Observability Subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import (
    ObservabilityManager,
    ModelPricingRegistry,
    ModelPricing,
    RedactionEngine,
    StructuredLogger,
    TraceCollector,
    generate_request_id,
    get_current_request_id,
    set_current_request_id,
    reset_current_request_id,
    compute_aggregate_metrics,
    RequestTrace,
    RequestMetadata,
    RouterTrace,
    SpecialistTrace,
    ToolCallTrace,
    LLMCallTrace,
    ValidationTrace,
)
from arbiter.orchestrator import ArbiterOrchestrator

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# 1. Request ID & Context Propagation
# ---------------------------------------------------------------------------
class TestContextAndRequestId:
    def test_request_id_generation_and_uniqueness(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100
        for rid in ids:
            assert rid.startswith("req_")
            assert len(rid) > 6

    def test_request_id_context_propagation(self):
        token0 = set_current_request_id(None)
        assert get_current_request_id() is None
        token = set_current_request_id("req_test_123")
        assert get_current_request_id() == "req_test_123"
        reset_current_request_id(token)
        assert get_current_request_id() is None
        reset_current_request_id(token0)



# ---------------------------------------------------------------------------
# 2. Pricing Registry & Cost Calculations
# ---------------------------------------------------------------------------
class TestModelPricingRegistry:
    def test_registered_model_cost_calculation(self):
        registry = ModelPricingRegistry()
        # gemini-3.6-flash: input $0.075 / 1M, output $0.30 / 1M
        # 10,000 in ($0.00075) + 2,000 out ($0.0006) = $0.00135
        cost = registry.calculate_cost("gemini-3.6-flash", input_tokens=10000, output_tokens=2000)
        assert cost == 0.00135

    def test_custom_model_registration(self):
        registry = ModelPricingRegistry()
        registry.register_price("custom-llm", input_cost_per_million=1.0, output_cost_per_million=2.0)
        cost = registry.calculate_cost("custom-llm", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 3.0

    def test_missing_pricing_returns_none(self):
        registry = ModelPricingRegistry()
        cost = registry.calculate_cost("unknown-model-xyz", input_tokens=100, output_tokens=100)
        assert cost is None

    def test_missing_token_counts_returns_none(self):
        registry = ModelPricingRegistry()
        assert registry.calculate_cost("gemini-3.6-flash", input_tokens=None, output_tokens=100) is None
        assert registry.calculate_cost("gemini-3.6-flash", input_tokens=100, output_tokens=None) is None


# ---------------------------------------------------------------------------
# 3. Sensitive Data & PII Redaction
# ---------------------------------------------------------------------------
class TestRedactionEngine:
    def test_pan_redaction(self):
        text = "Client PAN is ABCDE1234F on record."
        sanitized = RedactionEngine.redact_text(text)
        assert "ABCDE1234F" not in sanitized
        assert "****234F" in sanitized

    def test_bank_account_redaction(self):
        text = "Account number 123456789012 was credited."
        sanitized = RedactionEngine.redact_text(text)
        assert "123456789012" not in sanitized
        assert "****9012" in sanitized

    def test_api_key_redaction(self):
        text = "Using key AIzaSyD1234567890123456789012345678901 for access."
        sanitized = RedactionEngine.redact_text(text)
        assert "AIzaSyD" not in sanitized
        assert "[REDACTED_SECRET]" in sanitized

    def test_dictionary_field_redaction(self):
        payload = {
            "api_key": "secret-12345",
            "pan": "ABCDE1234F",
            "nested": {"bank_account": "987654321098"},
        }
        redacted = RedactionEngine.redact_value(payload)
        assert redacted["api_key"] == "[REDACTED]"
        assert "****234F" in redacted["pan"]
        assert "****1098" in redacted["nested"]["bank_account"]

    def test_tool_result_sanitization_truncation(self):
        large_list = [{"id": f"txn_{i}", "val": i} for i in range(50)]
        res = RedactionEngine.sanitize_tool_result(large_list)
        assert isinstance(res, dict)
        assert res["item_count"] == 50
        assert res["truncated"] is True
        assert len(res["sample"]) == 2


# ---------------------------------------------------------------------------
# 4. Structured Logger
# ---------------------------------------------------------------------------
class TestStructuredLogger:
    def test_structured_log_emission(self, caplog):
        logger = StructuredLogger("test_logger")
        with caplog.at_level("INFO"):
            logger.info("test_event", custom_key="value", pan="ABCDE1234F")

        assert "test_event" in caplog.text
        assert "custom_key" in caplog.text
        assert "ABCDE1234F" not in caplog.text
        assert "****234F" in caplog.text


# ---------------------------------------------------------------------------
# 5. Trace Lifecycle & Observability Manager
# ---------------------------------------------------------------------------
class TestObservabilityManager:
    def test_trace_lifecycle_start_to_finish(self):
        collector = TraceCollector()
        obs = ObservabilityManager(collector=collector)

        rid = obs.start_request(
            question_id="q_100",
            client_id="cli_1014",
            prompt="What is the cash balance?",
            provider="gemini",
            model="gemini-3.6-flash",
        )
        assert rid.startswith("req_")

        obs.record_router(
            request_id=rid,
            selected_specialist="book_qa",
            agent_path=["router", "book_qa"],
            latency_ms=25.0,
            llm_model="gemini-3.6-flash",
            input_tokens=150,
            output_tokens=20,
        )

        obs.record_tool_call(
            request_id=rid,
            tool_name="get_cash_balance",
            agent="book_qa",
            start_time="2026-09-01T00:00:00Z",
            end_time="2026-09-01T00:00:00Z",
            latency_ms=1.5,
            success=True,
            args={"cid": "cli_1014"},
            result_summary={"balance": "15386.78"},
        )

        obs.record_specialist_llm(
            request_id=rid,
            agent="book_qa",
            provider="gemini",
            model="gemini-3.6-flash",
            latency_ms=180.0,
            input_tokens=400,
            output_tokens=80,
        )

        obs.record_validation(
            request_id=rid,
            schema_valid=True,
            citation_count=1,
            citations=["cli_1014"],
        )

        trace = obs.finish_request(
            request_id=rid,
            response={
                "question_id": "q_100",
                "answer": "Cash balance is $15,386.78",
                "answer_value": "15386.78",
                "abstained": False,
                "refused": False,
                "citations": ["cli_1014"],
                "confidence": 1.0,
            },
        )

        assert trace.metadata.request_id == rid
        assert trace.status == "success"
        assert trace.router.selected_specialist == "book_qa"
        assert len(trace.specialist.tool_calls) == 1
        assert trace.specialist.tool_calls[0].tool_name == "get_cash_balance"
        assert trace.total_tokens == (150 + 20 + 400 + 80)
        assert trace.total_cost_usd is not None
        assert trace.total_latency_ms >= 0.0

        # Verify collector retrieval
        stored = obs.get_trace(rid)
        assert stored == trace

    def test_refusal_request_trace(self):
        obs = ObservabilityManager()
        rid = obs.start_request("q_ref", "cli_1014", "Should I buy AAPL?")
        trace = obs.finish_request(rid, {
            "question_id": "q_ref",
            "answer": "I cannot provide investment advice.",
            "answer_value": None,
            "abstained": False,
            "refused": True,
            "reason": "Policy constraint",
            "citations": [],
        })
        assert trace.status == "refused"

    def test_abstention_request_trace(self):
        obs = ObservabilityManager()
        rid = obs.start_request("q_abs", "cli_1014", "What is passport number?")
        trace = obs.finish_request(rid, {
            "question_id": "q_abs",
            "answer": "",
            "answer_value": None,
            "abstained": True,
            "refused": False,
            "reason": "Data not on file",
            "citations": [],
        })
        assert trace.status == "abstained"

    def test_upstream_error_trace(self):
        obs = ObservabilityManager()
        rid = obs.start_request("q_err", "cli_1014", "Query")
        trace = obs.finish_request(
            rid,
            {"question_id": "q_err", "flags": ["upstream_issue"], "abstained": True, "refused": False},
            error_message="Gateway timeout",
        )
        assert trace.status == "error"
        assert trace.error_message == "Gateway timeout"

    def test_multiple_tool_calls_in_request(self):
        obs = ObservabilityManager()
        rid = obs.start_request("q_multi", "cli_1014", "Multi tool query")

        for i in range(4):
            obs.record_tool_call(
                request_id=rid,
                tool_name=f"tool_{i}",
                agent="book_qa",
                start_time="2026-09-01T00:00:00Z",
                end_time="2026-09-01T00:00:00Z",
                latency_ms=float(i + 1),
                success=(i != 2),
            )

        trace = obs.finish_request(rid, {"question_id": "q_multi", "abstained": False, "refused": False})
        assert len(trace.specialist.tool_calls) == 4
        assert trace.specialist.tool_calls[2].success is False


# ---------------------------------------------------------------------------
# 6. Trace Collector & File Sink
# ---------------------------------------------------------------------------
class TestTraceCollector:
    def test_collector_capacity_eviction(self):
        collector = TraceCollector(max_traces=3)
        for i in range(5):
            meta = RequestMetadata(
                request_id=f"req_{i}",
                timestamp="2026-09-01T00:00:00Z",
                question_id=f"q_{i}",
                client_id="cli_1014",
            )
            collector.add_trace(RequestTrace(metadata=meta, total_latency_ms=10.0))

        traces = collector.get_all_traces()
        assert len(traces) == 3
        # Should contain req_2, req_3, req_4
        assert [t.metadata.request_id for t in traces] == ["req_2", "req_3", "req_4"]

    def test_jsonl_file_sink(self, tmp_path):
        sink = tmp_path / "traces.jsonl"
        collector = TraceCollector(sink_path=sink)

        meta = RequestMetadata(
            request_id="req_sink_1",
            timestamp="2026-09-01T00:00:00Z",
            question_id="q_1",
            client_id="cli_1014",
        )
        collector.add_trace(RequestTrace(metadata=meta, total_latency_ms=15.0))

        assert sink.exists()
        lines = sink.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["metadata"]["request_id"] == "req_sink_1"


# ---------------------------------------------------------------------------
# 7. Aggregate Metrics & Percentiles
# ---------------------------------------------------------------------------
class TestMetricsAggregation:
    def test_aggregate_metrics_calculations(self):
        traces = []
        for i in range(10):
            status = "success" if i < 7 else ("refused" if i < 9 else "abstained")
            meta = RequestMetadata(
                request_id=f"req_{i}",
                timestamp="2026-09-01T00:00:00Z",
                question_id=f"q_{i}",
                client_id="cli_1014",
                model="gemini-3.6-flash",
            )
            sp = SpecialistTrace(
                agent_name="book_qa" if i % 2 == 0 else "market_desk",
                latency_ms=float(i * 10),
                tool_calls=[
                    ToolCallTrace(
                        tool_name="tool_a",
                        agent="book_qa",
                        start_time="2026-09-01T00:00:00Z",
                        end_time="2026-09-01T00:00:00Z",
                        latency_ms=1.0,
                        success=(i != 0),
                    )
                ]
            )
            traces.append(RequestTrace(
                metadata=meta,
                specialist=sp,
                status=status,
                total_latency_ms=float((i + 1) * 10),
                total_tokens=100,
                total_cost_usd=0.001,
            ))

        metrics = compute_aggregate_metrics(traces)
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 7
        assert metrics.refused_requests == 2
        assert metrics.abstained_requests == 1
        assert metrics.error_requests == 0
        assert metrics.min_latency_ms == 10.0
        assert metrics.max_latency_ms == 100.0
        assert metrics.total_tokens == 1000
        assert metrics.avg_tokens_per_request == 100.0
        assert metrics.total_estimated_cost_usd == 0.01
        assert metrics.total_tool_calls == 10
        assert metrics.tool_success_rate == 0.9
        assert "book_qa" in metrics.requests_per_agent
        assert "market_desk" in metrics.requests_per_agent


# ---------------------------------------------------------------------------
# 8. Orchestrator Integration with Observability
# ---------------------------------------------------------------------------
class TestOrchestratorObservabilityIntegration:
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
        )

    def test_orchestrator_records_trace_on_abstention(self, store, config):
        orch = ArbiterOrchestrator(store, config)
        orch.obs.reset()

        res = orch.answer({"question_id": "q_unknown", "client_id": "cli_9999", "prompt": "Hi"})
        assert res["abstained"] is True

        traces = orch.obs.get_all_traces()
        assert len(traces) == 1
        trace = traces[0]
        assert trace.metadata.question_id == "q_unknown"
        assert trace.status == "abstained"

    def test_orchestrator_records_trace_on_compliance_refusal(self, store, config):
        from unittest.mock import MagicMock
        orch = ArbiterOrchestrator(store, config)
        orch.obs.reset()

        orch.specialists["compliance"].answer = MagicMock(return_value={
            "question_id": "q_advice",
            "answer": "I cannot provide personalized investment advice.",
            "answer_value": None,
            "abstained": False,
            "refused": True,
            "reason": "Personalized investment advice is prohibited under compliance policy.",
            "citations": [],
            "confidence": 1.0,
            "flags": [],
            "agents": ["router", "compliance"]
        })

        res = orch.answer({
            "question_id": "q_advice",
            "client_id": "cli_1014",
            "prompt": "What strategy do you recommend to buy more AAPL?"
        })
        assert res["refused"] is True

        traces = orch.obs.get_all_traces()
        assert len(traces) == 1
        trace = traces[0]
        assert trace.status == "refused"
        assert trace.router.selected_specialist == "compliance"

