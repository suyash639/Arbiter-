"""
arbiter/security/errors.py
--------------------------
Deterministic exception hierarchy for the Arbiter Security subsystem.
"""

from __future__ import annotations


class SecurityError(ValueError):
    """Base exception for all security policy and boundary violations."""


class InputValidationError(SecurityError):
    """Raised when an incoming user request fails format, length, or character sanitization."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Input validation error: {details}")
        self.details = details


class PromptInjectionDetectedError(SecurityError):
    """Raised when a user prompt matches explicit jailbreak, instruction override, or exfiltration patterns."""

    def __init__(self, reason: str = "Prompt injection heuristic pattern detected.") -> None:
        super().__init__(reason)
        self.reason = reason


class OutputSecurityViolationError(SecurityError):
    """Raised when a model output attempts to leak unmasked PII, credentials, or unauthorized cross-client citations."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Output security violation: {details}")
        self.details = details


class UnauthorizedAccessAttemptError(SecurityError):
    """Raised when an unauthorized entity attempts to access privileged functions or client scopes."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Unauthorized access attempt: {details}")
        self.details = details


class CrossClientAccessAttemptError(SecurityError):
    """Raised when a request attempts to inspect or cite data belonging to another client ID."""

    def __init__(self, authorized_cid: str, target_cid: str) -> None:
        super().__init__(
            f"Cross-client boundary violation: authorized '{authorized_cid}' attempted to access '{target_cid}'."
        )
        self.authorized_cid = authorized_cid
        self.target_cid = target_cid
