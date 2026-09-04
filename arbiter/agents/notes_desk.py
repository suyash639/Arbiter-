"""
arbiter/agents/notes_desk.py
-----------------------------
Specialist Notes Desk agent for Arbiter.

An agent that answers factual questions about client relationship notes,
transaction memos, and other note/memo-related details using ONLY
deterministic notes/memo tools.

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
from arbiter.tool_verification import ToolVerifier, ToolVerificationError

from arbiter.tools.book import (
    BookToolError,
    UnknownClientError,
    UnknownAccountError,
    UnsupportedFilterError,
    get_client_notes,
    get_transaction_memos,
)

logger = logging.getLogger("arbiter.agents.notes_desk")


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
        description="The single figure, count or date requested, as a string. Must be null when abstained or refused."
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
        description="Record ids the answer relies on. For client-book data, return the exact citation list provided by the tool (e.g. note_* or txn_*)."
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
        description="The ordered role path that produced this answer. Must be ['router', 'notes_desk']."
    )


# ---------------------------------------------------------------------------
# NotesDeskAgent Class
# ---------------------------------------------------------------------------

class NotesDeskAgent:
    """Specialist Notes Desk Agent.

    Wraps the Agno Agent abstraction and connects to the deterministic Notes tools
    with client-id isolation and OpenAI-compatible gateway routing.
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
        verifier = ToolVerifier(store=self.store, observability=obs)

        def track_errors(func):
            from functools import wraps
            tool_name = func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return verifier.verify_and_execute(
                        tool_func=func,
                        agent_name="notes_desk",
                        tool_name=tool_name,
                        args=args,
                        kwargs=kwargs,
                        trusted_client_id=client_id,
                    )
                except Exception as e:
                    tool_errors.append(e)
                    raise
            return wrapper

        def get_notes(cid: str) -> list[dict]:
            """Retrieve the list of relationship/free-text notes for the client."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_client_notes(self.store, cid)

        def get_memos(cid: str) -> list[dict]:
            """Retrieve transactions containing a memo or description for the client."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_transaction_memos(self.store, cid)

        tools_list = [
            track_errors(get_notes),
            track_errors(get_memos),
        ]

        # --- 3. Instantiate model and agent ---
        chosen_model = model_id if (model_id and model_id != "valura-fast") else self.config.llm_model
        model = OpenAIChat(
            id=chosen_model,
            base_url=self.config.llm_base_url,
            api_key=self.config.llm_api_key,
        )

        system_prompt = f"""You are the 'notes_desk' specialist agent for Arbiter, a back-office financial operations engine.
Your sole responsibility is answering factual client notes and transaction memo questions using the deterministic tools provided.

AUTHORIZED SCOPE:
- You are ONLY authorised to access data for client_id: '{client_id}'.
- You MUST pass '{client_id}' as the `cid` parameter to every tool call.
- Never search, infer, or call tools for other client IDs.

REASONING & SYNTHESIS RULES:
1. Identify the notes or transaction memos requested in the query.
2. Select and call the appropriate deterministic tool.
3. Read the tool result. Rely ONLY on the facts explicitly stated in the note/memo text. Do not invent any facts, details, dates, or transactions.
4. Report the exact details found in the notes/memos.
5. If the tool raises an error, if there are no notes/memos, or if the data cannot support the requested question, set:
   - abstained = true
   - answer_value = null
   - reason = a clear description of why the notes/memos cannot support the answer.
6. For personalized investment advice or allocation recommendation queries based on notes:
   - Refuse the request. Do NOT provide recommendations.
   - Set refused = true, abstained = false, answer_value = null.
   - Set reason = 'I cannot provide investment advice. I am a back-office operations engine.'

OUTPUT INSTRUCTIONS:
- You must populate all fields of the required AnswerSchema.
- The 'question_id' field must be '{question_id}'.
- The 'agents' field must be ['router', 'notes_desk'].
- The 'citations' field must contain exactly the citation IDs returned by the tool (e.g. ['note_5001'] or ['txn_100002']). Do not invent citations.
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
                        "agents": ["router", "notes_desk"]
                    }
                if isinstance(err, (ToolVerificationError, ValueError)) and ("Scope violation" in str(err) or isinstance(err, ToolVerificationError)):
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
                        "agents": ["router", "notes_desk"]
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
                agent="notes_desk",
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
                out_dict["agents"] = ["router", "notes_desk"]
                return out_dict
            
            if hasattr(res, "content") and isinstance(res.content, dict):
                res.content["question_id"] = question_id
                res.content["agents"] = ["router", "notes_desk"]
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
                    "agents": ["router", "notes_desk"]
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
                agent="notes_desk",
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
                "agents": ["router", "notes_desk"]
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
            "agents": ["router", "notes_desk"]
        }
