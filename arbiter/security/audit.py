"""
arbiter/security/audit.py
-------------------------
Security audit event logger recording structured security alerts and policy violations.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

from arbiter.observability import ObservabilityManager, get_observability_manager
from arbiter.observability.redaction import RedactionEngine


class SecurityAuditor:
    """Emits structured security events to the observability subsystem."""

    def __init__(self, observability: Optional[ObservabilityManager] = None) -> None:
        self.obs = observability or get_observability_manager()

    def record_security_event(
        self,
        event_type: str,
        request_id: Optional[str] = None,
        agent: str = "security",
        client_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a structured security audit event."""
        sanitized_details = RedactionEngine.redact_value(details) if details else {}

        self.obs.logger.warning(
            f"security_{event_type}",
            request_id=request_id,
            agent=agent,
            client_id=client_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **sanitized_details,
        )
