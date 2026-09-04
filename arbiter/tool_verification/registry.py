"""
arbiter/tool_verification/registry.py
-------------------------------------
Authoritative registry defining tool capabilities, parameter schemas,
and agent authorization boundaries.
"""

from __future__ import annotations

from typing import Dict, Optional, Set

from arbiter.tool_verification.schemas import (
    AccountAgeArgs,
    CashBalanceArgs,
    ClientOnlyArgs,
    ConflictCheckArgs,
    HoldingsCountArgs,
    InstrumentDetailsArgs,
    KycProfileArgs,
    MarketPriceArgs,
    MarketReturnArgs,
    MemosArgs,
    NotesArgs,
    PositionQuantityArgs,
    SuitabilityArgs,
    SymbolNewsArgs,
    TargetDriftArgs,
    ToolDefinition,
    TransactionFilterArgs,
    TransactionNumericArgs,
)

# ---------------------------------------------------------------------------
# Declarative Tool Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    # --- Book QA Tools ---
    "get_client_profile": ToolDefinition(
        name="get_client_profile",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ClientOnlyArgs,
        expected_result_type="dict",
        description="Retrieve client metadata record without sensitive PII.",
    ),
    "get_client_accounts": ToolDefinition(
        name="get_client_accounts",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ClientOnlyArgs,
        expected_result_type="list",
        description="Retrieve list of account dictionaries for the client.",
    ),
    "get_client_holdings": ToolDefinition(
        name="get_client_holdings",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ClientOnlyArgs,
        expected_result_type="list",
        description="Retrieve positions snapshot list for the client.",
    ),
    "get_client_suitability_reviews": ToolDefinition(
        name="get_client_suitability_reviews",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ClientOnlyArgs,
        expected_result_type="list",
        description="Retrieve suitability reviews list for the client.",
    ),
    "get_client_transactions": ToolDefinition(
        name="get_client_transactions",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TransactionFilterArgs,
        expected_result_type="list",
        description="Retrieve filtered transactions list for the client.",
    ),
    "find_earliest_transaction": ToolDefinition(
        name="find_earliest_transaction",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TransactionFilterArgs,
        expected_result_type="dict_or_none",
        description="Find the chronologically earliest transaction matching filters.",
    ),
    "find_largest_transaction": ToolDefinition(
        name="find_largest_transaction",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TransactionNumericArgs,
        expected_result_type="dict_or_none",
        description="Find transaction with largest numeric field value.",
    ),
    "get_cash_balance": ToolDefinition(
        name="get_cash_balance",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=CashBalanceArgs,
        expected_result_type="dict",
        description="Calculate USD cash balance aggregated from transactions.",
    ),
    "get_position_quantity": ToolDefinition(
        name="get_position_quantity",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=PositionQuantityArgs,
        expected_result_type="dict",
        description="Calculate held quantity of a security as of a date.",
    ),
    "get_holdings_count": ToolDefinition(
        name="get_holdings_count",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=HoldingsCountArgs,
        expected_result_type="dict",
        description="Calculate count of distinct held securities as of a date.",
    ),
    "get_transaction_total": ToolDefinition(
        name="get_transaction_total",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TransactionNumericArgs,
        expected_result_type="dict",
        description="Sum a numeric field across filtered transactions.",
    ),
    "get_transaction_count": ToolDefinition(
        name="get_transaction_count",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TransactionFilterArgs,
        expected_result_type="dict",
        description="Count transactions matching filter criteria.",
    ),
    "get_portfolio_value": ToolDefinition(
        name="get_portfolio_value",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ClientOnlyArgs,
        expected_result_type="dict",
        description="Calculate total market value of held positions.",
    ),
    "get_target_drift": ToolDefinition(
        name="get_target_drift",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=TargetDriftArgs,
        expected_result_type="dict",
        description="Calculate target allocation drift percentage.",
    ),
    "get_account_age": ToolDefinition(
        name="get_account_age",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=AccountAgeArgs,
        expected_result_type="dict",
        description="Calculate age of an account in days.",
    ),
    "check_position_snapshot_conflict": ToolDefinition(
        name="check_position_snapshot_conflict",
        owning_agents={"book_qa"},
        requires_client_id=True,
        args_schema=ConflictCheckArgs,
        expected_result_type="dict",
        description="Detect conflict between position snapshot and transaction history.",
    ),

    # --- KYC Profile Tools ---
    "get_kyc_profile": ToolDefinition(
        name="get_kyc_profile",
        owning_agents={"kyc_profile"},
        requires_client_id=True,
        args_schema=KycProfileArgs,
        expected_result_type="dict",
        description="Retrieve masked KYC profile view for a client.",
    ),
    "get_suitability": ToolDefinition(
        name="get_suitability",
        owning_agents={"kyc_profile"},
        requires_client_id=True,
        args_schema=SuitabilityArgs,
        expected_result_type="list",
        description="Retrieve suitability reviews list for a client.",
    ),

    # --- Notes Desk Tools ---
    "get_notes": ToolDefinition(
        name="get_notes",
        owning_agents={"notes_desk"},
        requires_client_id=True,
        args_schema=NotesArgs,
        expected_result_type="list",
        description="Retrieve relationship notes list for a client.",
    ),
    "get_memos": ToolDefinition(
        name="get_memos",
        owning_agents={"notes_desk"},
        requires_client_id=True,
        args_schema=MemosArgs,
        expected_result_type="list",
        description="Retrieve transaction memos list for a client.",
    ),

    # --- Market Desk Tools ---
    "get_instrument": ToolDefinition(
        name="get_instrument",
        owning_agents={"market_desk"},
        requires_client_id=False,
        args_schema=InstrumentDetailsArgs,
        expected_result_type="dict",
        description="Retrieve sector/exchange metadata for a covered symbol.",
    ),
    "get_price": ToolDefinition(
        name="get_price",
        owning_agents={"market_desk"},
        requires_client_id=False,
        args_schema=MarketPriceArgs,
        expected_result_type="dict",
        description="Retrieve monthly close price for a covered symbol as-of a date.",
    ),
    "get_return": ToolDefinition(
        name="get_return",
        owning_agents={"market_desk"},
        requires_client_id=False,
        args_schema=MarketReturnArgs,
        expected_result_type="dict",
        description="Calculate percentage return of a covered symbol between two dates.",
    ),
    "get_news": ToolDefinition(
        name="get_news",
        owning_agents={"market_desk"},
        requires_client_id=False,
        args_schema=SymbolNewsArgs,
        expected_result_type="list",
        description="Retrieve news articles for a covered symbol.",
    ),
}


def get_tool_definition(tool_name: str) -> Optional[ToolDefinition]:
    """Look up a tool definition in the authoritative registry."""
    return TOOL_REGISTRY.get(tool_name)


def get_authorized_tools_for_agent(agent_name: str) -> Set[str]:
    """Retrieve the set of tool names authorized for a given agent role."""
    return {
        name for name, defn in TOOL_REGISTRY.items()
        if agent_name in defn.owning_agents
    }
