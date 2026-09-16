"""Application error types.

Every error the API can raise is expressed as one of these classes. The
exception handlers in `app.main` turn them into a small JSON body:

    {"error": {"code": "llm_unavailable", "message": "..."}}

Internal details (stack traces, provider payloads) are logged server-side and
never returned to the browser.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for errors that are safe to show to a user."""

    code: str = "internal_error"
    status_code: int = 500
    message: str = "Something went wrong on the server."

    def __init__(self, message: str | None = None, *, detail: str | None = None) -> None:
        self.message = message or self.message
        # `detail` is for logs only; it is never serialised to the client.
        self.detail = detail
        super().__init__(self.message)


class ConversationNotFound(AppError):
    code = "conversation_not_found"
    status_code = 404
    message = "That conversation does not exist. It may have been deleted."


class EmptyMessage(AppError):
    code = "empty_message"
    status_code = 422
    message = "Write a message before sending."


class ConfigurationError(AppError):
    code = "configuration_error"
    status_code = 503
    message = (
        "The server is missing GROQ_API_KEY. Add it to your .env file and restart the backend."
    )


class LLMUnavailable(AppError):
    code = "llm_unavailable"
    status_code = 502
    message = "The language model did not respond. Try sending the message again."


class LLMTimeout(AppError):
    code = "llm_timeout"
    status_code = 504
    message = "The language model took too long to answer. Try again in a moment."


class RetrievalError(AppError):
    code = "retrieval_failed"
    status_code = 500
    message = "The knowledge base could not be searched."


class StorageError(AppError):
    code = "storage_error"
    status_code = 500
    message = "Conversations could not be read or saved."
