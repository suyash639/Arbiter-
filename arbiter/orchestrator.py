"""
arbiter/orchestrator.py
-----------------------
Central Arbiter Orchestrator.

Routes incoming query requests to the appropriate specialist agent
(book_qa, kyc_profile, notes_desk, market_desk, or compliance)
and returns a schema-valid response with complete observability tracing.
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
from arbiter.agents.book_qa import BookQAAgent
from arbiter.agents.kyc_profile import KYCProfileAgent
from arbiter.agents.notes_desk import NotesDeskAgent
from arbiter.agents.market_desk import MarketDeskAgent
from arbiter.agents.compliance import ComplianceAgent
from arbiter.observability import get_observability_manager
from arbiter.reliability import ReliabilityEngine
from arbiter.security import (
    InputValidationError,
    PromptInjectionDetectedError,
    get_security_manager,
)

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

    def __init__(
        self,
        store: DataStore,
        config: Config,
        reliability: ReliabilityEngine | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self.obs = get_observability_manager()
        self.reliability = reliability or ReliabilityEngine(config=config, observability=self.obs)
        self.security = get_security_manager(store=store)

        # Register and instantiate the specialist agents
        self.specialists = {
            "book_qa": BookQAAgent(store, config),
            "kyc_profile": KYCProfileAgent(store, config),
            "notes_desk": NotesDeskAgent(store, config),
            "market_desk": MarketDeskAgent(store, config),
            "compliance": ComplianceAgent(store, config),
        }


    def route_question(
        self,
        question_id: str,
        client_id: str,
        prompt: str,
        request_id: str | None = None,
    ) -> str:
        """Classifies the prompt into the target specialist agent using the router model.

        Contains deterministic overrides for safety/compliance before the LLM runs.
        """
        t0 = time.perf_counter()
        prompt_lower = prompt.lower()

        # Deterministic check for advice/compliance boundaries
        advice_keywords = [
            "recommend", "stock strategy", "portfolio strategy", "investment recommendation", "recommend allocation",
            "how should i rebalance", "what strategy do you recommend"
        ]
        if any(keyword in prompt_lower for keyword in advice_keywords) or (
            "should" in prompt_lower and any(act in prompt_lower for act in ("buy", "sell", "invest", "rebalance"))
        ):
            role = "compliance"
            lat_ms = (time.perf_counter() - t0) * 1000.0
            self.obs.record_router(request_id, role, ["router", role], lat_ms)
            return role

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

        role = None
        in_tokens, out_tokens = None, None
        err_cat = None

        try:
            res = self.reliability.execute(
                router.run,
                args=(prompt,),
                question_id=question_id,
                client_id=client_id,
                agents=["router"],
                operation_name="router_classification",
                request_id=request_id,
            )

            # Extract token metrics if available
            metrics = getattr(res, "metrics", None) or {}
            if isinstance(metrics, dict):
                in_tokens = metrics.get("input_tokens") or metrics.get("prompt_tokens")
                out_tokens = metrics.get("output_tokens") or metrics.get("completion_tokens")

            if hasattr(res, "content") and isinstance(res.content, RouteClassification):
                if res.content.specialist in self.specialists:
                    role = res.content.specialist
            elif hasattr(res, "content") and isinstance(res.content, dict):
                cand = res.content.get("specialist")
                if cand in self.specialists:
                    role = cand
        except Exception as e:
            logger.error(f"Router LLM classification failed: {e}", exc_info=True)
            err_cat = type(e).__name__

        # Keyword fallbacks on gateway/LLM failure or unparsed content
        if not role:
            if "note" in prompt_lower or "memo" in prompt_lower:
                role = "notes_desk"
            elif "pan" in prompt_lower or "address" in prompt_lower or "kyc" in prompt_lower or "dob" in prompt_lower:
                role = "kyc_profile"
            elif "price" in prompt_lower or "return" in prompt_lower or "news" in prompt_lower or "sector" in prompt_lower:
                role = "market_desk"
            else:
                role = "book_qa"

        lat_ms = (time.perf_counter() - t0) * 1000.0
        self.obs.record_router(
            request_id=request_id,
            selected_specialist=role,
            agent_path=["router", role],
            latency_ms=lat_ms,
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            success=(err_cat is None),
            error_category=err_cat,
        )

        return role

    def answer(self, payload: dict) -> dict:
        """Route the incoming question payload to the correct specialist and return the result."""
        question_id = payload.get("question_id") or "unknown"
        client_id = payload.get("client_id") or ""
        prompt = payload.get("prompt") or ""
        custom_req_id = payload.get("request_id")

        # Start observability request tracing
        rid = self.obs.start_request(
            question_id=question_id,
            client_id=client_id,
            prompt=prompt,
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            request_id=custom_req_id,
        )

        # --- 1. Pre-flight & Security Validation Checks ---
        if not payload.get("question_id"):
            res = self._build_abstention(
                "unknown",
                reason="Missing question_id in request payload."
            )
            self.obs.finish_request(rid, res)
            return res

        if not client_id or not client_id.strip():
            res = self._build_abstention(
                question_id,
                reason="Authoritative client scope (client_id) is missing."
            )
            self.obs.finish_request(rid, res)
            return res

        # Validate client ID exists
        try:
            self.store.client(client_id)
        except KeyError:
            res = self._build_abstention(
                question_id,
                reason=f"Client ID '{client_id}' is not in the client book."
            )
            self.obs.finish_request(rid, res)
            return res

        # Run Security Input Guard & Prompt Injection Scanner
        try:
            clean_payload = self.security.validate_request_payload(payload, request_id=rid)
            prompt = clean_payload["prompt"]
        except PromptInjectionDetectedError as inj_err:
            refusal_res = {
                "question_id": question_id,
                "answer": "",
                "answer_value": None,
                "abstained": False,
                "refused": True,
                "reason": f"Request refused due to security policy constraints: {inj_err}",
                "citations": [],
                "confidence": 1.0,
                "flags": [],
                "agents": ["router", "compliance"]
            }
            self.obs.finish_request(rid, refusal_res)
            return refusal_res
        except InputValidationError as val_err:
            abstention_res = self._build_abstention(question_id, reason=str(val_err))
            self.obs.finish_request(rid, abstention_res)
            return abstention_res

        # --- 2. Determine Specialist ---
        role = self.route_question(question_id, client_id, prompt, request_id=rid)
        logger.info(f"Router directed q_id {question_id} to agent {role}.")

        # --- 3. Delegate to Specialist with Reliability Protection ---
        specialist = self.specialists[role]
        try:
            response = self.reliability.execute(
                specialist.answer,
                args=(question_id, client_id, prompt),
                question_id=question_id,
                client_id=client_id,
                agents=["router", role],
                operation_name=f"specialist_{role}",
                request_id=rid,
            )

            # Ensure routing trace is preserved
            if "agents" not in response or not response["agents"]:
                response["agents"] = ["router", role]
            elif "router" not in response["agents"]:
                response["agents"] = ["router"] + response["agents"]

            # --- 4. Post-Generation Output Sanitization ---
            sanitized_response = self.security.sanitize_response(
                response=response,
                authorized_client_id=client_id,
                request_id=rid,
            )

            self.obs.finish_request(rid, sanitized_response)
            return sanitized_response

        except Exception as e:
            logger.error(f"Orchestrator delegation failed to specialist {role}: {e}", exc_info=True)
            err_response = {
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
            self.obs.finish_request(rid, err_response, error_message=str(e))
            return err_response

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

