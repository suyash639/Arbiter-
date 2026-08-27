"""
tests/test_data_store.py
------------------------
Tests for arbiter.data_store.DataStore.

All tests run against the actual practice data files.  They are read-only;
nothing in this test suite modifies data/.

Coverage required:
 1. Client book loads successfully.
 2. Market data loads successfully.
 3. Known client_id resolves through clients index.
 4. Known market symbol resolves through market_instruments.
 5. Market prices grouped by symbol and sorted ascending by date.
 6. Market news grouped by symbol and sorted ascending by date.
 7. Missing / malformed data raises DataStoreError.
 8. Financial values remain exact decimal strings (never silently float).
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

from arbiter.data_store import DataStore, DataStoreError


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
BOOK_PATH = DATA_DIR / "client_book.json"
MARKET_PATH = DATA_DIR / "market_data.json"


@pytest.fixture(scope="module")
def store() -> DataStore:
    """Load the full practice DataStore once for the entire test module."""
    return DataStore.load(BOOK_PATH, MARKET_PATH)


# ---------------------------------------------------------------------------
# 1. Client book loads successfully
# ---------------------------------------------------------------------------
class TestBookLoad:
    def test_store_is_created(self, store):
        assert store is not None

    def test_client_ids_is_non_empty_tuple(self, store):
        assert isinstance(store.client_ids, tuple)
        assert len(store.client_ids) > 0

    def test_book_meta_has_required_keys(self, store):
        meta = store.book_meta
        assert "as_of" in meta
        assert "base_currency" in meta

    def test_book_meta_as_of_is_string(self, store):
        # Should be an ISO date string, e.g. "2026-07-31"
        as_of = store.book_meta["as_of"]
        assert isinstance(as_of, str) and len(as_of) == 10


# ---------------------------------------------------------------------------
# 2. Market data loads successfully
# ---------------------------------------------------------------------------
class TestMarketLoad:
    def test_instruments_non_empty(self, store):
        assert len(store._instruments) > 0  # noqa: SLF001

    def test_covered_symbols_non_empty(self, store):
        assert len(store.covered_symbols) > 0

    def test_market_meta_has_as_of(self, store):
        assert "as_of" in store.market_meta
        assert isinstance(store.market_meta["as_of"], str)

    def test_covered_symbols_is_frozenset(self, store):
        assert isinstance(store.covered_symbols, frozenset)


# ---------------------------------------------------------------------------
# 3. Known client_id resolves through clients index
# ---------------------------------------------------------------------------
class TestClientIndex:
    KNOWN_ID = "cli_1001"

    def test_known_client_resolves(self, store):
        c = store.client(self.KNOWN_ID)
        assert isinstance(c, dict)
        assert c["id"] == self.KNOWN_ID

    def test_unknown_client_raises_key_error(self, store):
        with pytest.raises(KeyError):
            store.client("cli_DOES_NOT_EXIST")

    def test_client_has_expected_keys(self, store):
        c = store.client(self.KNOWN_ID)
        for key in ("id", "name", "kyc", "accounts", "transactions",
                    "positions_snapshot"):
            assert key in c, f"Expected key {key!r} missing from client record"

    def test_client_id_cli_1014_exists(self, store):
        # Used heavily in practice questions.
        c = store.client("cli_1014")
        assert c["id"] == "cli_1014"

    def test_all_client_ids_resolve(self, store):
        for cid in store.client_ids:
            c = store.client(cid)
            assert c["id"] == cid


# ---------------------------------------------------------------------------
# 4. Known market symbol resolves through market_instruments
# ---------------------------------------------------------------------------
class TestInstrumentIndex:
    KNOWN_SYMBOL = "AAPL"

    def test_known_symbol_resolves(self, store):
        inst = store.instrument(self.KNOWN_SYMBOL)
        assert inst is not None
        assert inst["symbol"] == self.KNOWN_SYMBOL

    def test_unknown_symbol_returns_none(self, store):
        assert store.instrument("NOT_A_REAL_SYMBOL") is None

    def test_instrument_has_sector(self, store):
        inst = store.instrument(self.KNOWN_SYMBOL)
        assert "sector" in inst

    def test_all_covered_symbols_have_instruments(self, store):
        for sym in store.covered_symbols:
            inst = store.instrument(sym)
            assert inst is not None, (
                f"Covered symbol {sym!r} has no instrument record."
            )


# ---------------------------------------------------------------------------
# 5. Market prices grouped by symbol and sorted ascending by date
# ---------------------------------------------------------------------------
class TestPriceIndex:
    KNOWN_SYMBOL = "AAPL"

    def test_known_symbol_has_prices(self, store):
        p = store.prices(self.KNOWN_SYMBOL)
        assert isinstance(p, list)
        assert len(p) > 0

    def test_unknown_symbol_returns_empty_list(self, store):
        p = store.prices("UNKNOWN_XYZ")
        assert p == []

    def test_prices_sorted_ascending(self, store):
        for sym in store.covered_symbols:
            plist = store.prices(sym)
            dates = [e["date"] for e in plist]
            assert dates == sorted(dates), (
                f"Prices for {sym!r} are not sorted ascending by date."
            )

    def test_price_entry_has_required_keys(self, store):
        entry = store.prices(self.KNOWN_SYMBOL)[0]
        assert "date" in entry
        assert "close" in entry

    def test_all_covered_symbols_have_prices(self, store):
        for sym in store.covered_symbols:
            assert len(store.prices(sym)) > 0, (
                f"Covered symbol {sym!r} has no price entries."
            )

    def test_price_dates_are_first_of_month(self, store):
        """Prices are month-start closes; all dates must end in '-01'."""
        for sym in store.covered_symbols:
            for entry in store.prices(sym):
                assert entry["date"].endswith("-01"), (
                    f"Price date {entry['date']!r} for {sym!r} is not "
                    f"a month-start date (expected YYYY-MM-01)."
                )


# ---------------------------------------------------------------------------
# 6. Market news grouped by symbol and sorted ascending by date
# ---------------------------------------------------------------------------
class TestNewsIndex:
    KNOWN_SYMBOL = "AAPL"

    def test_known_symbol_has_news(self, store):
        n = store.news_for(self.KNOWN_SYMBOL)
        assert isinstance(n, list)
        assert len(n) > 0

    def test_unknown_symbol_returns_empty_list(self, store):
        n = store.news_for("UNKNOWN_XYZ")
        assert n == []

    def test_news_sorted_ascending(self, store):
        for sym, items in store._news.items():  # noqa: SLF001
            dates = [e["date"] for e in items]
            assert dates == sorted(dates), (
                f"News for {sym!r} is not sorted ascending by date."
            )

    def test_news_entry_has_required_keys(self, store):
        entry = store.news_for(self.KNOWN_SYMBOL)[0]
        for key in ("id", "date", "symbol", "headline"):
            assert key in entry


# ---------------------------------------------------------------------------
# 7. Missing / malformed data raises DataStoreError
# ---------------------------------------------------------------------------
class TestValidationErrors:
    def test_missing_book_file_raises(self, tmp_path):
        with pytest.raises(DataStoreError, match="Cannot read"):
            DataStore.load(tmp_path / "nonexistent.json", MARKET_PATH)

    def test_missing_market_file_raises(self, tmp_path):
        with pytest.raises(DataStoreError, match="Cannot read"):
            DataStore.load(BOOK_PATH, tmp_path / "nonexistent.json")

    def test_invalid_json_book_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("NOT VALID JSON", encoding="utf-8")
        with pytest.raises(DataStoreError, match="Cannot parse"):
            DataStore.load(bad, MARKET_PATH)

    def test_book_missing_clients_key_raises(self, tmp_path):
        bad = tmp_path / "book.json"
        bad.write_text(json.dumps({"meta": {}}), encoding="utf-8")
        with pytest.raises(DataStoreError, match="Missing required keys"):
            DataStore.load(bad, MARKET_PATH)

    def test_book_missing_meta_key_raises(self, tmp_path):
        bad = tmp_path / "book.json"
        bad.write_text(json.dumps({"clients": []}), encoding="utf-8")
        with pytest.raises(DataStoreError, match="Missing required keys"):
            DataStore.load(bad, MARKET_PATH)

    def test_empty_clients_list_raises(self, tmp_path):
        bad = tmp_path / "book.json"
        bad.write_text(json.dumps({"meta": {}, "clients": []}), encoding="utf-8")
        with pytest.raises(DataStoreError, match="empty"):
            DataStore.load(bad, MARKET_PATH)

    def test_duplicate_client_id_raises(self, tmp_path):
        client = {
            "id": "cli_dup",
            "name": "Test",
            "kyc": {},
            "accounts": [],
            "transactions": [],
            "positions_snapshot": [],
        }
        bad = tmp_path / "book.json"
        bad.write_text(json.dumps({"meta": {}, "clients": [client, client]}),
                       encoding="utf-8")
        with pytest.raises(DataStoreError, match="Duplicate"):
            DataStore.load(bad, MARKET_PATH)

    def test_market_missing_meta_raises(self, tmp_path):
        bad = tmp_path / "market.json"
        bad.write_text(
            json.dumps({"instruments": [], "prices": {}, "news": []}),
            encoding="utf-8"
        )
        with pytest.raises(DataStoreError, match="Missing required keys"):
            DataStore.load(BOOK_PATH, bad)

    def test_close_as_float_in_json_raises(self, tmp_path):
        """If a price close value is stored as a JSON number (float), the
        DataStore must reject it to protect financial precision."""
        # Build a minimal market file where close is a number, not a string.
        market = {
            "meta": {"covered_symbols": ["TST"], "as_of": "2026-07-31"},
            "instruments": [{"symbol": "TST", "sector": "Test"}],
            "prices": {
                "TST": [{"date": "2026-01-01", "close": 123.45}]  # <-- number!
            },
            "news": [],
        }
        bad = tmp_path / "market.json"
        bad.write_text(json.dumps(market), encoding="utf-8")
        with pytest.raises(DataStoreError, match="decimal"):
            DataStore.load(BOOK_PATH, bad)


# ---------------------------------------------------------------------------
# 8. Financial values remain exact strings — never silently converted to float
# ---------------------------------------------------------------------------
class TestFinancialPrecision:
    def test_close_values_are_strings(self, store):
        """Every price close must be a plain str, not int or float."""
        for sym in store.covered_symbols:
            for entry in store.prices(sym):
                close = entry["close"]
                assert isinstance(close, str), (
                    f"Price close for {sym!r} on {entry['date']!r} is "
                    f"{type(close).__name__!r}, expected str."
                )

    def test_close_values_are_decimal_compatible(self, store):
        """Every close value string must be parseable as Decimal."""
        for sym in store.covered_symbols:
            for entry in store.prices(sym):
                close_str = entry["close"]
                try:
                    Decimal(close_str)
                except InvalidOperation:
                    pytest.fail(
                        f"Price close {close_str!r} for {sym!r} on "
                        f"{entry['date']!r} is not a valid Decimal string."
                    )

    def test_transaction_amounts_are_strings(self, store):
        """Dollar amounts in transactions must remain strings from JSON."""
        for cid in store.client_ids:
            c = store.client(cid)
            for txn in c["transactions"]:
                for field in ("amount_usd", "net_usd", "gross_usd",
                              "fees_usd", "price_usd"):
                    if field in txn:
                        val = txn[field]
                        assert isinstance(val, str), (
                            f"Transaction {txn.get('id')!r} field {field!r} "
                            f"is {type(val).__name__!r}, expected str."
                        )

    def test_position_quantities_are_strings(self, store):
        """Position quantities and values must remain strings."""
        for cid in store.client_ids:
            c = store.client(cid)
            for pos in c["positions_snapshot"]:
                for field in ("quantity", "avg_cost_usd", "market_value_usd"):
                    if field in pos:
                        val = pos[field]
                        assert isinstance(val, str), (
                            f"Position {pos.get('id')!r} field {field!r} "
                            f"is {type(val).__name__!r}, expected str."
                        )

    def test_summary_counts_are_ints(self, store):
        s = store.summary()
        assert isinstance(s["clients"], int)
        assert isinstance(s["instruments"], int)
        assert s["clients"] > 0
        assert s["instruments"] > 0
