"""Application configuration.

Every value here can be overridden from the environment (or a .env file).
Nothing secret is ever hard-coded: see .env.example at the project root.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime configuration for the API, the LLM chain and the RAG index."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Credentials -------------------------------------------------------
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    hf_token: str | None = Field(default=None, alias="HF_TOKEN")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(
        default="conversational-ai-rag-chatbot", alias="LANGSMITH_PROJECT"
    )

    # --- Models ------------------------------------------------------------
    # Same model the notebook used.
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    # --- Chat behaviour ----------------------------------------------------
    default_language: str = Field(default="English", alias="DEFAULT_LANGUAGE")
    # The notebook used max_tokens=70, which is a teaching value: it keeps only
    # the last couple of turns. 3000 leaves room for a real conversation while
    # still bounding the prompt. See docs/NOTEBOOK_ANALYSIS.md.
    max_history_tokens: int = Field(default=3000, alias="MAX_HISTORY_TOKENS")

    # --- RAG ---------------------------------------------------------------
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")
    chroma_dir: str = Field(default=str(BACKEND_DIR / "data" / "chroma"), alias="CHROMA_DIR")
    chroma_collection: str = Field(default="knowledge_base", alias="CHROMA_COLLECTION")
    knowledge_base_dir: str = Field(
        default=str(BACKEND_DIR / "knowledge_base"), alias="KNOWLEDGE_BASE_DIR"
    )

    # --- Storage -----------------------------------------------------------
    # SQLite for development. Swap in a PostgreSQL URL and nothing else changes:
    # postgresql+psycopg://user:pass@localhost:5432/chatdb
    database_url: str = Field(
        default=f"sqlite:///{BACKEND_DIR / 'data' / 'conversations.db'}",
        alias="DATABASE_URL",
    )

    # --- Server ------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("rag_top_k")
    @classmethod
    def _positive_k(cls, value: int) -> int:
        return max(1, value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key.strip())

    @property
    def langsmith_configured(self) -> bool:
        return self.langsmith_tracing and bool(
            self.langsmith_api_key and self.langsmith_api_key.strip()
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    # The notebook did `os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")`, which
    # raises TypeError when the variable is missing. Only set it when present.
    if settings.hf_token:
        os.environ.setdefault("HF_TOKEN", settings.hf_token)
        os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", settings.hf_token)

    # LangSmith's automatic LangChain callback reads process environment
    # variables. Pydantic loads them from .env without exporting them.
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)

    # Make sure local data directories exist before SQLite/Chroma touch them.
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("sqlite:///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return settings


settings = get_settings()
