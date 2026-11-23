import pytest

from data_analyst.guard import UnsafeSQLError, validate_sql


@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",
    "select count(*) from orders;",
    "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
    "SELECT name FROM customers WHERE name = 'DROP TABLE x'",       # keyword inside a string is fine
    "SELECT updated_at FROM t",                                       # column names containing a keyword
    "SELECT 1 -- DROP TABLE customers",                               # comment is stripped
])
def test_safe_queries_pass(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", [
    "DROP TABLE customers",
    "DELETE FROM orders",
    "UPDATE customers SET name = 'x'",
    "INSERT INTO customers VALUES (1,'a','b','c')",
    "SELECT 1; DROP TABLE customers",
    "WITH x AS (SELECT 1) DELETE FROM orders",
    "PRAGMA table_info(customers)",
    "ATTACH DATABASE 'x.db' AS x",
    "SELECT /* hi */ 1; SELECT 2",
    "",
    "   ",
])
def test_unsafe_queries_blocked(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_comments_and_trailing_semicolon_removed():
    assert validate_sql("SELECT 1 /* c */ ; ") == "SELECT 1"
