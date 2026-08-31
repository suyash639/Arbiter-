"""
evals/evaluators/schema.py
--------------------------
Evaluator for measuring response schema compliance and AnswerSchema invariants.
"""

from __future__ import annotations

from typing import Any
from evals.schemas import BenchmarkCase

REQUIRED_FIELDS = [
    "question_id",
    "answer",
    "answer_value",
    "abstained",
    "refused",
    "reason",
    "citations",
    "confidence",
]


def evaluate_schema(case: BenchmarkCase, response: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate that the response satisfies all AnswerSchema requirements and invariants.

    Checks:
    1. All 8 required fields exist.
    2. Data types match contract (boolean flags, string/null reason, list citations, float confidence).
    3. If abstained or refused is True:
       - answer_value MUST be null / None
       - reason MUST be a non-empty string
    4. Confidence is between 0.0 and 1.0 inclusive.
    5. Citations is a list of strings.
    6. question_id matches the query.
    """
    for field in REQUIRED_FIELDS:
        if field not in response:
            return False, f"Missing required schema field: '{field}'"

    # Type validation
    if not isinstance(response.get("abstained"), bool):
        return False, f"'abstained' must be a boolean, got {type(response.get('abstained')).__name__}"

    if not isinstance(response.get("refused"), bool):
        return False, f"'refused' must be a boolean, got {type(response.get('refused')).__name__}"

    citations = response.get("citations")
    if not isinstance(citations, list) or not all(isinstance(c, str) for c in citations):
        return False, f"'citations' must be a list of strings, got {citations}"

    confidence = response.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return False, f"'confidence' must be a number between 0.0 and 1.0, got {confidence}"

    # Semantic invariants
    is_abstained = response.get("abstained")
    is_refused = response.get("refused")
    answer_value = response.get("answer_value")
    reason = response.get("reason")

    if is_abstained or is_refused:
        if answer_value is not None:
            return False, f"Contract violation: 'answer_value' must be null when abstained or refused is True (got {answer_value!r})"
        if not reason or not isinstance(reason, str) or not reason.strip():
            return False, "Contract violation: 'reason' must be a non-empty string when abstained or refused is True"

    return True, None
