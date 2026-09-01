"""
arbiter/observability/redaction.py
---------------------------------
Sanitization and PII redaction engine for logs, traces, and telemetry.
"""

from __future__ import annotations

import re
from typing import Any

# Regex patterns for detecting sensitive data
PAN_REGEX = re.compile(r"\b([A-Z]{5})([0-9]{4})([A-Z])\b")
BANK_ACC_REGEX = re.compile(r"\b(\d{5,14})(\d{4})\b")
API_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)(bearer|key|token|api_key)[\s:=]+([a-zA-Z0-9_\-\.]{12,})"),
]
SENSITIVE_FIELD_NAMES = {
    "api_key", "_llm_api_key", "gemini_api_key", "google_api_key",
    "password", "secret", "token", "authorization"
}


class RedactionEngine:
    """Sanitizes text, parameters, and telemetry structures before persistence or logging."""

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redact sensitive PII and API keys from arbitrary text."""
        if not text or not isinstance(text, str):
            return text

        sanitized = text

        # 1. Mask API keys
        for pat in API_KEY_PATTERNS:
            sanitized = pat.sub("[REDACTED_SECRET]", sanitized)

        # 2. Mask PAN: replace first 6 characters with **** (e.g. ABCDE1234F -> ****234F)
        def _mask_pan(match: re.Match) -> str:
            full = match.group(0)
            return f"****{full[-4:]}"

        sanitized = PAN_REGEX.sub(_mask_pan, sanitized)

        # 3. Mask Bank Account: replace leading digits with **** (e.g. 1234567890 -> ****7890)
        def _mask_bank(match: re.Match) -> str:
            last4 = match.group(2)
            return f"****{last4}"

        sanitized = BANK_ACC_REGEX.sub(_mask_bank, sanitized)

        return sanitized

    @classmethod
    def redact_value(cls, val: Any) -> Any:
        """Recursively redact strings, lists, and dicts."""
        if isinstance(val, str):
            return cls.redact_text(val)
        if isinstance(val, dict):
            return {
                k: ("[REDACTED]" if str(k).lower() in SENSITIVE_FIELD_NAMES else cls.redact_value(v))
                for k, v in val.items()
            }
        if isinstance(val, (list, tuple)):
            return [cls.redact_value(item) for item in val]
        return val

    @classmethod
    def sanitize_tool_args(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Sanitize and mask tool call input arguments."""
        return cls.redact_value(kwargs)

    @classmethod
    def sanitize_tool_result(cls, result: Any, max_string_len: int = 300) -> Any:
        """Produce a safe, concise summary of a tool execution result."""
        if result is None:
            return None

        # Redact any PII first
        redacted = cls.redact_value(result)

        # Summarize large list responses (e.g. all transactions) rather than dumping 50KB into logs
        if isinstance(redacted, list):
            item_count = len(redacted)
            if item_count > 3:
                sample = redacted[:2]
                return {
                    "item_count": item_count,
                    "sample": sample,
                    "truncated": True,
                }
            return redacted

        if isinstance(redacted, dict):
            # If dictionary contains large raw arrays, summarize them
            compact: dict[str, Any] = {}
            for k, v in redacted.items():
                if isinstance(v, list) and len(v) > 3:
                    compact[k] = f"list(len={len(v)})"
                elif isinstance(v, str) and len(v) > max_string_len:
                    compact[k] = f"{v[:max_string_len]}... [truncated]"
                else:
                    compact[k] = v
            return compact

        if isinstance(redacted, str) and len(redacted) > max_string_len:
            return f"{redacted[:max_string_len]}... [truncated]"

        return redacted
