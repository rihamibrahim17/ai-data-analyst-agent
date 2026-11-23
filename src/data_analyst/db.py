"""Safe SQLite access: read-only connection, time limit and row cap (layers 2 and 3 of the guardrails)."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


class QueryError(Exception):
    """The database rejected or aborted the query."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple]
    truncated: bool = False


class Database:
    def __init__(self, path: str | Path, max_rows: int = 200, timeout_s: float = 5.0):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Database not found: {self.path}. Create it with: python -m data_analyst.sample_data")
        self.max_rows = max_rows
        self.timeout_s = timeout_s

    def _connect(self) -> sqlite3.Connection:
        # mode=ro: even if the validator were bypassed, SQLite itself refuses writes.
        return sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)

    def run_query(self, sql: str) -> QueryResult:
        conn = self._connect()
        deadline = time.monotonic() + self.timeout_s
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
        try:
            cur = conn.execute(sql)
            columns = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(self.max_rows + 1)
        except sqlite3.Error as exc:
            msg = "query exceeded the time limit" if "interrupted" in str(exc).lower() else str(exc)
            raise QueryError(msg) from exc
        finally:
            conn.close()
        truncated = len(rows) > self.max_rows
        return QueryResult(columns=columns, rows=rows[: self.max_rows], truncated=truncated)

    def get_schema(self, sample_rows: int = 3) -> str:
        """CREATE statements (with their column comments) plus a few sample rows per table."""
        conn = self._connect()
        try:
            tables = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            parts = []
            for name, ddl in tables:
                cur = conn.execute(f'SELECT * FROM "{name}" LIMIT {int(sample_rows)}')
                cols = [d[0] for d in cur.description]
                samples = "\n".join(f"--   {dict(zip(cols, row))}" for row in cur.fetchall())
                parts.append(f"{ddl};\n-- sample rows from {name}:\n{samples}")
            return "\n\n".join(parts)
        finally:
            conn.close()
