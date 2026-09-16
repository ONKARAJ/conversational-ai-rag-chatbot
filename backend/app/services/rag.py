"""Retrieval layer: HuggingFace embeddings → Chroma → retriever.

Straight from the notebook, with three changes:

1. The index is built **once**, during FastAPI startup, not per request.
   Loading `all-MiniLM-L6-v2` takes seconds and embedding the corpus costs
   real time; doing it inside a request handler would add that to every
   message the user sends.
2. Chroma is given a `persist_directory`, so restarting the server reuses the
   existing collection instead of re-embedding from scratch
   (`Chroma.from_documents(...)` in the notebook was purely in-memory).
3. Documents come from `backend/knowledge_base/*.md|*.txt` when that folder has
   content, falling back to the notebook's five pet documents. Dropping a file
   into that folder is how you extend the knowledge base.

If the optional heavy dependencies (sentence-transformers, chromadb) are not
installed, this service degrades to `available = False` and the chat still
works — just without retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import RetrievalError

logger = logging.getLogger(__name__)


def seed_documents() -> list[Any]:
    """The five documents from the notebook, used when knowledge_base/ is empty."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content="Dogs are great companions, known for their loyalty and friendliness.",
            metadata={"source": "mammal-pets-doc"},
        ),
        Document(
            page_content="Cats are independent pets that often enjoy their own space.",
            metadata={"source": "mammal-pets-doc"},
        ),
        Document(
            page_content=(
                "Goldfish are popular pets for beginners, requiring relatively simple care."
            ),
            metadata={"source": "fish-pets-doc"},
        ),
        Document(
            page_content="Parrots are intelligent birds capable of mimicking human speech.",
            metadata={"source": "bird-pets-doc"},
        ),
        Document(
            page_content="Rabbits are social animals that need plenty of space to hop around.",
            metadata={"source": "mammal-pets-doc"},
        ),
    ]


def load_documents() -> list[Any]:
    """Read .md/.txt files from the knowledge base folder, else use the seeds."""
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    folder = Path(settings.knowledge_base_dir)
    files = sorted(
        p
        for p in folder.glob("**/*")
        if p.suffix.lower() in {".md", ".txt"} and p.name.lower() != "readme.md"
    )

    if not files:
        logger.info("No files in %s; indexing the built-in sample documents.", folder)
        return seed_documents()

    raw: list[Any] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("Skipping %s: %s", path, exc)
            continue
        if text:
            raw.append(Document(page_content=text, metadata={"source": path.name}))

    if not raw:
        return seed_documents()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_documents(raw)
    logger.info("Indexed %d chunk(s) from %d file(s) in %s.", len(chunks), len(files), folder)
    return chunks


class RagService:
    """Owns the embedding model, the vector store and the retriever."""

    def __init__(self) -> None:
        self.available = False
        self.document_count = 0
        self._vector_store: Any | None = None
        self._retriever: Any | None = None

    # -- lifecycle ---------------------------------------------------------
    def startup(self) -> None:
        """Called once from the FastAPI lifespan handler."""
        if not settings.rag_enabled:
            logger.info("RAG disabled by configuration (RAG_ENABLED=false).")
            return

        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            logger.warning("RAG dependencies missing (%s); retrieval is off.", exc)
            return

        try:
            # `model_name` is the documented argument; the notebook's `model=`
            # alias is not accepted by every langchain-huggingface release.
            embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)

            self._vector_store = Chroma(
                collection_name=settings.chroma_collection,
                embedding_function=embeddings,
                persist_directory=settings.chroma_dir,
            )

            existing = self._count()
            if existing == 0:
                documents = load_documents()
                self._vector_store.add_documents(documents)
                logger.info("Built Chroma collection with %d document(s).", len(documents))
            else:
                logger.info("Reusing persisted Chroma collection (%d documents).", existing)

            self.document_count = self._count()
            self._retriever = self._vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.rag_top_k},
            )
            self.available = True
        except Exception as exc:  # noqa: BLE001 - startup must not kill the app
            logger.exception("RAG initialisation failed; continuing without retrieval: %s", exc)
            self.available = False

    def _count(self) -> int:
        try:
            return int(self._vector_store._collection.count())  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return 0

    # -- queries -----------------------------------------------------------
    def retrieve(self, query: str) -> list[dict[str, Any]]:
        """Return the top-k chunks for `query` as plain dicts.

        A retrieval failure is never fatal: the caller falls back to answering
        without context rather than failing the whole message.
        """
        if not self.available or self._vector_store is None:
            return []
        try:
            results = self._vector_store.similarity_search_with_relevance_scores(
                query, k=settings.rag_top_k
            )
        except Exception as exc:  # noqa: BLE001
            # Not every distance metric supports relevance scores; retry plain.
            logger.debug("Scored search unavailable (%s); retrying without scores.", exc)
            try:
                results = [
                    (document, None)
                    for document in self._vector_store.similarity_search(
                        query, k=settings.rag_top_k
                    )
                ]
            except Exception as inner:  # noqa: BLE001
                logger.warning("Retrieval failed for query %r: %s", query[:80], inner)
                return []

        hits: list[dict[str, Any]] = []
        for document, score in results:
            hits.append(
                {
                    "source": str(document.metadata.get("source", "knowledge-base")),
                    "text": document.page_content,
                    "score": float(score) if score is not None else None,
                }
            )
        return hits

    def search(self, query: str) -> list[dict[str, Any]]:
        """Public search used by the /api/rag/search debug endpoint."""
        if not self.available:
            raise RetrievalError("The knowledge base is not loaded on this server.")
        return self.retrieve(query)


rag_service = RagService()
