import json
from pathlib import Path

from run_eval import normalize, same_result

QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "questions.jsonl"


def test_every_gold_query_is_valid_and_returns_rows(db_path):
    from data_analyst.db import Database
    from data_analyst.guard import validate_sql

    db = Database(db_path, max_rows=1000)
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10
    for row in rows:
        result = db.run_query(validate_sql(row["gold_sql"]))
        assert result.rows, f"gold query returned nothing: {row['question']}"


def test_result_comparison_ignores_order_and_float_noise():
    assert same_result([(1, "a"), (2, "b")], [(2, "b"), (1, "a")])
    assert same_result([(1.2300001,)], [(1.23,)])
    assert not same_result([(1,)], [(2,)])
