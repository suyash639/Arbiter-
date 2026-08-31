"""
arbiter/agents/book_qa.py
-------------------------
Specialist Book QA agent for Arbiter.

An agent that answers factual questions about client transactions, holdings,
cash balances, portfolios, account age, target allocation, and allocation drift,
using ONLY deterministic Book tools.

It refuses to provide personal investment advice or recommendations.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.tools.book import (
    BookToolError,
    UnknownClientError,
    UnknownAccountError,
    UnsupportedFilterError,
    NoSuitabilityReviewError,
    get_client,
    get_accounts,
    get_holdings,
    get_suitability_reviews,
    get_transactions,
    find_first_transaction,
    find_max_transaction,
    calculate_cash_balance,
    calculate_position_quantity,
    calculate_holdings_count,
    calculate_transaction_total,
    calculate_transaction_count,
    calculate_portfolio_value,
    calculate_target_drift,
    calculate_account_age,
    detect_position_snapshot_conflict,
)

logger = logging.getLogger("arbiter.agents.book_qa")


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
        description="The single figure, count or date requested, as a string. USD with no symbol or separators; dates ISO. Must be null when abstained or refused."
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
        description="Record ids the answer relies on. For client-book data, return the exact citation list provided by the tool. If more than 6 records are involved, use the client_id."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )
    flags: list[str] = Field(
        default_factory=list,
        description="List of flags, e.g. ['conflict'] if snapshot disagrees with transactions, ['upstream_issue'] on LLM errors, or ['stale_data']."
    )
    agents: list[str] = Field(
        default_factory=list,
        description="The ordered role path that produced this answer. Must be ['router', 'book_qa']."
    )


# ---------------------------------------------------------------------------
# BookQAAgent Class
# ---------------------------------------------------------------------------

class BookQAAgent:
    """Specialist Book QA Agent.

    Wraps the Agno Agent abstraction and connects to the deterministic Book tools
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
        # --- 1. Client-id scope check ---
        if not client_id or not client_id.strip():
            return self._build_abstention(
                question_id,
                reason="Authoritative client scope is missing or unspecified."
            )

        # Deterministic check that the client exists in the client book before LLM execution
        try:
            self.store.client(client_id)
        except KeyError:
            return self._build_abstention(
                question_id,
                reason=f"Authoritative client scope check failed: client_id '{client_id}' is not in the client book."
            )

        # Collect exceptions raised during tool execution
        tool_errors: list[Exception] = []

        def track_errors(func):
            from functools import wraps
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tool_errors.append(e)
                    raise
            return wrapper

        # --- 2. Expose deterministic tools closed over store and client_id ---
        # Inside these helper functions, we check that client_id matches the authorised scope.
        # This acts as a python-level guardrail preventing cross-client queries.

        def get_client_profile(cid: str) -> dict:
            """Retrieve the non-sensitive client metadata profile (e.g. name, risk profile, annual income band, kyc status).
            Never includes PII like address, DOB, PAN, bank account.
            """
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_client(self.store, cid)

        def get_client_accounts(cid: str) -> list[dict]:
            """Retrieve investment accounts belonging to the client. Returns safe account metadata: id, opened date, broker reference, and base currency.
            """
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_accounts(self.store, cid)

        def get_client_holdings(cid: str) -> list[dict]:
            """Retrieve positions_snapshot holdings containing symbols, quantities, average cost, and market values."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_holdings(self.store, cid)

        def get_client_suitability_reviews(cid: str) -> list[dict]:
            """Retrieve sorted list of suitability reviews containing target allocation percentages and review dates."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return get_suitability_reviews(self.store, cid)

        def get_client_transactions(
            cid: str,
            symbol: str | None = None,
            txn_type: str | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
            **kwargs: Any,
        ) -> list[dict]:
            """Retrieve filtered list of client transactions. account_id filter is NOT supported and will raise UnsupportedFilterError."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            if "account_id" in kwargs or kwargs:
                raise UnsupportedFilterError("account_id", reason="Filter 'account_id' is not supported by transaction records.")
            return get_transactions(
                self.store, cid, symbol=symbol, txn_type=txn_type,
                start_date=start_date, end_date=end_date
            )

        def find_earliest_transaction(
            cid: str,
            txn_type: str | None = None,
            symbol: str | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
        ) -> dict | None:
            """Find the chronologically earliest transaction matching the filters."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return find_first_transaction(
                self.store, cid, txn_type=txn_type, symbol=symbol,
                start_date=start_date, end_date=end_date
            )

        def find_largest_transaction(
            cid: str,
            numeric_field: str,
            txn_type: str | None = None,
            symbol: str | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
        ) -> dict | None:
            """Find the transaction with the largest numeric value (e.g. 'amount_usd' or 'net_usd') matching the filters."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return find_max_transaction(
                self.store, cid, numeric_field, txn_type=txn_type, symbol=symbol,
                start_date=start_date, end_date=end_date
            )

        def get_cash_balance(cid: str, as_of: str | None = None) -> dict:
            """Retrieve the USD cash balance aggregated from transactions as of a date."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_cash_balance(self.store, cid, as_of=as_of)

        def get_position_quantity(cid: str, symbol: str, as_of: str | None = None) -> dict:
            """Retrieve the quantity of a symbol held as of a date, reconstructed historically if before the book date."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_position_quantity(self.store, cid, symbol=symbol, as_of=as_of)

        def get_holdings_count(cid: str, as_of: str | None = None) -> dict:
            """Retrieve the count of distinct symbols with a positive quantity held as of a date."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_holdings_count(self.store, cid, as_of=as_of)

        def get_transaction_total(
            cid: str,
            numeric_field: str,
            txn_type: str | None = None,
            symbol: str | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
        ) -> dict:
            """Sum a numeric field (e.g. 'amount_usd', 'net_usd') across filtered transactions."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_transaction_total(
                self.store, cid, numeric_field, txn_type=txn_type, symbol=symbol,
                start_date=start_date, end_date=end_date
            )

        def get_transaction_count(
            cid: str,
            txn_type: str | None = None,
            symbol: str | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
        ) -> dict:
            """Count transactions matching the filters."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_transaction_count(
                self.store, cid, txn_type=txn_type, symbol=symbol,
                start_date=start_date, end_date=end_date
            )

        def get_portfolio_value(cid: str) -> dict:
            """Sum the market_value_usd of all snapshot positions."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_portfolio_value(self.store, cid)

        def get_target_drift(cid: str, symbol: str) -> dict:
            """Calculate portfolio drift of a symbol from target allocation (actual % - target %). Denominator is equity-only."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_target_drift(self.store, cid, symbol=symbol)

        def get_account_age(cid: str, account_id: str, as_of: str | None = None) -> dict:
            """Retrieve the age of an account in days as of a date."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return calculate_account_age(self.store, cid, account_id=account_id, as_of=as_of)

        def check_position_snapshot_conflict(cid: str, symbol: str) -> dict:
            """Detect mismatches between snapshot quantity and transaction history."""
            if cid != client_id:
                raise ValueError("Scope violation: client_id mismatch.")
            return detect_position_snapshot_conflict(self.store, cid, symbol=symbol)

        tools_list = [
            track_errors(get_client_profile),
            track_errors(get_client_accounts),
            track_errors(get_client_holdings),
            track_errors(get_client_suitability_reviews),
            track_errors(get_client_transactions),
            track_errors(find_earliest_transaction),
            track_errors(find_largest_transaction),
            track_errors(get_cash_balance),
            track_errors(get_position_quantity),
            track_errors(get_holdings_count),
            track_errors(get_transaction_total),
            track_errors(get_transaction_count),
            track_errors(get_portfolio_value),
            track_errors(get_target_drift),
            track_errors(get_account_age),
            track_errors(check_position_snapshot_conflict),
        ]

        # --- 3. Instantiate model and agent ---
        # OpenAI-compatible gateway setup using config
        chosen_model = model_id if (model_id and model_id != "valura-fast") else self.config.llm_model
        model = OpenAIChat(
            id=chosen_model,
            base_url=self.config.llm_base_url,
            api_key=self.config.llm_api_key,
        )

        system_prompt = f"""You are the 'book_qa' specialist agent for Arbiter, a back-office financial operations engine.
Your sole responsibility is answering factual client-book questions using the deterministic tools provided.

AUTHORIZED SCOPE:
- You are ONLY authorised to access data for client_id: '{client_id}'.
- You MUST pass '{client_id}' as the `cid` (or `client_id`) parameter to every tool call.
- Never search, infer, or call tools for other client IDs.

REASONING RULES:
1. Identify the factual details requested in the user query.
2. Select and call the appropriate deterministic tool.
3. Read the tool result. Do NOT perform any financial arithmetic, aggregations, drift calculations, or date differences yourself.
4. Report the exact numeric values, dates, or counts returned by the tool.
5. If the tool raises an error (e.g. UnsupportedFilterError) or reports missing/unknown records, or if the data cannot support the answer, set:
   - abstained = true
   - answer_value = null
   - reason = a clear description of the missing data or filter limitation.
6. For personalized investment advice or allocation recommendation queries (e.g., 'should the client buy AMD?', 'what should the client sell?', 'what allocation should the client have?'):
   - Refuse the request. Do NOT make up recommendations.
   - Set refused = true, abstained = false, answer_value = null.
   - Set reason = 'I cannot provide investment advice. I am a back-office operations engine.'

OUTPUT INSTRUCTIONS:
- You must populate all fields of the required AnswerSchema.
- The 'question_id' field must be '{question_id}'.
- The 'agents' field must be ['router', 'book_qa'].
- The 'citations' field must contain exactly the citation list returned by the tool (e.g. ['pos_...'] or ['cli_...']). Do not invent citations.
- If conflict check tool reports a conflict (conflict = True), you must add 'conflict' to the 'flags' field.
"""

        agent = Agent(
            model=model,
            tools=tools_list,
            instructions=[system_prompt],
            output_schema=AnswerSchema,
            parse_response=True,
        )

        # Check tool errors first (so they take precedence over whatever Agno returns or raises)
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
                        "agents": ["router", "book_qa"]
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
                        "agents": ["router", "book_qa"]
                    }
            return None

        # --- 4. Execute Agno Agent with error fallbacks ---
        try:
            res = agent.run(prompt)
            
            # Check if any tool raised an error during execution
            tool_err_resp = check_tool_errors()
            if tool_err_resp:
                return tool_err_resp

            # If output is structured content conforming to AnswerSchema
            if hasattr(res, "content") and isinstance(res.content, AnswerSchema):
                out_dict = res.content.model_dump()
                out_dict["question_id"] = question_id
                out_dict["agents"] = ["router", "book_qa"]
                return out_dict
            
            # Fallback if content was parsed as raw dictionary
            if hasattr(res, "content") and isinstance(res.content, dict):
                res.content["question_id"] = question_id
                res.content["agents"] = ["router", "book_qa"]
                return res.content
            
            # If it's a string, it might be due to connection failure or validation failure
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
                    "agents": ["router", "book_qa"]
                }

            logger.warning(f"Response content was not parsed: {res.content}")
            return self._build_abstention(
                question_id,
                reason="Structured parser returned non-conforming content type."
            )

        except Exception as e:
            # Check tool errors in the exception block too
            tool_err_resp = check_tool_errors()
            if tool_err_resp:
                return tool_err_resp

            logger.error(f"LLM Gateway execution error: {e}", exc_info=True)
            err_msg = str(e)
            is_upstream = True
            if "UnsupportedFilterError" in err_msg or "Filter 'account_id' cannot be applied" in err_msg:
                is_upstream = False
                reason_str = "Filter 'account_id' is not supported by transaction records."
            else:
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
                "agents": ["router", "book_qa"]
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
            "agents": ["router", "book_qa"]
        }
