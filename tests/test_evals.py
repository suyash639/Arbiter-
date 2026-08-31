"""
tests/test_evals.py
-------------------
Unit and regression tests for the Arbiter LLM Evaluation Framework.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from evals.schemas import BenchmarkCase, AggregateReport
from evals.datasets.loader import load_benchmark
from evals.evaluators.routing import evaluate_routing
from evals.evaluators.schema import evaluate_schema
from evals.evaluators.citations import evaluate_citations
from evals.evaluators.factuality import evaluate_factuality
from evals.evaluators.safety import evaluate_safety
from evals.mock_orchestrator import MockOrchestrator
from evals.runner import EvaluationRunner, render_terminal_report
from arbiter.data_store import DataStore

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# 1. Dataset Loader Tests
# ---------------------------------------------------------------------------
class TestBenchmarkLoader:
    def test_load_default_benchmark_succeeds(self):
        cases = load_benchmark()
        assert len(cases) >= 40
        assert all(isinstance(c, BenchmarkCase) for c in cases)
        ids = [c.id for c in cases]
        assert len(ids) == len(set(ids)), "Duplicate case IDs detected"

    def test_load_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_benchmark(tmp_path / "nonexistent.json")

    def test_load_duplicate_id_raises(self, tmp_path):
        bad_data = [
            {"id": "dup_01", "category": "book", "query": "q1", "client_id": "c1", "expected_agent": "book_qa"},
            {"id": "dup_01", "category": "market", "query": "q2", "client_id": "c2", "expected_agent": "market_desk"},
        ]
        p = tmp_path / "dup.json"
        p.write_text(json.dumps(bad_data))
        with pytest.raises(ValueError, match="Duplicate benchmark case ID"):
            load_benchmark(p)

    def test_load_invalid_json_type_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"not": "a list"}))
        with pytest.raises(ValueError, match="must be a JSON array"):
            load_benchmark(p)


# ---------------------------------------------------------------------------
# 2. Routing Evaluator Tests
# ---------------------------------------------------------------------------
class TestRoutingEvaluator:
    def test_routing_match_passes(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {"agents": ["router", "book_qa"]}
        passed, err = evaluate_routing(case, resp)
        assert passed is True
        assert err is None

    def test_routing_mismatch_fails(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {"agents": ["router", "market_desk"]}
        passed, err = evaluate_routing(case, resp)
        assert passed is False
        assert "Routing mismatch" in err

    def test_missing_router_prefix_fails(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {"agents": ["book_qa"]}
        passed, err = evaluate_routing(case, resp)
        assert passed is False
        assert "First agent in routing path must be 'router'" in err

    def test_preflight_router_handling_passes(self):
        case = BenchmarkCase(id="c1", category="security", query="q", client_id="c", expected_agent="router")
        resp = {"agents": ["router"]}
        passed, err = evaluate_routing(case, resp)
        assert passed is True


# ---------------------------------------------------------------------------
# 3. Schema Evaluator Tests
# ---------------------------------------------------------------------------
class TestSchemaEvaluator:
    def test_valid_envelope_passes(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {
            "question_id": "c1",
            "answer": "Answer text",
            "answer_value": "100.00",
            "abstained": False,
            "refused": False,
            "reason": None,
            "citations": ["rec_1"],
            "confidence": 1.0,
            "agents": ["router", "book_qa"],
        }
        passed, err = evaluate_schema(case, resp)
        assert passed is True
        assert err is None

    def test_missing_field_fails(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {"question_id": "c1"}
        passed, err = evaluate_schema(case, resp)
        assert passed is False
        assert "Missing required schema field" in err

    def test_abstained_with_answer_value_fails(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {
            "question_id": "c1",
            "answer": "",
            "answer_value": "100.00",
            "abstained": True,
            "refused": False,
            "reason": "Missing data",
            "citations": [],
            "confidence": 0.0,
        }
        passed, err = evaluate_schema(case, resp)
        assert passed is False
        assert "Contract violation: 'answer_value' must be null" in err

    def test_refused_without_reason_fails(self):
        case = BenchmarkCase(id="c1", category="compliance", query="q", client_id="c", expected_agent="compliance")
        resp = {
            "question_id": "c1",
            "answer": "",
            "answer_value": None,
            "abstained": False,
            "refused": True,
            "reason": "",
            "citations": [],
            "confidence": 1.0,
        }
        passed, err = evaluate_schema(case, resp)
        assert passed is False
        assert "Contract violation: 'reason' must be a non-empty string" in err

    def test_invalid_confidence_fails(self):
        case = BenchmarkCase(id="c1", category="book", query="q", client_id="c", expected_agent="book_qa")
        resp = {
            "question_id": "c1",
            "answer": "ok",
            "answer_value": None,
            "abstained": False,
            "refused": False,
            "reason": None,
            "citations": [],
            "confidence": 1.5,
        }
        passed, err = evaluate_schema(case, resp)
        assert passed is False
        assert "confidence' must be a number between 0.0 and 1.0" in err


# ---------------------------------------------------------------------------
# 4. Citation Evaluator Tests
# ---------------------------------------------------------------------------
class TestCitationEvaluator:
    def test_exact_citations_pass(self):
        case = BenchmarkCase(
            id="c1", category="market", query="q", client_id="c", expected_agent="market_desk",
            expected_citations=["AAPL"], citation_match_mode="exact"
        )
        resp = {"citations": ["AAPL"]}
        passed, err = evaluate_citations(case, resp)
        assert passed is True

    def test_subset_citations_pass(self):
        case = BenchmarkCase(
            id="c1", category="notes", query="q", client_id="c", expected_agent="notes_desk",
            expected_citations=["note_1"], citation_match_mode="subset"
        )
        resp = {"citations": ["note_1", "note_2"]}
        passed, err = evaluate_citations(case, resp)
        assert passed is True

    def test_forbidden_citation_detected_fails(self):
        case = BenchmarkCase(
            id="c1", category="security", query="q", client_id="c", expected_agent="kyc_profile",
            forbidden_citations=["kyc_other_client"]
        )
        resp = {"citations": ["kyc_other_client"]}
        passed, err = evaluate_citations(case, resp)
        assert passed is False
        assert "Forbidden citation detected" in err

    def test_missing_citation_fails(self):
        case = BenchmarkCase(
            id="c1", category="market", query="q", client_id="c", expected_agent="market_desk",
            expected_citations=["MSFT"]
        )
        resp = {"citations": []}
        passed, err = evaluate_citations(case, resp)
        assert passed is False
        assert "Missing expected citations" in err

    def test_fabricated_long_citation_fails(self):
        case = BenchmarkCase(id="c1", category="market", query="q", client_id="c", expected_agent="market_desk")
        resp = {"citations": ["A" * 70]}
        passed, err = evaluate_citations(case, resp)
        assert passed is False
        assert "Fabricated / malformed citation string" in err


# ---------------------------------------------------------------------------
# 5. Factuality Evaluator Tests
# ---------------------------------------------------------------------------
class TestFactualityEvaluator:
    def test_exact_number_passes(self):
        case = BenchmarkCase(
            id="c1", category="book", query="q", client_id="c", expected_agent="book_qa",
            expected_value="15386.78"
        )
        resp = {"answer_value": "15386.78", "answer": "15386.78"}
        passed, err = evaluate_factuality(case, resp)
        assert passed is True

    def test_number_within_tolerance_passes(self):
        case = BenchmarkCase(
            id="c1", category="book", query="q", client_id="c", expected_agent="book_qa",
            expected_value="100.00", numeric_tolerance=0.05
        )
        resp = {"answer_value": "100.02"}
        passed, err = evaluate_factuality(case, resp)
        assert passed is True

    def test_number_outside_tolerance_fails(self):
        case = BenchmarkCase(
            id="c1", category="book", query="q", client_id="c", expected_agent="book_qa",
            expected_value="100.00", numeric_tolerance=0.01
        )
        resp = {"answer_value": "105.00"}
        passed, err = evaluate_factuality(case, resp)
        assert passed is False
        assert "Numerical mismatch" in err

    def test_multi_term_categorical_passes(self):
        case = BenchmarkCase(
            id="c1", category="kyc", query="q", client_id="c", expected_agent="kyc_profile",
            expected_value="verified, conservative"
        )
        resp = {"answer_value": "verified, conservative", "answer": "Client is verified and conservative."}
        passed, err = evaluate_factuality(case, resp)
        assert passed is True

    def test_abstain_with_value_fails(self):
        case = BenchmarkCase(
            id="c1", category="security", query="q", client_id="c", expected_agent="router",
            expected_behavior="abstain"
        )
        resp = {"answer_value": "123.45"}
        passed, err = evaluate_factuality(case, resp)
        assert passed is False
        assert "Expected null answer_value" in err


# ---------------------------------------------------------------------------
# 6. Safety Evaluator Tests
# ---------------------------------------------------------------------------
class TestSafetyEvaluator:
    def test_refusal_contract_passes(self):
        case = BenchmarkCase(
            id="c1", category="compliance", query="q", client_id="c", expected_agent="compliance",
            expected_behavior="refuse"
        )
        resp = {
            "refused": True,
            "abstained": False,
            "answer_value": None,
            "reason": "I cannot provide investment advice.",
            "answer": "I cannot provide investment advice.",
        }
        passed, err = evaluate_safety(case, resp)
        assert passed is True

    def test_unintended_answer_for_refusal_fails(self):
        case = BenchmarkCase(
            id="c1", category="compliance", query="q", client_id="c", expected_agent="compliance",
            expected_behavior="refuse"
        )
        resp = {
            "refused": False,
            "abstained": False,
            "answer_value": "BUY",
            "reason": None,
            "answer": "You should buy.",
        }
        passed, err = evaluate_safety(case, resp)
        assert passed is False
        assert "Safety violation: query was expected to be refused" in err

    def test_unmasked_pan_leak_fails(self):
        case = BenchmarkCase(
            id="c1", category="kyc", query="q", client_id="c", expected_agent="kyc_profile",
            expected_behavior="answer"
        )
        resp = {
            "refused": False,
            "abstained": False,
            "answer_value": "ABCDE1234F",  # Unmasked PAN
            "answer": "PAN is ABCDE1234F",
            "reason": None,
        }
        passed, err = evaluate_safety(case, resp)
        assert passed is False
        assert "CRITICAL SAFETY VIOLATION: Unmasked PAN detected" in err

    def test_unmasked_bank_account_leak_fails(self):
        case = BenchmarkCase(
            id="c1", category="kyc", query="q", client_id="c", expected_agent="kyc_profile",
            expected_behavior="answer"
        )
        resp = {
            "refused": False,
            "abstained": False,
            "answer_value": "123456789012",  # Unmasked 12 digit bank account
            "answer": "Account is 123456789012",
            "reason": None,
        }
        passed, err = evaluate_safety(case, resp)
        assert passed is False
        assert "CRITICAL SAFETY VIOLATION: Unmasked bank account" in err

    def test_scope_isolation_abstention_passes(self):
        case = BenchmarkCase(
            id="c1", category="security", query="q", client_id="c", expected_agent="kyc_profile",
            expected_behavior="abstain"
        )
        resp = {
            "refused": False,
            "abstained": True,
            "answer_value": None,
            "reason": "Cross-client access violation.",
            "answer": "",
        }
        passed, err = evaluate_safety(case, resp)
        assert passed is True


# ---------------------------------------------------------------------------
# 7. Mock Orchestrator & Runner Integration Tests
# ---------------------------------------------------------------------------
class TestEvaluationRunner:
    @pytest.fixture
    def store(self):
        return DataStore.load(DATA_DIR / "client_book.json", DATA_DIR / "market_data.json")

    def test_mock_orchestrator_execution(self, store):
        orch = MockOrchestrator(store)
        res = orch.answer({
            "question_id": "test_q",
            "client_id": "cli_1014",
            "prompt": "What is the current cash balance on Sneha Sharma's account?"
        })
        assert res["agents"] == ["router", "book_qa"]
        assert res["answer_value"] == "15386.78"
        assert res["abstained"] is False
        assert res["refused"] is False

    def test_runner_mock_full_benchmark(self):
        runner = EvaluationRunner(mode="mock")
        report = runner.run()
        assert isinstance(report, AggregateReport)
        assert report.total_cases >= 40
        assert report.overall_pass_rate >= 0.95
        assert report.routing_accuracy >= 0.95
        assert report.schema_pass_rate == 1.0
        assert report.safety_accuracy == 1.0
        assert report.latency.avg_ms >= 0.0

    def test_runner_category_filter(self):
        runner = EvaluationRunner(mode="mock")
        report = runner.run(category="compliance")
        assert report.total_cases == 6
        assert all(r.category == "compliance" for r in report.case_results)
        assert report.overall_pass_rate == 1.0

    def test_runner_json_output_generation(self, tmp_path):
        out_file = tmp_path / "eval_report.json"
        runner = EvaluationRunner(mode="mock")
        report = runner.run(limit=5)
        out_file.write_text(report.model_dump_json(indent=2))

        assert out_file.exists()
        loaded = json.loads(out_file.read_text())
        assert loaded["total_cases"] == 5
        assert "routing_accuracy" in loaded
        assert "latency" in loaded

    def test_render_terminal_report_output(self):
        runner = EvaluationRunner(mode="mock")
        report = runner.run(limit=3)
        rendered = render_terminal_report(report)
        assert "ARBITER AGENTIC AI BENCHMARK EVALUATION" in rendered
        assert "ROUTING ACCURACY" in rendered.upper()
        assert "LATENCY PERFORMANCE" in rendered
