"""
evals/evaluators/routing.py
---------------------------
Evaluator for measuring multi-agent routing and specialist selection accuracy.
"""

from __future__ import annotations

from typing import Any
from evals.schemas import BenchmarkCase


def evaluate_routing(case: BenchmarkCase, response: dict[str, Any]) -> tuple[bool, str | None]:
    """Verify that the orchestrator routed the query to the expected specialist agent.

    Rules:
    1. `agents` must be a list containing at least ['router'].
    2. The selected agent (either the last agent or specialist) must match `case.expected_agent`.
       - If expected_agent is 'router' (e.g. preflight rejection), `agents` can be ['router'].
       - If expected_agent is a specialist (e.g. 'book_qa'), `agents` must end with or contain that specialist.
    """
    agents = response.get("agents")
    if not isinstance(agents, list) or len(agents) == 0:
        return False, f"Missing or invalid 'agents' path in response: {agents}"

    if agents[0] != "router":
        return False, f"First agent in routing path must be 'router', got: {agents[0]}"

    if case.expected_agent == "router":
        if agents == ["router"]:
            return True, None
        return False, f"Expected preflight router handling, but routed to: {agents}"

    # For specialist routing: check that expected specialist is in the agents path (normally the last element)
    selected_specialist = agents[-1]
    if selected_specialist != case.expected_agent:
        return False, f"Routing mismatch: expected '{case.expected_agent}', got '{selected_specialist}' in path {agents}"

    return True, None
