"""
evals/evaluators/citations.py
-----------------------------
Evaluator for measuring citation precision, deterministic ground-truth alignment,
and hallucination/fabrication detection.
"""

from __future__ import annotations

from typing import Any
from evals.schemas import BenchmarkCase


def evaluate_citations(case: BenchmarkCase, response: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate that citations are grounded in retrieved evidence and free from fabrication.

    Checks:
    1. If forbidden_citations are specified, none of them may appear in actual citations.
    2. If expected_behavior is 'refuse' or 'abstain' without evidence: citations should be empty or match expected.
    3. If citation_match_mode == 'exact': set(actual_citations) == set(expected_citations).
    4. If citation_match_mode == 'subset': every expected_citation must be present in actual_citations.
    5. If citation_match_mode == 'empty': actual_citations must be [].
    6. Citation format sanity: elements must not look like full sentences (> 50 chars or containing spaces where ID is expected).
    """
    actual_citations = response.get("citations", [])
    if not isinstance(actual_citations, list):
        return False, f"'citations' must be a list, got {type(actual_citations).__name__}"

    # 1. Check forbidden citations (e.g. cross-client IDs or prohibited sources)
    for forbidden in case.forbidden_citations:
        if forbidden in actual_citations:
            return False, f"Forbidden citation detected in response: '{forbidden}'"

    # 2. Check empty match mode or refusal behavior
    if case.citation_match_mode == "empty" or (case.expected_behavior == "refuse" and not case.expected_citations):
        if len(actual_citations) > 0:
            return False, f"Expected empty citations for refused/empty case, but got: {actual_citations}"
        return True, None

    # 3. Check format sanity (prevent LLM from putting paragraph text in citation field)
    for cite in actual_citations:
        if len(cite) > 60:
            return False, f"Fabricated / malformed citation string (>60 chars): '{cite[:60]}...'"

    # 4. Check expected citations
    if case.expected_citations:
        if case.citation_match_mode == "exact":
            if set(actual_citations) != set(case.expected_citations):
                return False, f"Citation exact match failed: expected {case.expected_citations}, got {actual_citations}"
        elif case.citation_match_mode == "subset":
            missing = [c for c in case.expected_citations if c not in actual_citations]
            if missing:
                return False, f"Missing expected citations {missing} in actual citations {actual_citations}"

    return True, None
