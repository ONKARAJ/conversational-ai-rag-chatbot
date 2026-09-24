"""CRUD for conversations. Pure database work — no LangChain in this module."""

from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConversationNotFound, StorageError
from app.models import Conversation, Message, new_conversation_id, utcnow

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "New chat"
MAX_TITLE_LENGTH = 60


def create_conversation(
    db: Session,
    *,
    session_id: str,
    title: str | None = None,
    language: str | None = None,
    rag_enabled: bool | None = None,
) -> Conversation:
    conversation = Conversation(
        id=new_conversation_id(),
        session_id=session_id,
        title=(title or DEFAULT_TITLE).strip()[:255] or DEFAULT_TITLE,
        language=(language or settings.default_language).strip()[:64],
        rag_enabled=settings.rag_enabled if rag_enabled is None else rag_enabled,
    )
    try:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create conversation")
        raise StorageError(detail=str(exc)) from exc
    return conversation


def list_conversations(
    db: Session, *, session_id: str, search: str | None = None, limit: int = 200
) -> list[Conversation]:
    """Most recently updated first. `search` matches titles and message bodies."""
    statement = select(Conversation).where(Conversation.session_id == session_id)

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        matching_ids = select(Message.conversation_id).where(
            func.lower(Message.content).like(pattern)
        )
        statement = statement.where(
            or_(func.lower(Conversation.title).like(pattern), Conversation.id.in_(matching_ids))
        )

    statement = statement.order_by(Conversation.updated_at.desc()).limit(limit)
    try:
        return list(db.scalars(statement).all())
    except SQLAlchemyError as exc:
        logger.exception("Failed to list conversations")
        raise StorageError(detail=str(exc)) from exc


def get_conversation(db: Session, conversation_id: str, *, session_id: str) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id,
        )
    )
    if conversation is None:
        raise ConversationNotFound()
    return conversation


def update_conversation(
    db: Session,
    conversation_id: str,
    *,
    session_id: str,
    title: str | None = None,
    language: str | None = None,
    rag_enabled: bool | None = None,
) -> Conversation:
    conversation = get_conversation(db, conversation_id, session_id=session_id)
    if title is not None:
        conversation.title = title[:255]
    if language is not None:
        conversation.language = language[:64]
    if rag_enabled is not None:
        conversation.rag_enabled = rag_enabled
    conversation.updated_at = utcnow()
    try:
        db.commit()
        db.refresh(conversation)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update conversation %s", conversation_id)
        raise StorageError(detail=str(exc)) from exc
    return conversation


def delete_conversation(db: Session, conversation_id: str, *, session_id: str) -> None:
    conversation = get_conversation(db, conversation_id, session_id=session_id)
    try:
        # Messages go with it via cascade="all, delete-orphan".
        db.delete(conversation)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to delete conversation %s", conversation_id)
        raise StorageError(detail=str(exc)) from exc


def title_from_first_message(text: str) -> str:
    """Derive a sidebar title from the opening user message."""
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= MAX_TITLE_LENGTH:
        return cleaned or DEFAULT_TITLE
    trimmed = cleaned[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0]
    return f"{trimmed or cleaned[:MAX_TITLE_LENGTH]}…"
