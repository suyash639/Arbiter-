"""
arbiter/security/manager.py
---------------------------
Centralized Security Manager coordinating input validation, prompt injection defense,
data encapsulation, output sanitization, and security audit logging.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from arbiter.data_store import DataStore
from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.security.audit import SecurityAuditor
from arbiter.security.errors import (
    InputValidationError,
    PromptInjectionDetectedError,
    SecurityError,
)
from arbiter.security.input_guard import InputGuard, MAX_ID_LENGTH, MAX_PROMPT_LENGTH
from arbiter.security.output_guard import OutputGuard
from arbiter.security.prompt_guard import PromptGuard


class SecurityManager:
    """Enterprise security manager enforcing trust boundaries, injection defense,

    PII protection, and security auditing across Arbiter.
    """

    def __init__(
        self,
        store: Optional[DataStore] = None,
        observability: Optional[ObservabilityManager] = None,
    ) -> None:
        self.store = store
        self.obs = observability or get_observability_manager()
        self.auditor = SecurityAuditor(observability=self.obs)

    def validate_request_payload(self, payload: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate and sanitize incoming request payload fields and detect prompt injection attempts.

        Returns sanitized payload if valid.
        Raises InputValidationError or PromptInjectionDetectedError on violation.
        """
        if not isinstance(payload, dict):
            raise InputValidationError("Request payload must be a dictionary.")

        raw_qid = payload.get("question_id")
        if not raw_qid or not isinstance(raw_qid, str) or not raw_qid.strip():
            raise InputValidationError("Missing or invalid 'question_id' in request payload.")

        raw_cid = payload.get("client_id")
        if not raw_cid or not isinstance(raw_cid, str) or not raw_cid.strip():
            raise InputValidationError("Missing or invalid 'client_id' in request payload.")

        raw_prompt = payload.get("prompt")
        if not raw_prompt or not isinstance(raw_prompt, str) or not raw_prompt.strip():
            raise InputValidationError("Missing or invalid 'prompt' in request payload.")

        # Sanitize string lengths and remove control characters
        clean_qid = InputGuard.sanitize_string(raw_qid, max_length=MAX_ID_LENGTH, field_name="question_id")
        clean_cid = InputGuard.sanitize_string(raw_cid, max_length=MAX_ID_LENGTH, field_name="client_id")
        clean_prompt = InputGuard.sanitize_string(raw_prompt, max_length=MAX_PROMPT_LENGTH, field_name="prompt")

        # Scan for explicit prompt injection / jailbreak patterns
        scan_res = InputGuard.scan_for_prompt_injection(clean_prompt)
        if scan_res.is_injection:
            self.auditor.record_security_event(
                "prompt_injection_detected",
                request_id=request_id,
                client_id=clean_cid,
                details={"pattern": scan_res.pattern_matched, "reason": scan_res.reason},
            )
            raise PromptInjectionDetectedError(
                scan_res.reason or "Prompt injection or system override pattern detected."
            )

        sanitized_payload = dict(payload)
        sanitized_payload["question_id"] = clean_qid
        sanitized_payload["client_id"] = clean_cid
        sanitized_payload["prompt"] = clean_prompt
        return sanitized_payload

    def sanitize_response(
        self,
        response: Dict[str, Any],
        authorized_client_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post-generation scan ensuring no unmasked PII, credentials, or cross-client citations leak."""
        def _handle_event(evt_type: str, **kwargs: Any) -> None:
            self.auditor.record_security_event(
                evt_type,
                request_id=request_id,
                client_id=authorized_client_id,
                details=kwargs,
            )

        return OutputGuard.sanitize_output(
            response=response,
            authorized_client_id=authorized_client_id,
            on_security_event=_handle_event,
        )

    def encapsulate_data(self, data: Any, data_type: str = "retrieved_record") -> str:
        """Encapsulate dynamic data in strict XML boundaries for indirect injection defense."""
        return PromptGuard.encapsulate_untrusted_data(data, data_type=data_type)


# Global singleton instance
_GLOBAL_SECURITY_MANAGER: Optional[SecurityManager] = None


def get_security_manager(store: Optional[DataStore] = None) -> SecurityManager:
    """Retrieve or initialize the global SecurityManager singleton."""
    global _GLOBAL_SECURITY_MANAGER
    if _GLOBAL_SECURITY_MANAGER is None:
        _GLOBAL_SECURITY_MANAGER = SecurityManager(store=store)
    elif store is not None and _GLOBAL_SECURITY_MANAGER.store is None:
        _GLOBAL_SECURITY_MANAGER.store = store
    return _GLOBAL_SECURITY_MANAGER
