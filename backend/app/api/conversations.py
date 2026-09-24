"""REST endpoints for conversations and messages."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ConversationNotFound, EmptyMessage
from app.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.services import conversations as conversation_service
from app.services.chat import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


async def get_client_session_id(
    value: Annotated[UUID, Header(alias="X-Client-Session-ID")],
) -> str:
    return str(value)


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate | None = None,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> ConversationSummary:
    """Create a conversation and return its unique id (the LangChain session id)."""
    payload = payload or ConversationCreate()
    conversation = conversation_service.create_conversation(
        db,
        session_id=session_id,
        title=payload.title,
        language=payload.language,
        rag_enabled=payload.rag_enabled,
    )
    return ConversationSummary.model_validate(conversation)


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> list[ConversationSummary]:
    """List conversations, most recently updated first."""
    rows = conversation_service.list_conversations(db, session_id=session_id, search=search)
    return [ConversationSummary.model_validate(row) for row in rows]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> ConversationDetail:
    """Full transcript for one conversation."""
    conversation = conversation_service.get_conversation(
        db, conversation_id, session_id=session_id
    )
    return ConversationDetail.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> ConversationSummary:
    """Rename a conversation or change its language / RAG setting."""
    conversation = conversation_service.update_conversation(
        db,
        conversation_id,
        session_id=session_id,
        title=payload.title,
        language=payload.language,
        rag_enabled=payload.rag_enabled,
    )
    return ConversationSummary.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> Response:
    """Delete a conversation and every message in it."""
    conversation_service.delete_conversation(db, conversation_id, session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_client_session_id),
) -> MessageResponse:
    """Send a user message and get the assistant's reply.

    The LangChain call is blocking, so it runs in a worker thread; the event
    loop stays free to serve other requests while Groq is thinking.
    """
    # Fail fast on an unknown id before paying for a model call.
    conversation_service.get_conversation(db, conversation_id, session_id=session_id)

    if not payload.content.strip():
        raise EmptyMessage()

    result = await run_in_threadpool(
        chat_service.send_message,
        conversation_id,
        payload.content,
        session_id=session_id,
        language=payload.language,
        use_rag=payload.use_rag,
    )

    if result["user_message"] is None or result["assistant_message"] is None:
        # The history adapter should always have written both rows by now.
        raise ConversationNotFound("The reply could not be saved to this conversation.")

    return MessageResponse(
        conversation_id=conversation_id,
        user_message=result["user_message"],
        assistant_message=result["assistant_message"],
        sources=result["sources"],
        used_rag=result["used_rag"],
        title=result["title"],
    )
