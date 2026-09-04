"""
arbiter/tool_verification/errors.py
-----------------------------------
Deterministic exception hierarchy for the Arbiter Tool Verification layer.
"""

from __future__ import annotations


class ToolVerificationError(ValueError):
    """Base exception for all tool verification and authorization failures."""


class UnknownToolError(ToolVerificationError):
    """Raised when an unregistered or unknown tool name is invoked."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' is not registered in the authoritative tool registry.")
        self.tool_name = tool_name


class UnauthorizedToolError(ToolVerificationError):
    """Raised when an agent attempts to invoke a tool it is not authorized to access."""

    def __init__(self, agent_name: str, tool_name: str) -> None:
        super().__init__(
            f"Agent '{agent_name}' is not authorized to invoke tool '{tool_name}'."
        )
        self.agent_name = agent_name
        self.tool_name = tool_name


class ToolArgumentValidationError(ToolVerificationError):
    """Raised when tool arguments fail schema, type, range, or format validation."""

    def __init__(self, tool_name: str, details: str) -> None:
        super().__init__(f"Argument validation failed for tool '{tool_name}': {details}")
        self.tool_name = tool_name
        self.details = details


class ToolScopeViolationError(ToolVerificationError):
    """Raised when tool arguments violate client boundary or cross-client isolation."""

    def __init__(self, expected_client_id: str, provided_client_id: str) -> None:
        super().__init__(
            f"Scope violation: client_id mismatch. Expected '{expected_client_id}', got '{provided_client_id}'."
        )
        self.expected_client_id = expected_client_id
        self.provided_client_id = provided_client_id


class MissingClientScopeError(ToolVerificationError):
    """Raised when a client-scoped tool is called without a valid client_id."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' requires an authoritative client_id in request context.")
        self.tool_name = tool_name


class UnknownClientScopeError(ToolVerificationError):
    """Raised when a client-scoped tool references a client_id not in the client book."""

    def __init__(self, client_id: str) -> None:
        super().__init__(f"Client ID '{client_id}' is not in the client book.")
        self.client_id = client_id


class ToolResultValidationError(ToolVerificationError):
    """Raised when a tool execution returns a malformed, invalid, or unexpected payload."""

    def __init__(self, tool_name: str, details: str) -> None:
        super().__init__(f"Result validation failed for tool '{tool_name}': {details}")
        self.tool_name = tool_name
        self.details = details


class ToolExecutionError(ToolVerificationError):
    """Raised when underlying deterministic business tool logic raises an expected domain error."""

    def __init__(self, tool_name: str, cause: Exception) -> None:
        super().__init__(f"Execution error in tool '{tool_name}': {cause}")
        self.tool_name = tool_name
        self.cause = cause
