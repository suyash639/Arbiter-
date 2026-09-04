"""
arbiter/tool_verification/verifier.py
-------------------------------------
Core Tool Verification Engine enforcing authorization, argument validation,
client-scope isolation, result validation, and audit telemetry.
"""

from __future__ import annotations

import datetime
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from pydantic import ValidationError

from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.observability.redaction import RedactionEngine
from arbiter.tool_verification.errors import (
    MissingClientScopeError,
    ToolArgumentValidationError,
    ToolExecutionError,
    ToolResultValidationError,
    ToolScopeViolationError,
    UnauthorizedToolError,
    UnknownClientScopeError,
    UnknownToolError,
)
from arbiter.tool_verification.registry import TOOL_REGISTRY, get_tool_definition
from arbiter.tool_verification.schemas import ToolDefinition, VerificationAuditRecord

T = TypeVar("T")


class ToolVerifier:
    """Production-grade tool verification boundary separating untrusted LLM requests

    from deterministic business logic.
    """

    def __init__(
        self,
        store: Optional[DataStore] = None,
        observability: Optional[ObservabilityManager] = None,
    ) -> None:
        self.store = store
        self.obs = observability or get_observability_manager()

    def verify_and_execute(
        self,
        tool_func: Callable[..., Any],
        agent_name: str,
        tool_name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        trusted_client_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Any:
        """Execute a tool through the full authorization, argument, scope, and result verification pipeline."""
        t0 = time.perf_counter()
        start_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        kw = dict(kwargs) if kwargs is not None else {}
        
        # Combine args into kwargs if positional arguments provided
        if args and not kw:
            # Inspection for single argument functions (e.g. cid or symbol)
            import inspect
            sig = inspect.signature(tool_func)
            param_names = list(sig.parameters.keys())
            for idx, arg_val in enumerate(args):
                if idx < len(param_names):
                    kw[param_names[idx]] = arg_val

        sanitized_call_args = dict(kw)

        # -------------------------------------------------------------------
        # Step 1: Authorization Validation
        # -------------------------------------------------------------------
        defn = get_tool_definition(tool_name)
        if defn is None:
            err = UnknownToolError(tool_name)
            self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
            raise err

        if agent_name not in defn.owning_agents:
            err = UnauthorizedToolError(agent_name, tool_name)
            self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
            raise err

        # -------------------------------------------------------------------
        # Step 2: Client Scope Validation
        # -------------------------------------------------------------------
        if defn.requires_client_id:
            # Client scope is mandatory
            if not trusted_client_id or not trusted_client_id.strip():
                err = MissingClientScopeError(tool_name)
                self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
                raise err

            # Check client existence in store if available
            if self.store is not None:
                try:
                    self.store.client(trusted_client_id)
                except KeyError:
                    err = UnknownClientScopeError(trusted_client_id)
                    self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
                    raise err

            # Verify that any client_id passed in tool kwargs matches trusted scope
            provided_cid = kw.get("cid") or kw.get("client_id")
            if provided_cid is not None and str(provided_cid).strip() != trusted_client_id.strip():
                err = ToolScopeViolationError(
                    expected_client_id=trusted_client_id,
                    provided_client_id=str(provided_cid),
                )
                self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
                raise err

            # Force authoritative client_id into kwargs
            if "cid" in kw or "cid" in (defn.args_schema.model_fields if defn.args_schema else {}):
                kw["cid"] = trusted_client_id
            elif "client_id" in kw:
                kw["client_id"] = trusted_client_id

        # -------------------------------------------------------------------
        # Step 3: Argument Schema Validation
        # -------------------------------------------------------------------
        if defn.args_schema is not None:
            try:
                # Clean None values for optional parameters if passed as empty strings
                cleaned_kw = {}
                for k, v in kw.items():
                    if isinstance(v, str) and v == "" and k in ("start_date", "end_date", "as_of", "txn_type", "symbol", "account_id"):
                        cleaned_kw[k] = None
                    else:
                        cleaned_kw[k] = v

                validated_model = defn.args_schema.model_validate(cleaned_kw)
                # Use validated attributes
                kw = validated_model.model_dump(exclude_unset=False)
                # Remove None keys that the underlying function may not expect as None
                kw = {k: v for k, v in kw.items() if v is not None}
            except (ValidationError, ValueError) as exc:
                err = ToolArgumentValidationError(tool_name, str(exc))
                self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
                raise err

        # -------------------------------------------------------------------
        # Step 4: Tool Execution
        # -------------------------------------------------------------------
        try:
            result = tool_func(**kw)
        except Exception as exc:
            self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, exc)
            raise

        # -------------------------------------------------------------------
        # Step 5: Result Validation
        # -------------------------------------------------------------------
        if not self._validate_result_shape(result, defn.expected_result_type):
            err = ToolResultValidationError(
                tool_name,
                f"Result did not match expected shape '{defn.expected_result_type}'. Got: {type(result).__name__}",
            )
            self._record_failure(request_id, agent_name, tool_name, start_iso, t0, sanitized_call_args, err)
            raise err

        # -------------------------------------------------------------------
        # Step 6: Telemetry & Audit Recording
        # -------------------------------------------------------------------
        dt_ms = (time.perf_counter() - t0) * 1000.0
        end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.obs.record_tool_call(
            request_id=request_id,
            tool_name=tool_name,
            agent=agent_name,
            start_time=start_iso,
            end_time=end_iso,
            latency_ms=dt_ms,
            success=True,
            args=sanitized_call_args,
            result_summary=result,
        )

        return result

    @staticmethod
    def _validate_result_shape(result: Any, expected_type: str) -> bool:
        """Verify that the tool output satisfies the declared shape and citation invariants."""
        if expected_type == "dict":
            if not isinstance(result, dict):
                return False
            # Verify citations field if present
            if "citations" in result and not isinstance(result["citations"], list):
                return False
            return True
        elif expected_type == "list":
            if not isinstance(result, list):
                return False
            return True
        elif expected_type == "dict_or_none":
            if result is None:
                return True
            if not isinstance(result, dict):
                return False
            if "citations" in result and not isinstance(result["citations"], list):
                return False
            return True
        return True

    def _record_failure(
        self,
        request_id: Optional[str],
        agent_name: str,
        tool_name: str,
        start_iso: str,
        t0: float,
        args: dict,
        error: Exception,
    ) -> None:
        """Record a verified tool failure in the observability subsystem."""
        dt_ms = (time.perf_counter() - t0) * 1000.0
        end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        err_cat = type(error).__name__
        self.obs.record_tool_call(
            request_id=request_id,
            tool_name=tool_name,
            agent=agent_name,
            start_time=start_iso,
            end_time=end_iso,
            latency_ms=dt_ms,
            success=False,
            args=args,
            error_category=err_cat,
        )


def create_verified_tool(
    func: Callable[..., Any],
    agent_name: str,
    store: Optional[DataStore] = None,
    trusted_client_id: Optional[str] = None,
    tool_name_override: Optional[str] = None,
    verifier: Optional[ToolVerifier] = None,
) -> Callable[..., Any]:
    """Decorator factory creating a verified tool wrapper for agent dispatch."""
    v = verifier or ToolVerifier(store=store)
    tool_name = tool_name_override or func.__name__

    @wraps(func)
    def verified_wrapper(*args: Any, **kwargs: Any) -> Any:
        return v.verify_and_execute(
            tool_func=func,
            agent_name=agent_name,
            tool_name=tool_name,
            args=args,
            kwargs=kwargs,
            trusted_client_id=trusted_client_id,
        )

    return verified_wrapper
