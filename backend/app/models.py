"""ORM models for the conversation store.

This database holds *conversation memory* only: who said what, in which
conversation. It is not the vector store. The Chroma index under
backend/data/chroma is a separate, read-mostly knowledge base and knows
nothing about users or sessions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ROLE_HUMAN = "human"
ROLE_AI = "ai"
ROLE_SYSTEM = "system"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_conversation_id() -> str:
    """Readable, globally unique id, e.g. conversation_8f42a1c9d0b74e3a."""
    return f"conversation_{uuid.uuid4().hex[:16]}"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_conversation_id)
    title: Mapped[str] = mapped_column(String(255), default="New chat", nullable=False)
    # Per-conversation settings. `language` feeds the {language} prompt variable
    # from the notebook; `rag_enabled` toggles retrieval for this conversation.
    language: Mapped[str] = mapped_column(String(64), default="English", nullable=False)
    rag_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
        lazy="selectin",
    )

    @property
    def message_count(self) -> int:
        return len(self.messages)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    # "human" | "ai" | "system" — matches LangChain's message types so the
    # history adapter can convert rows straight into BaseMessage objects.
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


# Loading one conversation's transcript is the hottest query in the app.
Index("ix_messages_conversation_id_id", Message.conversation_id, Message.id)
