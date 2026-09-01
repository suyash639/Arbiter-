"""
evals/runner.py
---------------
CLI and programmatic evaluation runner for Arbiter.

Supports:
- Offline mock benchmark mode (`--mode mock`)
- Live Gemini multi-agent evaluation (`--mode live`)
- Configurable rate-limit pacing (`--delay FLOAT`)
- Category filtering (`--category {book,kyc,notes,market,compliance,security,edge_case}`)
- Terminal reporting and machine-readable JSON exports (`--output PATH`)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.orchestrator import ArbiterOrchestrator
from evals.datasets.loader import load_benchmark
from evals.evaluators.citations import evaluate_citations
from evals.evaluators.factuality import evaluate_factuality
from evals.evaluators.routing import evaluate_routing
from evals.evaluators.safety import evaluate_safety
from evals.evaluators.schema import evaluate_schema
from evals.mock_orchestrator import MockOrchestrator
from evals.schemas import (
    AggregateReport,
    BenchmarkCase,
    CaseEvaluationResult,
    CategoryMetrics,
    LatencyStats,
)


class EvaluationRunner:
    """Executes benchmark cases against an orchestrator and compiles metrics."""

    def __init__(
        self,
        mode: str = "mock",
        dataset_path: Path | str | None = None,
        delay_seconds: float = 0.0,
        config: Config | None = None,
        data_dir: Path | str = "data",
    ):
        self.mode = mode
        self.dataset_path = dataset_path
        self.delay_seconds = delay_seconds
        self.data_dir = Path(data_dir)

        # Load configuration
        if config is not None:
            self.config = config
        else:
            self.config = Config.from_env()

        # Load data store
        self.store = DataStore.load(
            self.data_dir / "client_book.json",
            self.data_dir / "market_data.json",
        )

        # Initialize orchestrator
        if self.mode == "mock":
            self.orchestrator = MockOrchestrator(self.store, self.config)
        else:
            self.orchestrator = ArbiterOrchestrator(self.store, self.config)

    def run(
        self,
        category: str | None = None,
        limit: int | None = None,
    ) -> AggregateReport:
        """Execute evaluation on benchmark cases and compute aggregate metrics."""
        cases = load_benchmark(self.dataset_path)

        if category:
            cases = [c for c in cases if c.category.lower() == category.lower()]

        if limit and limit > 0:
            cases = cases[:limit]

        case_results: list[CaseEvaluationResult] = []
        failures: list[dict[str, Any]] = []

        total_cases = len(cases)
        latencies: list[float] = []

        for idx, case in enumerate(cases):
            if idx > 0 and self.delay_seconds > 0:
                time.sleep(self.delay_seconds)

            payload = {
                "question_id": case.id,
                "client_id": case.client_id,
                "prompt": case.query,
            }

            t0 = time.perf_counter()
            try:
                raw_response = self.orchestrator.answer(payload)
                dt_ms = (time.perf_counter() - t0) * 1000.0
            except Exception as exc:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                raw_response = {
                    "question_id": case.id,
                    "answer": "",
                    "answer_value": None,
                    "abstained": True,
                    "refused": False,
                    "reason": f"Execution error: {exc}",
                    "citations": [],
                    "confidence": 0.0,
                    "flags": ["upstream_issue"],
                    "agents": ["router"],
                }

            latencies.append(dt_ms)

            # Evaluate dimensions
            routing_pass, r_err = evaluate_routing(case, raw_response)
            schema_pass, s_err = evaluate_schema(case, raw_response)
            citation_pass, c_err = evaluate_citations(case, raw_response)
            factual_pass, f_err = evaluate_factuality(case, raw_response)
            safety_pass, sf_err = evaluate_safety(case, raw_response)

            case_fail_reasons: list[str] = []
            for err in [r_err, s_err, c_err, f_err, sf_err]:
                if err:
                    case_fail_reasons.append(err)

            overall_pass = len(case_fail_reasons) == 0

            # Determine case status
            if "upstream_issue" in raw_response.get("flags", []):
                status = "UPSTREAM_ERROR"
            elif raw_response.get("refused"):
                status = "REFUSED" if overall_pass else "FAIL"
            elif raw_response.get("abstained"):
                status = "ABSTAINED" if overall_pass else "FAIL"
            else:
                status = "PASS" if overall_pass else "FAIL"

            result = CaseEvaluationResult(
                case_id=case.id,
                category=case.category,
                expected_agent=case.expected_agent,
                actual_agents=raw_response.get("agents", []),
                routing_pass=routing_pass,
                schema_pass=schema_pass,
                factual_pass=factual_pass,
                citation_pass=citation_pass,
                safety_pass=safety_pass,
                overall_pass=overall_pass,
                status=status,
                failure_reasons=case_fail_reasons,
                latency_ms=round(dt_ms, 2),
                actual_value=raw_response.get("answer_value"),
                actual_citations=raw_response.get("citations", []),
                raw_answer=raw_response.get("answer"),
            )
            case_results.append(result)

            if not overall_pass:
                failures.append({
                    "case_id": case.id,
                    "category": case.category,
                    "query": case.query,
                    "expected_agent": case.expected_agent,
                    "actual_agents": raw_response.get("agents"),
                    "expected_value": case.expected_value,
                    "actual_value": raw_response.get("answer_value"),
                    "failure_reasons": case_fail_reasons,
                })

        # Calculate statistics
        passed_count = sum(1 for r in case_results if r.overall_pass)
        failed_count = total_cases - passed_count

        routing_acc = sum(1 for r in case_results if r.routing_pass) / total_cases if total_cases else 0.0
        factual_acc = sum(1 for r in case_results if r.factual_pass) / total_cases if total_cases else 0.0
        citation_acc = sum(1 for r in case_results if r.citation_pass) / total_cases if total_cases else 0.0
        safety_acc = sum(1 for r in case_results if r.safety_pass) / total_cases if total_cases else 0.0
        schema_rate = sum(1 for r in case_results if r.schema_pass) / total_cases if total_cases else 0.0
        overall_rate = passed_count / total_cases if total_cases else 0.0

        # Latency metrics
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95) if sorted_latencies else 0
        p95_val = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)] if sorted_latencies else 0.0

        slowest_pairs = sorted(
            [{"case_id": r.case_id, "latency_ms": r.latency_ms} for r in case_results],
            key=lambda x: x["latency_ms"],
            reverse=True,
        )[:5]

        latency_stats = LatencyStats(
            avg_ms=round(statistics.mean(latencies), 2) if latencies else 0.0,
            median_ms=round(statistics.median(latencies), 2) if latencies else 0.0,
            p95_ms=round(p95_val, 2),
            min_ms=round(min(latencies), 2) if latencies else 0.0,
            max_ms=round(max(latencies), 2) if latencies else 0.0,
            slowest_cases=slowest_pairs,
        )

        # Category breakdowns
        categories: dict[str, CategoryMetrics] = {}
        all_categories = sorted({c.category for c in cases})
        for cat in all_categories:
            cat_results = [r for r in case_results if r.category == cat]
            c_total = len(cat_results)
            c_passed = sum(1 for r in cat_results if r.overall_pass)
            categories[cat] = CategoryMetrics(
                total=c_total,
                passed=c_passed,
                pass_rate=round(c_passed / c_total, 4) if c_total else 0.0,
                routing_accuracy=round(sum(1 for r in cat_results if r.routing_pass) / c_total, 4) if c_total else 0.0,
                factual_accuracy=round(sum(1 for r in cat_results if r.factual_pass) / c_total, 4) if c_total else 0.0,
                citation_accuracy=round(sum(1 for r in cat_results if r.citation_pass) / c_total, 4) if c_total else 0.0,
                safety_accuracy=round(sum(1 for r in cat_results if r.safety_pass) / c_total, 4) if c_total else 0.0,
                schema_pass_rate=round(sum(1 for r in cat_results if r.schema_pass) / c_total, 4) if c_total else 0.0,
            )

        # Query observability manager for telemetry totals
        from arbiter.observability import get_observability_manager
        obs_metrics = get_observability_manager().get_metrics()

        report = AggregateReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            dataset=str(Path(self.dataset_path).name if self.dataset_path else "benchmark.json"),
            mode=self.mode,
            provider=self.config.llm_provider if self.mode == "live" else "deterministic-mock",
            model=self.config.llm_model if self.mode == "live" else "rule-engine",
            total_cases=total_cases,
            passed=passed_count,
            failed=failed_count,
            overall_pass_rate=round(overall_rate, 4),
            routing_accuracy=round(routing_acc, 4),
            factual_accuracy=round(factual_acc, 4),
            citation_accuracy=round(citation_acc, 4),
            safety_accuracy=round(safety_acc, 4),
            schema_pass_rate=round(schema_rate, 4),
            latency=latency_stats,
            total_tokens=obs_metrics.total_tokens if obs_metrics.total_tokens > 0 else None,
            estimated_cost_usd=obs_metrics.total_estimated_cost_usd if obs_metrics.total_estimated_cost_usd > 0 else None,
            total_tool_calls=obs_metrics.total_tool_calls,
            tool_success_rate=obs_metrics.tool_success_rate,
            categories=categories,
            case_results=case_results,
            failures=failures,
        )

        return report


def render_terminal_report(report: AggregateReport) -> str:
    """Format an AggregateReport into an executive CLI terminal display."""
    lines = [
        "=" * 64,
        "  ARBITER AGENTIC AI BENCHMARK EVALUATION",
        "=" * 64,
        f"Timestamp:       {report.timestamp}",
        f"Mode:            {report.mode.upper()}",
        f"Provider:        {report.provider}",
        f"Model:           {report.model}",
        f"Dataset:         {report.dataset} ({report.total_cases} test cases)",
        "-" * 64,
        "  OVERALL EVALUATION METRICS",
        "-" * 64,
        f"Routing Accuracy:       {report.routing_accuracy * 100:6.1f}%",
        f"Factual Accuracy:       {report.factual_accuracy * 100:6.1f}%",
        f"Citation Accuracy:      {report.citation_accuracy * 100:6.1f}%",
        f"Safety / Refusal:       {report.safety_accuracy * 100:6.1f}%",
        f"Schema Compliance:      {report.schema_pass_rate * 100:6.1f}%",
        "-" * 64,
        f"TOTAL PASSED:           {report.passed} / {report.total_cases} ({report.overall_pass_rate * 100:.1f}%)",
        f"TOTAL FAILED:           {report.failed} / {report.total_cases}",
        "-" * 64,
        "  LATENCY PERFORMANCE",
        "-" * 64,
        f"Average Latency:        {report.latency.avg_ms:8.2f} ms",
        f"Median Latency:         {report.latency.median_ms:8.2f} ms",
        f"P95 Latency:            {report.latency.p95_ms:8.2f} ms",
        f"Min / Max:              {report.latency.min_ms:.1f} ms / {report.latency.max_ms:.1f} ms",
        f"Total Tool Calls:       {report.total_tool_calls} (Success Rate: {report.tool_success_rate * 100:.1f}%)",
    ]

    if report.total_tokens is not None:
        lines.append(f"Total Tokens:           {report.total_tokens:,}")
    if report.estimated_cost_usd is not None:
        lines.append(f"Estimated Cost:        ${report.estimated_cost_usd:.6f} USD")

    lines.extend([
        "-" * 64,
        "  CATEGORY BREAKDOWN",
        "-" * 64,
        f"{'Category':<15} {'Cases':<8} {'Passed':<8} {'Pass %':<8} {'Routing':<8} {'Factuality':<10}",
    ])


    for cat_name, metrics in report.categories.items():
        lines.append(
            f"{cat_name:<15} {metrics.total:<8} {metrics.passed:<8} "
            f"{metrics.pass_rate * 100:5.1f}%  {metrics.routing_accuracy * 100:5.1f}%   "
            f"{metrics.factual_accuracy * 100:5.1f}%"
        )

    if report.failures:
        lines.extend([
            "-" * 64,
            "  FAILURES & REGRESSIONS",
            "-" * 64,
        ])
        for fail in report.failures:
            lines.append(f"[{fail['case_id']}] ({fail['category']}) Query: {fail['query'][:50]}...")
            for r in fail["failure_reasons"]:
                lines.append(f"  -> {r}")

    lines.append("=" * 64)
    return "\n".join(lines)


def main():
    """Main CLI entrypoint for python -m evals.runner."""
    parser = argparse.ArgumentParser(description="Arbiter Multi-Agent LLM Evaluation Runner")
    parser.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="Evaluation mode: 'mock' (deterministic offline) or 'live' (real Gemini backend)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to benchmark JSON dataset",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter evaluation to a specific category (e.g. book, market, compliance)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between requests (recommended 12.0 for live Gemini free tier)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit evaluation to first N test cases",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evals/reports/latest.json",
        help="Path to save output JSON benchmark report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON report to stdout instead of terminal table",
    )

    args = parser.parse_args()

    # If live mode requested with default 0 delay, set reasonable live pacing
    delay = args.delay
    if args.mode == "live" and delay == 0.0:
        delay = 12.0

    runner = EvaluationRunner(
        mode=args.mode,
        dataset_path=args.dataset,
        delay_seconds=delay,
    )

    report = runner.run(category=args.category, limit=args.limit)

    # Save JSON report
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(render_terminal_report(report))
        if args.output:
            print(f"\nSaved benchmark JSON report to: {args.output}")


if __name__ == "__main__":
    main()
