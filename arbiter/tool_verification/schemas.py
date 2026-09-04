"""
arbiter/tool_verification/schemas.py
------------------------------------
Pydantic schemas and dataclasses for tool definitions, argument verification,
and audit records.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, Set, Type
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Base Argument Schema (Strict, No Extra Fields)
# ---------------------------------------------------------------------------

class StrictBaseModel(BaseModel):
    """Base model prohibiting undeclared/extra fields for strict argument verification."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _validate_iso_date(value: str | None, field_name: str) -> str | None:
    """Validate that a date string matches strict YYYY-MM-DD ISO format."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid date value {value!r} for '{field_name}'.")
    val_clean = value.strip()
    try:
        datetime.date.fromisoformat(val_clean)
        return val_clean
    except ValueError as exc:
        raise ValueError(f"Date '{value}' for '{field_name}' must be formatted as YYYY-MM-DD.") from exc


# ---------------------------------------------------------------------------
# Argument Schemas: Book QA
# ---------------------------------------------------------------------------

class ClientOnlyArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64, description="Authoritative client identifier")


class CashBalanceArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    as_of: Optional[str] = Field(default=None)

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "as_of")


class PositionQuantityArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=16)
    as_of: Optional[str] = Field(default=None)

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "as_of")


class HoldingsCountArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    as_of: Optional[str] = Field(default=None)

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "as_of")


class AccountAgeArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    account_id: str = Field(min_length=1, max_length=64)
    as_of: Optional[str] = Field(default=None)

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "as_of")


class TargetDriftArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=16)


class ConflictCheckArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=16)


class TransactionFilterArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    txn_type: Optional[Literal["deposit", "withdrawal", "fee", "buy", "sell", "dividend"]] = None
    symbol: Optional[str] = Field(default=None, max_length=16)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account_id: Optional[str] = None

    @field_validator("start_date")
    @classmethod
    def check_start_date(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def check_end_date(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "end_date")


class TransactionNumericArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)
    numeric_field: Literal["amount_usd", "net_usd", "gross_amount_usd", "price_per_share", "shares"]
    txn_type: Optional[Literal["deposit", "withdrawal", "fee", "buy", "sell", "dividend"]] = None
    symbol: Optional[str] = Field(default=None, max_length=16)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator("start_date")
    @classmethod
    def check_start_date(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def check_end_date(cls, v: str | None) -> str | None:
        return _validate_iso_date(v, "end_date")


# ---------------------------------------------------------------------------
# Argument Schemas: KYC Profile & Notes Desk
# ---------------------------------------------------------------------------

class KycProfileArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)


class SuitabilityArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)


class NotesArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)


class MemosArgs(StrictBaseModel):
    cid: str = Field(min_length=1, max_length=64)


# ---------------------------------------------------------------------------
# Argument Schemas: Market Desk
# ---------------------------------------------------------------------------

class InstrumentDetailsArgs(StrictBaseModel):
    symbol: str = Field(min_length=1, max_length=16)


class MarketPriceArgs(StrictBaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    date: str = Field(min_length=1)

    @field_validator("date")
    @classmethod
    def check_date(cls, v: str) -> str:
        res = _validate_iso_date(v, "date")
        if res is None:
            raise ValueError("Parameter 'date' is required.")
        return res


class MarketReturnArgs(StrictBaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)

    @field_validator("start_date")
    @classmethod
    def check_start(cls, v: str) -> str:
        res = _validate_iso_date(v, "start_date")
        if res is None:
            raise ValueError("Parameter 'start_date' is required.")
        return res

    @field_validator("end_date")
    @classmethod
    def check_end(cls, v: str) -> str:
        res = _validate_iso_date(v, "end_date")
        if res is None:
            raise ValueError("Parameter 'end_date' is required.")
        return res


class SymbolNewsArgs(StrictBaseModel):
    symbol: str = Field(min_length=1, max_length=16)


# ---------------------------------------------------------------------------
# Tool Definition & Registry Schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolDefinition:
    """Declarative specification of an authorized tool."""

    name: str
    owning_agents: Set[str]
    requires_client_id: bool
    args_schema: Optional[Type[BaseModel]]
    expected_result_type: Literal["dict", "list", "dict_or_none"]
    description: str


@dataclass(frozen=True)
class VerificationAuditRecord:
    """Telemetry record capturing verification decisions and performance."""

    request_id: Optional[str]
    agent: str
    tool_name: str
    authorized: bool
    arguments_valid: bool
    scope_valid: bool
    execution_success: bool
    result_valid: bool
    latency_ms: float
    error_category: Optional[str] = None
    sanitized_error: Optional[str] = None
