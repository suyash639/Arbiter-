"""
arbiter/security
----------------
Production-grade security subsystem for Arbiter.
"""

from arbiter.security.audit import SecurityAuditor
from arbiter.security.errors import (
    CrossClientAccessAttemptError,
    InputValidationError,
    OutputSecurityViolationError,
    PromptInjectionDetectedError,
    SecurityError,
    UnauthorizedAccessAttemptError,
)
from arbiter.security.input_guard import (
    INJECTION_PATTERNS,
    InjectionScanResult,
    InputGuard,
)
from arbiter.security.manager import SecurityManager, get_security_manager
from arbiter.security.output_guard import OutputGuard
from arbiter.security.prompt_guard import PromptGuard

__all__ = [
    "SecurityError",
    "InputValidationError",
    "PromptInjectionDetectedError",
    "OutputSecurityViolationError",
    "UnauthorizedAccessAttemptError",
    "CrossClientAccessAttemptError",
    "INJECTION_PATTERNS",
    "InjectionScanResult",
    "InputGuard",
    "PromptGuard",
    "OutputGuard",
    "SecurityAuditor",
    "SecurityManager",
    "get_security_manager",
]
