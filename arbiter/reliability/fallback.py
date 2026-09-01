"""
arbiter/reliability/fallback.py
-------------------------------
Deterministic safe fallback envelope builder for upstream LLM failures,
circuit breaker trips, and retry exhaustion.
"""

from __future__ import annotations

from typing import Any, List


def build_reliability_fallback(
    question_id: str,
    client_id: str | None = None,
    agents: List[str] | None = None,
    reason: str = "Upstream LLM gateway failure. Request safely abstained.",
    citations: List[str] | None = None,
    flags: List[str] | None = None,
) -> dict[str, Any]:
    """Construct a contract-compliant, schema-valid abstention envelope under failure."""
    agent_path = list(agents) if agents else ["router"]
    if "router" not in agent_path:
        agent_path = ["router"] + agent_path

    citation_list = list(citations) if citations else ([client_id] if client_id else [])

    return {
        "question_id": question_id,
        "answer": "",
        "answer_value": None,
        "abstained": True,
        "refused": False,
        "reason": reason,
        "citations": citation_list,
        "confidence": 0.0,
        "flags": list(flags) if flags is not None else ["upstream_issue"],
        "agents": agent_path,
    }
