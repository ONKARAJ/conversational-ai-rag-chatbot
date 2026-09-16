"""Health and knowledge-base endpoints.

/api/health is what the frontend calls on load to decide whether to show the
"backend is not configured" banner, so it must never raise.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.config import settings
from app.schemas import HealthOut, SourceOut
from app.services.rag import rag_service

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(
        status="ok",
        llm_configured=settings.llm_configured,
        llm_model=settings.groq_model,
        rag_available=rag_service.available,
        rag_documents=rag_service.document_count,
        embedding_model=settings.embedding_model,
        max_history_tokens=settings.max_history_tokens,
    )


@router.get("/rag/search", response_model=list[SourceOut])
async def rag_search(q: str = Query(min_length=1, max_length=500)) -> list[SourceOut]:
    """Inspect what the retriever returns for a query — handy while demoing."""
    hits = rag_service.search(q)
    return [
        SourceOut(source=hit["source"], snippet=hit["text"][:400], score=hit.get("score"))
        for hit in hits
    ]
