"""
arbiter/observability/manager.py
--------------------------------
Central manager coordinating request lifecycle tracing, telemetry recording,
and metrics aggregation.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from arbiter.observability.collector import TraceCollector
from arbiter.observability.context import (
    generate_request_id,
    get_current_request_id,
    set_current_request_id,
)
from arbiter.observability.logger import StructuredLogger, get_logger
from arbiter.observability.metrics import compute_aggregate_metrics
from arbiter.observability.pricing import ModelPricingRegistry
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


class ObservabilityManager:
    """Manages end-to-end request tracing, tool metrics, LLM telemetry, and log events."""

    def __init__(
        self,
        collector: TraceCollector | None = None,
        pricing: ModelPricingRegistry | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.collector = collector or TraceCollector()
        self.pricing = pricing or ModelPricingRegistry()
        self.logger = logger or get_logger("arbiter.observability")
        self._in_flight: Dict[str, Dict[str, Any]] = {}

    def start_request(
        self,
        question_id: str,
        client_id: str,
        prompt: str,
        provider: str = "gemini",
        model: str = "gemini-3.6-flash",
        request_id: str | None = None,
    ) -> str:
        """Initialize a new request trace and bind request_id to the context."""
        rid = request_id or generate_request_id()
        set_current_request_id(rid)

        t_start_utc = datetime.now(timezone.utc).isoformat()
        t_perf = time.perf_counter()

        metadata = RequestMetadata(
            request_id=rid,
            timestamp=t_start_utc,
            question_id=question_id,
            client_id=client_id,
            provider=provider,
            model=model,
        )

        self._in_flight[rid] = {
            "metadata": metadata,
            "t_perf_start": t_perf,
            "router": None,
            "specialist": None,
            "tool_calls": [],
            "validation": None,
            "prompt_length": len(prompt),
        }

        self.logger.info(
            "request_started",
            request_id=rid,
            question_id=question_id,
            client_id=client_id,
            provider=provider,
            model=model,
            prompt_length=len(prompt),
        )

        return rid

    def record_router(
        self,
        request_id: str | None,
        selected_specialist: str,
        agent_path: list[str],
        latency_ms: float,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        success: bool = True,
        error_category: str | None = None,
    ) -> None:
        """Record the routing decision and router LLM execution metrics."""
        rid = request_id or get_current_request_id()
        if not rid or rid not in self._in_flight:
            return

        llm_trace = None
        if llm_model:
            tot_tokens = (input_tokens + output_tokens) if (input_tokens is not None and output_tokens is not None) else None
            cost = self.pricing.calculate_cost(llm_model, input_tokens, output_tokens)
            llm_trace = LLMCallTrace(
                provider=llm_provider or self._in_flight[rid]["metadata"].provider,
                model=llm_model,
                latency_ms=round(latency_ms, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=tot_tokens,
                estimated_cost_usd=cost,
                success=success,
                error_category=error_category,
            )

        router_trace = RouterTrace(
            selected_specialist=selected_specialist,
            agent_path=agent_path,
            latency_ms=round(latency_ms, 2),
            llm_call=llm_trace,
        )

        self._in_flight[rid]["router"] = router_trace
        self.logger.info(
            "route_selected",
            request_id=rid,
            selected_specialist=selected_specialist,
            agent_path=agent_path,
            latency_ms=round(latency_ms, 2),
        )

    def record_tool_call(
        self,
        request_id: str | None,
        tool_name: str,
        agent: str,
        start_time: str,
        end_time: str,
        latency_ms: float,
        success: bool = True,
        args: dict[str, Any] | None = None,
        result_summary: Any = None,
        error_category: str | None = None,
    ) -> None:
        """Record an individual deterministic tool call invocation."""
        rid = request_id or get_current_request_id()
        if not rid or rid not in self._in_flight:
            return

        sanitized_args = RedactionEngine.sanitize_tool_args(args or {})
        sanitized_res = RedactionEngine.sanitize_tool_result(result_summary)

        trace = ToolCallTrace(
            tool_name=tool_name,
            agent=agent,
            start_time=start_time,
            end_time=end_time,
            latency_ms=round(latency_ms, 2),
            success=success,
            sanitized_args=sanitized_args,
            sanitized_result_summary=sanitized_res,
            error_category=error_category,
        )

        self._in_flight[rid]["tool_calls"].append(trace)

        if success:
            self.logger.debug(
                "tool_executed",
                request_id=rid,
                tool_name=tool_name,
                agent=agent,
                latency_ms=round(latency_ms, 2),
            )
        else:
            self.logger.warning(
                "tool_failed",
                request_id=rid,
                tool_name=tool_name,
                agent=agent,
                error_category=error_category,
                latency_ms=round(latency_ms, 2),
            )

    def record_specialist_llm(
        self,
        request_id: str | None,
        agent: str,
        provider: str,
        model: str,
        latency_ms: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        success: bool = True,
        error_category: str | None = None,
    ) -> None:
        """Record the specialist agent's LLM reasoning call."""
        rid = request_id or get_current_request_id()
        if not rid or rid not in self._in_flight:
            return

        tot_tokens = total_tokens
        if tot_tokens is None and input_tokens is not None and output_tokens is not None:
            tot_tokens = input_tokens + output_tokens

        cost = self.pricing.calculate_cost(model, input_tokens, output_tokens)

        llm_trace = LLMCallTrace(
            provider=provider,
            model=model,
            latency_ms=round(latency_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=tot_tokens,
            estimated_cost_usd=cost,
            success=success,
            error_category=error_category,
        )

        self._in_flight[rid]["specialist_llm"] = llm_trace

        self.logger.info(
            "llm_invoked",
            request_id=rid,
            agent=agent,
            model=model,
            latency_ms=round(latency_ms, 2),
            tokens=tot_tokens,
            cost_usd=cost,
        )

    def record_validation(
        self,
        request_id: str | None,
        schema_valid: bool,
        citation_count: int,
        citations: list[str],
        validation_errors: list[str] | None = None,
    ) -> None:
        """Record the response envelope and citation validation outcome."""
        rid = request_id or get_current_request_id()
        if not rid or rid not in self._in_flight:
            return

        val_trace = ValidationTrace(
            schema_valid=schema_valid,
            citation_count=citation_count,
            citations=citations,
            validation_errors=validation_errors or [],
        )
        self._in_flight[rid]["validation"] = val_trace

    def finish_request(
        self,
        request_id: str | None,
        response: dict[str, Any],
        error_message: str | None = None,
    ) -> RequestTrace:
        """Finalize request trace, compute overall latency, aggregate tokens/cost, and store trace."""
        rid = request_id or get_current_request_id()
        if not rid or rid not in self._in_flight:
            # Fallback if request was not formally initiated
            meta = RequestMetadata(
                request_id=rid or generate_request_id(),
                timestamp=datetime.now(timezone.utc).isoformat(),
                question_id=response.get("question_id", "unknown"),
                client_id="unknown",
            )
            fallback_trace = RequestTrace(
                metadata=meta,
                status="success" if not response.get("refused") and not response.get("abstained") else ("refused" if response.get("refused") else "abstained"),
                confidence=response.get("confidence", 1.0),
                total_latency_ms=0.0,
            )
            self.collector.add_trace(fallback_trace)
            return fallback_trace

        data = self._in_flight.pop(rid)
        total_latency_ms = (time.perf_counter() - data["t_perf_start"]) * 1000.0

        # Classify final status
        if error_message or "upstream_issue" in response.get("flags", []):
            status = "error"
        elif response.get("refused"):
            status = "refused"
        elif response.get("abstained"):
            status = "abstained"
        else:
            status = "success"

        # Build SpecialistTrace
        agent_name = (
            data["router"].selected_specialist
            if data.get("router")
            else (response.get("agents", ["router"])[-1] if response.get("agents") else "router")
        )

        specialist_trace = SpecialistTrace(
            agent_name=agent_name,
            latency_ms=round(total_latency_ms - (data["router"].latency_ms if data.get("router") else 0.0), 2),
            llm_call=data.get("specialist_llm"),
            tool_calls=data.get("tool_calls", []),
        )

        # Aggregate total tokens and cost
        tokens_sum: int | None = None
        cost_sum: float | None = None

        all_llm_calls = []
        if data.get("router") and data["router"].llm_call:
            all_llm_calls.append(data["router"].llm_call)
        if data.get("specialist_llm"):
            all_llm_calls.append(data["specialist_llm"])

        for call in all_llm_calls:
            if call.total_tokens is not None:
                tokens_sum = (tokens_sum or 0) + call.total_tokens
            if call.estimated_cost_usd is not None:
                cost_sum = round((cost_sum or 0.0) + call.estimated_cost_usd, 6)

        # Create validation trace if not recorded
        val_trace = data.get("validation")
        if val_trace is None:
            cites = response.get("citations", [])
            val_trace = ValidationTrace(
                schema_valid=True,
                citation_count=len(cites),
                citations=cites,
            )

        root_trace = RequestTrace(
            metadata=data["metadata"],
            router=data.get("router"),
            specialist=specialist_trace,
            validation=val_trace,
            status=status,
            confidence=response.get("confidence", 1.0),
            total_latency_ms=round(total_latency_ms, 2),
            total_tokens=tokens_sum,
            total_cost_usd=cost_sum,
            error_message=error_message or (response.get("reason") if status == "error" else None),
        )

        self.collector.add_trace(root_trace)

        self.logger.info(
            "request_finished",
            request_id=rid,
            status=status,
            latency_ms=root_trace.total_latency_ms,
            tokens=tokens_sum,
            cost_usd=cost_sum,
            tool_count=len(specialist_trace.tool_calls),
            citations=val_trace.citation_count,
        )

        return root_trace

    def get_trace(self, request_id: str) -> Optional[RequestTrace]:
        """Retrieve a stored trace by request_id."""
        return self.collector.get_trace(request_id)

    def get_all_traces(self) -> list[RequestTrace]:
        """Retrieve all collected traces."""
        return self.collector.get_all_traces()

    def get_metrics(self) -> AggregateMetrics:
        """Compute aggregate telemetry across all stored traces."""
        return compute_aggregate_metrics(self.collector.get_all_traces())

    def reset(self) -> None:
        """Clear all in-memory traces and reset in-flight state."""
        self.collector.clear()
        self._in_flight.clear()


# Global default manager singleton
_GLOBAL_OBSERVABILITY_MANAGER: ObservabilityManager | None = None


def get_observability_manager() -> ObservabilityManager:
    """Obtain or initialize the global ObservabilityManager singleton."""
    global _GLOBAL_OBSERVABILITY_MANAGER
    if _GLOBAL_OBSERVABILITY_MANAGER is None:
        _GLOBAL_OBSERVABILITY_MANAGER = ObservabilityManager()
    return _GLOBAL_OBSERVABILITY_MANAGER
