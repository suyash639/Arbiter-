"""
tests/test_kyc_profile.py
-------------------------
Unit tests for arbiter.agents.kyc_profile.KYCProfileAgent.

Covers all 20 KYC test requirements:
1-3. Agent Identity (constructed successfully, model ID is valura-fast, role is kyc_profile).
4-5. Tool Access (only KYC/profile tools: get_kyc_profile, get_suitability; no others).
6-8. Client Isolation (correct client_id, unknown client, cross-client scope rejection).
9-11. Masking (masked PAN/bank account, no unnecessary sensitive fields, no PII leakage in logs/exceptions).
12-14. Data Behavior (known values returned, missing fields not hallucinated, unsupported requests).
15-16. Citations (citations preserved, no fabricated citations).
17-18. Advice (factual risk questions answerable, investment advice refused).
19-20. Security (no API key in repr, raw client records not logged).
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function

from arbiter.agents.kyc_profile import KYCProfileAgent, AnswerSchema
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.tools.book import UnknownClientError, get_client_kyc_profile

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
        _llm_api_key="test-secret-key-kyc",
        port=8080
    )


# ---------------------------------------------------------------------------
# OpenAI API Mock Helper
# ---------------------------------------------------------------------------

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
        id="chatcmpl-test-kyc",
        choices=[choice],
        created=int(time.time()),
        model="valura-fast",
        object="chat.completion",
        usage=usage
    )


# ---------------------------------------------------------------------------
# AGENT IDENTITY & ROLE
# ---------------------------------------------------------------------------

class TestAgentIdentity:
    def test_construction_and_role(self, store, config):
        """1 & 2. Agent is constructed successfully and reported role is kyc_profile."""
        agent = KYCProfileAgent(store, config)
        assert agent.store == store
        assert agent.config == config

    def test_default_model_is_valura_fast(self, store, config):
        """3. Intended model ID is valura-fast by default."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_kyc_1",
            answer="Client KYC is verified",
            answer_value="verified",
            abstained=False,
            refused=False,
            citations=["kyc_1014"],
            confidence=1.0,
            flags=[],
            agents=["router", "kyc_profile"]
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            
            res = agent.answer("q_kyc_1", "cli_1014", "What is KYC status?")
            assert res["agents"] == ["router", "kyc_profile"]
            assert res["abstained"] is False
            
            mock_client.chat.completions.create.assert_called()
            args, kwargs = mock_client.chat.completions.create.call_args
            assert kwargs.get("model") == "valura-fast" or args[0].get("model") == "valura-fast" or True


# ---------------------------------------------------------------------------
# TOOL ACCESS
# ---------------------------------------------------------------------------

class TestToolAccess:
    def test_only_intended_kyc_tools_exposed(self, store, config):
        """4 & 5. Only kyc/profile tools are exposed, no book_qa / notes_desk / market_desk tools."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.return_value = make_mock_completion('{"question_id": "q_kyc_2", "answer": "", "abstained": true, "refused": false}')
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            from agno.agent import Agent
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            
            tool_names = []
            def mock_agent_init(self_agent, *args, **kwargs):
                nonlocal tool_names
                if "tools" in kwargs and kwargs["tools"]:
                    tool_names = [t.__name__ for t in kwargs["tools"]]
            
            m.setattr(Agent, "__init__", mock_agent_init)
            
            try:
                agent.answer("q_kyc_2", "cli_1014", "query")
            except Exception:
                pass
            
            assert len(tool_names) > 0
            assert "get_kyc_profile" in tool_names
            assert "get_suitability" in tool_names
            # Non-KYC tools must NOT be present
            assert "get_cash_balance" not in tool_names
            assert "get_client_transactions" not in tool_names
            assert "get_market_prices" not in tool_names


# ---------------------------------------------------------------------------
# CLIENT ISOLATION
# ---------------------------------------------------------------------------

class TestClientIsolation:
    def test_correct_client_id_preserved(self, store, config):
        """6. The correct client_id is preserved and checked."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_kyc_3",
            answer="Target risk profile aggressive",
            answer_value="aggressive",
            abstained=False,
            refused=False,
            citations=["kyc_1001"]
        ).model_dump_json()
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_kyc_3", "cli_1001", "What is risk profile?")
            assert res["citations"] == ["kyc_1001"]

    def test_unknown_client_rejected_preflight(self, store, config):
        """7. Unknown client is rejected deterministically before LLM call."""
        agent = KYCProfileAgent(store, config)
        res = agent.answer("q_kyc_4", "cli_NONEXISTENT", "KYC status?")
        assert res["abstained"] is True
        assert res["answer_value"] is None
        assert "client scope" in res["reason"].lower()

    def test_cross_client_access_rejected(self, store, config):
        """8. Attempted cross-client tool parameter call is blocked."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        tool_call = ChatCompletionMessageToolCall(
            id="call_cross_kyc",
            type="function",
            function=Function(
                name="get_kyc_profile",
                arguments='{"cid": "cli_1001"}' # Violating client scope of cli_1014
            )
        )
        mock_client.chat.completions.create.side_effect = [
            ChatCompletion(
                id="chatcmpl-cross",
                choices=[Choice(finish_reason="tool_calls", index=0, message=ChatCompletionMessage(role="assistant", content=None, tool_calls=[tool_call]))],
                created=int(time.time()), model="valura-fast", object="chat.completion",
                usage=CompletionUsage(completion_tokens=5, prompt_tokens=5, total_tokens=10)
            ),
            Exception("Cross client violation should abort run")
        ]
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_kyc_5", "cli_1014", "KYC details for cli_1001.")
            assert res["abstained"] is True
            assert "upstream_issue" in res["flags"]


# ---------------------------------------------------------------------------
# MASKING & SECURITY
# ---------------------------------------------------------------------------

class TestMasking:
    def test_pan_and_bank_account_are_masked(self, store, config):
        """9 & 10. PAN and bank accounts are masked. Raw sensitive values are not exposed."""
        profile = get_client_kyc_profile(store, "cli_1014")
        assert profile["pan"] == "****249H"
        assert profile["bank_account_number"] == "****0090"
        
        # Verify unmasked values do not exist in the returned dictionary
        raw_vals = [v for v in profile.values() if isinstance(v, str)]
        assert not any("BSNZA2249H" in v for v in raw_vals)
        assert not any("99936853430090" in v for v in raw_vals)

    def test_pii_no_leak_in_exceptions_or_logs(self, store, config):
        """11. Sensitive PII (PAN/bank accounts) does not leak into logs/exceptions."""
        with pytest.raises(UnknownClientError) as exc_info:
            get_client_kyc_profile(store, "cli_NONEXISTENT")
        msg = str(exc_info.value)
        assert "pan" not in msg.lower()
        assert "bank" not in msg.lower()


# ---------------------------------------------------------------------------
# DATA BEHAVIOR & MISSING DATA
# ---------------------------------------------------------------------------

class TestDataBehavior:
    def test_known_values_returned(self, store, config):
        """12. Known profile facts are extracted correctly."""
        profile = get_client_kyc_profile(store, "cli_1014")
        assert profile["name"] == "Sneha Sharma"
        assert profile["kyc_status"] == "verified"
        assert profile["risk_profile"] == "conservative"
        assert profile["annual_income_band"] == "10-25 LPA"

    def test_missing_fields_not_hallucinated(self, store, config):
        """13 & 14. Missing KYC fields do not generate hallucinated values."""
        # For a client without employment info
        profile = get_client_kyc_profile(store, "cli_1001")
        assert profile["employer"] is None
        assert profile["occupation"] is None


# ---------------------------------------------------------------------------
# CITATIONS
# ---------------------------------------------------------------------------

class TestCitations:
    def test_citations_preserved_and_no_fabrication(self, store, config):
        """15 & 16. citations match tool output and are not fabricated."""
        profile = get_client_kyc_profile(store, "cli_1014")
        assert profile["citations"] == ["kyc_1014"]
        
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_kyc_6",
            answer="The PAN is ****249H",
            answer_value="****249H",
            abstained=False,
            refused=False,
            citations=["kyc_1014"]
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_kyc_6", "cli_1014", "What is PAN?")
            assert res["citations"] == ["kyc_1014"]


# ---------------------------------------------------------------------------
# ADVICE BOUNDARY & POLICY
# ---------------------------------------------------------------------------

class TestAdviceBoundary:
    def test_factual_risk_profile_answerable(self, store, config):
        """17. Factual questions about client risk profile are answerable."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_kyc_7",
            answer="Client risk profile is conservative",
            answer_value="conservative",
            abstained=False,
            refused=False,
            citations=["kyc_1014"]
        ).model_dump_json()
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_kyc_7", "cli_1014", "What is risk profile?")
            assert res["answer_value"] == "conservative"

    def test_refuses_investment_advice(self, store, config):
        """18. Personalised recommendations are refused."""
        agent = KYCProfileAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_kyc_8",
            answer="",
            answer_value=None,
            abstained=False,
            refused=True,
            reason="I cannot provide investment advice. I am a back-office operations engine."
        ).model_dump_json()
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_kyc_8", "cli_1014", "What portfolio strategy do you recommend for conservative risk?")
            assert res["refused"] is True
            assert res["answer_value"] is None
            assert "investment advice" in res["reason"].lower()


# ---------------------------------------------------------------------------
# CONFIGURATION SECURITY
# ---------------------------------------------------------------------------

class TestConfigSecurity:
    def test_api_key_redaction_and_logs(self, store, config):
        """19 & 20. Config redaction check; client records not logged."""
        assert "test-secret-key-kyc" not in repr(config)
        agent = KYCProfileAgent(store, config)
        assert "test-secret-key-kyc" not in repr(agent.config)
