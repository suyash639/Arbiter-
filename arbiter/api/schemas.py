"""
arbiter/api/schemas.py
----------------------
Transport schemas and Pydantic models for FastAPI service boundary.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRequest(BaseModel):
    """Transport request model for /v1/query endpoint."""

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Authoritative client identifier (e.g. 'cli_1014').",
        examples=["cli_1014"],
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Natural language financial operations question.",
        examples=["What is the current cash balance for cli_1014?"],
    )
    request_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional caller correlation ID.",
    )

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("client_id cannot be empty or whitespace.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
            raise ValueError("client_id contains invalid characters. Must be alphanumeric with underscores/hyphens.")
        return cleaned

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("question cannot be empty or whitespace.")
        return cleaned


class QueryResponse(BaseModel):
    """Stable HTTP response contract mirroring AnswerSchema with request correlation."""

    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(description="Unique correlation ID for this request.")
    question_id: str = Field(description="Unique question identifier.")
    answer: str = Field(description="Natural language answer text.")
    answer_value: Optional[str] = Field(default=None, description="Precise value formatted as string or None.")
    abstained: bool = Field(description="True if request could not be answered due to data constraints.")
    refused: bool = Field(description="True if request was refused by compliance/security policies.")
    reason: Optional[str] = Field(default=None, description="Reason for refusal or abstention.")
    citations: List[str] = Field(default_factory=list, description="Authoritative record IDs cited.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score.")
    flags: List[str] = Field(default_factory=list, description="Audit flags (e.g. 'upstream_issue', 'conflict').")
    agents: List[str] = Field(default_factory=list, description="Ordered path of agents that handled the query.")


class HealthResponse(BaseModel):
    """Response model for /health liveness probe."""

    status: str = Field(default="ok", description="Service liveness state.")
    service: str = Field(default="arbiter", description="Service identifier.")


class ReadinessResponse(BaseModel):
    """Response model for /ready readiness probe."""

    status: str = Field(default="ready", description="Service readiness state.")
    clients_loaded: int = Field(description="Number of client records loaded.")
    instruments_loaded: int = Field(description="Number of instruments loaded in market dataset.")
    llm_provider: str = Field(description="Configured LLM provider.")
    llm_model: str = Field(description="Configured LLM model.")


class ErrorResponse(BaseModel):
    """Standardized error envelope for API exceptions."""

    error: str = Field(description="Standardized error code.")
    message: str = Field(description="Sanitized human-readable description.")
    request_id: Optional[str] = Field(default=None, description="Request correlation ID.")
    details: Optional[Any] = Field(default=None, description="Sanitized validation or error details.")
