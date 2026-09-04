"""
arbiter/api/routes/metadata.py
------------------------------
Read-only metadata endpoints serving safe structural system information to the operations console.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends

from arbiter.api.dependencies import get_config, get_observability, get_orchestrator, get_store
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager
from arbiter.orchestrator import ArbiterOrchestrator
from arbiter.tool_verification.registry import TOOL_REGISTRY

router = APIRouter(prefix="/v1", tags=["Metadata"])


@router.get("/clients", summary="List Authorized Clients")
async def list_clients(store: DataStore = Depends(get_store)) -> List[Dict[str, Any]]:
    """Return safe metadata summaries for all clients in the client book."""
    results = []
    for cid in store.client_ids:
        raw = store.client(cid)
        profile = raw.get("profile", {})
        accounts = raw.get("accounts", [])
        suitability = raw.get("suitability_reviews", [])
        latest_suitability = suitability[-1] if suitability else {}

        results.append({
            "client_id": cid,
            "name": profile.get("name", "Unknown"),
            "risk_profile": profile.get("risk_profile", "Moderate"),
            "kyc_status": profile.get("kyc_status", "verified"),
            "accounts_count": len(accounts),
            "total_suitability_reviews": len(suitability),
            "target_risk": latest_suitability.get("target_risk", "Moderate"),
        })
    return results


@router.get("/agents", summary="List Agent Network Topology")
async def list_agents() -> List[Dict[str, Any]]:
    """Return structural topology and roles for the 6 specialist agents."""
    return [
        {
            "id": "router",
            "name": "Router Coordinator",
            "role": "Intent Classification & Safety Gate",
            "tool_count": 0,
            "description": "Classifies incoming natural language queries into specialist domains with deterministic safety overrides.",
            "color": "indigo",
        },
        {
            "id": "book_qa",
            "name": "Book QA Specialist",
            "role": "Portfolio & Transactions",
            "tool_count": 16,
            "description": "Calculates exact portfolio balances, transactions, holdings, drift, and account snapshots using Decimal arithmetic.",
            "color": "emerald",
        },
        {
            "id": "kyc_profile",
            "name": "KYC Profile Specialist",
            "role": "Identity & Compliance Suitability",
            "tool_count": 2,
            "description": "Retrieves masked client identity records, employment, income, risk profile, and suitability reviews.",
            "color": "sky",
        },
        {
            "id": "notes_desk",
            "name": "Notes Desk Specialist",
            "role": "CRM & Relationship Intelligence",
            "tool_count": 2,
            "description": "Searches relationship notes, author history, and transaction memos with indirect injection safeguards.",
            "color": "amber",
        },
        {
            "id": "market_desk",
            "name": "Market Desk Specialist",
            "role": "Pricing & Covered Securities",
            "tool_count": 4,
            "description": "Answers factual market queries, monthly close prices, returns, and news headlines for covered tickers.",
            "color": "purple",
        },
        {
            "id": "compliance",
            "name": "Compliance Specialist",
            "role": "Regulatory & Policy Refusal",
            "tool_count": 0,
            "description": "Deterministic safety refusal agent handling out-of-scope requests and personalized investment advice.",
            "color": "rose",
        },
    ]


@router.get("/tools", summary="List Verified Tool Registry")
async def list_tools() -> List[Dict[str, Any]]:
    """Return the authoritative 24-tool registry with authorization and scope mappings."""
    tools_list = []
    for name, defn in TOOL_REGISTRY.items():
        schema_name = getattr(defn.args_schema, "__name__", str(defn.args_schema)) if defn.args_schema else "None"
        tools_list.append({
            "name": name,
            "owning_agents": list(defn.owning_agents),
            "is_client_scoped": defn.requires_client_id,
            "description": defn.description,
            "expected_shape": defn.expected_result_type,
            "argument_schema": schema_name,
            "verification_status": "active",
        })
    return tools_list


@router.get("/security/summary", summary="Security Subsystem Status")
async def security_summary() -> Dict[str, Any]:
    """Return active security controls and trust boundaries."""
    return {
        "status": "active",
        "controls": [
            {"name": "Prompt Injection Defense", "status": "active", "description": "Heuristic regex scanner detecting direct jailbreaks and role override attempts."},
            {"name": "Indirect Injection Quarantine", "status": "active", "description": "Strict XML boundary encapsulation (<untrusted_retrieved_data>) for dynamic notes/news."},
            {"name": "Deterministic Client Isolation", "status": "active", "description": "Context-enforced client ID boundary verified pre-flight against authoritative DataStore."},
            {"name": "Automated PII Masking", "status": "active", "description": "Automatic regex masking for Indian PANs (****249H) and bank accounts (****9012)."},
            {"name": "Secret Leak Prevention", "status": "active", "description": "Automatic redaction of API keys, bearer tokens, and credentials in logs and outputs."},
            {"name": "Output Security Guard", "status": "active", "description": "Post-generation AnswerSchema contract verification and cross-client citation isolation."},
        ],
        "trust_boundaries": {
            "untrusted": ["User Prompts", "LLM Reasoning", "Dynamic Notes", "Market News", "Tool Parameters"],
            "trusted": ["Authenticated Client ID", "Server Config", "Tool Registry", "Deterministic Calculation Engine", "Verified Results"],
        },
    }


@router.get("/reliability/summary", summary="Reliability Subsystem Status")
async def reliability_summary(config: Config = Depends(get_config)) -> Dict[str, Any]:
    """Return configured reliability parameters and circuit breaker configuration."""
    return {
        "status": "active",
        "max_attempts": config.reliability_max_attempts,
        "initial_backoff_seconds": config.reliability_initial_backoff,
        "max_backoff_seconds": config.reliability_max_backoff,
        "jitter_enabled": config.reliability_jitter,
        "llm_timeout_seconds": config.llm_timeout_seconds,
        "circuit_breaker": {
            "failure_threshold": config.circuit_breaker_failure_threshold,
            "recovery_seconds": config.circuit_breaker_recovery_seconds,
            "state": "CLOSED",
        },
        "non_retryable_categories": [
            "NON_RETRYABLE_CLIENT_ERROR (4xx)",
            "NON_RETRYABLE_TOOL_ERROR",
            "NON_RETRYABLE_SCHEMA_ERROR",
            "Policy Refusal / Scope Violation",
            "Prompt Injection Detection",
        ],
    }


@router.get("/observability/summary", summary="Observability & Telemetry Metrics")
async def observability_summary(
    obs: ObservabilityManager = Depends(get_observability),
) -> Dict[str, Any]:
    """Return real aggregate metrics and recent request traces from in-memory collector."""
    from arbiter.observability.metrics import compute_aggregate_metrics

    traces = obs.collector.get_all_traces() if hasattr(obs, "collector") else []
    metrics = compute_aggregate_metrics(traces)

    safe_traces = []
    for tr in traces[-10:]:
        safe_traces.append({
            "request_id": tr.metadata.request_id,
            "question_id": tr.metadata.question_id,
            "client_id": tr.metadata.client_id,
            "provider": tr.llm.provider if tr.llm else "unknown",
            "model": tr.llm.model if tr.llm else "unknown",
            "agent_path": tr.agent_path,
            "total_latency_ms": round(tr.total_latency_ms, 2) if tr.total_latency_ms else None,
            "router_latency_ms": round(tr.router.latency_ms, 2) if tr.router and tr.router.latency_ms else None,
            "specialist_latency_ms": round(tr.specialist.latency_ms, 2) if tr.specialist and tr.specialist.latency_ms else None,
            "tool_call_count": len(tr.tool_calls),
            "refused": tr.refused,
            "abstained": tr.abstained,
            "success": tr.status == "success",
            "error": tr.error,
        })

    return {
        "total_requests": metrics.total_requests,
        "successful_requests": metrics.successful_requests,
        "refused_requests": metrics.refused_requests,
        "abstained_requests": metrics.abstained_requests,
        "error_requests": metrics.error_requests,
        "p50_latency_ms": metrics.p50_latency_ms,
        "p95_latency_ms": metrics.p95_latency_ms,
        "recent_traces": safe_traces,
    }
