"""
mini_supabase.py — an in-memory fake Supabase client that actually filters.

Every other fake `admin_client` in this test suite is hand-rolled per test
and returns whatever canned `data` the test author hardcoded, regardless of
which table/column/value the code under test queried for. That pattern can
prove "my code calls .execute() and handles the response" but is structurally
incapable of catching a bug where the code queries the WRONG column — e.g.
filtering by `username` when it should filter by `id`. Both production bugs
this suite's isolation tests exist to catch (the missing `school_name`
column, the "likha" username collision) were invisible to 2000+ tests built
that way, precisely because none of them modeled real row data.

MiniSupabaseClient instead holds real rows per table and evaluates `.eq()` /
`.neq()` / `.ilike()` / `.in_()` / `.gte()` / `.lte()` against them, so a test
that seeds two DIFFERENT profiles sharing a username and then asserts "only
MY rows come back" will actually fail if the code queries by the wrong key —
the same way it would fail against a real Postgres table.

Deliberately supports only the query-builder methods the routes under test
use — grep for `admin_client.table(` in the module you're testing and extend
`_Query` if a chain you need isn't here yet.
"""
from __future__ import annotations

import re
from typing import Any


class _ExecResult:
    def __init__(self, data: list[dict]):
        self.data = data


class _Query:
    def __init__(self, rows: list[dict], on_insert=None):
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []  # (op, col, val)
        self._limit: int | None = None
        self._insert_payload: dict | list[dict] | None = None
        self._on_insert = on_insert
        self._single = False

    # ── filters ──────────────────────────────────────────────────────────
    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val))
        return self

    def ilike(self, col, val):
        self._filters.append(("ilike", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self._filters.append(("lte", col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    # ── writes ───────────────────────────────────────────────────────────
    def insert(self, payload):
        self._insert_payload = payload
        return self

    # ── terminal ─────────────────────────────────────────────────────────
    def execute(self):
        if self._insert_payload is not None:
            rows = self._insert_payload if isinstance(self._insert_payload, list) else [self._insert_payload]
            for row in rows:
                self._rows.append(dict(row))
                if self._on_insert:
                    self._on_insert(row)
            return _ExecResult(list(rows))

        matched = [r for r in self._rows if self._row_matches(r)]
        order = getattr(self, "_order", None)
        if order:
            col, desc = order
            matched.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._limit is not None:
            matched = matched[: self._limit]
        if self._single:
            return _ExecResult(matched[0] if matched else None)
        return _ExecResult(matched)

    def _row_matches(self, row: dict) -> bool:
        for op, col, val in self._filters:
            cell = row.get(col)
            if op == "eq" and cell != val:
                return False
            if op == "neq" and cell == val:
                return False
            if op == "ilike":
                pattern = re.escape(str(val)).replace(r"\%", ".*")
                if not re.fullmatch(pattern, str(cell or ""), re.IGNORECASE):
                    return False
            if op == "in" and cell not in val:
                return False
            if op == "gte" and (cell is None or cell < val):
                return False
            if op == "lte" and (cell is None or cell > val):
                return False
        return True


class MiniSupabaseClient:
    """
    Minimal in-memory Supabase stand-in. Seed rows directly via
    `client.tables["profiles"].append({...})`, or let routes insert them.
    """

    def __init__(self, table_names: list[str]):
        self.tables: dict[str, list[dict]] = {name: [] for name in table_names}

    def table(self, name: str) -> _Query:
        if name not in self.tables:
            self.tables[name] = []
        return _Query(self.tables[name])
