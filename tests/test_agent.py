from langchain_core.language_models.fake_chat_models import FakeListChatModel

from data_analyst.agent import DataAnalystAgent, extract_sql


def agent_with(db, responses, **kw):
    return DataAnalystAgent(FakeListChatModel(responses=responses), db, today="2026-11-23", **kw)


def test_extract_sql_variants():
    assert extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"
    assert extract_sql("```\nSELECT 2\n```") == "SELECT 2"
    assert extract_sql("SELECT 3") == "SELECT 3"
    assert extract_sql("I think the answer is 4") is None


def test_happy_path(db):
    res = agent_with(db, ["```sql\nSELECT COUNT(*) FROM customers\n```", "There are 200 customers."]).ask("How many customers?")
    assert res.ok and res.rows == [(200,)] and res.answer == "There are 200 customers."
    assert len(res.attempts) == 1 and res.attempts[0].error is None


def test_self_corrects_a_bad_column(db):
    res = agent_with(db, [
        "```sql\nSELECT COUNT(*) FROM customer_table\n```",
        "```sql\nSELECT COUNT(*) FROM customers\n```",
        "200 customers.",
    ]).ask("How many customers?")
    assert res.ok and res.rows == [(200,)]
    assert len(res.attempts) == 2 and "no such table" in res.attempts[0].error


def test_unsafe_sql_is_rejected_then_corrected(db):
    res = agent_with(db, [
        "```sql\nDROP TABLE customers\n```",
        "```sql\nSELECT COUNT(*) FROM customers\n```",
        "200.",
    ]).ask("Delete everything")
    assert res.ok and "Only SELECT" in res.attempts[0].error
    assert db.run_query("SELECT COUNT(*) FROM customers").rows == [(200,)]  # data untouched


def test_gives_up_after_max_retries(db):
    res = agent_with(db, ["```sql\nSELECT x FROM nowhere\n```"], max_retries=2).ask("anything")
    assert not res.ok and len(res.attempts) == 3 and "3 attempts" in res.answer


def test_cannot_answer_out_of_scope_questions(db):
    res = agent_with(db, ["CANNOT_ANSWER: the database has no weather data."]).ask("What's the weather?")
    assert not res.ok and res.answer == "the database has no weather data." and res.sql is None


def test_handles_list_style_content_blocks(db):
    from langchain_core.messages import AIMessage

    from data_analyst.agent import message_text

    assert message_text(AIMessage(content=[{"type": "text", "text": "SELECT 1"}])) == "SELECT 1"
