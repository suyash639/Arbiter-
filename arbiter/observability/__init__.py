"""
arbiter/observability/__init__.py
---------------------------------
Arbiter Observability & Tracing Subsystem.
"""

from __future__ import annotations

from arbiter.observability.collector import TraceCollector
from arbiter.observability.context import (
    generate_request_id,
    get_current_request_id,
    set_current_request_id,
    reset_current_request_id,
)
from arbiter.observability.logger import StructuredLogger, get_logger
from arbiter.observability.manager import (
    ObservabilityManager,
    get_observability_manager,
)
from arbiter.observability.metrics import compute_aggregate_metrics
from arbiter.observability.pricing import ModelPricing, ModelPricingRegistry
from arbiter.observability.redaction import RedactionEngine
from arbiter.observability.schemas import (
    AggregateMetrics,
    LLMCallTrace,
    RequestMetadata,
    RequestTrace,
    RouterTrace,
    SpecialistTrace,
    ToolCallTrace,
    ValidationTrace,
)

__all__ = [
    "ObservabilityManager",
    "get_observability_manager",
    "TraceCollector",
    "ModelPricingRegistry",
    "ModelPricing",
    "RedactionEngine",
    "StructuredLogger",
    "get_logger",
    "compute_aggregate_metrics",
    "generate_request_id",
    "get_current_request_id",
    "set_current_request_id",
    "reset_current_request_id",
    "RequestMetadata",
    "LLMCallTrace",
    "ToolCallTrace",
    "RouterTrace",

    "SpecialistTrace",
    "ValidationTrace",
    "RequestTrace",
    "AggregateMetrics",
]
