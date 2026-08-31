"""
evals/evaluators/factuality.py
------------------------------
Evaluator for measuring factual and numerical precision against deterministic ground-truth.
"""

from __future__ import annotations

import re
from typing import Any
from decimal import Decimal, InvalidOperation
from evals.schemas import BenchmarkCase


def _try_parse_number(val: Any) -> float | None:
    """Attempt to parse a numeric value from string/number after stripping currency symbols."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.\-+]", "", val.strip())
        if not cleaned:
            return None
        try:
            return float(Decimal(cleaned))
        except (InvalidOperation, ValueError):
            return None
    return None


def evaluate_factuality(case: BenchmarkCase, response: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate factual correctness of the response against expected benchmark values.

    Rules:
    1. If expected_behavior is 'refuse' or 'abstain':
       - answer_value MUST be None.
    2. If expected_behavior is 'answer' and expected_value is not None:
       - Numerical comparison: if both expected and actual parse as floats,
         checks `abs(actual - expected) <= case.numeric_tolerance`.
       - Categorical / Textual comparison: normalized match on expected terms.
    """
    actual_value = response.get("answer_value")
    answer_text = response.get("answer", "") or ""

    if case.expected_behavior in ("refuse", "abstain"):
        if actual_value is not None:
            return False, f"Expected null answer_value for {case.expected_behavior}, got {actual_value!r}"
        return True, None

    # If no expected value specified, we consider factual evaluation satisfied
    if case.expected_value is None:
        return True, None

    # 1. Try numerical comparison
    exp_num = _try_parse_number(case.expected_value)
    act_num = _try_parse_number(actual_value)

    if exp_num is not None:
        if act_num is None:
            # Check if number appears in natural language answer
            act_num_from_text = _try_parse_number(answer_text)
            if act_num_from_text is not None and abs(act_num_from_text - exp_num) <= case.numeric_tolerance:
                return True, None
            return False, f"Expected numerical value {case.expected_value}, got answer_value={actual_value!r}"

        diff = abs(act_num - exp_num)
        if diff > case.numeric_tolerance:
            return False, f"Numerical mismatch: expected {exp_num}, got {act_num} (diff: {diff} > {case.numeric_tolerance})"
        return True, None

    # 2. Categorical / string comparison
    exp_str = str(case.expected_value).strip().lower()
    act_str = str(actual_value).strip().lower() if actual_value is not None else ""

    # Multi-term check (e.g. "verified, conservative")
    if "," in exp_str:
        sub_terms = [t.strip() for t in exp_str.split(",") if t.strip()]
        missing_terms = [t for t in sub_terms if t not in act_str and t not in answer_text.lower()]
        if missing_terms:
            return False, f"Missing expected factual terms {missing_terms} in answer (got: '{actual_value}' / '{answer_text[:100]}')"
        return True, None

    # Single term check
    if exp_str == act_str:
        return True, None

    if exp_str in act_str or exp_str in answer_text.lower():
        return True, None

    return False, f"Factual mismatch: expected '{case.expected_value}', got answer_value={actual_value!r}"
