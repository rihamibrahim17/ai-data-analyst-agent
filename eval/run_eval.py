"""Execution-accuracy evaluation: does the agent's query return the same result as the gold query?

Run (needs an LLM key and data/shop.db):  python eval/run_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_analyst.db import Database  # noqa: E402


def normalize(rows) -> list:
    """Order-insensitive, float-tolerant representation of a result set."""
    return sorted(tuple(round(v, 2) if isinstance(v, float) else v for v in row) for row in rows)


def same_result(gold_rows, agent_rows) -> bool:
    return normalize(gold_rows) == normalize(agent_rows)


def main() -> None:
    from data_analyst.config import Settings
    from data_analyst.factory import get_agent

    settings = Settings.from_env()
    agent = get_agent(settings)
    db = Database(settings.db_path, max_rows=10_000)
    rows = [json.loads(l) for l in Path(__file__).with_name("questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    correct = self_fixed = 0
    for row in rows:
        gold = db.run_query(row["gold_sql"]).rows
        res = agent.ask(row["question"])
        ok = res.ok and same_result(gold, res.rows)
        correct += ok
        self_fixed += ok and len(res.attempts) > 1
        print(f"{'PASS' if ok else 'FAIL'}  ({len(res.attempts)} attempt(s))  {row['question']}")
        if not ok and res.sql:
            print(f"      agent SQL: {res.sql}")

    n = len(rows)
    print(f"\nExecution accuracy: {correct}/{n} = {correct / n:.0%}   (fixed by self-correction: {self_fixed})")


if __name__ == "__main__":
    main()
