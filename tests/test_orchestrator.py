"""
tests/test_orchestrator.py
--------------------------
Unit tests for arbiter.orchestrator.ArbiterOrchestrator.

Verifies construction, routing, specialist isolation, client security,
compliance and advice boundaries, schema contracts, and error handling.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from arbiter.orchestrator import ArbiterOrchestrator, RouteClassification
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.agents.book_qa import AnswerSchema as BookAnswerSchema
from arbiter.agents.kyc_profile import AnswerSchema as KYCAnswerSchema
from arbiter.agents.notes_desk import AnswerSchema as NotesAnswerSchema
from arbiter.agents.market_desk import AnswerSchema as MarketAnswerSchema
from arbiter.agents.compliance import AnswerSchema as ComplianceAnswerSchema

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def store() -> DataStore:
    return DataStore.load(DATA_DIR / "client_book.json", DATA_DIR / "market_data.json")


@pytest.fixture(scope="module")
def config() -> Config:
    return Config(
        book_path=DATA_DIR / "client_book.json",
        market_path=DATA_DIR / "market_data.json",
        llm_base_url="http://localhost:8600/v1",
        _llm_api_key="test-secret-key-orch",
        port=8080
    )


def make_mock_completion(content_str: str) -> ChatCompletion:
    message = ChatCompletionMessage(
        role="assistant",
        content=content_str
    )
    choice = Choice(
        finish_reason="stop",
        index=0,
        message=message
    )
    usage = CompletionUsage(
        completion_tokens=10,
        prompt_tokens=15,
        total_tokens=25
    )
    return ChatCompletion(
        id="chatcmpl-test-orch",
        choices=[choice],
        created=int(time.time()),
        model="valura-fast",
        object="chat.completion",
        usage=usage
    )


# ---------------------------------------------------------------------------
# CONSTRUCTION & SPECIALISTS
# ---------------------------------------------------------------------------

class TestOrchestratorConstruction:
    def test_construction_and_specialists(self, store, config):
        """Orchestrator constructs successfully and registers all specialists."""
        orch = ArbiterOrchestrator(store, config)
        assert "book_qa" in orch.specialists
        assert "kyc_profile" in orch.specialists
        assert "notes_desk" in orch.specialists
        assert "market_desk" in orch.specialists
        assert "compliance" in orch.specialists


# ---------------------------------------------------------------------------
# SPECIALIST ROUTING
# ---------------------------------------------------------------------------

class TestOrchestratorRouting:
    def test_routing_to_specialists(self, store, config):
        """Verifies routing logic dispatches to appropriate specialist agents."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False

        # 1. Book route classification mock
        mock_classification = RouteClassification(specialist="book_qa").model_dump_json()
        mock_book_resp = BookAnswerSchema(
            question_id="q_orch_1",
            answer="Balance is 100 USD",
            answer_value="100.00",
            abstained=False,
            refused=False,
            citations=["client_id"]
        ).model_dump_json()

        mock_client.chat.completions.create.side_effect = [
            make_mock_completion(mock_classification),
            make_mock_completion(mock_book_resp)
        ]

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_1",
                "client_id": "cli_1014",
                "prompt": "What is the cash balance for cli_1014?"
            })
            assert res["agents"] == ["router", "book_qa"]
            assert res["answer_value"] == "100.00"

    def test_advice_deterministic_override(self, store, config):
        """Verifies investment advice is routed to compliance immediately via deterministic overrides."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False

        mock_compliance_resp = ComplianceAnswerSchema(
            question_id="q_orch_2",
            answer="",
            answer_value=None,
            abstained=False,
            refused=True,
            reason="I cannot provide investment advice."
        ).model_dump_json()

        mock_client.chat.completions.create.return_value = make_mock_completion(mock_compliance_resp)

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_2",
                "client_id": "cli_1014",
                "prompt": "Should cli_1014 buy more AAPL?"
            })
            assert res["agents"] == ["router", "compliance"]
            assert res["refused"] is True


# ---------------------------------------------------------------------------
# ISOLATION & SECURITY
# ---------------------------------------------------------------------------

class TestOrchestratorIsolation:
    def test_unknown_client_rejected_preflight(self, store, config):
        """Unknown client is rejected in pre-flight before executing any LLM code."""
        orch = ArbiterOrchestrator(store, config)
        res = orch.answer({
            "question_id": "q_orch_3",
            "client_id": "cli_NONEXISTENT",
            "prompt": "Cash balance?"
        })
        assert res["abstained"] is True
        assert res["answer_value"] is None
        assert "not in the client book" in res["reason"]

    def test_missing_payload_parameters(self, store, config):
        """Malformed requests (missing client_id / question_id) are rejected cleanly."""
        orch = ArbiterOrchestrator(store, config)
        res1 = orch.answer({
            "question_id": "q_orch_4",
            "prompt": "query"
        })
        assert res1["abstained"] is True

        res2 = orch.answer({
            "client_id": "cli_1014",
            "prompt": "query"
        })
        assert res2["abstained"] is True


# ---------------------------------------------------------------------------
# CITATIONS & ERROR PRESERVATION
# ---------------------------------------------------------------------------

class TestOrchestratorContracts:
    def test_api_key_redacted(self, store, config):
        """API key is never exposed in the configuration repr."""
        assert "test-secret-key-orch" not in repr(config)

    def test_kyc_profile_routing(self, store, config):
        """Verifies kyc_profile routing works correctly."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False

        mock_classification = RouteClassification(specialist="kyc_profile").model_dump_json()
        mock_kyc_resp = KYCAnswerSchema(
            question_id="q_orch_kyc",
            answer="PAN is ****249H",
            answer_value="****249H",
            abstained=False,
            refused=False,
            citations=["kyc_1014"]
        ).model_dump_json()

        mock_client.chat.completions.create.side_effect = [
            make_mock_completion(mock_classification),
            make_mock_completion(mock_kyc_resp)
        ]

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_kyc",
                "client_id": "cli_1014",
                "prompt": "What is the PAN for cli_1014?"
            })
            assert res["agents"] == ["router", "kyc_profile"]
            assert res["answer_value"] == "****249H"

    def test_notes_desk_routing(self, store, config):
        """Verifies notes_desk routing works correctly."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False

        mock_classification = RouteClassification(specialist="notes_desk").model_dump_json()
        mock_notes_resp = NotesAnswerSchema(
            question_id="q_orch_notes",
            answer="Client requested LRS limit check",
            answer_value="note_5001",
            abstained=False,
            refused=False,
            citations=["note_5001"]
        ).model_dump_json()

        mock_client.chat.completions.create.side_effect = [
            make_mock_completion(mock_classification),
            make_mock_completion(mock_notes_resp)
        ]

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_notes",
                "client_id": "cli_1001",
                "prompt": "What notes do we have for cli_1001?"
            })
            assert res["agents"] == ["router", "notes_desk"]
            assert res["answer_value"] == "note_5001"

    def test_market_desk_routing(self, store, config):
        """Verifies market_desk routing works correctly."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False

        mock_classification = RouteClassification(specialist="market_desk").model_dump_json()
        mock_mkt_resp = MarketAnswerSchema(
            question_id="q_orch_mkt",
            answer="Price is 190.17",
            answer_value="190.17",
            abstained=False,
            refused=False,
            citations=["AAPL"]
        ).model_dump_json()

        mock_client.chat.completions.create.side_effect = [
            make_mock_completion(mock_classification),
            make_mock_completion(mock_mkt_resp)
        ]

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_mkt",
                "client_id": "cli_1014",
                "prompt": "What was AAPL price on 2026-05-17?"
            })
            assert res["agents"] == ["router", "market_desk"]
            assert res["answer_value"] == "190.17"

    def test_gateway_failure_handling(self, store, config):
        """Verifies that gateway failures result in upstream_issue flag inside orchestrator."""
        orch = ArbiterOrchestrator(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.side_effect = Exception("API connection failure")

        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)

            res = orch.answer({
                "question_id": "q_orch_err",
                "client_id": "cli_1014",
                "prompt": "Factual query"
            })
            assert res["abstained"] is True
            assert "upstream_issue" in res["flags"]

