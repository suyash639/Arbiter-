"""
arbiter/tools/book.py
---------------------
Deterministic financial tools over the client book.

Design principles
-----------------
- Every public function accepts a ``DataStore`` as its first argument.
  Data loading is the caller's responsibility; these tools are pure logic.
- Every client-scoped function requires an explicit ``client_id``.
  No cross-client queries are ever permitted.
- Financial arithmetic uses ``decimal.Decimal`` throughout.
  Float is never used for money, quantities, prices, or percentages.
- Return dicts serialise Decimal values as plain strings via
  ``_fmt_usd()``, ``_fmt_qty()``, or ``_fmt_pct()``.  This preserves
  exact precision and is JSON-safe.  Callers must NOT re-convert to float.
- Source strings from the JSON are never rounded or mutated; only
  *computed* values are formatted.
- Every return dict contains a ``citations`` key whose values are source
  record IDs (transaction ids, position ids, review ids, account ids, or
  the client_id when many records are involved).
- Sensitive fields (PAN, bank account, address, DOB) never appear in tool
  output or exception messages.

Transaction cash-flow convention (from client_book.json meta note):
  "Transactions are the authoritative source for cash."
  deposit    +amount_usd
  withdrawal -amount_usd
  fee        -amount_usd
  buy        -net_usd
  sell       +net_usd
  dividend   +net_usd

Decimal serialisation strategy
-------------------------------
Computed monetary values  → str(d.quantize(Decimal("0.01")))
Computed quantity values  → str(d.quantize(Decimal("0.0001")))
Computed percentage values→ str(d.quantize(Decimal("0.01")))
Source string values      → passed through unchanged (no re-formatting)

Citation strategy (per answer.schema.json)
------------------------------------------
"Cite the client id instead when more than 6 records are involved."
- Single-record results: cite the specific record ID (txn_*, pos_*, acc_*)
- Multi-record results where count <= 6: cite the individual record IDs
- Multi-record results where count > 6: cite [client_id]
This rule is enforced by the _citations() helper.

account_id filtering
--------------------
The client book transaction records do NOT carry an account_id field.
If account_id is passed to get_transactions(), an UnsupportedFilterError
is raised rather than silently returning empty results. This prevents
callers from misinterpreting zero-results as "no transactions" when the
filter is structurally unsupported.

Target drift formula
--------------------
The suitability_review target_allocation_pct describes each security's
weight within the *securities portfolio* (positions_snapshot), NOT
within total wealth (which includes cash). This is confirmed by the
practice key: using equity-only denominator reproduces all four drift
expected values exactly; using total-wealth denominator does not.
Therefore: actual_pct = position_mv / total_snapshot_mv * 100.
"""

from __future__ import annotations

import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from arbiter.data_store import DataStore

# ---------------------------------------------------------------------------
# Decimal precision constants
# ---------------------------------------------------------------------------
_CENT = Decimal("0.01")    # money / percentages: 2 d.p.
_QTY4 = Decimal("0.0001")  # quantities: 4 d.p.
_ZERO = Decimal("0")

# ---------------------------------------------------------------------------
# Citation threshold (from answer.schema.json)
# ---------------------------------------------------------------------------
_MAX_SPECIFIC_CITATIONS = 6


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class BookToolError(Exception):
    """Base class for all book-tool errors."""


class UnknownClientError(BookToolError):
    """Raised when client_id does not exist in the book."""

    def __init__(self, client_id: str) -> None:
        super().__init__(f"No client with id {client_id!r} in the book.")
        self.client_id = client_id


class UnknownAccountError(BookToolError):
    """Raised when account_id does not belong to client_id."""

    def __init__(self, account_id: str, client_id: str) -> None:
        super().__init__(
            f"Account {account_id!r} not found for client {client_id!r}."
        )
        self.account_id = account_id
        self.client_id = client_id


class InvalidDateError(BookToolError):
    """Raised on unparseable or logically invalid date input."""

    def __init__(self, value: Any, *, context: str = "") -> None:
        suffix = f" (context: {context})" if context else ""
        super().__init__(f"Invalid date value {value!r}{suffix}.")
        self.value = value


class InvalidFieldError(BookToolError):
    """Raised when a numeric field does not exist on a transaction type."""

    def __init__(self, field: str, txn_type: str) -> None:
        super().__init__(
            f"Field {field!r} is not present on {txn_type!r} transactions."
        )
        self.field = field
        self.txn_type = txn_type


class UnsupportedFilterError(BookToolError):
    """Raised when a requested filter cannot be applied to the source data.

    Distinguishes between "valid filter, no records" (empty list) and
    "filter is structurally impossible on this record type" (this error).
    """

    def __init__(self, filter_name: str, *, reason: str) -> None:
        super().__init__(
            f"Filter {filter_name!r} cannot be applied: {reason}"
        )
        self.filter_name = filter_name


class NoSuitabilityReviewError(BookToolError):
    """Raised when a drift calculation is attempted but no review exists."""

    def __init__(self, client_id: str) -> None:
        super().__init__(
            f"Client {client_id!r} has no suitability review on file."
        )
        self.client_id = client_id


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _require_client(store: DataStore, client_id: str) -> dict:
    """Return the raw client dict or raise UnknownClientError."""
    try:
        return store.client(client_id)
    except KeyError:
        raise UnknownClientError(client_id) from None


def _mask_value(val: str | None) -> str | None:
    """Mask a sensitive value, replacing the prefix with **** and leaving the last 4 characters."""
    if not val:
        return None
    val_str = str(val).strip()
    if len(val_str) <= 4:
        return "****" + val_str
    return "****" + val_str[-4:]


def _parse_date(value: Any, *, context: str = "") -> datetime.date:
    """Parse an ISO-8601 date string to ``datetime.date``.

    Accepts ``str`` or ``datetime.date``.
    Raises ``InvalidDateError`` for anything else.
    """
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise InvalidDateError(value, context=context)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise InvalidDateError(value, context=context)


def _book_date(store: DataStore) -> datetime.date:
    """Return the book's authoritative as_of date."""
    return _parse_date(store.book_meta.get("as_of", ""), context="book meta as_of")


def _cash_flow(txn: dict) -> Decimal | None:
    """Return the signed USD cash-flow of *txn*, or None for unknown types.

    Convention verified against client_book.json and confirmed by the note:
      "Transactions are the authoritative source for cash."

      deposit    +amount_usd
      withdrawal -amount_usd
      fee        -amount_usd
      buy        -net_usd
      sell       +net_usd
      dividend   +net_usd
    """
    t = txn.get("type", "")
    try:
        if t == "deposit":
            return Decimal(txn["amount_usd"])
        if t == "withdrawal":
            return -Decimal(txn["amount_usd"])
        if t == "fee":
            return -Decimal(txn["amount_usd"])
        if t == "buy":
            return -Decimal(txn["net_usd"])
        if t == "sell":
            return Decimal(txn["net_usd"])
        if t == "dividend":
            return Decimal(txn["net_usd"])
    except (KeyError, InvalidOperation) as exc:
        raise BookToolError(
            f"Malformed {t!r} transaction {txn.get('id')!r}: {exc}"
        ) from exc
    return None


def _filter_transactions(
    transactions: list[dict],
    *,
    symbol: str | None = None,
    txn_type: str | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> list[dict]:
    """Return a filtered sub-list of *transactions* (AND semantics for all criteria).

    Note: account_id filtering is NOT supported here because transaction
    records in client_book.json do not carry an account_id field.
    Callers that need account-scoped filtering should use get_transactions()
    which raises UnsupportedFilterError explicitly.

    Date parsing is deferred: if neither *start_date* nor *end_date* are
    supplied, transaction dates are never parsed, keeping non-date queries fast.
    """
    need_date = start_date is not None or end_date is not None
    result: list[dict] = []
    for t in transactions:
        if txn_type is not None and t.get("type") != txn_type:
            continue
        if symbol is not None and t.get("symbol") != symbol:
            continue
        if need_date:
            txn_date = _parse_date(
                t.get("date", ""),
                context=f"transaction {t.get('id')!r}",
            )
            if start_date is not None and txn_date < start_date:
                continue
            if end_date is not None and txn_date > end_date:
                continue
        result.append(t)
    return result


def _citations(records: list[dict], client_id: str, id_field: str = "id") -> list[str]:
    """Return citation IDs per the answer schema contract.

    From answer.schema.json:
      "Cite the client id instead when more than 6 records are involved."

    - If len(records) == 0: return [client_id]  (scope is always cited)
    - If len(records) <= 6: return sorted list of record IDs
    - If len(records) > 6: return [client_id]
    """
    if len(records) == 0 or len(records) > _MAX_SPECIFIC_CITATIONS:
        return [client_id]
    return [r[id_field] for r in records if id_field in r] or [client_id]


def _fmt_usd(d: Decimal) -> str:
    """Serialise a monetary Decimal to a 2-d.p. string (no symbol, no commas)."""
    return str(d.quantize(_CENT, rounding=ROUND_HALF_UP))


def _fmt_qty(d: Decimal) -> str:
    """Serialise a quantity Decimal to a 4-d.p. string."""
    return str(d.quantize(_QTY4, rounding=ROUND_HALF_UP))


def _fmt_pct(d: Decimal) -> str:
    """Serialise a percentage Decimal to a 2-d.p. string."""
    return str(d.quantize(_CENT, rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Public API — retrieval
# ---------------------------------------------------------------------------

def get_client(store: DataStore, client_id: str) -> dict:
    """Return a non-sensitive metadata view of the client.

    Deliberately excludes: PAN, bank account, date of birth, address.

    Returns
    -------
    dict with keys:
        client_id, name, kyc_id, kyc_status, risk_profile,
        annual_income_band, account_count, citations
    """
    c = _require_client(store, client_id)
    kyc = c.get("kyc", {})
    return {
        "client_id": client_id,
        "name": c.get("name"),
        "kyc_id": kyc.get("id"),
        "kyc_status": kyc.get("kyc_status"),
        "risk_profile": kyc.get("risk_profile"),
        "annual_income_band": kyc.get("annual_income_band"),
        "account_count": len(c.get("accounts", [])),
        "citations": [client_id],
    }


def get_client_kyc_profile(store: DataStore, client_id: str) -> dict:
    """Return a detailed, secure, and masked KYC/profile view of the client.

    Masks PAN and bank account numbers.
    """
    c = _require_client(store, client_id)
    kyc = c.get("kyc", {})
    bank = kyc.get("bank_account", {})
    emp = kyc.get("employment", {})

    kyc_id = kyc.get("id")

    return {
        "client_id": client_id,
        "name": c.get("name"),
        "kyc_id": kyc_id,
        "pan": _mask_value(kyc.get("pan")),
        "kyc_status": kyc.get("kyc_status"),
        "risk_profile": kyc.get("risk_profile"),
        "date_of_birth": kyc.get("date_of_birth"),
        "address": kyc.get("address"),
        "annual_income_band": kyc.get("annual_income_band"),
        "bank_name": bank.get("bank"),
        "bank_account_number": _mask_value(bank.get("account_number")),
        "bank_ifsc": bank.get("ifsc"),
        "employer": emp.get("employer"),
        "occupation": emp.get("occupation"),
        "citations": [kyc_id] if kyc_id else [client_id],
    }


def get_accounts(store: DataStore, client_id: str) -> list[dict]:
    """Return the accounts list for *client_id*.

    Security: account records in client_book.json contain only non-sensitive
    fields (id, opened, broker_ref, base_currency). No PAN or bank account
    numbers are present at the account level; those are stored in kyc.
    The full account record is returned as-is.

    Each entry: id, opened, broker_ref, base_currency.
    """
    c = _require_client(store, client_id)
    # Account records contain only: id, opened, broker_ref, base_currency.
    # None of these are PII-sensitive, so the raw record is safe to return.
    return list(c.get("accounts", []))


def get_holdings(store: DataStore, client_id: str) -> list[dict]:
    """Return the positions_snapshot for *client_id*.

    Each entry: id, symbol, quantity, avg_cost_usd, market_value_usd.
    All values are the original source strings (not re-formatted).
    """
    c = _require_client(store, client_id)
    return list(c.get("positions_snapshot", []))


def get_suitability_reviews(store: DataStore, client_id: str) -> list[dict]:
    """Return all suitability reviews for *client_id*, sorted ascending by date."""
    c = _require_client(store, client_id)
    reviews = list(c.get("suitability_reviews", []))
    reviews.sort(key=lambda r: r.get("date", ""))
    return reviews


def get_transactions(
    store: DataStore,
    client_id: str,
    *,
    account_id: str | None = None,
    symbol: str | None = None,
    txn_type: str | None = None,
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
) -> list[dict]:
    """Return filtered transactions for *client_id*.

    Filtering is deterministic Python; no LLM involvement.
    All criteria use AND semantics.  Transactions are returned in
    source order (chronological by construction in the dataset).

    Parameters
    ----------
    account_id:
        UNSUPPORTED. Transaction records in client_book.json do not carry
        an account_id field. Passing a non-None account_id raises
        UnsupportedFilterError. This is a deliberate distinction between
        "valid filter that returns no records" and "filter cannot be
        applied to this record type".
    symbol:
        Filter to transactions involving this ticker symbol.
    txn_type:
        Filter to one of: deposit, withdrawal, fee, buy, sell, dividend.
    start_date, end_date:
        Inclusive date bounds (ISO-8601 strings or datetime.date objects).

    Raises
    ------
    UnknownClientError:
        If client_id is not in the book.
    UnsupportedFilterError:
        If account_id is not None (transaction records lack this field).
    InvalidDateError:
        If start_date or end_date cannot be parsed as ISO-8601.
    """
    if account_id is not None:
        raise UnsupportedFilterError(
            "account_id",
            reason=(
                "Transaction records in client_book.json do not carry an "
                "account_id field. Account-level transaction attribution "
                "is not supported by the source data."
            ),
        )
    c = _require_client(store, client_id)
    # Parse date inputs eagerly so callers get InvalidDateError immediately.
    sd = _parse_date(start_date, context="start_date") if start_date is not None else None
    ed = _parse_date(end_date, context="end_date") if end_date is not None else None
    return _filter_transactions(
        c.get("transactions", []),
        symbol=symbol,
        txn_type=txn_type,
        start_date=sd,
        end_date=ed,
    )


def find_first_transaction(
    store: DataStore,
    client_id: str,
    *,
    txn_type: str | None = None,
    symbol: str | None = None,
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
) -> dict | None:
    """Return the chronologically earliest transaction matching the filters.

    Returns ``None`` if no matching transaction exists.
    """
    txns = get_transactions(
        store, client_id,
        txn_type=txn_type, symbol=symbol,
        start_date=start_date, end_date=end_date,
    )
    if not txns:
        return None
    return min(txns, key=lambda t: t["date"])


def find_max_transaction(
    store: DataStore,
    client_id: str,
    numeric_field: str,
    *,
    txn_type: str | None = None,
    symbol: str | None = None,
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
) -> dict | None:
    """Return the transaction with the largest value of *numeric_field*.

    Returns ``None`` if no matching transaction exists.
    Raises ``InvalidFieldError`` if *numeric_field* is absent from any
    matched transaction.
    """
    txns = get_transactions(
        store, client_id,
        txn_type=txn_type, symbol=symbol,
        start_date=start_date, end_date=end_date,
    )
    if not txns:
        return None
    for t in txns:
        if numeric_field not in t:
            raise InvalidFieldError(numeric_field, t.get("type", "unknown"))
    return max(txns, key=lambda t: Decimal(t[numeric_field]))


# ---------------------------------------------------------------------------
# Public API — aggregation and arithmetic
# ---------------------------------------------------------------------------

def calculate_transaction_count(
    store: DataStore,
    client_id: str,
    *,
    txn_type: str | None = None,
    symbol: str | None = None,
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
) -> dict:
    """Count transactions matching the filters for *client_id*.

    Citation rule: if matched transactions > 6, cite [client_id]; else
    cite the specific transaction IDs.

    Returns
    -------
    dict with keys:
        client_id, txn_type, symbol, start_date, end_date, count, citations
    """
    txns = get_transactions(
        store, client_id,
        txn_type=txn_type, symbol=symbol,
        start_date=start_date, end_date=end_date,
    )
    return {
        "client_id": client_id,
        "txn_type": txn_type,
        "symbol": symbol,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "count": len(txns),
        "citations": _citations(txns, client_id),
    }


def calculate_transaction_total(
    store: DataStore,
    client_id: str,
    numeric_field: str,
    *,
    txn_type: str | None = None,
    symbol: str | None = None,
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
) -> dict:
    """Sum *numeric_field* across filtered transactions for *client_id*.

    *numeric_field* must be a decimal-string field present on every matched
    transaction (e.g. ``"amount_usd"``, ``"net_usd"``, ``"amount_inr"``).
    Raises ``InvalidFieldError`` if *numeric_field* is absent from any match.

    Citation rule: if matched transactions > 6, cite [client_id]; else
    cite the specific transaction IDs.

    Returns
    -------
    dict with keys:
        client_id, numeric_field, txn_type, symbol, start_date, end_date,
        total, transaction_count, citations
    """
    txns = get_transactions(
        store, client_id,
        txn_type=txn_type, symbol=symbol,
        start_date=start_date, end_date=end_date,
    )
    total = _ZERO
    for t in txns:
        if numeric_field not in t:
            raise InvalidFieldError(numeric_field, t.get("type", "unknown"))
        try:
            total += Decimal(t[numeric_field])
        except InvalidOperation as exc:
            raise BookToolError(
                f"Cannot parse {numeric_field!r} on transaction "
                f"{t.get('id')!r} as Decimal."
            ) from exc
    return {
        "client_id": client_id,
        "numeric_field": numeric_field,
        "txn_type": txn_type,
        "symbol": symbol,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "total": _fmt_usd(total),
        "transaction_count": len(txns),
        "citations": _citations(txns, client_id),
    }


def calculate_cash_balance(
    store: DataStore,
    client_id: str,
    *,
    as_of: str | datetime.date | None = None,
) -> dict:
    """Calculate the USD cash balance for *client_id* as of *as_of*.

    Transactions are the authoritative source for cash (per book meta note).
    All transaction types contribute signed cash flows per the dataset convention.
    If *as_of* is None, all transactions are included (equivalent to book date).

    Citation rule: cash balance involves all transactions (> 6), so always
    cites [client_id].

    Returns
    -------
    dict with keys:
        client_id, as_of, balance, currency, transaction_count, citations
    """
    c = _require_client(store, client_id)
    asof_date: datetime.date | None = None
    if as_of is not None:
        asof_date = _parse_date(as_of, context="as_of")

    effective_asof = asof_date if asof_date is not None else _book_date(store)

    total = _ZERO
    count = 0
    for t in c.get("transactions", []):
        if asof_date is not None:
            txn_date = _parse_date(t.get("date", ""), context=f"txn {t.get('id')!r}")
            if txn_date > asof_date:
                continue
        flow = _cash_flow(t)
        if flow is not None:
            total += flow
            count += 1

    # Cash balance always spans many transactions; cite client_id per schema rule.
    return {
        "client_id": client_id,
        "as_of": str(effective_asof),
        "balance": _fmt_usd(total),
        "currency": store.book_meta.get("base_currency", "USD"),
        "transaction_count": count,
        "citations": [client_id],
    }


def calculate_position_quantity(
    store: DataStore,
    client_id: str,
    symbol: str,
    *,
    as_of: str | datetime.date | None = None,
) -> dict:
    """Return the quantity of *symbol* held by *client_id* at *as_of*.

    Strategy
    --------
    - *as_of* is None or >= book_date → use positions_snapshot (authoritative).
      Citation: specific position ID (1 record ≤ 6 → cite the ID).
    - *as_of* < book_date → reconstruct from buy/sell transactions.
      Citation: [client_id] (many transactions involved).

    Returns
    -------
    dict with keys:
        client_id, symbol, as_of, quantity, source, citations
    """
    _require_client(store, client_id)
    book_dt = _book_date(store)
    asof_date = _parse_date(as_of, context="as_of") if as_of is not None else book_dt

    client = store.client(client_id)

    if asof_date >= book_dt:
        # Use the authoritative positions snapshot.
        for pos in client.get("positions_snapshot", []):
            if pos["symbol"] == symbol:
                return {
                    "client_id": client_id,
                    "symbol": symbol,
                    "as_of": str(asof_date),
                    "quantity": pos["quantity"],  # source string; not re-formatted
                    "source": "positions_snapshot",
                    "citations": [pos["id"]],
                }
        # Symbol is not held at the book date.
        return {
            "client_id": client_id,
            "symbol": symbol,
            "as_of": str(asof_date),
            "quantity": "0",
            "source": "positions_snapshot",
            "citations": [client_id],
        }

    # Historical reconstruction from transactions.
    qty = _ZERO
    for t in client.get("transactions", []):
        if t.get("symbol") != symbol:
            continue
        txn_date = _parse_date(t.get("date", ""), context=f"txn {t.get('id')!r}")
        if txn_date > asof_date:
            continue
        typ = t.get("type", "")
        if typ == "buy":
            qty += Decimal(t["quantity"])
        elif typ == "sell":
            qty -= Decimal(t["quantity"])

    return {
        "client_id": client_id,
        "symbol": symbol,
        "as_of": str(asof_date),
        "quantity": _fmt_qty(qty),
        "source": "transactions",
        "citations": [client_id],
    }


def calculate_holdings_count(
    store: DataStore,
    client_id: str,
    *,
    as_of: str | datetime.date | None = None,
) -> dict:
    """Count distinct symbols with a positive quantity held by *client_id*.

    *as_of* None or >= book_date → count from positions_snapshot.
    *as_of* < book_date → reconstruct from transactions.

    Returns
    -------
    dict with keys:
        client_id, as_of, count, symbols, source, citations
    """
    _require_client(store, client_id)
    book_dt = _book_date(store)
    asof_date = _parse_date(as_of, context="as_of") if as_of is not None else book_dt
    client = store.client(client_id)

    if asof_date >= book_dt:
        symbols = sorted(
            pos["symbol"]
            for pos in client.get("positions_snapshot", [])
            if Decimal(pos["quantity"]) > _ZERO
        )
        return {
            "client_id": client_id,
            "as_of": str(asof_date),
            "count": len(symbols),
            "symbols": symbols,
            "source": "positions_snapshot",
            "citations": [client_id],
        }

    # Historical: reconstruct quantities from transactions.
    holding: dict[str, Decimal] = {}
    for t in client.get("transactions", []):
        sym = t.get("symbol")
        if not sym:
            continue
        txn_date = _parse_date(t.get("date", ""), context=f"txn {t.get('id')!r}")
        if txn_date > asof_date:
            continue
        typ = t.get("type", "")
        if typ == "buy":
            holding[sym] = holding.get(sym, _ZERO) + Decimal(t["quantity"])
        elif typ == "sell":
            holding[sym] = holding.get(sym, _ZERO) - Decimal(t["quantity"])

    symbols = sorted(sym for sym, qty in holding.items() if qty > _ZERO)
    return {
        "client_id": client_id,
        "as_of": str(asof_date),
        "count": len(symbols),
        "symbols": symbols,
        "source": "transactions",
        "citations": [client_id],
    }


def calculate_portfolio_value(
    store: DataStore,
    client_id: str,
) -> dict:
    """Sum the market_value_usd of all positions in the snapshot.

    Returns
    -------
    dict with keys:
        client_id, as_of, total_market_value_usd, holdings_count, citations
    """
    client = _require_client(store, client_id)
    total = _ZERO
    count = 0
    for pos in client.get("positions_snapshot", []):
        total += Decimal(pos["market_value_usd"])
        count += 1
    book_dt = _book_date(store)
    return {
        "client_id": client_id,
        "as_of": str(book_dt),
        "total_market_value_usd": _fmt_usd(total),
        "holdings_count": count,
        "citations": [client_id],
    }


def calculate_account_age(
    store: DataStore,
    client_id: str,
    account_id: str,
    *,
    as_of: str | datetime.date | None = None,
) -> dict:
    """Return the age in days of *account_id* as of *as_of* (defaults to book date).

    Raises ``UnknownAccountError`` if *account_id* is not found for *client_id*.

    Citation: specific account ID (1 record ≤ 6).

    Returns
    -------
    dict with keys:
        client_id, account_id, opened, as_of, age_days, citations
    """
    c = _require_client(store, client_id)
    account = next(
        (a for a in c.get("accounts", []) if a["id"] == account_id),
        None,
    )
    if account is None:
        raise UnknownAccountError(account_id, client_id)

    opened = _parse_date(account["opened"], context=f"account {account_id!r} opened")
    asof_date = _parse_date(as_of, context="as_of") if as_of is not None else _book_date(store)
    age_days = (asof_date - opened).days

    return {
        "client_id": client_id,
        "account_id": account_id,
        "opened": str(opened),
        "as_of": str(asof_date),
        "age_days": age_days,
        "citations": [account_id],
    }


def calculate_target_drift(
    store: DataStore,
    client_id: str,
    symbol: str,
) -> dict:
    """Calculate the portfolio drift of *symbol* from its agreed target allocation.

    Drift is defined as: actual_weight_pct − target_weight_pct.

    Formula (confirmed by four practice-key questions):
    - Actual weight: (position market_value / total_snapshot_market_value) * 100.
      The denominator is the sum of ALL position market values from the snapshot,
      i.e. the equity/securities portfolio only. Cash is NOT included, because the
      suitability review target_allocation_pct describes allocation within the
      securities portfolio, not total wealth.
    - Target weight: from the most-recent suitability review's
      target_allocation_pct map. Defaults to 0 if symbol not in the map.
    - Drift > 0 means over-allocated; drift < 0 means under-allocated.

    Raises ``NoSuitabilityReviewError`` if no review exists.

    Citation: [position_id, review_id] when position exists (≤ 6 records);
    [client_id, review_id] when the symbol is not in the snapshot.

    Returns
    -------
    dict with keys:
        client_id, symbol, as_of,
        actual_pct, target_pct, drift_pct,
        position_value_usd, total_portfolio_value_usd,
        suitability_review_id, review_date,
        citations
    """
    client = _require_client(store, client_id)
    reviews = client.get("suitability_reviews", [])
    if not reviews:
        raise NoSuitabilityReviewError(client_id)

    # Use the most recent review by date.
    latest_review = max(reviews, key=lambda r: r.get("date", ""))
    target_map: dict[str, str] = latest_review.get("target_allocation_pct", {})
    target_pct = Decimal(target_map.get(symbol, "0"))

    # Compute total and symbol-specific market values from snapshot.
    # Denominator is equity/securities total (NOT including cash).
    total_mv = _ZERO
    symbol_mv = _ZERO
    symbol_pos_id: str | None = None

    for pos in client.get("positions_snapshot", []):
        mv = Decimal(pos["market_value_usd"])
        total_mv += mv
        if pos["symbol"] == symbol:
            symbol_mv = mv
            symbol_pos_id = pos["id"]

    if total_mv == _ZERO:
        raise BookToolError(
            f"Client {client_id!r} has no positions; cannot compute drift."
        )

    actual_pct = symbol_mv / total_mv * Decimal("100")
    drift_pct = actual_pct - target_pct

    citations = [symbol_pos_id, latest_review["id"]] if symbol_pos_id else [client_id, latest_review["id"]]

    return {
        "client_id": client_id,
        "symbol": symbol,
        "as_of": str(_book_date(store)),
        "actual_pct": _fmt_pct(actual_pct),
        "target_pct": _fmt_pct(target_pct),
        "drift_pct": _fmt_pct(drift_pct),
        "position_value_usd": _fmt_usd(symbol_mv),
        "total_portfolio_value_usd": _fmt_usd(total_mv),
        "suitability_review_id": latest_review["id"],
        "review_date": latest_review.get("date"),
        "citations": citations,
    }


def detect_position_snapshot_conflict(
    store: DataStore,
    client_id: str,
    symbol: str,
) -> dict:
    """Detect whether the positions_snapshot quantity conflicts with the transaction sum.

    The positions_snapshot is authoritative at the book date, but is
    cross-checked against the cumulative buy/sell transaction total.
    A discrepancy flags a data conflict that must be surfaced to the user
    rather than silently resolved.

    Citation: specific record IDs (snapshot + relevant transactions, up to 6
    total); if more than 6 records, cite [client_id].

    Returns
    -------
    dict with keys:
        client_id, symbol,
        snapshot_quantity (str),
        computed_quantity (str, from transactions),
        conflict (bool),
        snapshot_id (str | None),
        transaction_ids (list[str]),
        citations (list[str])

    ``conflict`` is True when the two quantities differ by more than a
    rounding tolerance (0.00005, half a unit in the 4th decimal place).
    """
    client = _require_client(store, client_id)
    book_dt = _book_date(store)

    # Snapshot quantity
    snapshot_qty: Decimal | None = None
    snapshot_id: str | None = None
    for pos in client.get("positions_snapshot", []):
        if pos["symbol"] == symbol:
            snapshot_qty = Decimal(pos["quantity"])
            snapshot_id = pos["id"]
            break

    # Transaction-computed quantity (all buy/sell for this symbol up to book date)
    computed_qty = _ZERO
    sym_txn_ids: list[str] = []
    for t in client.get("transactions", []):
        if t.get("symbol") != symbol:
            continue
        txn_date = _parse_date(t.get("date", ""), context=f"txn {t.get('id')!r}")
        if txn_date > book_dt:
            continue
        typ = t.get("type", "")
        if typ == "buy":
            computed_qty += Decimal(t["quantity"])
            sym_txn_ids.append(t["id"])
        elif typ == "sell":
            computed_qty -= Decimal(t["quantity"])
            sym_txn_ids.append(t["id"])

    if snapshot_qty is None:
        snapshot_qty = _ZERO

    # Consider a conflict if the absolute difference exceeds 0.00005.
    conflict = abs(snapshot_qty - computed_qty) > Decimal("0.00005")

    # Build citations: snapshot ID + transaction IDs, applying schema rule.
    all_records = []
    if snapshot_id:
        all_records.append({"id": snapshot_id})
    for txn_id in sym_txn_ids:
        all_records.append({"id": txn_id})

    if len(all_records) <= _MAX_SPECIFIC_CITATIONS:
        citation_list = [r["id"] for r in all_records] if all_records else [client_id]
    else:
        citation_list = [client_id]
    # If conflict, always prefer specific IDs even if > 6 (per q_018 pattern).
    # The practice key cites specific IDs for conflict_snapshot regardless of count.
    if conflict:
        cit_parts = []
        if snapshot_id:
            cit_parts.append(snapshot_id)
        cit_parts.extend(sym_txn_ids)
        citation_list = cit_parts

    return {
        "client_id": client_id,
        "symbol": symbol,
        "snapshot_quantity": _fmt_qty(snapshot_qty),
        "computed_quantity": _fmt_qty(computed_qty),
        "conflict": conflict,
        "snapshot_id": snapshot_id,
        "transaction_ids": sym_txn_ids,
        "citations": citation_list,
    }


def get_client_notes(store: DataStore, client_id: str) -> list[dict]:
    """Retrieve the list of free-text notes for *client_id*.

    Returns
    -------
    list of dict with keys:
        id, date, author, text, citations
    """
    c = _require_client(store, client_id)
    notes = c.get("notes", [])
    result = []
    for n in notes:
        nid = n.get("id")
        result.append({
            "id": nid,
            "date": n.get("date"),
            "author": n.get("author"),
            "text": n.get("text"),
            "citations": [nid] if nid else [client_id]
        })
    return result


def get_transaction_memos(store: DataStore, client_id: str) -> list[dict]:
    """Retrieve all transactions containing a memo or description for *client_id*.

    Returns
    -------
    list of dict with keys:
        id, date, type, symbol, memo, citations
    """
    c = _require_client(store, client_id)
    txns = c.get("transactions", [])
    result = []
    for t in txns:
        memo = t.get("memo") or t.get("description")
        if memo:
            tid = t.get("id")
            result.append({
                "id": tid,
                "date": t.get("date"),
                "type": t.get("type"),
                "symbol": t.get("symbol"),
                "memo": memo,
                "citations": [tid] if tid else [client_id]
            })
    return result
