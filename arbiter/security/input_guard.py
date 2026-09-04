"""
arbiter/security/input_guard.py
-------------------------------
Input sanitization and deterministic prompt injection defense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from arbiter.security.errors import InputValidationError, PromptInjectionDetectedError


MAX_PROMPT_LENGTH = 10_000
MAX_ID_LENGTH = 64


# High-confidence injection and system extraction patterns
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(dan|jailbreak|unrestricted|god)\s+mode", re.IGNORECASE),
    re.compile(r"(print|reveal|output|dump|show)\s+(your\s+)?(hidden\s+)?(system\s+prompt|system\s+instructions)", re.IGNORECASE),
    re.compile(r"(reveal|print|show|dump)\s+(the\s+)?(api_?key|gemini_api_key|openai_api_key|secret)", re.IGNORECASE),
    re.compile(r"you\s+are\s+no\s+longer\s+a\s+back-office\s+operations\s+engine", re.IGNORECASE),
    re.compile(r"act\s+as\s+an\s+unrestricted\s+financial\s+advisor", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?(security|guardrails|safety|compliance)\s+rules", re.IGNORECASE),
    re.compile(r"forget\s+all\s+(your\s+)?(rules|constraints)", re.IGNORECASE),
]


@dataclass(frozen=True)
class InjectionScanResult:
    """Result of an injection pattern scan."""

    is_injection: bool
    reason: Optional[str] = None
    pattern_matched: Optional[str] = None


class InputGuard:
    """Validates, sanitizes, and inspects incoming user requests."""

    @classmethod
    def sanitize_string(cls, text: str, max_length: int = MAX_PROMPT_LENGTH, field_name: str = "prompt") -> str:
        """Sanitize text by stripping null bytes, normalizing whitespace, and checking length limits."""
        if not isinstance(text, str):
            raise InputValidationError(f"Field '{field_name}' must be a string.")

        # Strip null bytes and control chars (except standard whitespace \n, \r, \t)
        cleaned = "".join(ch for ch in text if ch == "\t" or ch == "\n" or ch == "\r" or ord(ch) >= 32)
        cleaned = cleaned.strip()

        if not cleaned:
            raise InputValidationError(f"Field '{field_name}' cannot be empty.")

        if len(cleaned) > max_length:
            raise InputValidationError(
                f"Field '{field_name}' exceeds maximum permitted length of {max_length} characters (got {len(cleaned)})."
            )

        return cleaned

    @classmethod
    def scan_for_prompt_injection(cls, prompt: str) -> InjectionScanResult:
        """Scan prompt for explicit prompt injection, jailbreaks, or exfiltration heuristics."""
        if not prompt:
            return InjectionScanResult(is_injection=False)

        for pattern in INJECTION_PATTERNS:
            match = pattern.search(prompt)
            if match:
                matched_str = match.group(0)
                return InjectionScanResult(
                    is_injection=True,
                    reason=f"Prompt contains prohibited injection pattern: '{matched_str}'",
                    pattern_matched=matched_str,
                )

        return InjectionScanResult(is_injection=False)
