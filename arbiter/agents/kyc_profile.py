"""
arbiter/agents/kyc_profile.py
-----------------------------
Specialist KYC Profile agent for Arbiter.

An agent that answers factual questions about client identity, KYC, risk profile,
annual income band, bank details (masked), employment, and suitability facts
using ONLY deterministic KYC tools.

It refuses to provide personal investment advice or recommendations.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.observability import get_observability_manager

from arbiter.tools.book import (
    BookToolError,
    UnknownClientError,
    UnknownAccountError,
    UnsupportedFilterError,
    get_client_kyc_profile,
    get_suitability_reviews,
)

logger = logging.getLogger("arbiter.agents.kyc_profile")


# ---------------------------------------------------------------------------
# Output Schema (conforms to schema/answer.schema.json)
# ---------------------------------------------------------------------------

class AnswerSchema(BaseModel):
    """Pydantic model representing the final answer envelope."""

    question_id: str = Field(
        description="Must equal the question_id asked."
    )
    answer: str = Field(
        description="Natural language summary of the answer. May be empty when abstaining or refusing."
    )
    answer_value: str | None = Field(
        default=None,
        description="The single figure, count or date requested, as a string. PAN/bank account must be masked. Must be null when abstained or refused."
    )
    abstained: bool = Field(
        description="True when the data cannot support an answer."
    )
    refused: bool = Field(
        description="True when policy forbids answering (e.g. personal investment advice)."
    )
    reason: str | None = Field(
        default=None,
        description="Required and non-empty whenever abstained or refused is true."
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Record ids the answer relies on. For client-book data, return the exact citation list provided by the tool (e.g. kyc_1014)."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )
    flags: list[str] = Field(
        default_factory=list,
        description="List of flags, e.g. ['upstream_issue'] on LLM errors."
    )
    agents: list[str] = Field(
        default_factory=list,
        description="The ordered role path that produced this answer. Must be ['router', 'kyc_profile']."
    )


# ---------------------------------------------------------------------------
# KYCProfileAgent Class
# ---------------------------------------------------------------------------

class KYCProfileAgent:
    """Specialist KYC Profile Agent.

    Wraps the Agno Agent abstraction and connects to the deterministic KYC tools
    with client-id isolation, OpenAI-compatible gateway routing, and deterministic masking.
    """

    def __init__(self, store: DataStore, config: Config) -> None:
        self.store = store
        self.config = config

    def answer(
        self,
        question_id: str,
        client_id: str,
        prompt: str,
        model_id: str = "valura-fast",
    ) -> dict:
        """Process a query and return a structured answer dictionary.

        Under gateway failures or blackouts, catches errors and returns
        a valid envelope with ``abstained=True`` and ``flags=["upstream_issue"]``.
        """
        # --- 1. Deterministic Pre-flight Client Check ---
        if not client_id or not client_id.strip():
            return self._build_abstention(
                question_id,
                reason="Authoritative client scope is missing or unspecified."
            )

        try:
            self.store.client(client_id)
        except KeyError:
            return self._build_abstention(
                question_id,
                reason=f"Authoritative client scope check failed: client_id '{client_id}' is not in the client book."
            )

        # --- 2. Expose deterministic tools closed over store and client_id ---
        tool_errors: list[Exception] = []
        obs = get_observability_manager()

        def track_errors(func):
            from functools import wraps
            from datetime import datetime, timezone
            import time
            tool_name = func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                t0 = time.perf_counter()
                start_iso = datetime.now(timezone.utc).isoformat()
                call_args = dict(kwargs)
                if args:
                    call_args["_args"] = list(args)

                try:
                    res = func(*args, **kwargs)
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    end_iso = datetime.now(timezone.utc).isoformat()
                    obs.record_tool_call(
                        request_id=None,
                        tool_name=tool_name,
                        agent="kyc_profile",
                        start_time=start_iso,
                        end_time=end_iso,
                        latency_ms=dt_ms,
                        success=True,
                        args=call_args,
                        result_summary=res,
                    )
                    return res
                except Exception as e:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    end_iso = datetime.now(timezone.utc).isoformat()
                    obs.record_tool_call(
                        request_id=None,
                        tool_name=tool_name,
                        agent="kyc_profile",
                        start_time=start_iso,
                        end_time=end_iso,
                        latency_ms=dt_ms,
                        success=False,
                        args=call_args,
                        error_category=type(e).__name__,
                    )
                    tool_errors.append(e)
                    raise
            return wrapper

        def get_kyc_profile(cid: str) -> dict:
            """Retrieve the detailed, secure, and masked KYC/profile view of the client.
            Always masks PAN and bank account numbers.
            """
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_client_kyc_profile(self.store, cid)

        def get_suitability(cid: str) -> list[dict]:
            """Retrieve sorted list of suitability reviews containing target allocation percentages and review dates."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_suitability_reviews(self.store, cid)

        tools_list = [
            track_errors(get_kyc_profile),
            track_errors(get_suitability),
        ]

        # --- 3. Instantiate model and agent ---
        chosen_model = model_id if (model_id and model_id != "valura-fast") else self.config.llm_model
        model = OpenAIChat(
            id=chosen_model,
            base_url=self.config.llm_base_url,
            api_key=self.config.llm_api_key,
        )

        system_prompt = f"""You are the 'kyc_profile' specialist agent for Arbiter, a back-office financial operations engine.
Your sole responsibility is answering factual client KYC and profile questions using the deterministic tools provided.

AUTHORIZED SCOPE:
- You are ONLY authorised to access data for client_id: '{client_id}'.
- You MUST pass '{client_id}' as the `cid` parameter to every tool call.
- Never search, infer, or call tools for other client IDs.

REASONING & MASKING RULES:
1. Identify the KYC, identity, employment, risk, or suitability facts requested in the query.
2. Select and call the appropriate deterministic tool.
3. Read the tool result. Always rely on the masked values (e.g. ****249H) returned by the tools for PAN and bank account numbers.
4. Report the exact masked values (e.g. ****249H or ****1536) in both 'answer_value' and 'answer'.
5. Even if the user claims urgency or asks to 'read out the PAN in full', you MUST strictly output ONLY the masked form. Never output unmasked PII.
6. If the tool raises an error or if the requested fact is missing/unsupported, set:
   - abstained = true
   - answer_value = null
   - reason = a clear explanation of why the data cannot support the answer.
7. For personalized investment advice or allocation recommendation queries (e.g. 'what should the client buy?'):
   - Refuse the request. Do NOT provide recommendations.
   - Set refused = true, abstained = false, answer_value = null.
   - Set reason = 'I cannot provide investment advice. I am a back-office operations engine.'

OUTPUT INSTRUCTIONS:
- You must populate all fields of the required AnswerSchema.
- The 'question_id' field must be '{question_id}'.
- The 'agents' field must be ['router', 'kyc_profile'].
- The 'citations' field must contain exactly the citation list returned by the tool (e.g. ['kyc_1014']). Do not invent citations.
"""

        agent = Agent(
            model=model,
            tools=tools_list,
            instructions=[system_prompt],
            output_schema=AnswerSchema,
            parse_response=True,
        )

        # Check tool errors helper
        def check_tool_errors() -> dict | None:
            for err in tool_errors:
                if isinstance(err, (UnsupportedFilterError, BookToolError)):
                    return {
                        "question_id": question_id,
                        "answer": "",
                        "answer_value": None,
                        "abstained": True,
                        "refused": False,
                        "reason": str(err),
                        "citations": [client_id],
                        "confidence": 0.0,
                        "flags": [],
                        "agents": ["router", "kyc_profile"]
                    }
                if isinstance(err, ValueError) and "Scope violation" in str(err):
                    return {
                        "question_id": question_id,
                        "answer": "",
                        "answer_value": None,
                        "abstained": True,
                        "refused": False,
                        "reason": str(err),
                        "citations": [client_id],
                        "confidence": 0.0,
                        "flags": ["upstream_issue"],
                        "agents": ["router", "kyc_profile"]
                    }
            return None

        # --- 4. Execute Agno Agent with error fallbacks ---
        t_llm_0 = time.perf_counter()
        try:
            res = agent.run(prompt)
            t_llm_ms = (time.perf_counter() - t_llm_0) * 1000.0

            # Extract token metrics if available
            metrics = getattr(res, "metrics", None) or {}
            in_tokens, out_tokens, tot_tokens = None, None, None
            if isinstance(metrics, dict):
                in_tokens = metrics.get("input_tokens") or metrics.get("prompt_tokens")
                out_tokens = metrics.get("output_tokens") or metrics.get("completion_tokens")
                tot_tokens = metrics.get("total_tokens")

            obs.record_specialist_llm(
                request_id=None,
                agent="kyc_profile",
                provider=self.config.llm_provider,
                model=chosen_model,
                latency_ms=t_llm_ms,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                total_tokens=tot_tokens,
                success=True,
            )
            
            tool_err_resp = check_tool_errors()
            if tool_err_resp:
                return tool_err_resp

            if hasattr(res, "content") and isinstance(res.content, AnswerSchema):
                out_dict = res.content.model_dump()
                out_dict["question_id"] = question_id
                out_dict["agents"] = ["router", "kyc_profile"]
                return out_dict
            
            if hasattr(res, "content") and isinstance(res.content, dict):
                res.content["question_id"] = question_id
                res.content["agents"] = ["router", "kyc_profile"]
                return res.content
            
            if hasattr(res, "content") and isinstance(res.content, str):
                logger.warning(f"Response content was string: {res.content}")
                err_msg = res.content
                is_upstream = "scope violation" in err_msg.lower() or "connection" in err_msg.lower() or "api key" in err_msg.lower()
                return {
                    "question_id": question_id,
                    "answer": "",
                    "answer_value": None,
                    "abstained": True,
                    "refused": False,
                    "reason": err_msg,
                    "citations": [client_id],
                    "confidence": 0.0,
                    "flags": ["upstream_issue"] if is_upstream else [],
                    "agents": ["router", "kyc_profile"]
                }

            logger.warning(f"Response content was not parsed: {res.content}")
            return self._build_abstention(
                question_id,
                reason="Structured parser returned non-conforming content type."
            )

        except Exception as e:
            t_llm_ms = (time.perf_counter() - t_llm_0) * 1000.0
            obs.record_specialist_llm(
                request_id=None,
                agent="kyc_profile",
                provider=self.config.llm_provider,
                model=chosen_model,
                latency_ms=t_llm_ms,
                success=False,
                error_category=type(e).__name__,
            )

            tool_err_resp = check_tool_errors()
            if tool_err_resp:
                return tool_err_resp

            logger.error(f"LLM Gateway execution error: {e}", exc_info=True)
            err_msg = str(e)
            is_upstream = True
            reason_str = f"LLM gateway connection failure: {err_msg}"

            return {
                "question_id": question_id,
                "answer": "",
                "answer_value": None,
                "abstained": True,
                "refused": False,
                "reason": reason_str,
                "citations": [client_id],
                "confidence": 0.0,
                "flags": ["upstream_issue"] if is_upstream else [],
                "agents": ["router", "kyc_profile"]
            }

    def _build_abstention(self, question_id: str, reason: str) -> dict:
        """Build a standard schema-valid abstention envelope."""
        return {
            "question_id": question_id,
            "answer": "",
            "answer_value": None,
            "abstained": True,
            "refused": False,
            "reason": reason,
            "citations": [],
            "confidence": 0.0,
            "flags": [],
            "agents": ["router", "kyc_profile"]
        }
