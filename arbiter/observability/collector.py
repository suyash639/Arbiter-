"""
arbiter/observability/collector.py
----------------------------------
In-memory and file-based trace collection and persistence interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import OrderedDict

from arbiter.observability.schemas import RequestTrace


class TraceCollector:
    """Collects, indexes, and optionally persists RequestTrace records."""

    def __init__(
        self,
        max_traces: int = 1000,
        sink_path: Path | str | None = None,
    ) -> None:
        self.max_traces = max_traces
        self.sink_path = Path(sink_path) if sink_path else None
        self._traces: OrderedDict[str, RequestTrace] = OrderedDict()

    def add_trace(self, trace: RequestTrace) -> None:
        """Store a completed RequestTrace in memory and optional file sink."""
        req_id = trace.metadata.request_id

        # Enforce max buffer size (FIFO)
        if len(self._traces) >= self.max_traces and req_id not in self._traces:
            self._traces.popitem(last=False)

        self._traces[req_id] = trace

        # Write to JSONL file sink if configured
        if self.sink_path:
            try:
                self.sink_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.sink_path, "a", encoding="utf-8") as f:
                    f.write(trace.model_dump_json() + "\n")
            except Exception:
                pass

    def get_trace(self, request_id: str) -> Optional[RequestTrace]:
        """Retrieve a specific trace by request_id."""
        return self._traces.get(request_id)

    def get_all_traces(self) -> List[RequestTrace]:
        """Retrieve all currently stored traces."""
        return list(self._traces.values())

    def clear(self) -> None:
        """Clear all stored in-memory traces."""
        self._traces.clear()
