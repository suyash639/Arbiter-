"""
arbiter/agents/market_desk.py
-----------------------------
Specialist Market Desk agent for Arbiter.

An agent that answers factual questions about instruments, sectors, prices, and news
using ONLY deterministic market tools.

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

from arbiter.tools.market import (
    MarketToolError,
    MarketCoverageError,
    NoPriceDataError,
    get_instrument_details,
    get_market_price,
    get_market_return,
    get_symbol_news,
)

logger = logging.getLogger("arbiter.agents.market_desk")


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
        description="Record ids the answer relies on. For market data, use the symbol itself (e.g. ['AMD']) or news ID (e.g. ['news_2008'])."
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
        description="The ordered role path that produced this answer. Must be ['router', 'market_desk']."
    )


# ---------------------------------------------------------------------------
# MarketDeskAgent Class
# ---------------------------------------------------------------------------

class MarketDeskAgent:
    """Specialist Market Desk Agent.

    Wraps the Agno Agent abstraction and connects to the deterministic Market tools
    with client-id validation and OpenAI-compatible gateway routing.
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

        # --- 2. Expose deterministic tools closed over store ---
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
                        agent="market_desk",
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
                        agent="market_desk",
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

        def get_instrument(symbol: str) -> dict:
            """Retrieve details (sector, industry, currency, exchange) for a covered symbol."""
            return get_instrument_details(self.store, symbol)

        def get_price(symbol: str, date: str) -> dict:
            """Retrieve monthly close price for a symbol on or before the requested date."""
            return get_market_price(self.store, symbol, date)

        def get_return(symbol: str, start_date: str, end_date: str) -> dict:
            """Calculate percentage return of a symbol between start_date and end_date using Decimal arithmetic."""
            return get_market_return(self.store, symbol, start_date, end_date)

        def get_news(symbol: str) -> list[dict]:
            """Retrieve all news headlines and bodies for a symbol."""
            return get_symbol_news(self.store, symbol)

        tools_list = [
            track_errors(get_instrument),
            track_errors(get_price),
            track_errors(get_return),
            track_errors(get_news),
        ]

        # --- 3. Instantiate model and agent ---
        chosen_model = model_id if (model_id and model_id != "valura-fast") else self.config.llm_model
        model = OpenAIChat(
            id=chosen_model,
            base_url=self.config.llm_base_url,
            api_key=self.config.llm_api_key,
        )

        system_prompt = f"""You are the 'market_desk' specialist agent for Arbiter, a back-office financial operations engine.
Your sole responsibility is answering factual market questions (prices, sectors, returns, news) using the deterministic tools provided.

COVERAGE RULE (HARD BOUNDARY):
- The market dataset coverage is strictly limited to covered symbols.
- If a symbol is outside this coverage, the tools will raise a MarketCoverageError.
- You MUST immediately abstain and report that the symbol is outside the supplied dataset. Never answer using outside/pretrained knowledge.

REASONING & SYNTHESIS RULES:
1. Identify the instrument details, prices, returns, or news requested in the query.
2. Select and call the appropriate deterministic tool.
3. Read the tool result. Rely ONLY on the facts returned by the tools.
4. For price queries, identify the actual monthly close date used (since observations are monthly closes, not daily).
5. If a tool raises an error, set:
   - abstained = true
   - answer_value = null
   - reason = a clear description of the data limitation.
6. For personalized investment advice or recommendations (e.g. 'should I buy X stock?'):
   - Refuse the request. Do NOT provide recommendations.
   - Set refused = true, abstained = false, answer_value = null.
   - Set reason = 'I cannot provide investment advice. I am a back-office operations engine.'

OUTPUT INSTRUCTIONS:
- You must populate all fields of the required AnswerSchema.
- The 'question_id' field must be '{question_id}'.
- The 'agents' field must be ['router', 'market_desk'].
- The 'citations' field must contain exactly the citation IDs returned by the tool (e.g. the symbol like ['AMD'] or news ID like ['news_2008']). Do not invent citations.
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
                if isinstance(err, MarketCoverageError):
                    return {
                        "question_id": question_id,
                        "answer": "",
                        "answer_value": None,
                        "abstained": True,
                        "refused": False,
                        "reason": str(err),
                        "citations": [],
                        "confidence": 0.0,
                        "flags": [],
                        "agents": ["router", "market_desk"]
                    }
                if isinstance(err, (NoPriceDataError, MarketToolError)):
                    return {
                        "question_id": question_id,
                        "answer": "",
                        "answer_value": None,
                        "abstained": True,
                        "refused": False,
                        "reason": str(err),
                        "citations": [],
                        "confidence": 0.0,
                        "flags": [],
                        "agents": ["router", "market_desk"]
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
                agent="market_desk",
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
                out_dict["agents"] = ["router", "market_desk"]
                return out_dict
            
            if hasattr(res, "content") and isinstance(res.content, dict):
                res.content["question_id"] = question_id
                res.content["agents"] = ["router", "market_desk"]
                return res.content
            
            if hasattr(res, "content") and isinstance(res.content, str):
                logger.warning(f"Response content was string: {res.content}")
                err_msg = res.content
                is_upstream = "connection" in err_msg.lower() or "api key" in err_msg.lower()
                return {
                    "question_id": question_id,
                    "answer": "",
                    "answer_value": None,
                    "abstained": True,
                    "refused": False,
                    "reason": err_msg,
                    "citations": [],
                    "confidence": 0.0,
                    "flags": ["upstream_issue"] if is_upstream else [],
                    "agents": ["router", "market_desk"]
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
                agent="market_desk",
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
                "citations": [],
                "confidence": 0.0,
                "flags": ["upstream_issue"] if is_upstream else [],
                "agents": ["router", "market_desk"]
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
            "agents": ["router", "market_desk"]
        }
