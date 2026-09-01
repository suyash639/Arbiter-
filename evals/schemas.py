"""
evals/schemas.py
----------------
Typed schema definitions for benchmark cases, individual evaluation results,
latency statistics, and aggregate evaluation reports.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class BenchmarkCase(BaseModel):
    """Definition of a single benchmark test case."""

    id: str
    category: Literal["book", "kyc", "notes", "market", "compliance", "security", "edge_case"]
    query: str
    client_id: str
    expected_agent: str
    expected_behavior: Literal["answer", "refuse", "abstain"] = "answer"
    expected_value: Any = None
    expected_citations: list[str] = Field(default_factory=list)
    forbidden_citations: list[str] = Field(default_factory=list)
    citation_match_mode: Literal["exact", "subset", "empty"] = "subset"
    numeric_tolerance: float = 0.01
    description: str = ""


class CaseEvaluationResult(BaseModel):
    """Evaluation result for a single benchmark test case."""

    case_id: str
    category: str
    expected_agent: str
    actual_agents: list[str] = Field(default_factory=list)
    routing_pass: bool = False
    schema_pass: bool = False
    factual_pass: bool = False
    citation_pass: bool = False
    safety_pass: bool = False
    overall_pass: bool = False
    status: Literal["PASS", "FAIL", "ABSTAINED", "REFUSED", "UPSTREAM_ERROR", "EVALUATION_ERROR"] = "PASS"
    failure_reasons: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    actual_value: Any = None
    actual_citations: list[str] = Field(default_factory=list)
    raw_answer: str | None = None


class LatencyStats(BaseModel):
    """Statistical summary of execution latencies."""

    avg_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    slowest_cases: list[dict[str, Any]] = Field(default_factory=list)


class CategoryMetrics(BaseModel):
    """Aggregate evaluation metrics for a single benchmark category."""

    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    routing_accuracy: float = 0.0
    factual_accuracy: float = 0.0
    citation_accuracy: float = 0.0
    safety_accuracy: float = 0.0
    schema_pass_rate: float = 0.0


class AggregateReport(BaseModel):
    """Full aggregate benchmark evaluation report."""

    timestamp: str
    dataset: str = "benchmark.json"
    mode: str = "mock"
    provider: str = "gemini"
    model: str = "gemini-3.6-flash"
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    overall_pass_rate: float = 0.0
    routing_accuracy: float = 0.0
    factual_accuracy: float = 0.0
    citation_accuracy: float = 0.0
    safety_accuracy: float = 0.0
    schema_pass_rate: float = 0.0
    latency: LatencyStats = Field(default_factory=LatencyStats)
    total_tokens: int | None = Field(default=None, description="Total LLM tokens consumed across evaluation run.")
    estimated_cost_usd: float | None = Field(default=None, description="Total estimated LLM cost in USD.")
    total_tool_calls: int = Field(default=0, description="Total deterministic tool calls executed.")
    tool_success_rate: float = Field(default=1.0, description="Fraction of tool calls that succeeded.")
    categories: dict[str, CategoryMetrics] = Field(default_factory=dict)
    case_results: list[CaseEvaluationResult] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)

