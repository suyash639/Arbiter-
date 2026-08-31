"""
evals/datasets/loader.py
------------------------
Utility functions to load and validate benchmark datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from evals.schemas import BenchmarkCase


def load_benchmark(path: Path | str | None = None) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSON file.

    If path is None, defaults to `evals/datasets/benchmark.json` relative to project root.
    Raises ValueError if duplicate case IDs or invalid structures are detected.
    """
    if path is None:
        path = Path(__file__).parent / "benchmark.json"
    else:
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Benchmark root must be a JSON array of test cases, got {type(data).__name__}")

    cases: list[BenchmarkCase] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} must be a dictionary")
        case = BenchmarkCase.model_validate(item)
        if case.id in seen_ids:
            raise ValueError(f"Duplicate benchmark case ID found: '{case.id}'")
        seen_ids.add(case.id)
        cases.append(case)

    return cases
