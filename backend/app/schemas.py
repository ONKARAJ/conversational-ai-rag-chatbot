"""Pydantic models for request validation and response serialisation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["human", "ai", "system"]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Role
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """Shape used by the sidebar list — no message bodies."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    language: str
    rag_enabled: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=64)
    rag_enabled: bool | None = None


class ConversationUpdate(BaseModel):
    """PATCH body. Every field is optional; at least one must be provided."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    language: str | None = Field(default=None, min_length=1, max_length=64)
    rag_enabled: bool | None = None

    @field_validator("title", "language")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank.")
        return cleaned


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=16_000)
    # Per-request overrides; when omitted the conversation's own settings win.
    language: str | None = Field(default=None, max_length=64)
    use_rag: bool | None = None

    @field_validator("content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Write a message before sending.")
        return cleaned


class SourceOut(BaseModel):
    """A knowledge-base chunk that was retrieved for this answer."""

    source: str
    snippet: str
    score: float | None = None


class MessageResponse(BaseModel):
    conversation_id: str
    user_message: MessageOut
    assistant_message: MessageOut
    sources: list[SourceOut] = Field(default_factory=list)
    used_rag: bool = False
    title: str


class HealthOut(BaseModel):
    status: str
    llm_configured: bool
    llm_model: str
    rag_available: bool
    rag_documents: int
    embedding_model: str
    max_history_tokens: int


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
