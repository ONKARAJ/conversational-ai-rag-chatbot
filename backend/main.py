"""FastAPI entrypoint.

Run with:  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.conversations import router as conversations_router
from app.api.system import router as system_router
from app.core.config import settings
from app.core.database import init_db
from app.core.errors import AppError
from app.services.chat import chat_service
from app.services.rag import rag_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Expensive setup happens here — once — not inside request handlers.

    The embedding model and the Chroma collection both take seconds to load.
    Doing that per request would add that cost to every message.
    """
    logger.info("Starting up…")
    init_db()
    rag_service.startup()
    chat_service.startup()
    logger.info(
        "Ready. model=%s | llm_configured=%s | langsmith_tracing=%s | "
        "langsmith_configured=%s | project=%s | rag_available=%s (%d docs)",
        settings.groq_model,
        settings.llm_configured,
        settings.langsmith_tracing,
        settings.langsmith_configured,
        settings.langsmith_project,
        rag_service.available,
        rag_service.document_count,
    )
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Context-Aware Conversational AI",
    description=(
        "Session-based conversational memory (LangChain + Groq) with a Chroma RAG "
        "knowledge base, backing a React chat client."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(conversations_router)


# --------------------------------------------------------------------------
# Error handling: one JSON shape for everything the frontend might receive.
# --------------------------------------------------------------------------
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    if exc.detail:
        logger.error("%s on %s: %s", exc.code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    message = first.get("msg", "That request was not valid.")
    message = message.replace("Value error, ", "")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": message}},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback to the server log; a generic message to the browser.
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Something went wrong on the server. Check the backend logs.",
            }
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "Context-Aware Conversational AI API",
        "docs": "/docs",
        "health": "/api/health",
    }
