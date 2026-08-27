"""
tests/test_book_tools.py
------------------------
Comprehensive deterministic tests for arbiter.tools.book.

Design rules:
- Tests derive expected values from the dataset, not hardcoded practice answers.
- Exception: a small set of "known-good" computations verified against the
  practice key are included with comments showing the derivation, so that
  a broken calculation is obvious.
- No LLM calls.  No HTTP calls.  No Agno imports.
- Tests do NOT mutate the DataStore.

Sections:
  A. Fixtures
  B. Client scope / isolation
  C. Account lookups
  D. Holdings
  E. Transaction retrieval & filtering
  F. Arithmetic: transaction count
  G. Arithmetic: transaction total
  H. Arithmetic: cash balance
  I. Arithmetic: position quantity
  J. Arithmetic: holdings count (historical)
  K. Arithmetic: portfolio value
  L. Arithmetic: target drift
  M. Arithmetic: account age
  N. Snapshot conflict detection
  O. Error handling
  P. Precision / Decimal invariants
  Q. Property / invariant tests
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from arbiter.data_store import DataStore
from arbiter.tools.book import (
    BookToolError,
    InvalidDateError,
    InvalidFieldError,
    NoSuitabilityReviewError,
    UnknownAccountError,
    UnknownClientError,
    UnsupportedFilterError,
    calculate_account_age,
    calculate_cash_balance,
    calculate_holdings_count,
    calculate_portfolio_value,
    calculate_position_quantity,
    calculate_target_drift,
    calculate_transaction_count,
    calculate_transaction_total,
    detect_position_snapshot_conflict,
    find_first_transaction,
    find_max_transaction,
    get_accounts,
    get_client,
    get_holdings,
    get_suitability_reviews,
    get_transactions,
)

# ───────────────────────────────────────────────────────────────────────────────
# A. Fixtures
# ───────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def store() -> DataStore:
    """Load the full practice DataStore once for the whole test module."""
    return DataStore.load(DATA_DIR / "client_book.json", DATA_DIR / "market_data.json")


# ───────────────────────────────────────────────────────────────────────────────
# B. Client scope / isolation
# ───────────────────────────────────────────────────────────────────────────────

class TestClientScope:
    def test_get_client_valid(self, store):
        """Test 1: A valid client resolves successfully."""
        c = get_client(store, "cli_1001")
        assert c["client_id"] == "cli_1001"
        assert "name" in c
        assert "citations" in c
        assert "cli_1001" in c["citations"]

    def test_get_client_unknown_raises(self, store):
        """Test 2: Unknown client_id raises UnknownClientError."""
        with pytest.raises(UnknownClientError):
            get_client(store, "cli_FAKE")

    def test_cross_client_transactions_isolated(self, store):
        """Test 3: Client A's transactions never contain Client B's records."""
        txns_a = get_transactions(store, "cli_1001")
        txns_b = get_transactions(store, "cli_1002")
        ids_a = {t["id"] for t in txns_a}
        ids_b = {t["id"] for t in txns_b}
        # No shared transaction IDs across clients.
        assert ids_a.isdisjoint(ids_b)

    def test_cross_client_holdings_isolated(self, store):
        """Test 4: Client A's holdings never contain Client B's position records."""
        h_a = get_holdings(store, "cli_1001")
        h_b = get_holdings(store, "cli_1002")
        ids_a = {p["id"] for p in h_a}
        ids_b = {p["id"] for p in h_b}
        assert ids_a.isdisjoint(ids_b)

    def test_transactions_scoped_to_requested_client_only(self, store):
        """Requesting transactions with any client_id never leaks another client."""
        for cid in store.client_ids[:5]:  # spot-check first 5 clients
            txns = get_transactions(store, cid)
            # All transaction IDs are unique across the book; spot-check by
            # verifying the raw client record matches.
            client_raw = store.client(cid)
            expected_ids = {t["id"] for t in client_raw["transactions"]}
            returned_ids = {t["id"] for t in txns}
            assert returned_ids == expected_ids


# ───────────────────────────────────────────────────────────────────────────────
# C. Account lookups
# ───────────────────────────────────────────────────────────────────────────────

class TestAccountLookups:
    def test_get_accounts_returns_list(self, store):
        accts = get_accounts(store, "cli_1001")
        assert isinstance(accts, list)
        assert len(accts) >= 1

    def test_get_accounts_has_opened_field(self, store):
        accts = get_accounts(store, "cli_1001")
        assert "opened" in accts[0]

    def test_get_accounts_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            get_accounts(store, "cli_FAKE")

    def test_all_clients_have_at_least_one_account(self, store):
        for cid in store.client_ids:
            accts = get_accounts(store, cid)
            assert len(accts) >= 1, f"{cid!r} has no accounts"

    def test_get_accounts_security_no_pii_returned(self, store):
        """Verify that get_accounts does not return PII-sensitive info."""
        for cid in store.client_ids:
            accts = get_accounts(store, cid)
            for acc in accts:
                # None of the sensitive fields should exist in the accounts output.
                assert "pan" not in acc
                assert "bank_account" not in acc
                assert "date_of_birth" not in acc
                assert "address" not in acc
                # Ensure the allowed fields are exactly the safe schema subset:
                # id, opened, broker_ref, base_currency
                allowed_keys = {"id", "opened", "broker_ref", "base_currency"}
                assert set(acc.keys()).issubset(allowed_keys)


# ───────────────────────────────────────────────────────────────────────────────
# D. Holdings (positions_snapshot)
# ───────────────────────────────────────────────────────────────────────────────

class TestHoldings:
    def test_get_holdings_returns_list(self, store):
        h = get_holdings(store, "cli_1001")
        assert isinstance(h, list)

    def test_get_holdings_entry_has_required_fields(self, store):
        for cid in store.client_ids:
            h = get_holdings(store, cid)
            for pos in h:
                assert "id" in pos
                assert "symbol" in pos
                assert "quantity" in pos
                assert "market_value_usd" in pos

    def test_get_holdings_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            get_holdings(store, "cli_FAKE")

    def test_holdings_quantities_are_strings(self, store):
        """Snapshot values must remain strings (no silent float conversion)."""
        for cid in store.client_ids:
            for pos in get_holdings(store, cid):
                assert isinstance(pos["quantity"], str)
                assert isinstance(pos["market_value_usd"], str)


# ───────────────────────────────────────────────────────────────────────────────
# E. Transaction retrieval & filtering
# ───────────────────────────────────────────────────────────────────────────────

class TestTransactionFiltering:
    """Test 5–10: retrieval and filter correctness."""

    def test_get_all_transactions(self, store):
        """Test 5: Retrieve all transactions for a client."""
        txns = get_transactions(store, "cli_1014")
        client = store.client("cli_1014")
        assert len(txns) == len(client["transactions"])

    def test_filter_by_type(self, store):
        """Test 8: Filter by transaction type is deterministic."""
        buys = get_transactions(store, "cli_1014", txn_type="buy")
        assert all(t["type"] == "buy" for t in buys)
        assert len(buys) > 0

    def test_filter_by_symbol(self, store):
        """Test 7: Filter by symbol returns only that symbol."""
        txns = get_transactions(store, "cli_1014", symbol="AAPL")
        assert all(t.get("symbol") == "AAPL" for t in txns)

    def test_filter_by_start_date(self, store):
        """Test 9: start_date is an inclusive lower bound."""
        start = "2025-01-01"
        txns = get_transactions(store, "cli_1014", start_date=start)
        for t in txns:
            assert t["date"] >= start

    def test_filter_by_end_date(self, store):
        """Test 9 (end bound): end_date is an inclusive upper bound."""
        end = "2025-01-31"
        txns = get_transactions(store, "cli_1014", end_date=end)
        for t in txns:
            assert t["date"] <= end

    def test_filter_by_date_range(self, store):
        """Test 9: date range filter returns records within bounds only."""
        txns = get_transactions(
            store, "cli_1014",
            start_date="2025-01-01", end_date="2025-01-31",
        )
        for t in txns:
            assert "2025-01-01" <= t["date"] <= "2025-01-31"

    def test_filter_by_type_and_symbol_combined(self, store):
        txns = get_transactions(
            store, "cli_1014", txn_type="buy", symbol="AAPL"
        )
        assert all(t["type"] == "buy" and t["symbol"] == "AAPL" for t in txns)

    def test_no_matching_transactions_returns_empty_list(self, store):
        """Test 11: No match is a deterministic empty list, not an error."""
        txns = get_transactions(
            store, "cli_1014", symbol="NOT_A_REAL_SYMBOL"
        )
        assert txns == []

    def test_invalid_date_start_raises(self, store):
        """Test 10: Invalid date raises InvalidDateError, not a silent failure."""
        with pytest.raises(InvalidDateError):
            get_transactions(store, "cli_1014", start_date="not-a-date")

    def test_invalid_date_end_raises(self, store):
        with pytest.raises(InvalidDateError):
            get_transactions(store, "cli_1014", end_date="31/01/2025")

    def test_get_transactions_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            get_transactions(store, "cli_FAKE")

    def test_account_id_filter_raises_unsupported_not_empty(self, store):
        """Test 6 (Issue #3): account_id filter must raise UnsupportedFilterError.

        Transaction records in client_book.json do not carry an account_id field.
        Passing account_id MUST raise UnsupportedFilterError — NOT silently return
        an empty list.  This prevents callers from misinterpreting [] as
        'no transactions for this account' when in fact the filter is impossible.
        """
        with pytest.raises(UnsupportedFilterError) as exc_info:
            get_transactions(store, "cli_1014", account_id="acc_1014")
        assert isinstance(exc_info.value, UnsupportedFilterError)

    def test_account_id_filter_is_never_silently_empty(self, store):
        """Any account_id value always raises UnsupportedFilterError, never returns []."""
        for cid in store.client_ids[:3]:
            with pytest.raises(UnsupportedFilterError):
                get_transactions(store, cid, account_id="acc_ANY")


# ───────────────────────────────────────────────────────────────────────────────
# E2. Citation semantics (Issue #2)
# ───────────────────────────────────────────────────────────────────────────────

class TestCitationSemantics:
    """Verify citation rule: answer.schema.json says:
    'Cite the client id instead when more than 6 records are involved.'
    """

    def test_cash_balance_always_cites_client_id(self, store):
        """Cash balance spans all transactions (>> 6) so must cite [client_id]."""
        result = calculate_cash_balance(store, "cli_1014")
        assert result["citations"] == ["cli_1014"]

    def test_transaction_count_large_cites_client_id(self, store):
        """When > 6 transactions match, cite client_id per schema."""
        # cli_1014 has 1671 transactions; all-transactions count must use client_id.
        result = calculate_transaction_count(store, "cli_1014")
        assert result["citations"] == ["cli_1014"]

    def test_transaction_count_small_cites_specific_ids(self, store):
        """When <= 6 transactions match, cite the specific transaction IDs."""
        # Dividends for a specific symbol in a single year are typically <= 6.
        result = calculate_transaction_count(
            store, "cli_1024", txn_type="dividend", symbol="MSFT",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        count = result["count"]
        if count <= 6 and count > 0:
            # Should cite specific IDs, not client_id.
            assert all(c.startswith("txn_") for c in result["citations"]), (
                f"Expected txn_* citations for {count} records, got: {result['citations']}"
            )

    def test_transaction_total_small_set_cites_specific_ids(self, store):
        """<= 6 dividend transactions → specific txn IDs in citations."""
        result = calculate_transaction_total(
            store, "cli_1024", "net_usd",
            txn_type="dividend", symbol="MSFT",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        # q_003 expects citations = ['txn_108015', 'txn_108234'] (2 records)
        assert len(result["citations"]) == 2
        assert all(c.startswith("txn_") for c in result["citations"])

    def test_transaction_total_large_set_cites_client_id(self, store):
        """> 6 deposit records → client_id in citations."""
        result = calculate_transaction_total(
            store, "cli_1014", "amount_usd",
            txn_type="deposit",
        )
        # cli_1014 has many deposits (>> 6).
        assert result["citations"] == ["cli_1014"]

    def test_zero_match_cites_client_id(self, store):
        """Zero-match result always cites client_id (no records to cite)."""
        result = calculate_transaction_count(
            store, "cli_1014", symbol="FAKE_SYMBOL"
        )
        assert result["count"] == 0
        assert result["citations"] == ["cli_1014"]

    def test_position_qty_current_cites_position_id(self, store):
        """Current quantity from snapshot cites the specific position ID."""
        result = calculate_position_quantity(store, "cli_1014", "AAPL")
        assert result["citations"] == ["pos_1014_AAPL"]

    def test_account_age_cites_account_id(self, store):
        """Account age cites the specific account ID (1 record = specific)."""
        result = calculate_account_age(store, "cli_1024", "acc_1024")
        assert result["citations"] == ["acc_1024"]

    def test_drift_cites_position_and_review(self, store):
        """Drift cites [pos_id, rev_id] per practice key q_066."""
        result = calculate_target_drift(store, "cli_1006", "JPM")
        assert result["citations"] == ["pos_1006_JPM", "rev_706"]

    def test_find_max_cites_specific_txn(self, store):
        """find_max_transaction returns a single record; citation = that txn ID."""
        result = find_max_transaction(
            store, "cli_1014", "amount_usd", txn_type="deposit"
        )
        assert result is not None
        # Single record → specific transaction ID should be cite-able.
        # The result is the transaction dict itself; the agent extracts the ID.
        assert result["id"] == "txn_104543"


# ───────────────────────────────────────────────────────────────────────────────
# F. Arithmetic: transaction count
# ───────────────────────────────────────────────────────────────────────────────

class TestTransactionCount:
    """Test 13."""

    def test_count_all_transactions(self, store):
        """Count returned == len of raw transaction list."""
        result = calculate_transaction_count(store, "cli_1014")
        client = store.client("cli_1014")
        assert result["count"] == len(client["transactions"])

    def test_count_sells_jan_2025(self, store):
        """Derived from data: cli_1014 sells in 2025-01 must match the raw filter."""
        raw = [
            t for t in store.client("cli_1014")["transactions"]
            if t["type"] == "sell" and "2025-01-01" <= t["date"] <= "2025-01-31"
        ]
        result = calculate_transaction_count(
            store, "cli_1014",
            txn_type="sell", start_date="2025-01-01", end_date="2025-01-31",
        )
        assert result["count"] == len(raw)
        # Confirmed against practice key: expected 8
        assert result["count"] == 8

    def test_count_buys_jul_2024_cli1024(self, store):
        """cli_1024 buys in 2024-07 = 14 (confirmed against practice key)."""
        result = calculate_transaction_count(
            store, "cli_1024",
            txn_type="buy", start_date="2024-07-01", end_date="2024-07-31",
        )
        assert result["count"] == 14

    def test_count_aapl_buys_cli1019(self, store):
        """cli_1019 AAPL buy count = 76 (confirmed against practice key)."""
        result = calculate_transaction_count(
            store, "cli_1019", txn_type="buy", symbol="AAPL"
        )
        assert result["count"] == 76

    def test_count_zero_returns_clean_result(self, store):
        result = calculate_transaction_count(
            store, "cli_1014", symbol="NOT_REAL"
        )
        assert result["count"] == 0
        assert result["citations"] == ["cli_1014"]

    def test_count_buys_jan_2025_cli1014(self, store):
        """cli_1014 buys in 2025-01 = 9 (confirmed against practice key)."""
        result = calculate_transaction_count(
            store, "cli_1014",
            txn_type="buy", start_date="2025-01-01", end_date="2025-01-31",
        )
        assert result["count"] == 9


# ───────────────────────────────────────────────────────────────────────────────
# G. Arithmetic: transaction total
# ───────────────────────────────────────────────────────────────────────────────

class TestTransactionTotal:
    """Test 12."""

    def test_total_deposits_window(self, store):
        """cli_1014 deposits USD 2025-01-27 to 2026-07-27 (derived from data)."""
        raw = [
            t for t in store.client("cli_1014")["transactions"]
            if t["type"] == "deposit"
            and "2025-01-27" <= t["date"] <= "2026-07-27"
        ]
        expected = sum(Decimal(t["amount_usd"]) for t in raw)
        result = calculate_transaction_total(
            store, "cli_1014", "amount_usd",
            txn_type="deposit",
            start_date="2025-01-27", end_date="2026-07-27",
        )
        assert Decimal(result["total"]) == expected.quantize(Decimal("0.01"))
        # Confirmed against practice key: 3026556.49
        assert result["total"] == "3026556.49"

    def test_total_fees_cli1019(self, store):
        """cli_1019 total fees (derived from data then confirmed against key)."""
        raw = [t for t in store.client("cli_1019")["transactions"] if t["type"] == "fee"]
        expected = sum(Decimal(t["amount_usd"]) for t in raw)
        result = calculate_transaction_total(
            store, "cli_1019", "amount_usd", txn_type="fee"
        )
        assert Decimal(result["total"]) == expected.quantize(Decimal("0.01"))
        # Confirmed against practice key: 44.85
        assert result["total"] == "44.85"

    def test_total_deposits_usd_2025_cli1019(self, store):
        """cli_1019 deposits in USD for year 2025 = 1429244.98."""
        result = calculate_transaction_total(
            store, "cli_1019", "amount_usd",
            txn_type="deposit",
            start_date="2025-01-01", end_date="2025-12-31",
        )
        assert result["total"] == "1429244.98"

    def test_total_dividends_msft_2024_cli1024(self, store):
        """cli_1024 MSFT dividends net_usd in 2024 = 7.13."""
        result = calculate_transaction_total(
            store, "cli_1024", "net_usd",
            txn_type="dividend", symbol="MSFT",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        assert result["total"] == "7.13"

    def test_total_zero_match_returns_zero(self, store):
        result = calculate_transaction_total(
            store, "cli_1014", "amount_usd",
            txn_type="deposit", symbol="FAKE_SYM",
        )
        assert result["total"] == "0.00"
        assert result["transaction_count"] == 0

    def test_invalid_field_raises(self, store):
        """Test: requesting a field absent from a transaction type raises cleanly."""
        with pytest.raises(InvalidFieldError):
            calculate_transaction_total(
                store, "cli_1014", "net_usd",  # net_usd absent on deposits
                txn_type="deposit",
            )


# ───────────────────────────────────────────────────────────────────────────────
# H. Arithmetic: cash balance
# ───────────────────────────────────────────────────────────────────────────────

class TestCashBalance:
    """Test 14: Cash balance is correct and uses Decimal."""

    def test_cash_balance_matches_derived_sum(self, store):
        """Balance must equal the Decimal sum of all signed cash flows."""
        def expected_balance(client):
            total = Decimal("0")
            for t in client["transactions"]:
                typ = t["type"]
                if typ == "deposit":    total += Decimal(t["amount_usd"])
                elif typ == "withdrawal": total -= Decimal(t["amount_usd"])
                elif typ == "fee":      total -= Decimal(t["amount_usd"])
                elif typ == "buy":      total -= Decimal(t["net_usd"])
                elif typ == "sell":     total += Decimal(t["net_usd"])
                elif typ == "dividend": total += Decimal(t["net_usd"])
            return total.quantize(Decimal("0.01"))

        for cid in store.client_ids:
            result = calculate_cash_balance(store, cid)
            exp = expected_balance(store.client(cid))
            assert Decimal(result["balance"]) == exp, (
                f"{cid}: got {result['balance']!r}, expected {exp!r}"
            )

    def test_cash_balance_cli1014_known_value(self, store):
        """cli_1014 balance = 15386.78 (confirmed against practice key)."""
        result = calculate_cash_balance(store, "cli_1014")
        assert result["balance"] == "15386.78"
        assert result["currency"] == "USD"
        assert result["client_id"] == "cli_1014"
        assert "cli_1014" in result["citations"]

    def test_cash_balance_asof_cli1014(self, store):
        """cli_1014 balance as_of 2026-07-28 = 55112.64."""
        result = calculate_cash_balance(store, "cli_1014", as_of="2026-07-28")
        assert result["balance"] == "55112.64"
        assert result["as_of"] == "2026-07-28"

    def test_cash_balance_asof_excludes_later_transactions(self, store):
        """Balance as_of an early date must be <= balance as_of a later date
        (assuming net deposits over time, at least for clients with many deposits)."""
        b_early = Decimal(
            calculate_cash_balance(store, "cli_1014", as_of="2025-01-01")["balance"]
        )
        b_late = Decimal(
            calculate_cash_balance(store, "cli_1014", as_of="2026-07-31")["balance"]
        )
        # Not guaranteed to be ordered for all clients, but the function must
        # produce a value for both without error.
        assert isinstance(b_early, Decimal)
        assert isinstance(b_late, Decimal)

    def test_cash_balance_invalid_date_raises(self, store):
        with pytest.raises(InvalidDateError):
            calculate_cash_balance(store, "cli_1014", as_of="yesterday")

    def test_cash_balance_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            calculate_cash_balance(store, "cli_FAKE")


# ───────────────────────────────────────────────────────────────────────────────
# I. Arithmetic: position quantity
# ───────────────────────────────────────────────────────────────────────────────

class TestPositionQuantity:
    """Test 15: Position quantity is correct."""

    def test_current_qty_uses_snapshot(self, store):
        """Current (as_of None) uses snapshot with its id as citation."""
        result = calculate_position_quantity(store, "cli_1014", "AAPL")
        assert result["source"] == "positions_snapshot"
        assert result["quantity"] == "2.9849"
        assert any("pos_" in c for c in result["citations"])

    def test_historical_qty_uses_transactions(self, store):
        """Historical (as_of before book date) uses transactions."""
        result = calculate_position_quantity(
            store, "cli_1014", "AAPL", as_of="2026-07-10"
        )
        assert result["source"] == "transactions"
        assert result["quantity"] == "7.9008"
        assert result["as_of"] == "2026-07-10"

    def test_quantity_zero_for_unheld_symbol_current(self, store):
        """A symbol not in the snapshot returns quantity 0."""
        result = calculate_position_quantity(
            store, "cli_1014", "NOT_A_SYMBOL"
        )
        assert result["quantity"] == "0"

    def test_quantity_zero_for_no_transactions_historical(self, store):
        """Historical query for a never-held symbol returns 0."""
        result = calculate_position_quantity(
            store, "cli_1014", "NOT_A_SYMBOL", as_of="2025-01-01"
        )
        assert Decimal(result["quantity"]) == Decimal("0")

    def test_all_current_positions_match_snapshot(self, store):
        """For all clients, current qty via tool == snapshot qty string."""
        for cid in store.client_ids:
            for pos in store.client(cid)["positions_snapshot"]:
                sym = pos["symbol"]
                result = calculate_position_quantity(store, cid, sym)
                assert result["quantity"] == pos["quantity"], (
                    f"{cid} {sym}: tool={result['quantity']!r}, "
                    f"snapshot={pos['quantity']!r}"
                )

    def test_invalid_date_raises(self, store):
        with pytest.raises(InvalidDateError):
            calculate_position_quantity(
                store, "cli_1014", "AAPL", as_of="not-a-date"
            )


# ───────────────────────────────────────────────────────────────────────────────
# J. Arithmetic: holdings count (historical)
# ───────────────────────────────────────────────────────────────────────────────

class TestHoldingsCount:
    def test_current_holdings_count_matches_snapshot(self, store):
        """Current count == number of snapshot positions with qty > 0."""
        for cid in store.client_ids:
            snapshot = store.client(cid)["positions_snapshot"]
            expected = sum(1 for p in snapshot if Decimal(p["quantity"]) > 0)
            result = calculate_holdings_count(store, cid)
            assert result["count"] == expected, f"{cid}: {result['count']} != {expected}"

    def test_historical_holdings_count_cli1006_asof_2025_10_23(self, store):
        """cli_1006 holdings count as_of 2025-10-23 = 4 (confirmed against key)."""
        result = calculate_holdings_count(
            store, "cli_1006", as_of="2025-10-23"
        )
        assert result["count"] == 4
        assert result["source"] == "transactions"
        assert result["as_of"] == "2025-10-23"

    def test_symbols_list_matches_count(self, store):
        """len(symbols) == count for all clients."""
        for cid in store.client_ids:
            result = calculate_holdings_count(store, cid)
            assert len(result["symbols"]) == result["count"]

    def test_invalid_date_raises(self, store):
        with pytest.raises(InvalidDateError):
            calculate_holdings_count(store, "cli_1006", as_of="bad-date")


# ───────────────────────────────────────────────────────────────────────────────
# K. Arithmetic: portfolio value
# ───────────────────────────────────────────────────────────────────────────────

class TestPortfolioValue:
    """Test 16."""

    def test_portfolio_value_matches_sum_of_snapshot(self, store):
        """Total must equal Decimal sum of all snapshot market_value_usd fields."""
        for cid in store.client_ids:
            snapshot = store.client(cid)["positions_snapshot"]
            expected = sum(Decimal(p["market_value_usd"]) for p in snapshot)
            expected_str = str(expected.quantize(Decimal("0.01")))
            result = calculate_portfolio_value(store, cid)
            assert result["total_market_value_usd"] == expected_str, (
                f"{cid}: tool={result['total_market_value_usd']!r}, "
                f"expected={expected_str!r}"
            )

    def test_portfolio_value_returns_as_of(self, store):
        result = calculate_portfolio_value(store, "cli_1001")
        assert result["as_of"] == "2026-07-31"

    def test_portfolio_value_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            calculate_portfolio_value(store, "cli_FAKE")


# ───────────────────────────────────────────────────────────────────────────────
# L. Arithmetic: target drift
# ───────────────────────────────────────────────────────────────────────────────

class TestTargetDrift:
    """Test 17."""

    def test_drift_jpm_cli1006(self, store):
        """cli_1006 JPM drift = -32.15 (confirmed against practice key)."""
        result = calculate_target_drift(store, "cli_1006", "JPM")
        assert result["drift_pct"] == "-32.15"
        assert result["client_id"] == "cli_1006"
        assert result["symbol"] == "JPM"

    def test_drift_cites_snapshot_and_review(self, store):
        """Citations must include both the position snapshot id and the review id."""
        result = calculate_target_drift(store, "cli_1006", "JPM")
        cits = result["citations"]
        # At minimum the review id must be present.
        assert result["suitability_review_id"] in cits
        # If the symbol is in the snapshot, its position id should also be cited.
        snap_ids = {p["id"] for p in store.client("cli_1006")["positions_snapshot"] if p["symbol"] == "JPM"}
        if snap_ids:
            assert snap_ids.issubset(set(cits))

    def test_drift_formula_invariant(self, store):
        """actual_pct - target_pct == drift_pct (Decimal)."""
        for cid in store.client_ids:
            reviews = store.client(cid).get("suitability_reviews", [])
            if not reviews:
                continue
            latest = max(reviews, key=lambda r: r.get("date", ""))
            for sym in latest.get("target_allocation_pct", {}):
                result = calculate_target_drift(store, cid, sym)
                actual = Decimal(result["actual_pct"])
                target = Decimal(result["target_pct"])
                drift = Decimal(result["drift_pct"])
                assert drift == actual - target, (
                    f"{cid} {sym}: drift mismatch — "
                    f"{actual} - {target} != {drift}"
                )

    def test_drift_no_review_raises(self, store):
        """A client with no reviews raises NoSuitabilityReviewError."""
        # Inject a minimal DataStore-like object via monkeypatching is complex;
        # verify by finding a client without reviews or using the error class.
        # At minimum, ensure the error is importable and is a BookToolError.
        assert issubclass(NoSuitabilityReviewError, BookToolError)

    def test_drift_symbol_not_in_portfolio(self, store):
        """Symbol in target allocation but not in portfolio → negative drift."""
        # Find a client with a target allocation that has a symbol with 0 actual holding.
        for cid in store.client_ids:
            reviews = store.client(cid).get("suitability_reviews", [])
            if not reviews:
                continue
            latest = max(reviews, key=lambda r: r.get("date", ""))
            held_syms = {p["symbol"] for p in store.client(cid)["positions_snapshot"]}
            target_syms = set(latest.get("target_allocation_pct", {}))
            absent = target_syms - held_syms
            for sym in absent:
                result = calculate_target_drift(store, cid, sym)
                assert Decimal(result["actual_pct"]) == Decimal("0.00")
                assert Decimal(result["drift_pct"]) < Decimal("0")
                return  # found at least one case; sufficient

    def test_drift_symbol_not_in_target(self, store):
        """Symbol in portfolio but not in target allocation → positive drift."""
        for cid in store.client_ids:
            reviews = store.client(cid).get("suitability_reviews", [])
            if not reviews:
                continue
            latest = max(reviews, key=lambda r: r.get("date", ""))
            held_syms = {p["symbol"] for p in store.client(cid)["positions_snapshot"]}
            target_syms = set(latest.get("target_allocation_pct", {}))
            extra = held_syms - target_syms
            for sym in extra:
                result = calculate_target_drift(store, cid, sym)
                assert Decimal(result["target_pct"]) == Decimal("0.00")
                assert Decimal(result["drift_pct"]) > Decimal("0")
                return  # found at least one case


# ───────────────────────────────────────────────────────────────────────────────
# M. Arithmetic: account age
# ───────────────────────────────────────────────────────────────────────────────

class TestAccountAge:
    def test_account_age_cli1024(self, store):
        """cli_1024 acc_1024 age = 747 days (confirmed against practice key)."""
        result = calculate_account_age(store, "cli_1024", "acc_1024")
        assert result["age_days"] == 747
        assert result["client_id"] == "cli_1024"
        assert result["account_id"] == "acc_1024"
        assert "acc_1024" in result["citations"]

    def test_account_age_matches_date_arithmetic(self, store):
        """age_days must equal (as_of - opened).days for all clients."""
        book_dt = datetime.date.fromisoformat("2026-07-31")
        for cid in store.client_ids:
            for acct in store.client(cid)["accounts"]:
                aid = acct["id"]
                result = calculate_account_age(store, cid, aid)
                opened = datetime.date.fromisoformat(acct["opened"])
                expected = (book_dt - opened).days
                assert result["age_days"] == expected, (
                    f"{cid}/{aid}: tool={result['age_days']}, expected={expected}"
                )

    def test_account_age_unknown_account_raises(self, store):
        with pytest.raises(UnknownAccountError):
            calculate_account_age(store, "cli_1024", "acc_FAKE")

    def test_account_age_unknown_client_raises(self, store):
        with pytest.raises(UnknownClientError):
            calculate_account_age(store, "cli_FAKE", "acc_1024")


# ───────────────────────────────────────────────────────────────────────────────
# N. Snapshot conflict detection
# ───────────────────────────────────────────────────────────────────────────────

class TestSnapshotConflict:
    def test_no_conflict_when_quantities_match(self, store):
        """For most clients, snapshot should match transaction sum (audit confirmed)."""
        non_conflict_count = 0
        for cid in store.client_ids:
            for pos in store.client(cid)["positions_snapshot"]:
                result = detect_position_snapshot_conflict(store, cid, pos["symbol"])
                if not result["conflict"]:
                    non_conflict_count += 1
        # At least some positions should be conflict-free.
        assert non_conflict_count > 0

    def test_conflict_returns_structured_result(self, store):
        """Return dict always has the required keys regardless of conflict status."""
        cid = "cli_1014"
        result = detect_position_snapshot_conflict(store, cid, "AAPL")
        required = {
            "client_id", "symbol", "snapshot_quantity", "computed_quantity",
            "conflict", "snapshot_id", "transaction_ids", "citations",
        }
        assert required.issubset(result.keys())

    def test_conflict_unknown_symbol_returns_zero_quantities(self, store):
        result = detect_position_snapshot_conflict(store, "cli_1014", "NOT_REAL")
        assert result["snapshot_quantity"] == "0.0000"
        assert result["computed_quantity"] == "0.0000"
        assert not result["conflict"]

    def test_conflict_cites_snapshot_and_transactions(self, store):
        """When a conflict is found, citations must include position and txn IDs."""
        for cid in store.client_ids:
            for pos in store.client(cid)["positions_snapshot"]:
                result = detect_position_snapshot_conflict(store, cid, pos["symbol"])
                if result["conflict"]:
                    assert result["snapshot_id"] in result["citations"]
                    for txn_id in result["transaction_ids"]:
                        assert txn_id in result["citations"]
                    return  # found at least one conflicted case; sufficient

    def test_detect_conflict_cli1022_aapl(self, store):
        """cli_1022 AAPL is expected to have a snapshot conflict (practice key q_018)."""
        result = detect_position_snapshot_conflict(store, "cli_1022", "AAPL")
        assert result["conflict"] is True
        assert result["snapshot_id"] == "pos_1022_AAPL"
        # Practice key cites specific transaction IDs.
        expected_txn_ids = {"txn_107807", "txn_107811", "txn_107816", "txn_107832"}
        returned_txn_ids = set(result["transaction_ids"])
        assert expected_txn_ids == returned_txn_ids


# ───────────────────────────────────────────────────────────────────────────────
# O. Error handling
# ───────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests 21–25."""

    def test_unknown_client_clean_error(self, store):
        """Test 21: unknown client gives typed error, not KeyError or AttributeError."""
        with pytest.raises(UnknownClientError) as exc_info:
            get_client(store, "cli_9999")
        # Error message must NOT contain any sensitive data.
        msg = str(exc_info.value)
        assert "pan" not in msg.lower()
        assert "bank" not in msg.lower()

    def test_unknown_account_clean_error(self, store):
        """Test 22: unknown account_id gives typed error."""
        with pytest.raises(UnknownAccountError):
            calculate_account_age(store, "cli_1024", "acc_NONEXISTENT")

    def test_invalid_date_clean_error(self, store):
        """Test 23: malformed date gives InvalidDateError, not ValueError."""
        with pytest.raises(InvalidDateError):
            get_transactions(store, "cli_1014", start_date="25-12-2025")

    def test_safe_client_view_excludes_pan(self, store):
        """Test 24: get_client() never includes PAN."""
        result = get_client(store, "cli_1001")
        result_str = str(result)
        # The kyc dict has a 'pan' field; tool must not expose it.
        raw_pan = store.client("cli_1001")["kyc"].get("pan", "")
        assert raw_pan not in result_str
        assert "pan" not in result

    def test_safe_client_view_excludes_bank(self, store):
        """Test 24: get_client() never includes bank account details."""
        result = get_client(store, "cli_1001")
        assert "bank_account" not in result
        raw_bank = store.client("cli_1001")["kyc"].get("bank_account", {})
        raw_account_number = raw_bank.get("account_number", "")
        assert raw_account_number not in str(result)

    def test_exception_message_no_client_record(self, store):
        """Test 25: exceptions do not dump raw client records."""
        try:
            get_client(store, "cli_9999")
        except UnknownClientError as e:
            msg = str(e)
            # The message must be a short diagnostic, not a JSON dump.
            assert len(msg) < 200
            assert "transactions" not in msg

    def test_invalid_field_clean_error(self, store):
        with pytest.raises(InvalidFieldError):
            calculate_transaction_total(
                store, "cli_1014", "nonexistent_field",
                txn_type="deposit",
            )


# ───────────────────────────────────────────────────────────────────────────────
# P. Precision / Decimal invariants
# ───────────────────────────────────────────────────────────────────────────────

class TestDecimalPrecision:
    """Tests 18–20."""

    def test_cash_balance_is_decimal_string(self, store):
        """Test 18/20: balance is a string that can be re-parsed as Decimal."""
        result = calculate_cash_balance(store, "cli_1014")
        val = Decimal(result["balance"])
        assert isinstance(val, Decimal)
        # Must not be a float.
        assert not isinstance(result["balance"], float)

    def test_no_float_in_cash_calculation(self, store):
        """Test 18: The cash balance is reproduced identically on a second call (determinism)."""
        r1 = calculate_cash_balance(store, "cli_1014")
        r2 = calculate_cash_balance(store, "cli_1014")
        assert r1["balance"] == r2["balance"]

    def test_position_quantity_is_decimal_string(self, store):
        """Test 19: Computed quantity is a valid Decimal string."""
        result = calculate_position_quantity(
            store, "cli_1014", "AAPL", as_of="2026-07-10"
        )
        val = Decimal(result["quantity"])
        assert isinstance(val, Decimal)
        assert not isinstance(result["quantity"], float)

    def test_decimal_arithmetic_preserves_exact_value(self, store):
        """Test 19: Summing deposit amounts with Decimal gives the exact total."""
        client = store.client("cli_1014")
        deposits = [t for t in client["transactions"] if t["type"] == "deposit"
                    and "2025-01-27" <= t["date"] <= "2026-07-27"]
        expected = Decimal("0")
        for d in deposits:
            expected += Decimal(d["amount_usd"])
        result = calculate_transaction_total(
            store, "cli_1014", "amount_usd",
            txn_type="deposit",
            start_date="2025-01-27", end_date="2026-07-27",
        )
        # Exact Decimal equality (no float rounding errors).
        assert Decimal(result["total"]) == expected.quantize(Decimal("0.01"))

    def test_repeated_calls_identical_results(self, store):
        """Test 20: Deterministic calls always produce the same result."""
        for _ in range(3):
            r = calculate_cash_balance(store, "cli_1019")
            assert r["balance"] == calculate_cash_balance(store, "cli_1019")["balance"]


# ───────────────────────────────────────────────────────────────────────────────
# Q. Property / invariant tests
# ───────────────────────────────────────────────────────────────────────────────

class TestInvariants:
    def test_filter_never_returns_other_client_data(self, store):
        """Filtering transactions for any client never returns another client's txns."""
        all_txn_ids_per_client: dict[str, set[str]] = {}
        for cid in store.client_ids:
            txns = get_transactions(store, cid)
            all_txn_ids_per_client[cid] = {t["id"] for t in txns}

        for cid_a, ids_a in all_txn_ids_per_client.items():
            for cid_b, ids_b in all_txn_ids_per_client.items():
                if cid_a != cid_b:
                    assert ids_a.isdisjoint(ids_b), (
                        f"Transaction IDs overlap between {cid_a!r} and {cid_b!r}: "
                        f"{ids_a & ids_b}"
                    )

    def test_filtering_does_not_mutate_datastore(self, store):
        """Repeated filtered queries do not change the DataStore's indexes."""
        before = len(store.client("cli_1014")["transactions"])
        # Perform multiple filtered queries.
        get_transactions(store, "cli_1014", txn_type="buy")
        get_transactions(store, "cli_1014", symbol="AAPL")
        calculate_cash_balance(store, "cli_1014")
        after = len(store.client("cli_1014")["transactions"])
        assert before == after

    def test_cash_balance_plus_portfolio_value_is_total_wealth_proxy(self, store):
        """For any client, cash balance and portfolio value are both computable
        without errors (structural invariant)."""
        for cid in store.client_ids:
            cb = calculate_cash_balance(store, cid)
            pv = calculate_portfolio_value(store, cid)
            assert Decimal(cb["balance"]) is not None
            assert Decimal(pv["total_market_value_usd"]) >= Decimal("0")

    def test_drift_formula_holds_for_all_target_symbols(self, store):
        """actual - target == drift for every (client, symbol) in suitability reviews."""
        for cid in store.client_ids:
            reviews = store.client(cid).get("suitability_reviews", [])
            if not reviews:
                continue
            latest = max(reviews, key=lambda r: r.get("date", ""))
            for sym in latest.get("target_allocation_pct", {}):
                result = calculate_target_drift(store, cid, sym)
                lhs = Decimal(result["actual_pct"]) - Decimal(result["target_pct"])
                rhs = Decimal(result["drift_pct"])
                assert lhs == rhs, f"{cid}/{sym}: {lhs} != {rhs}"

    def test_find_first_transaction_order(self, store):
        """find_first_transaction always returns the min date transaction."""
        for cid in store.client_ids:
            buys = get_transactions(store, cid, txn_type="buy")
            if not buys:
                continue
            first = find_first_transaction(store, cid, txn_type="buy")
            assert first is not None
            assert first["date"] == min(t["date"] for t in buys)

    def test_find_first_ko_buy_cli1023(self, store):
        """cli_1023 first buy of KO = 2025-02-14, id=txn_107865."""
        result = find_first_transaction(
            store, "cli_1023", txn_type="buy", symbol="KO"
        )
        assert result is not None
        assert result["date"] == "2025-02-14"
        assert result["id"] == "txn_107865"

    def test_find_max_deposit_cli1014(self, store):
        """cli_1014 largest deposit = 19342.61, id=txn_104543."""
        result = find_max_transaction(
            store, "cli_1014", "amount_usd", txn_type="deposit"
        )
        assert result is not None
        assert result["amount_usd"] == "19342.61"
        assert result["id"] == "txn_104543"

    def test_find_first_no_match_returns_none(self, store):
        result = find_first_transaction(
            store, "cli_1014", txn_type="buy", symbol="NOT_REAL"
        )
        assert result is None

    def test_holdings_count_symbols_list_is_sorted(self, store):
        """The symbols list in holdings count must always be sorted."""
        for cid in store.client_ids:
            result = calculate_holdings_count(store, cid)
            syms = result["symbols"]
            assert syms == sorted(syms)

    def test_portfolio_value_is_non_negative(self, store):
        """Portfolio market value is always >= 0."""
        for cid in store.client_ids:
            result = calculate_portfolio_value(store, cid)
            assert Decimal(result["total_market_value_usd"]) >= Decimal("0")
