"""
arbiter/orchestrator.py
-----------------------
Central Arbiter Orchestrator.

Routes incoming query requests to the appropriate specialist agent
(book_qa, kyc_profile, notes_desk, market_desk, or compliance)
and returns a schema-valid response.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.agents.book_qa import BookQAAgent
from arbiter.agents.kyc_profile import KYCProfileAgent
from arbiter.agents.notes_desk import NotesDeskAgent
from arbiter.agents.market_desk import MarketDeskAgent
from arbiter.agents.compliance import ComplianceAgent

logger = logging.getLogger("arbiter.orchestrator")


# ---------------------------------------------------------------------------
# Router classification Pydantic model
# ---------------------------------------------------------------------------

class RouteClassification(BaseModel):
    """Pydantic model representing the router's classification output."""

    specialist: str = Field(
        description="The target specialist role. Must be one of: 'book_qa', 'kyc_profile', 'notes_desk', 'market_desk', 'compliance'."
    )


# ---------------------------------------------------------------------------
# ArbiterOrchestrator Class
# ---------------------------------------------------------------------------

class ArbiterOrchestrator:
    """Central router/coordinator that classifies and delegates questions to specialist agents.

    Exposes no tools directly and performs no business calculations.
    """

    def __init__(self, store: DataStore, config: Config) -> None:
        self.store = store
        self.config = config

        # Register and instantiate the specialist agents
        self.specialists = {
            "book_qa": BookQAAgent(store, config),
            "kyc_profile": KYCProfileAgent(store, config),
            "notes_desk": NotesDeskAgent(store, config),
            "market_desk": MarketDeskAgent(store, config),
            "compliance": ComplianceAgent(store, config),
        }

    def route_question(self, question_id: str, client_id: str, prompt: str) -> str:
        """Classifies the prompt into the target specialist agent using the router model.

        Contains deterministic overrides for safety/compliance before the LLM runs.
        """
        prompt_lower = prompt.lower()

        # Deterministic check for advice/compliance boundaries
        advice_keywords = [
            "recommend", "stock strategy", "portfolio strategy", "investment recommendation", "recommend allocation",
            "how should I rebalance", "what strategy do you recommend"
        ]
        if any(keyword in prompt_lower for keyword in advice_keywords) or (
            "should" in prompt_lower and any(act in prompt_lower for act in ("buy", "sell", "invest", "rebalance"))
        ):
            return "compliance"

        # Agno Agent configured to classify request
        model = OpenAIChat(
            id=self.config.llm_model,
            base_url=self.config.llm_base_url,
            api_key=self.config.llm_api_key,
        )

        system_prompt = f"""You are the 'router' coordinator agent for Arbiter.
Your sole job is to classify the user's query into exactly one of these five specialist roles:

1. 'book_qa': For portfolio cash balance, holdings, transactions, transaction counts, portfolio value, position quantity, target drift, account age, snapshot conflicts, or suitability targets.
2. 'kyc_profile': For KYC status, risk profile, PAN/bank account details (masked), DOB, address, income, employer, or occupation.
3. 'notes_desk': For relationship notes, note text/date/author, or transaction memos.
4. 'market_desk': For covered instruments, sectors, industries, monthly prices, returns, or market news.
5. 'compliance': For out-of-scope requests, cross-client information requests, or personalised investment/allocation recommendations.

You are classification routing for client_id: '{client_id}'.
Respond strictly in JSON matching the RouteClassification schema.
"""

        router = Agent(
            model=model,
            instructions=[system_prompt],
            output_schema=RouteClassification,
            parse_response=True,
        )

        try:
            res = router.run(prompt)
            if hasattr(res, "content") and isinstance(res.content, RouteClassification):
                role = res.content.specialist
                if role in self.specialists:
                    return role
            if hasattr(res, "content") and isinstance(res.content, dict):
                role = res.content.get("specialist")
                if role in self.specialists:
                    return role
        except Exception as e:
            logger.error(f"Router LLM classification failed: {e}", exc_info=True)

        # Keyword fallbacks on gateway/LLM failure
        if "note" in prompt_lower or "memo" in prompt_lower:
            return "notes_desk"
        if "pan" in prompt_lower or "address" in prompt_lower or "kyc" in prompt_lower or "dob" in prompt_lower:
            return "kyc_profile"
        if "price" in prompt_lower or "return" in prompt_lower or "news" in prompt_lower or "sector" in prompt_lower:
            return "market_desk"
        return "book_qa"

    def answer(self, payload: dict) -> dict:
        """Route the incoming question payload to the correct specialist and return the result."""
        question_id = payload.get("question_id")
        client_id = payload.get("client_id")
        prompt = payload.get("prompt")

        # --- 1. Pre-flight Checks ---
        if not question_id:
            return self._build_abstention(
                "unknown",
                reason="Missing question_id in request payload."
            )

        if not client_id or not client_id.strip():
            return self._build_abstention(
                question_id,
                reason="Authoritative client scope (client_id) is missing."
            )

        # Validate client ID exists
        try:
            self.store.client(client_id)
        except KeyError:
            return self._build_abstention(
                question_id,
                reason=f"Client ID '{client_id}' is not in the client book."
            )

        # --- 2. Determine Specialist ---
        role = self.route_question(question_id, client_id, prompt)
        logger.info(f"Router directed q_id {question_id} to agent {role}.")

        # --- 3. Delegate to Specialist ---
        specialist = self.specialists[role]
        try:
            response = specialist.answer(question_id, client_id, prompt)

            # Ensure routing trace is preserved
            if "agents" not in response or not response["agents"]:
                response["agents"] = ["router", role]
            elif "router" not in response["agents"]:
                response["agents"] = ["router"] + response["agents"]

            return response

        except Exception as e:
            logger.error(f"Orchestrator delegation failed to specialist {role}: {e}", exc_info=True)
            return {
                "question_id": question_id,
                "answer": "",
                "answer_value": None,
                "abstained": True,
                "refused": False,
                "reason": f"Orchestrator failed to delegate or execute specialist agent: {e}",
                "citations": [],
                "confidence": 0.0,
                "flags": ["upstream_issue"],
                "agents": ["router", role]
            }

    def _build_abstention(self, question_id: str, reason: str) -> dict:
        """Build a schema-valid abstention envelope."""
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
            "agents": ["router"]
        }
