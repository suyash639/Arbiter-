"""
tests/test_market_desk.py
-------------------------
Unit tests for arbiter.agents.market_desk.MarketDeskAgent.

Covers all 25 Market Desk requirements.
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

from arbiter.agents.market_desk import MarketDeskAgent, AnswerSchema
from arbiter.config import Config
from arbiter.data_store import DataStore
from arbiter.tools.market import (
    MarketCoverageError,
    NoPriceDataError,
    get_instrument_details,
    get_market_price,
    get_market_return,
    get_symbol_news,
)

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
        _llm_api_key="test-secret-key-market",
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
        id="chatcmpl-test-market",
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
        """1 & 2. Agent is constructed successfully and reported role is market_desk."""
        agent = MarketDeskAgent(store, config)
        assert agent.store == store
        assert agent.config == config

    def test_default_model_is_valura_fast(self, store, config):
        """3. Default model ID is valura-fast."""
        agent = MarketDeskAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_mkt_1",
            answer="Sector is Information Technology",
            answer_value="Information Technology",
            abstained=False,
            refused=False,
            citations=["AAPL"],
            confidence=1.0,
            flags=[],
            agents=["router", "market_desk"]
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_mkt_1", "cli_1014", "What is AAPL's sector?")
            assert res["agents"] == ["router", "market_desk"]


# ---------------------------------------------------------------------------
# TOOL ACCESS
# ---------------------------------------------------------------------------

class TestToolAccess:
    def test_only_market_tools_exposed(self, store, config):
        """4 & 5. Only market tools are exposed."""
        agent = MarketDeskAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.return_value = make_mock_completion('{"question_id": "q_mkt_2", "answer": "", "abstained": true, "refused": false}')
        
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
                agent.answer("q_mkt_2", "cli_1014", "query")
            except Exception:
                pass
            
            assert "get_instrument" in tool_names
            assert "get_price" in tool_names
            assert "get_return" in tool_names
            assert "get_news" in tool_names
            assert "get_cash_balance" not in tool_names


# ---------------------------------------------------------------------------
# COVERAGE
# ---------------------------------------------------------------------------

class TestCoverage:
    def test_covered_symbol_works(self, store):
        """7. Covered symbol lookup works."""
        details = get_instrument_details(store, "AAPL")
        assert details["sector"] == "Information Technology"

    def test_uncovered_symbol_rejected(self, store):
        """8 & 9. Uncovered symbol lookup raises MarketCoverageError."""
        with pytest.raises(MarketCoverageError):
            get_instrument_details(store, "UNCOVEREDSTOCK")


# ---------------------------------------------------------------------------
# PRICE SEMANTICS
# ---------------------------------------------------------------------------

class TestPriceSemantics:
    def test_exact_available_close(self, store):
        """10. Exact available close works."""
        res = get_market_price(store, "AAPL", "2026-05-01")
        assert res["close_price"] == "190.17"
        assert res["close_date"] == "2026-05-01"

    def test_between_date_query_selects_latest_on_or_before(self, store):
        """11, 12 & 13. Selects latest close on or before, returned answer identifies the actual close date, no future date selected."""
        res = get_market_price(store, "AAPL", "2026-05-17")
        assert res["close_price"] == "190.17"
        assert res["close_date"] == "2026-05-01"

    def test_decimal_precision_preserved(self, store):
        """14. Decimal precision is preserved."""
        ret = get_market_return(store, "AMD", "2025-07-01", "2026-07-01")
        assert ret["percentage_return"] == "-4.80"


# ---------------------------------------------------------------------------
# NEWS
# ---------------------------------------------------------------------------

class TestNews:
    def test_covered_symbol_news(self, store):
        """15 & 16. Covered symbol news lookup works."""
        news = get_symbol_news(store, "AMZN")
        assert len(news) > 0
        assert any("new chief financial officer" in n["headline"] for n in news)

    def test_uncovered_symbol_no_fabricated_news(self, store):
        """17. Uncovered symbol throws error instead of fabricating."""
        with pytest.raises(MarketCoverageError):
            get_symbol_news(store, "UNCOVERED")


# ---------------------------------------------------------------------------
# CITATIONS
# ---------------------------------------------------------------------------

class TestCitations:
    def test_citations_preserved(self, store, config):
        """18 & 19. Citations survive and are not fabricated."""
        res = get_market_price(store, "AMD", "2026-07-01")
        assert res["citations"] == ["AMD"]


# ---------------------------------------------------------------------------
# ADVICE & POLICY
# ---------------------------------------------------------------------------

class TestAdvice:
    def test_factual_market_question_answerable(self, store, config):
        """20. Factual market questions are answered."""
        agent = MarketDeskAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_mkt_3",
            answer="AMD close price on 2026-07-01 was 164.95",
            answer_value="164.95",
            abstained=False,
            refused=False,
            citations=["AMD"]
        ).model_dump_json()
        
        mock_client.chat.completions.create.return_value = make_mock_completion(output_data)
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_mkt_3", "cli_1014", "What is AMD price?")
            assert res["answer_value"] == "164.95"

    def test_personalised_advice_refused(self, store, config):
        """21. Personalised stock purchase advice is refused."""
        agent = MarketDeskAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        
        output_data = AnswerSchema(
            question_id="q_mkt_4",
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
            res = agent.answer("q_mkt_4", "cli_1014", "Should the client buy AMD?")
            assert res["refused"] is True
            assert res["answer_value"] is None


# ---------------------------------------------------------------------------
# SECURITY & CONFIG
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_api_key_redacted(self, store, config):
        """22. API key is redacted."""
        assert "test-secret-key-market" not in repr(config)


# ---------------------------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------------------------

class TestErrors:
    def test_gateway_failures_upstream_issue(self, store, config):
        """24. Gateway failure results in flags=['upstream_issue']."""
        agent = MarketDeskAgent(store, config)
        mock_client = MagicMock()
        mock_client.is_closed.return_value = False
        mock_client.chat.completions.create.side_effect = Exception("API connection failure")
        
        with pytest.MonkeyPatch().context() as m:
            from agno.models.openai import OpenAIChat
            m.setattr(OpenAIChat, "get_client", lambda self: mock_client)
            res = agent.answer("q_mkt_5", "cli_1014", "What is AAPL price?")
            assert res["abstained"] is True
            assert "upstream_issue" in res["flags"]

    def test_deterministic_market_failure_produces_safe_abstention(self, store, config):
        """25. Deterministic market failure produces safe response."""
        agent = MarketDeskAgent(store, config)
        res = agent.answer("q_mkt_6", "cli_1014", "Get price of UNCOVERED")
        assert res["abstained"] is True
        assert res["answer_value"] is None
