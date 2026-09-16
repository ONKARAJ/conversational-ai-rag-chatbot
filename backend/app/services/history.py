"""Persistent chat history for RunnableWithMessageHistory.

The notebook kept history in a module-level dict:

    store = {}
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

That is exactly the right *interface* — LangChain only needs an object with
`messages`, `add_messages()` and `clear()`. What it cannot do is survive a
restart, and it would keep a second copy of the transcript next to the one the
REST API serves.

So the dict is replaced with a class that reads and writes the same `messages`
table the API reads. One source of truth, and `session_id` is literally the
`conversation_id` the frontend sends.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models import ROLE_AI, ROLE_HUMAN, ROLE_SYSTEM, Message

logger = logging.getLogger(__name__)

_ROLE_TO_CLASS = {ROLE_HUMAN: HumanMessage, ROLE_AI: AIMessage, ROLE_SYSTEM: SystemMessage}


def _role_of(message: BaseMessage) -> str:
    if isinstance(message, HumanMessage):
        return ROLE_HUMAN
    if isinstance(message, AIMessage):
        return ROLE_AI
    if isinstance(message, SystemMessage):
        return ROLE_SYSTEM
    # Fall back on LangChain's own type string for anything exotic.
    return ROLE_AI if message.type == "ai" else ROLE_HUMAN


def content_to_text(content: object) -> str:
    """Groq can return content as a list of blocks; flatten to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return str(content)


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """A BaseChatMessageHistory whose backing store is the conversations DB.

    Each instance opens short-lived sessions of its own, which keeps it safe to
    use from the worker thread that runs the LangChain chain.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    @property
    def messages(self) -> list[BaseMessage]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(Message)
                .where(Message.conversation_id == self.session_id)
                .order_by(Message.id)
            ).all()
        return [
            _ROLE_TO_CLASS.get(row.role, HumanMessage)(content=row.content)
            for row in rows
        ]

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        rows = [
            Message(
                conversation_id=self.session_id,
                role=_role_of(message),
                content=content_to_text(message.content),
            )
            for message in messages
            if content_to_text(message.content).strip()
        ]
        if not rows:
            return
        with SessionLocal() as db:
            db.add_all(rows)
            db.commit()

    def clear(self) -> None:
        with SessionLocal() as db:
            db.execute(delete(Message).where(Message.conversation_id == self.session_id))
            db.commit()


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Factory handed to RunnableWithMessageHistory.

    Same signature as the notebook's function, different storage. LangChain
    calls this once per invocation with the `session_id` from
    `config={"configurable": {"session_id": ...}}`, which is where conversation
    isolation comes from: a different id reads a different set of rows, so
    conversation A can never see conversation B's turns.
    """
    return SQLiteChatMessageHistory(session_id)
