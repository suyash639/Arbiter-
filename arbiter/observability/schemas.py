"""
arbiter/observability/schemas.py
--------------------------------
Pydantic data models for Arbiter observability, request tracing, and telemetry.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RequestMetadata(BaseModel):
    """Metadata identifying an individual orchestrator request."""

    request_id: str = Field(description="Unique request correlation ID (e.g. req_abc123).")
    timestamp: str = Field(description="ISO 8601 UTC timestamp when request started.")
    question_id: str = Field(description="Identifier of the question being asked.")
    client_id: str = Field(description="Authorized client scope.")
    provider: str = Field(default="gemini", description="LLM provider name.")
    model: str = Field(default="gemini-3.6-flash", description="Active model ID.")


class LLMCallTrace(BaseModel):
    """Telemetry record for an individual LLM invocation."""

    provider: str = Field(description="Provider name (e.g. gemini, openai, valura).")
    model: str = Field(description="Model identifier.")
    latency_ms: float = Field(default=0.0, description="Execution latency in milliseconds.")
    input_tokens: int | None = Field(default=None, description="Input/prompt token count.")
    output_tokens: int | None = Field(default=None, description="Output/completion token count.")
    total_tokens: int | None = Field(default=None, description="Total tokens consumed.")
    estimated_cost_usd: float | None = Field(default=None, description="Estimated LLM cost in USD.")
    success: bool = Field(default=True, description="Whether LLM invocation succeeded.")
    error_category: str | None = Field(default=None, description="Categorized error type if failed.")


class ToolCallTrace(BaseModel):
    """Telemetry record for a deterministic tool invocation."""

    tool_name: str = Field(description="Name of the invoked tool.")
    agent: str = Field(description="Specialist agent that executed the tool.")
    start_time: str = Field(description="ISO 8601 start timestamp.")
    end_time: str = Field(description="ISO 8601 completion timestamp.")
    latency_ms: float = Field(default=0.0, description="Tool execution latency in milliseconds.")
    success: bool = Field(default=True, description="Whether tool execution succeeded.")
    sanitized_args: dict[str, Any] = Field(default_factory=dict, description="Redacted input parameters.")
    sanitized_result_summary: Any = Field(default=None, description="Sanitized result metadata or string summary.")
    error_category: str | None = Field(default=None, description="Error classification if failed.")


class RouterTrace(BaseModel):
    """Telemetry record for the request router classification stage."""

    selected_specialist: str = Field(description="Specialist agent selected by router.")
    agent_path: list[str] = Field(default_factory=list, description="Cumulative agent route path.")
    latency_ms: float = Field(default=0.0, description="Router execution latency in milliseconds.")
    llm_call: LLMCallTrace | None = Field(default=None, description="Telemetry of router LLM call if invoked.")


class SpecialistTrace(BaseModel):
    """Telemetry record for the specialist agent execution stage."""

    agent_name: str = Field(description="Name of specialist agent handling query.")
    latency_ms: float = Field(default=0.0, description="Specialist execution latency in milliseconds.")
    llm_call: LLMCallTrace | None = Field(default=None, description="Telemetry of specialist LLM call.")
    tool_calls: list[ToolCallTrace] = Field(default_factory=list, description="Tool invocations executed.")


class ValidationTrace(BaseModel):
    """Telemetry record for response schema and citation validation."""

    schema_valid: bool = Field(default=True, description="Whether envelope conforms to AnswerSchema.")
    citation_count: int = Field(default=0, description="Number of citations produced.")
    citations: list[str] = Field(default_factory=list, description="Citation IDs cited.")
    validation_errors: list[str] = Field(default_factory=list, description="List of contract violations if any.")


class RequestTrace(BaseModel):
    """Complete root trace representing an end-to-end request lifecycle."""

    metadata: RequestMetadata
    router: RouterTrace | None = None
    specialist: SpecialistTrace | None = None
    validation: ValidationTrace | None = None
    status: str = Field(default="success", description="Final status: 'success' | 'refused' | 'abstained' | 'error'.")
    confidence: float = Field(default=1.0, description="Final answer confidence score.")
    total_latency_ms: float = Field(default=0.0, description="Total end-to-end latency in milliseconds.")
    total_tokens: int | None = Field(default=None, description="Sum of tokens across all LLM calls.")
    total_cost_usd: float | None = Field(default=None, description="Sum of estimated costs in USD.")
    error_message: str | None = Field(default=None, description="Error message if request failed.")


class AggregateMetrics(BaseModel):
    """Aggregated operational metrics across collected request traces."""

    total_requests: int = 0
    successful_requests: int = 0
    refused_requests: int = 0
    abstained_requests: int = 0
    error_requests: int = 0

    # Latencies
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Token & Cost
    total_tokens: int = 0
    avg_tokens_per_request: float = 0.0
    total_estimated_cost_usd: float = 0.0
    avg_cost_per_request: float = 0.0

    # Tool execution
    total_tool_calls: int = 0
    tool_success_rate: float = 1.0

    # Reliability & Resilience
    total_retries: int = 0
    retry_rate: float = 0.0
    timeout_count: int = 0
    upstream_failures: int = 0
    circuit_breaker_trips: int = 0
    avg_attempts_per_request: float = 1.0

    # Categorical distributions
    requests_per_agent: dict[str, int] = Field(default_factory=dict)
    latency_per_agent: dict[str, float] = Field(default_factory=dict)
    requests_per_model: dict[str, int] = Field(default_factory=dict)
    tokens_per_model: dict[str, int] = Field(default_factory=dict)

