"""
arbiter/observability/metrics.py
--------------------------------
Metrics aggregation and percentile calculation across request traces.
"""

from __future__ import annotations

import statistics
from typing import List
from arbiter.observability.schemas import AggregateMetrics, RequestTrace


def _calculate_percentile(sorted_data: list[float], percentile: float) -> float:
    """Calculate percentile value from sorted numeric array."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[f]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return round(d0 + d1, 2)


def compute_aggregate_metrics(traces: List[RequestTrace]) -> AggregateMetrics:
    """Compute aggregate operational telemetry across a list of request traces."""
    if not traces:
        return AggregateMetrics()

    total_requests = len(traces)
    successful = sum(1 for t in traces if t.status == "success")
    refused = sum(1 for t in traces if t.status == "refused")
    abstained = sum(1 for t in traces if t.status == "abstained")
    errors = sum(1 for t in traces if t.status == "error")

    # Latencies
    latencies = sorted([t.total_latency_ms for t in traces])
    avg_lat = statistics.mean(latencies) if latencies else 0.0
    p50_lat = _calculate_percentile(latencies, 50.0)
    p95_lat = _calculate_percentile(latencies, 95.0)
    p99_lat = _calculate_percentile(latencies, 99.0)
    min_lat = min(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    # Tokens
    tokens_list = [t.total_tokens for t in traces if t.total_tokens is not None]
    total_tokens = sum(tokens_list)
    avg_tokens = (total_tokens / len(tokens_list)) if tokens_list else 0.0

    # Costs
    costs_list = [t.total_cost_usd for t in traces if t.total_cost_usd is not None]
    total_cost = sum(costs_list)
    avg_cost = (total_cost / len(costs_list)) if costs_list else 0.0

    # Tool calls
    all_tool_calls = []
    for t in traces:
        if t.specialist and t.specialist.tool_calls:
            all_tool_calls.extend(t.specialist.tool_calls)

    total_tool_calls = len(all_tool_calls)
    successful_tool_calls = sum(1 for tc in all_tool_calls if tc.success)
    tool_success_rate = (successful_tool_calls / total_tool_calls) if total_tool_calls else 1.0

    # Per agent breakdowns
    agent_counts: dict[str, int] = {}
    agent_latencies: dict[str, list[float]] = {}
    for t in traces:
        agent_name = t.specialist.agent_name if t.specialist else "router"
        agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
        agent_latencies.setdefault(agent_name, []).append(t.total_latency_ms)

    avg_agent_latencies = {
        k: round(statistics.mean(v), 2) for k, v in agent_latencies.items()
    }

    # Per model breakdowns
    model_counts: dict[str, int] = {}
    model_tokens: dict[str, int] = {}
    for t in traces:
        m = t.metadata.model
        model_counts[m] = model_counts.get(m, 0) + 1
        if t.total_tokens:
            model_tokens[m] = model_tokens.get(m, 0) + t.total_tokens

    # Reliability stats
    upstream_fails = errors
    for t in traces:
        if t.specialist and t.specialist.llm_call and not t.specialist.llm_call.success:
            upstream_fails += 1
        if t.router and t.router.llm_call and not t.router.llm_call.success:
            upstream_fails += 1

    return AggregateMetrics(
        total_requests=total_requests,
        successful_requests=successful,
        refused_requests=refused,
        abstained_requests=abstained,
        error_requests=errors,
        avg_latency_ms=round(avg_lat, 2),
        p50_latency_ms=round(p50_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        p99_latency_ms=round(p99_lat, 2),
        min_latency_ms=round(min_lat, 2),
        max_latency_ms=round(max_lat, 2),
        total_tokens=total_tokens,
        avg_tokens_per_request=round(avg_tokens, 2),
        total_estimated_cost_usd=round(total_cost, 6),
        avg_cost_per_request=round(avg_cost, 6),
        total_tool_calls=total_tool_calls,
        tool_success_rate=round(tool_success_rate, 4),
        total_retries=0,
        retry_rate=0.0,
        timeout_count=0,
        upstream_failures=upstream_fails,
        circuit_breaker_trips=0,
        avg_attempts_per_request=1.0,
        requests_per_agent=agent_counts,
        latency_per_agent=avg_agent_latencies,
        requests_per_model=model_counts,
        tokens_per_model=model_tokens,
    )

