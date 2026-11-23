"""SQL safety validator: layer 1 of 3 (the others: read-only connection, timeout + row cap).

Only a single read-only SELECT / WITH ... SELECT statement is allowed.
"""
from __future__ import annotations

import re


class UnsafeSQLError(ValueError):
    """Raised when generated SQL is not a single read-only query."""


# Quoted strings / identifiers and comments, matched together so comment markers inside strings are safe.
_TOKEN = re.compile(r"""'(?:[^']|'')*'|"(?:[^"]|"")*"|--[^\n]*|/\*.*?\*/""", re.DOTALL)
_FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "attach", "detach",
    "pragma", "vacuum", "reindex", "load_extension",
}


def _remove_comments(sql: str) -> str:
    def repl(m: re.Match) -> str:
        t = m.group(0)
        return " " if t.startswith(("--", "/*")) else t

    return _TOKEN.sub(repl, sql)


def _skeleton(sql: str) -> str:
    """SQL with string literals and comments blanked out, so keyword checks cannot be fooled."""
    return _TOKEN.sub(" ", sql)


def validate_sql(sql: str) -> str:
    """Return the cleaned SQL (comments and trailing ';' removed) or raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty query.")
    cleaned = _remove_comments(sql).strip().rstrip(";").strip()
    skeleton = _skeleton(sql).strip().rstrip(";").strip().lower()

    if not skeleton:
        raise UnsafeSQLError("Empty query.")
    if ";" in skeleton:
        raise UnsafeSQLError("Only a single statement is allowed.")
    if not re.match(r"(select|with)\b", skeleton):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    bad = sorted(set(re.findall(r"[a-z_]+", skeleton)) & _FORBIDDEN)
    if bad:
        raise UnsafeSQLError(f"Forbidden keyword(s): {', '.join(bad)}. Only read-only queries are allowed.")
    return cleaned
