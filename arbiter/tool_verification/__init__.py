"""
arbiter/tool_verification
-------------------------
Production-grade Tool Verification layer for Arbiter.
"""

from arbiter.tool_verification.errors import (
    MissingClientScopeError,
    ToolArgumentValidationError,
    ToolExecutionError,
    ToolResultValidationError,
    ToolScopeViolationError,
    ToolVerificationError,
    UnauthorizedToolError,
    UnknownClientScopeError,
    UnknownToolError,
)
from arbiter.tool_verification.registry import (
    TOOL_REGISTRY,
    get_authorized_tools_for_agent,
    get_tool_definition,
)
from arbiter.tool_verification.schemas import (
    ToolDefinition,
    VerificationAuditRecord,
)
from arbiter.tool_verification.verifier import (
    ToolVerifier,
    create_verified_tool,
)

__all__ = [
    "ToolVerificationError",
    "UnknownToolError",
    "UnauthorizedToolError",
    "ToolArgumentValidationError",
    "ToolScopeViolationError",
    "MissingClientScopeError",
    "UnknownClientScopeError",
    "ToolResultValidationError",
    "ToolExecutionError",
    "TOOL_REGISTRY",
    "get_tool_definition",
    "get_authorized_tools_for_agent",
    "ToolDefinition",
    "VerificationAuditRecord",
    "ToolVerifier",
    "create_verified_tool",
]
