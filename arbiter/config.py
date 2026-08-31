"""
arbiter/config.py
-----------------
Centralised, typed configuration for Arbiter.

Reads environment variables:

    BOOK_PATH      Path to data/client_book.json   (default: data/client_book.json)
    MARKET_PATH    Path to data/market_data.json   (default: data/market_data.json)
    LLM_PROVIDER   Provider name: 'gemini' | 'valura' | 'openai' (default: 'valura' or 'gemini')
    LLM_MODEL      Model name: e.g. 'gemini-2.0-flash' or 'valura-fast'
    GEMINI_API_KEY API key for Gemini OpenAI-compatible backend
    LLM_BASE_URL   Base URL of the LLM gateway / OpenAI-compatible endpoint
    LLM_API_KEY    API key sent to the gateway / endpoint
    PORT           TCP port the service listens on (default: 8080)

Rules:
- BOOK_PATH and MARKET_PATH must point to existing files at config creation time.
- LLM_API_KEY and GEMINI_API_KEY are stored but NEVER printed, logged, or serialised.
- Config is a plain dataclass -- no FastAPI dependency -- so tests can build it directly.
- Use Config.from_env() for production; build Config(...) directly in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    """Raised when the configuration is invalid or required fields are absent."""


@dataclass(frozen=True)
class Config:
    """Immutable configuration snapshot.

    Build via ``Config.from_env()`` in production.
    Construct directly in tests to avoid environment pollution.
    """

    # --- data paths --------------------------------------------------------
    book_path: Path
    market_path: Path

    # --- gateway / model options -------------------------------------------
    llm_base_url: str
    # LLM_API_KEY is intentionally stored in a private attribute and
    # excluded from __repr__ / __str__ so it never leaks into logs.
    _llm_api_key: str = field(repr=False, compare=False)

    # --- server ------------------------------------------------------------
    port: int = 8080

    # --- provider & model abstraction --------------------------------------
    llm_provider: str = "valura"
    llm_model: str = "valura-fast"

    # ------------------------------------------------------------------
    # Public accessor (allows the gateway client to read the key without
    # the caller needing to know the internal attribute name).
    # ------------------------------------------------------------------
    @property
    def llm_api_key(self) -> str:
        return self._llm_api_key  # noqa: SLF001

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> "Config":
        """Build a Config from the process environment and optional .env file.

        Raises ConfigError if any required variable is absent or if
        BOOK_PATH / MARKET_PATH do not exist on disk.
        """
        if "PYTEST_CURRENT_TEST" not in os.environ or env_file:
            try:
                from dotenv import load_dotenv
                if env_file:
                    load_dotenv(dotenv_path=env_file, override=False)
                else:
                    load_dotenv(override=False)
            except ImportError:
                pass

        book_path = cls._require_path("BOOK_PATH", "data/client_book.json")
        market_path = cls._require_path("MARKET_PATH", "data/market_data.json")

        provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()

        if provider == "gemini" or (not provider and gemini_key):
            llm_provider = "gemini"
            llm_base_url = os.environ.get("LLM_BASE_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/openai/"
            llm_api_key = gemini_key or os.environ.get("LLM_API_KEY", "").strip() or "local-dev"
            llm_model = os.environ.get("LLM_MODEL", "").strip() or "gemini-2.0-flash"
        else:
            llm_provider = provider or "valura"
            llm_base_url = os.environ.get("LLM_BASE_URL", "").strip()
            if not llm_base_url:
                llm_base_url = "http://localhost:8600/v1"
            llm_api_key = os.environ.get("LLM_API_KEY", "").strip()
            if not llm_api_key:
                llm_api_key = "local-dev"
            llm_model = os.environ.get("LLM_MODEL", "").strip() or "valura-fast"

        try:
            port = int(os.environ.get("PORT", "8080"))
        except ValueError as exc:
            raise ConfigError(
                f"PORT environment variable is not a valid integer: "
                f"{os.environ.get('PORT')!r}"
            ) from exc

        if not (0 < port <= 65535):
            raise ConfigError(
                f"PORT environment variable is out of range [1, 65535]: {port}"
            )

        return cls(
            book_path=book_path,
            market_path=market_path,
            llm_base_url=llm_base_url,
            _llm_api_key=llm_api_key,
            port=port,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _require_path(env_var: str, default: str) -> Path:
        """Resolve an env-var to an absolute Path and verify it exists."""
        raw = os.environ.get(env_var, default).strip()
        if not raw:
            raise ConfigError(
                f"Environment variable {env_var!r} is required but was not set."
            )
        p = Path(raw)
        if not p.is_absolute():
            # Resolve relative paths against the current working directory so
            # that the caller can run from anywhere inside the project tree.
            p = Path.cwd() / p
        if not p.exists():
            raise ConfigError(
                f"Path referenced by {env_var!r} does not exist: {p}"
            )
        if not p.is_file():
            raise ConfigError(
                f"Path referenced by {env_var!r} is not a file: {p}"
            )
        return p.resolve()

    # ------------------------------------------------------------------
    # Safe string representations (key is always redacted)
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # noqa: D105
        return (
            f"Config("
            f"book_path={self.book_path!r}, "
            f"market_path={self.market_path!r}, "
            f"llm_base_url={self.llm_base_url!r}, "
            f"llm_api_key=<REDACTED>, "
            f"port={self.port!r}, "
            f"llm_provider={self.llm_provider!r}, "
            f"llm_model={self.llm_model!r})"
        )
