"""
tests/conftest.py
-----------------
Pytest configuration and production-grade test isolation fixtures.

Guarantees:
1. Pure in-memory execution for unit tests: blocks unmocked real network calls
   to localhost:8600 or external APIs so tests fail-fast instantly without
   waiting for 15s TCP socket timeouts.
2. Fast-forwards backoff sleeps during test retries so retry tests execute in milliseconds.
3. Provides reusable fixtures for DataStore and Config.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from arbiter.config import Config
from arbiter.data_store import DataStore

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture(scope="session")
def store() -> DataStore:
    return DataStore.load(DATA_DIR / "client_book.json", DATA_DIR / "market_data.json")


@pytest.fixture
def config() -> Config:
    return Config(
        book_path=DATA_DIR / "client_book.json",
        market_path=DATA_DIR / "market_data.json",
        llm_base_url="http://localhost:8600/v1",
        _llm_api_key="test-secret-key-mock",
        llm_provider="valura",
        llm_model="valura-fast",
    )


def make_mock_completion(content_str: str) -> ChatCompletion:
    """Helper creating a mock ChatCompletion response."""
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
        id="chatcmpl-test-conftest",
        choices=[choice],
        created=int(time.time()),
        model="valura-fast",
        object="chat.completion",
        usage=usage
    )


@pytest.fixture(autouse=True)
def fast_retry_sleep(monkeypatch):
    """Automatically mock backoff sleeps during retry loops while preserving real time.sleep."""
    from arbiter.reliability import retry
    monkeypatch.setattr(retry, "default_sleep", lambda _: None)




@pytest.fixture(autouse=True)
def isolate_unmocked_gateway_network(monkeypatch, request):
    """Prevent unmocked tests from waiting 15s for inactive localhost:8600 TCP sockets.

    If a test does not monkeypatch OpenAIChat.get_client, this fixture ensures
    un-mocked gateway requests fail immediately with a clean connection error (0ms)
    rather than waiting on OS socket timeouts.
    """
    if "live_api" in request.keywords:
        return

    import openai
    from agno.models.openai import OpenAIChat

    original_get_client = OpenAIChat.get_client

    def fast_mock_or_fail(self_model):
        # If the test already assigned a mock client, return it
        if hasattr(self_model, "client") and isinstance(self_model.client, MagicMock):
            return self_model.client

        # Create a fast-fail mock client that raises APIConnectionError instantly with 0 delay
        mock = MagicMock()
        mock.is_closed.return_value = False

        class FastMockCompletions:
            def create(self, *args, **kwargs):
                raise openai.APIConnectionError(
                    message="Fast test isolation: localhost:8600 gateway is not running.",
                    request=None,
                )

        mock.chat.completions = FastMockCompletions()
        return mock

    monkeypatch.setattr(OpenAIChat, "get_client", fast_mock_or_fail)
