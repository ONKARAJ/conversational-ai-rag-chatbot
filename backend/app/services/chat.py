"""The request-time chat pipeline.

    user message
        → load conversation settings (language, RAG on/off)
        → retrieve context from Chroma (optional)
        → RunnableWithMessageHistory(session_id = conversation_id)
              → trim_messages
              → prompt (system + {language} + {context} + history placeholder)
              → ChatGroq
        → history rows persisted by the history adapter
        → reply + sources returned to the API layer

Session isolation lives in one line: the `session_id` passed in `config` is the
conversation id from the URL, and `SQLiteChatMessageHistory` only ever reads
rows with that id. Two conversations cannot see each other's turns.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import (
    AppError,
    ConfigurationError,
    EmptyMessage,
    LLMTimeout,
    LLMUnavailable,
)
from app.models import ROLE_AI, ROLE_HUMAN, Message, utcnow
from app.services import conversations as conversation_service
from app.services.history import content_to_text
from app.services.llm import build_conversational_chain, build_langsmith_tracer, format_context
from app.services.rag import rag_service

logger = logging.getLogger(__name__)

SNIPPET_LENGTH = 220


class ChatService:
    """Holds the compiled chain so it is built once, not per request."""

    def __init__(self) -> None:
        self._chain: Any | None = None

    def startup(self) -> None:
        if not settings.llm_configured:
            logger.warning(
                "GROQ_API_KEY is not set. The API will start, but sending a message "
                "will return a configuration error until the key is added to .env."
            )
            return
        try:
            self._chain = build_conversational_chain()
            logger.info("Chat chain ready (model=%s).", settings.groq_model)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Could not build the chat chain at startup: %s", exc)
            self._chain = None

    @property
    def ready(self) -> bool:
        return self._chain is not None

    def _get_chain(self) -> Any:
        if self._chain is None:
            # Lazy retry: lets the app recover if the key was added after boot.
            self._chain = build_conversational_chain()
        return self._chain

    # -- main entry point --------------------------------------------------
    def send_message(
        self,
        conversation_id: str,
        content: str,
        *,
        session_id: str,
        language: str | None = None,
        use_rag: bool | None = None,
    ) -> dict[str, Any]:
        """Run one turn. Called in a worker thread, so it owns its DB session."""
        question = content.strip()
        if not question:
            raise EmptyMessage()

        with SessionLocal() as db:
            conversation = conversation_service.get_conversation(
                db, conversation_id, session_id=session_id
            )
            resolved_language = (language or conversation.language or settings.default_language).strip()
            wants_rag = conversation.rag_enabled if use_rag is None else use_rag
            is_first_message = not conversation.messages
            current_title = conversation.title

        # --- retrieval ----------------------------------------------------
        hits: list[dict[str, Any]] = []
        if wants_rag and rag_service.available:
            hits = rag_service.retrieve(question)
        context_block = format_context([(hit["source"], hit["text"]) for hit in hits])

        # --- generation ---------------------------------------------------
        chain = self._get_chain()
        try:
            response = chain.invoke(
                {
                    "messages": [HumanMessage(content=question)],
                    "language": resolved_language,
                    "context": context_block,
                    "model_name": settings.groq_model
                },
                config={
                    "configurable": {"session_id": conversation_id},
                    "callbacks": [tracer] if (tracer := build_langsmith_tracer()) else None,
                    "run_name": "conversation_turn",
                    "tags": ["chat", "rag" if hits else "no-rag"],
                    "metadata": {
                        "conversation_id": conversation_id,
                        "client_session_id": session_id,
                        "language": resolved_language,
                        "rag_enabled": wants_rag,
                        "retrieved_documents": len(hits),
                        "model": settings.groq_model,
                    },
                },
            )
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise self._translate_llm_error(exc) from exc

        answer = content_to_text(getattr(response, "content", response)).strip()
        if not answer:
            raise LLMUnavailable("The model returned an empty response. Try rephrasing.")

        # --- persistence bookkeeping --------------------------------------
        # RunnableWithMessageHistory already wrote the human and AI rows through
        # SQLiteChatMessageHistory. Read them back for the API response and
        # refresh the conversation's title/timestamp.
        with SessionLocal() as db:
            rows = db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id.desc())
                .limit(2)
            ).all()
            saved = {row.role: row for row in rows}
            user_row = saved.get(ROLE_HUMAN)
            ai_row = saved.get(ROLE_AI)

            conversation = conversation_service.get_conversation(
                db, conversation_id, session_id=session_id
            )
            if is_first_message and current_title == conversation_service.DEFAULT_TITLE:
                conversation.title = conversation_service.title_from_first_message(question)
            conversation.updated_at = utcnow()
            db.commit()
            db.refresh(conversation)
            title = conversation.title

        return {
            "user_message": user_row,
            "assistant_message": ai_row,
            "answer": answer,
            "title": title,
            "used_rag": bool(hits),
            "sources": [
                {
                    "source": hit["source"],
                    "snippet": hit["text"][:SNIPPET_LENGTH],
                    "score": hit.get("score"),
                }
                for hit in hits
            ],
        }

    # -- error mapping -----------------------------------------------------
    @staticmethod
    def _translate_llm_error(exc: Exception) -> AppError:
        """Turn provider exceptions into safe, actionable API errors."""
        text = f"{type(exc).__name__}: {exc}".lower()
        logger.exception("LLM call failed")

        if "api key" in text or "authentication" in text or "401" in text or "invalid_api_key" in text:
            return ConfigurationError(
                "Groq rejected the API key. Check GROQ_API_KEY in your .env file."
            )
        if "timeout" in text or "timed out" in text:
            return LLMTimeout()
        if "rate limit" in text or "429" in text:
            return LLMUnavailable("Groq rate limit reached. Wait a few seconds and try again.")
        if "connection" in text or "network" in text or "dns" in text:
            return LLMUnavailable("Could not reach Groq. Check your internet connection.")
        if "model" in text and ("not found" in text or "decommission" in text):
            return LLMUnavailable(
                f"The model '{settings.groq_model}' is unavailable. "
                "Set GROQ_MODEL in .env to a current Groq model."
            )
        return LLMUnavailable()


chat_service = ChatService()
