"""
arbiter/security/output_guard.py
--------------------------------
Post-generation output validation, PII leakage detection, and cross-client citation sanitization.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from arbiter.observability.redaction import RedactionEngine
from arbiter.security.errors import OutputSecurityViolationError


# Regex patterns detecting unmasked PANs (e.g. ABCDE1234F not preceded by ****)
UNMASKED_PAN_PATTERN = re.compile(r"(?<!\*)[A-Z]{5}[0-9]{4}[A-Z](?!\*)")
# Regex detecting unmasked bank accounts (9 to 18 digits not preceded by ****)
UNMASKED_BANK_PATTERN = re.compile(r"(?<!\*)\b[0-9]{9,18}\b(?!\*)")
# Regex detecting potential client identifiers
CLIENT_ID_PATTERN = re.compile(r"\bcli_[0-9]{4}\b")


class OutputGuard:
    """Validates and sanitizes model output envelopes prior to returning to the caller."""

    @classmethod
    def sanitize_output(
        cls,
        response: Dict[str, Any],
        authorized_client_id: Optional[str] = None,
        on_security_event: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Verify and sanitize final AnswerSchema dictionary."""
        if not isinstance(response, dict):
            raise OutputSecurityViolationError(f"Response must be a dict, got {type(response).__name__}")

        sanitized = dict(response)

        # 1. PII and Secret Sanitization on Text Fields
        for field in ("answer", "answer_value", "reason"):
            val = sanitized.get(field)
            if isinstance(val, str) and val:
                # Check for unmasked PANs
                if UNMASKED_PAN_PATTERN.search(val):
                    sanitized[field] = RedactionEngine.redact_text(val)
                    if on_security_event:
                        on_security_event("pii_redaction", field=field, pii_type="unmasked_pan")

                # Check for unmasked Bank Accounts
                if UNMASKED_BANK_PATTERN.search(val):
                    sanitized[field] = RedactionEngine.redact_text(val)
                    if on_security_event:
                        on_security_event("pii_redaction", field=field, pii_type="unmasked_bank_account")

                # Check for API keys / Secrets
                if any(k in val.lower() for k in ("sk-", "api_key", "secret-key")):
                    sanitized[field] = RedactionEngine.redact_text(val)
                    if on_security_event:
                        on_security_event("secret_leak_prevented", field=field)

        # 2. Citation Scope Verification
        if authorized_client_id and "citations" in sanitized and isinstance(sanitized["citations"], list):
            valid_citations: List[str] = []
            for cit in sanitized["citations"]:
                if isinstance(cit, str):
                    # Check if citation is an unauthorized client ID
                    if cit.startswith("cli_") and cit != authorized_client_id:
                        if on_security_event:
                            on_security_event(
                                "cross_client_access_attempt",
                                authorized_client_id=authorized_client_id,
                                attempted_citation=cit,
                            )
                        # Omit unauthorized client citation
                        continue
                    valid_citations.append(cit)
            sanitized["citations"] = valid_citations

        return sanitized
