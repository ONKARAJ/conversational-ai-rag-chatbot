"""The LangChain pipeline, ported from ChatBotsHistory.ipynb.

Notebook → web mapping
----------------------
* `ChatGroq(model=..., groq_api_key=...)`            → `build_model()`, built once
* `ChatPromptTemplate` + `MessagesPlaceholder`       → `build_prompt()` (+ a {context} slot)
* `trim_messages(...)`                               → `build_trimmer()`
* `RunnablePassthrough.assign(messages=... | trimmer) | prompt | model`
                                                     → `build_chain()`
* `RunnableWithMessageHistory(chain, get_session_history, input_messages_key="messages")`
                                                     → `build_conversational_chain()`

The composition is unchanged. What changed is that these are built once at
startup instead of at import time in a cell, and the trimmer counts tokens
locally instead of delegating to the model object.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from operator import itemgetter
from typing import Any

from langchain_core.messages import BaseMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.core.config import settings
from app.core.errors import ConfigurationError
from app.services.history import get_session_history

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the assistant powering this application. You are not ChatGPT, and
you were not built by OpenAI — you are running on an open-weight model
served via the Groq API. If asked who you are, say you are this app's AI
assistant, running on {model_name} via Groq. Never claim to be ChatGPT or
ClaudeGPT or any other named product. {language}.

Formatting: use Markdown. Put code in fenced blocks with a language tag. Keep answers focused.

{context}"""

# Wrapper used when retrieval found something. The "use the context only"
# instruction is the notebook's RAG prompt, kept intact but scoped to the
# grounded portion of the answer so the assistant can still hold a normal
# conversation around it.
CONTEXT_TEMPLATE = """Reference material retrieved from the knowledge base for the user's latest question:

{documents}

When the question is covered by this material, answer using the material only and say which source you used. When it is not covered, ignore the material and answer normally from your own knowledge — do not invent citations."""

NO_CONTEXT = "No reference material was retrieved for this question; answer from your own knowledge."


# --------------------------------------------------------------------------
# Token counting
# --------------------------------------------------------------------------
@lru_cache
def _encoder() -> Any | None:
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # pragma: no cover - tiktoken is optional
        logger.info("tiktoken unavailable; falling back to character-based token estimate.")
        return None


def count_tokens(messages: list[BaseMessage]) -> int:
    """Approximate token count for a list of messages.

    The notebook passed `token_counter=model`, which couples trimming to the
    chat model (and, on some providers, costs a network round-trip per call).
    A local encoder is deterministic, offline and fast; trimming only needs to
    be approximately right.
    """
    encoder = _encoder()
    total = 0
    for message in messages:
        content = message.content if isinstance(message.content, str) else str(message.content)
        # ~4 tokens of per-message overhead for role/formatting tokens.
        total += 4
        total += len(encoder.encode(content)) if encoder else max(1, len(content) // 4)
    return total


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
def build_model() -> Runnable:
    """The Groq chat model from the notebook."""
    if not settings.llm_configured:
        raise ConfigurationError()

    from langchain_groq import ChatGroq

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.7,
        timeout=60,
        max_retries=2,
    )


def build_prompt() -> ChatPromptTemplate:
    """System prompt + MessagesPlaceholder, as in the notebook."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )


def build_trimmer() -> Runnable:
    """`trim_messages` with the notebook's strategy and a usable budget.

    Why trimming matters: every turn is re-sent to the model on the next turn,
    so an untrimmed conversation grows the prompt without bound — costs rise
    linearly, latency rises with it, and eventually the request exceeds the
    model's context window and fails outright. `strategy="last"` keeps the most
    recent turns (the ones that carry the current topic) and drops the oldest.
    `start_on="human"` guarantees the surviving window begins with a user turn,
    so the model never sees a reply with no question attached.
    """
    return trim_messages(
        max_tokens=settings.max_history_tokens,
        strategy="last",
        token_counter=count_tokens,
        include_system=True,
        allow_partial=False,
        start_on="human",
    )


def build_chain(model: Runnable | None = None) -> Runnable:
    """`RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer) | prompt | model`."""
    model = model or build_model()
    trimmer = build_trimmer()
    prompt = build_prompt()
    return RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer) | prompt | model


def build_conversational_chain(model: Runnable | None = None) -> RunnableWithMessageHistory:
    """Wrap the chain in message history keyed by conversation id."""
    return RunnableWithMessageHistory(
        build_chain(model),
        get_session_history,
        input_messages_key="messages",
    )


@lru_cache
def build_langsmith_tracer() -> Any | None:
    """Build an explicit tracer for deployed environments when configured."""
    if not settings.langsmith_configured:
        return None
    try:
        from langchain_core.tracers import LangChainTracer

        return LangChainTracer(project_name=settings.langsmith_project)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LangSmith tracer could not be initialized: %s", exc)
        return None


def format_context(documents: list[tuple[str, str]]) -> str:
    """Render retrieved chunks into the {context} prompt slot."""
    if not documents:
        return NO_CONTEXT
    rendered = "\n\n".join(
        f"[{index}] source: {source}\n{text}" for index, (source, text) in enumerate(documents, 1)
    )
    return CONTEXT_TEMPLATE.format(documents=rendered)
