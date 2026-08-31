"""
evals package
-------------
Automated benchmarking and evaluation framework for Arbiter.
"""

from evals.schemas import (
    BenchmarkCase,
    CaseEvaluationResult,
    LatencyStats,
    AggregateReport,
)

__all__ = [
    "BenchmarkCase",
    "CaseEvaluationResult",
    "LatencyStats",
    "AggregateReport",
]
