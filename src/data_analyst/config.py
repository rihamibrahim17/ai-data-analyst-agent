"""Configuration from environment variables (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CHAT_MODELS = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini"}


@dataclass(frozen=True)
class Settings:
    provider: str = "gemini"
    chat_model: str = DEFAULT_CHAT_MODELS["gemini"]
    db_path: Path = Path("data/shop.db")
    max_rows: int = 200
    query_timeout_s: float = 5.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider not in DEFAULT_CHAT_MODELS:
            raise ValueError(f"LLM_PROVIDER must be one of {sorted(DEFAULT_CHAT_MODELS)}, got '{provider}'")
        return cls(
            provider=provider,
            chat_model=os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODELS[provider]),
            db_path=Path(os.getenv("DB_PATH", str(cls.db_path))),
        )
