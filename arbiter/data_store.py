"""
arbiter/data_store.py
---------------------
In-memory data store for the Arbiter service.

Loaded ONCE at application startup (via a FastAPI lifespan or direct call).
The two source files must never be re-fetched per-question; this module is the
single access point for all agent tools.

Public surface
--------------
DataStore.load(book_path, market_path) -> DataStore
    Class-method factory.  Validates structure, builds indexes, returns an
    immutable-ish snapshot.  Fails loudly on any structural violation.

DataStore.client(client_id) -> dict
    Returns the raw client object (never mutate the result).

DataStore.instrument(symbol) -> dict | None
    Returns the instrument metadata for a covered symbol.

DataStore.prices(symbol) -> list[dict]
    Returns the sorted (ascending date) price list for a covered symbol.
    Each entry: {"date": "YYYY-MM-DD", "close": "<decimal string>"}

DataStore.news_for(symbol) -> list[dict]
    Returns the sorted (ascending date) news list for a covered symbol.

DataStore.covered_symbols -> frozenset[str]
    The exact set of symbols declared in market_data["meta"]["covered_symbols"].

DataStore.book_meta -> dict
    The "meta" block from client_book.json (as_of date, currency, note).

DataStore.market_meta -> dict
    The "meta" block from market_data.json.

DataStore.client_ids -> tuple[str, ...]
    All client IDs present in the book (sorted).

Design principles:
- All financial values stay as the original decimal strings from JSON.
  Conversion to Decimal happens only inside calculation tools, never here.
- Indexes are plain dicts/lists for O(1) lookups.
- Source dicts are NOT mutated; the store references the parsed originals.
- No sensitive data (PAN, bank, names) is printed anywhere in this module.
- DataStoreError is the single error type for structural validation failures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DataStoreError(ValueError):
    """Raised when the source data is structurally invalid or missing."""


class DataStore:
    """Indexed, in-memory view of the client book and market data.

    Attributes are read-only by convention; the underlying dicts should never
    be mutated after load().
    """

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, book_path: Path, market_path: Path) -> "DataStore":
        """Load both JSON files, validate structure, build indexes.

        Parameters
        ----------
        book_path:
            Absolute path to data/client_book.json.
        market_path:
            Absolute path to data/market_data.json.

        Returns
        -------
        DataStore
            Fully indexed snapshot ready for agent queries.

        Raises
        ------
        DataStoreError
            If either file is missing, unparseable, or structurally invalid.
        """
        book = cls._load_json(book_path, "client_book")
        market = cls._load_json(market_path, "market_data")

        store = cls.__new__(cls)
        store._init_book(book)
        store._init_market(market)
        return store

    # ------------------------------------------------------------------
    # Public queries
    # ------------------------------------------------------------------
    def client(self, client_id: str) -> dict:
        """Return the raw client object for *client_id*.

        Raises
        ------
        KeyError
            If *client_id* is not in the book.
        """
        try:
            return self._clients[client_id]
        except KeyError:
            raise KeyError(
                f"client_id {client_id!r} not found in the book. "
                f"Known ids: {len(self._clients)} clients indexed."
            ) from None

    def instrument(self, symbol: str) -> dict | None:
        """Return instrument metadata for a covered *symbol*, or None."""
        return self._instruments.get(symbol)

    def prices(self, symbol: str) -> list[dict]:
        """Return the sorted price list for *symbol* (empty if not covered)."""
        return self._prices.get(symbol, [])

    def news_for(self, symbol: str) -> list[dict]:
        """Return the sorted news list for *symbol* (empty if none)."""
        return self._news.get(symbol, [])

    @property
    def covered_symbols(self) -> frozenset:
        """Exact set of symbols declared in market_data meta."""
        return self._covered_symbols

    @property
    def book_meta(self) -> dict:
        """Meta block from client_book.json (as_of, base_currency, etc.)."""
        return self._book_meta

    @property
    def market_meta(self) -> dict:
        """Meta block from market_data.json."""
        return self._market_meta

    @property
    def client_ids(self) -> tuple:
        """Sorted tuple of all client IDs in the book."""
        return self._client_ids

    # ------------------------------------------------------------------
    # Private initialisation helpers
    # ------------------------------------------------------------------
    def _init_book(self, book: dict) -> None:
        """Validate the client book and build the clients index."""
        _require_keys(book, ("meta", "clients"), context="client_book root")

        meta = book["meta"]
        if not isinstance(meta, dict):
            raise DataStoreError("client_book['meta'] must be a JSON object.")

        clients_list = book["clients"]
        if not isinstance(clients_list, list):
            raise DataStoreError("client_book['clients'] must be a JSON array.")
        if not clients_list:
            raise DataStoreError("client_book['clients'] is empty.")

        clients: dict[str, Any] = {}
        for idx, c in enumerate(clients_list):
            if not isinstance(c, dict):
                raise DataStoreError(
                    f"client_book['clients'][{idx}] is not a JSON object."
                )
            _require_keys(
                c,
                ("id", "name", "kyc", "accounts", "transactions", "positions_snapshot"),
                context=f"client at index {idx}",
            )
            cid = c["id"]
            if not isinstance(cid, str) or not cid.strip():
                raise DataStoreError(
                    f"client_book['clients'][{idx}]['id'] must be a non-empty string."
                )
            if cid in clients:
                raise DataStoreError(
                    f"Duplicate client_id {cid!r} at index {idx}."
                )
            clients[cid] = c

        self._book_meta: dict = meta
        self._clients: dict[str, Any] = clients
        self._client_ids: tuple = tuple(sorted(clients.keys()))

    def _init_market(self, market: dict) -> None:
        """Validate market data and build instruments / prices / news indexes."""
        _require_keys(market, ("meta", "instruments", "prices", "news"),
                      context="market_data root")

        meta = market["meta"]
        if not isinstance(meta, dict):
            raise DataStoreError("market_data['meta'] must be a JSON object.")

        covered_raw = meta.get("covered_symbols")
        if not isinstance(covered_raw, list) or not covered_raw:
            raise DataStoreError(
                "market_data['meta']['covered_symbols'] must be a non-empty list."
            )
        covered = frozenset(covered_raw)

        # --- instruments ---------------------------------------------------
        instruments_list = market["instruments"]
        if not isinstance(instruments_list, list):
            raise DataStoreError("market_data['instruments'] must be a JSON array.")

        instruments: dict[str, Any] = {}
        for idx, inst in enumerate(instruments_list):
            if not isinstance(inst, dict):
                raise DataStoreError(
                    f"market_data['instruments'][{idx}] is not a JSON object."
                )
            _require_keys(inst, ("symbol",),
                          context=f"market instrument at index {idx}")
            sym = inst["symbol"]
            if sym in instruments:
                raise DataStoreError(
                    f"Duplicate instrument symbol {sym!r} at index {idx}."
                )
            instruments[sym] = inst

        # Warn structurally if covered_symbols and instruments diverge.
        missing_instr = covered - set(instruments)
        if missing_instr:
            raise DataStoreError(
                f"Symbols declared in covered_symbols lack instrument records: "
                f"{sorted(missing_instr)}"
            )

        # --- prices --------------------------------------------------------
        prices_raw = market["prices"]
        if not isinstance(prices_raw, dict):
            raise DataStoreError("market_data['prices'] must be a JSON object.")

        prices: dict[str, list] = {}
        for sym, plist in prices_raw.items():
            if not isinstance(plist, list):
                raise DataStoreError(
                    f"market_data['prices'][{sym!r}] must be a JSON array."
                )
            validated: list[dict] = []
            for entry in plist:
                _require_keys(entry, ("date", "close"),
                              context=f"price entry for {sym!r}")
                if not isinstance(entry["close"], str):
                    raise DataStoreError(
                        f"market_data['prices'][{sym!r}] close value must be a "
                        f"string (decimal), got {type(entry['close']).__name__!r}. "
                        f"Financial values must never be silently converted to float."
                    )
                validated.append(entry)
            # Sort ascending by date string (ISO-8601 sorts lexicographically).
            prices[sym] = sorted(validated, key=lambda e: e["date"])

        # --- news ----------------------------------------------------------
        news_list = market["news"]
        if not isinstance(news_list, list):
            raise DataStoreError("market_data['news'] must be a JSON array.")

        news: dict[str, list] = {}
        for idx, item in enumerate(news_list):
            if not isinstance(item, dict):
                raise DataStoreError(
                    f"market_data['news'][{idx}] is not a JSON object."
                )
            _require_keys(item, ("id", "date", "symbol"),
                          context=f"news item at index {idx}")
            sym = item["symbol"]
            news.setdefault(sym, []).append(item)

        # Sort each symbol's news ascending by date.
        for sym in news:
            news[sym] = sorted(news[sym], key=lambda e: e["date"])

        self._market_meta: dict = meta
        self._covered_symbols: frozenset = covered
        self._instruments: dict[str, Any] = instruments
        self._prices: dict[str, list] = prices
        self._news: dict[str, list] = news

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_json(path: Path, label: str) -> dict:
        """Read and parse a JSON file, raising DataStoreError on failure."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataStoreError(
                f"Cannot read {label} file at {path}: {exc}"
            ) from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataStoreError(
                f"Cannot parse {label} file at {path}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise DataStoreError(
                f"{label} file must contain a JSON object at the top level."
            )
        return data

    # ------------------------------------------------------------------
    # Summary (safe: no sensitive data)
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        """Return a non-sensitive summary of index counts for health checks."""
        return {
            "clients": len(self._clients),
            "instruments": len(self._instruments),
            "price_symbols": len(self._prices),
            "news_symbols": len(self._news),
            "covered_symbols": len(self._covered_symbols),
            "book_as_of": self._book_meta.get("as_of"),
            "market_as_of": self._market_meta.get("as_of"),
        }

    def __repr__(self) -> str:  # noqa: D105
        s = self.summary()
        return (
            f"DataStore(clients={s['clients']}, "
            f"instruments={s['instruments']}, "
            f"price_symbols={s['price_symbols']}, "
            f"news_symbols={s['news_symbols']})"
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------
def _require_keys(obj: dict, keys: tuple, *, context: str) -> None:
    """Raise DataStoreError if any of *keys* are missing from *obj*."""
    missing = [k for k in keys if k not in obj]
    if missing:
        raise DataStoreError(
            f"Missing required keys {missing!r} in {context}. "
            f"Present keys: {sorted(obj.keys())}"
        )
