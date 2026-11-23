import sqlite3

import pytest

from data_analyst.db import Database, QueryError
from data_analyst.sample_data import create_sample_db


def test_sample_db_is_reproducible(tmp_path):
    a, b = create_sample_db(tmp_path / "a.db"), create_sample_db(tmp_path / "b.db")
    q = "SELECT COUNT(*), ROUND(SUM(unit_price), 2) FROM order_items"
    assert Database(a).run_query(q).rows == Database(b).run_query(q).rows


def test_run_query_and_row_cap(db):
    res = db.run_query("SELECT id FROM orders")
    assert len(res.rows) == 50 and res.truncated and res.columns == ["id"]


def test_database_is_read_only_even_if_validator_is_bypassed(db):
    with pytest.raises(QueryError):
        db.run_query("DELETE FROM customers")


def test_bad_column_raises_query_error(db):
    with pytest.raises(QueryError, match="no such column"):
        db.run_query("SELECT nope FROM customers")


def test_timeout_stops_runaway_queries(db):
    with pytest.raises(QueryError, match="time limit"):
        db.run_query("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c")


def test_schema_contains_tables_comments_and_samples(db):
    schema = db.get_schema()
    for table in ("customers", "products", "orders", "order_items"):
        assert f"CREATE TABLE {table}" in schema
    assert "delivered, cancelled, pending" in schema and "sample rows from orders" in schema


def test_missing_db_has_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="sample_data"):
        Database(tmp_path / "missing.db")
