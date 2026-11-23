"""FastAPI service.  Run:  uvicorn data_analyst.api:app --reload"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from .agent import DataAnalystAgent

app = FastAPI(title="AI Data Analyst Agent", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AttemptOut(BaseModel):
    sql: str | None = None
    error: str | None = None


class AskResponse(BaseModel):
    ok: bool
    answer: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[list] = []
    truncated: bool = False
    attempts: list[AttemptOut] = []


@lru_cache(maxsize=1)
def get_agent_dep() -> DataAnalystAgent:
    from .factory import get_agent

    return get_agent()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, agent: DataAnalystAgent = Depends(get_agent_dep)) -> AskResponse:
    r = agent.ask(req.question)
    return AskResponse(
        ok=r.ok, answer=r.answer, sql=r.sql, columns=r.columns, rows=[list(x) for x in r.rows],
        truncated=r.truncated, attempts=[AttemptOut(sql=a.sql, error=a.error) for a in r.attempts],
    )
