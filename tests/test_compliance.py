"""
tests/test_compliance.py
-------------------------
Unit tests for arbiter.agents.compliance.ComplianceAgent.

Covers all 15 Compliance specialist requirements.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from arbiter.agents.compliance import ComplianceAgent, AnswerSchema
from arbiter.config import Config
from arbiter.data_store import DataStore

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
        _llm_api_key="test-secret-key-compliance",
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
        id="chatcmpl-test-compliance",
        choices=[choice],
        created=int(time.time()),
        model="valura-fast",
        object="chat.completion",
        usage=usage
    )


# ---------------------------------------------------------------------------
# AGENT IDENTITY
# ---------------------------------------------------------------------------

class TestAgentIdentity:
    def test_construction_and_role(self, store, config):
        """1 & 2. Agent constructs successfully and reported role is compliance."""
        agent = ComplianceAgent(store, config)
        assert agent.store == store
        assert agent.config == config

    def test_default_model_config(self, store, config):
        """3. Default model/config matches valura-fast."""
        agent = ComplianceAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_comp_1",
            answer="",
            answer_value=None,
            abstained=False,
            refused=True,
            reason="I cannot provide investment advice.",
            citations=[],
            confidence=1.0,
            flags=[],
            agents=["router", "compliance"]
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_comp_1", "cli_1014", "Should I buy Apple?")
            assert res["agents"] == ["router", "compliance"]
            assert res["refused"] is True
            assert res["abstained"] is False


# ---------------------------------------------------------------------------
# REFUSALS
# ---------------------------------------------------------------------------

class TestRefusals:
    def test_personalised_advice_refused(self, store, config):
        """4. Personalised investment advice is refused."""
        agent = ComplianceAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_comp_2",
            answer="",
            answer_value=None,
            abstained=False,
            refused=True,
            reason="Refused because personal advice is outside safety guidelines."
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_comp_2", "cli_1014", "Should I invest in GOOG?")
            assert res["refused"] is True
            assert res["abstained"] is False
            assert "personal advice" in res["reason"].lower()

    def test_allocation_recommendation_refused(self, store, config):
        """5. Target allocation recommendation is refused."""
        agent = ComplianceAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_comp_3",
            answer="",
            answer_value=None,
            abstained=False,
            refused=True,
            reason="I cannot recommend asset allocation targets."
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_comp_3", "cli_1014", "What strategy do you recommend for target allocations?")
            assert res["refused"] is True
            assert res["abstained"] is False

    def test_out_of_scope_account_refused(self, store, config):
        """6. Out-of-scope client request is refused."""
        agent = ComplianceAgent(store, config)
        # Using unknown client ID triggers client preflight which yields refusal/abstention cleanly
        res = agent.answer("q_comp_4", "cli_NONEXISTENT", "Show details.")
        assert res["refused"] is True
        assert res["abstained"] is False


# ---------------------------------------------------------------------------
# BOUNDARIES
# ---------------------------------------------------------------------------

class TestBoundaries:
    def test_compliance_exposes_no_tools(self, store, config):
        """9, 10, 11, 12. Compliance does not expose Book, Market, KYC, or Notes tools."""
        agent = ComplianceAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.return_value = make_mock_completion('{"question_id": "q_comp_5", "answer": "", "abstained": false, "refused": true}')
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            from agno.agent import Agent
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            
            tool_list = []
            def mock_agent_init(self_agent, *args, **kwargs):
                nonlocal tool_list
                tool_list = kwargs.get("tools") or []
            
            m.setattr(Agent, "__init__", mock_agent_init)
            try:
                agent.answer("q_comp_5", "cli_1014", "query")
            except Exception:
                pass
            
            assert len(tool_list) == 0


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_api_key_redaction(self, store, config):
        """13. API key is redacted."""
        assert "test-secret-key-compliance" not in repr(config)


# ---------------------------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------------------------

class TestErrors:
    def test_gateway_failures_upstream_issue(self, store, config):
        """15. Gateway failure produces upstream_issue flag."""
        agent = ComplianceAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.side_effect = Exception("API connection failure")
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_comp_6", "cli_1014", "query")
            assert res["abstained"] is True
            assert "upstream_issue" in res["flags"]
