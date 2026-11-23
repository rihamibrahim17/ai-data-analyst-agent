"""The agent loop: generate SQL -> validate -> execute -> self-correct on errors -> explain the result."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .db import Database, QueryError
from .guard import UnsafeSQLError, validate_sql
from .prompts import SQL_SYSTEM, SUMMARY_HUMAN, SUMMARY_SYSTEM

CANNOT_ANSWER = "CANNOT_ANSWER"
_SQL_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class Attempt:
    sql: str | None
    error: str | None = None


@dataclass
class AgentResult:
    question: str
    answer: str
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    truncated: bool = False
    attempts: list[Attempt] = field(default_factory=list)
    ok: bool = True


def message_text(msg: BaseMessage) -> str:
    """Plain text of a model reply (some providers return a list of content blocks)."""
    content = msg.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)


def extract_sql(text: str) -> str | None:
    match = _SQL_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    stripped = text.strip()
    return stripped if re.match(r"(?i)(select|with)\b", stripped) else None


class DataAnalystAgent:
    def __init__(self, llm, db: Database, notes: str = "", max_retries: int = 2, today: str | None = None):
        self.llm, self.db, self.notes = llm, db, notes
        self.max_retries = max_retries
        self.today = today or date.today().isoformat()
        self._schema = db.get_schema()

    def ask(self, question: str) -> AgentResult:
        messages: list[BaseMessage] = [
            SystemMessage(SQL_SYSTEM.format(schema=self._schema, notes=self.notes or "none", today=self.today)),
            HumanMessage(question),
        ]
        attempts: list[Attempt] = []

        for _ in range(self.max_retries + 1):
            raw = message_text(self.llm.invoke(messages)).strip()
            if raw.startswith(CANNOT_ANSWER):
                reason = raw[len(CANNOT_ANSWER):].lstrip(": ").strip()
                return AgentResult(question, reason or "This question can't be answered from the database.", attempts=attempts, ok=False)

            sql = extract_sql(raw)
            try:
                if sql is None:
                    raise UnsafeSQLError("No SQL query found. Reply with a single SQL query in a ```sql block.")
                clean = validate_sql(sql)
                result = self.db.run_query(clean)
            except (UnsafeSQLError, QueryError) as exc:
                attempts.append(Attempt(sql=sql, error=str(exc)))
                messages += [AIMessage(raw), HumanMessage(f"That query failed: {exc}\nFix it and reply with the corrected SQL only.")]
                continue

            attempts.append(Attempt(sql=clean))
            answer = self._explain(question, result.columns, result.rows, result.truncated)
            return AgentResult(question, answer, clean, result.columns, result.rows, result.truncated, attempts)

        last = attempts[-1].error if attempts else "unknown error"
        return AgentResult(
            question,
            f"I couldn't produce a valid query for this question after {len(attempts)} attempts ({last}). Try rephrasing it.",
            attempts=attempts,
            ok=False,
        )

    def _explain(self, question: str, columns: list[str], rows: list[tuple], truncated: bool) -> str:
        shown = rows[:30]
        human = SUMMARY_HUMAN.format(
            question=question,
            columns=", ".join(columns),
            shown=len(shown),
            total=f"{len(rows)}+" if truncated else len(rows),
            truncated=", truncated" if truncated else "",
            rows="\n".join(str(r) for r in shown) or "(no rows)",
        )
        return message_text(self.llm.invoke([SystemMessage(SUMMARY_SYSTEM), HumanMessage(human)])).strip()
