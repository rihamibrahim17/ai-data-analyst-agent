from __future__ import annotations

from .agent import DataAnalystAgent
from .config import Settings
from .db import Database
from .sample_data import BUSINESS_NOTES


def get_llm(settings: Settings):
    if settings.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.chat_model, temperature=0)
    from langchain_google_genai import ChatGoogleGenerativeAI  # reads GOOGLE_API_KEY

    return ChatGoogleGenerativeAI(model=settings.chat_model, temperature=0)


def get_agent(settings: Settings | None = None) -> DataAnalystAgent:
    settings = settings or Settings.from_env()
    db = Database(settings.db_path, max_rows=settings.max_rows, timeout_s=settings.query_timeout_s)
    return DataAnalystAgent(get_llm(settings), db, notes=BUSINESS_NOTES, max_retries=settings.max_retries)
