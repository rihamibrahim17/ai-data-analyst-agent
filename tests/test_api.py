from fastapi.testclient import TestClient

from data_analyst.agent import AgentResult, Attempt
from data_analyst.api import app, get_agent_dep


class Stub:
    def ask(self, question):
        return AgentResult(question, "200 customers", "SELECT COUNT(*) FROM customers", ["n"], [(200,)], attempts=[Attempt("SELECT COUNT(*) FROM customers")])


def test_ask_and_validation():
    app.dependency_overrides[get_agent_dep] = lambda: Stub()
    try:
        client = TestClient(app)
        assert client.get("/health").json() == {"status": "ok"}
        body = client.post("/ask", json={"question": "How many customers?"}).json()
        assert body["ok"] and body["rows"] == [[200]] and body["columns"] == ["n"]
        assert client.post("/ask", json={"question": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()
