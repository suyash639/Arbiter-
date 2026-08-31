"""
tests/test_config.py
--------------------
Unit tests for arbiter.config.Config.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from arbiter.config import Config, ConfigError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
BOOK = Path("data/client_book.json").resolve()
MARKET = Path("data/market_data.json").resolve()


def _make_config(**overrides) -> Config:
    """Build a Config directly (no environment required)."""
    defaults = dict(
        book_path=BOOK,
        market_path=MARKET,
        llm_base_url="http://localhost:8600/v1",
        _llm_api_key="test-key",
        port=8080,
    )
    defaults.update(overrides)
    return Config(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestConfigDirectConstruction:
    def test_builds_successfully(self):
        cfg = _make_config()
        assert cfg.book_path == BOOK
        assert cfg.market_path == MARKET
        assert cfg.llm_base_url == "http://localhost:8600/v1"
        assert cfg.port == 8080

    def test_api_key_accessible_via_property(self):
        cfg = _make_config()
        assert cfg.llm_api_key == "test-key"

    def test_repr_does_not_contain_api_key(self):
        cfg = _make_config()
        r = repr(cfg)
        assert "test-key" not in r
        assert "<REDACTED>" in r

    def test_config_is_immutable(self):
        cfg = _make_config()
        with pytest.raises((AttributeError, TypeError)):
            cfg.port = 9999  # type: ignore[misc]


class TestConfigFromEnv:
    def test_from_env_resolves_defaults(self, monkeypatch):
        """from_env() should succeed with no env vars set, falling back to local defaults."""
        monkeypatch.delenv("BOOK_PATH", raising=False)
        monkeypatch.delenv("MARKET_PATH", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("PORT", raising=False)
        # Change CWD to the project root so relative defaults resolve.
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert cfg.book_path.exists()
        assert cfg.market_path.exists()
        assert cfg.port == 8080

    def test_from_env_reads_custom_port(self, monkeypatch):
        monkeypatch.setenv("PORT", "9090")
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert cfg.port == 9090

    def test_from_env_bad_port_raises(self, monkeypatch):
        monkeypatch.setenv("PORT", "not-a-number")
        monkeypatch.chdir(Path(__file__).parent.parent)
        with pytest.raises(ConfigError, match="not a valid integer"):
            Config.from_env()

    def test_from_env_out_of_range_port_raises(self, monkeypatch):
        monkeypatch.chdir(Path(__file__).parent.parent)
        for bad_port in ["0", "-100", "65536"]:
            monkeypatch.setenv("PORT", bad_port)
            with pytest.raises(ConfigError, match="out of range"):
                Config.from_env()

    def test_from_env_missing_book_path_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv("BOOK_PATH", str(tmp_path / "nonexistent.json"))
        with pytest.raises(ConfigError, match="does not exist"):
            Config.from_env()

    def test_from_env_key_is_redacted_in_repr(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "super-secret-key-xyz")
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert "super-secret-key-xyz" not in repr(cfg)
        assert "<REDACTED>" in repr(cfg)

    def test_from_env_gemini_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret-123")
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert cfg.llm_provider == "gemini"
        assert cfg.llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
        assert cfg.llm_api_key == "gemini-secret-123"
        assert cfg.llm_model == "gemini-2.0-flash"
        assert "gemini-secret-123" not in repr(cfg)

    def test_from_env_gemini_custom_model(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret-456")
        monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert cfg.llm_provider == "gemini"
        assert cfg.llm_model == "gemini-1.5-flash"

    def test_from_env_google_api_key_detection(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-secret-789")
        monkeypatch.chdir(Path(__file__).parent.parent)
        cfg = Config.from_env()
        assert cfg.llm_provider == "gemini"
        assert cfg.llm_api_key == "google-secret-789"
        assert cfg.llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"

