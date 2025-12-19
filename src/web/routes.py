"""Web routes for server-rendered pages."""

from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from src.api.rate_limit import get_rate_limit_string, limiter
from src.config import Settings, get_settings
from src.infrastructure.embeddings import OpenAIEmbeddingProvider
from src.infrastructure.llm import LLMProviderError, OpenRouterProvider
from src.infrastructure.llm.openrouter import DEFAULT_SYSTEM_PROMPT
from src.infrastructure.vectordb import ChromaVectorStore
from src.modules.rag import RAGService
from src.web.templates import templates

logger = structlog.get_logger()

router = APIRouter()

# Input constraints
MAX_QUESTION_LENGTH = 2000

# Cache for vector store (singleton per process)
_vector_store_cache: dict[str, ChromaVectorStore] = {}


def get_llm_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OpenRouterProvider | None:
    """Get the LLM provider if configured, None otherwise.

    Returns None when API key is not set, allowing graceful fallback
    to hardcoded responses during development/testing.
    """
    if settings.openrouter_api_key is None:
        return None

    return OpenRouterProvider(
        api_key=settings.openrouter_api_key.get_secret_value(),
        default_model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
        circuit_breaker_timeout=settings.circuit_breaker_timeout,
    )


def get_vector_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChromaVectorStore:
    """Get or create the vector store singleton.

    The vector store is cached per persist path to avoid re-initializing
    Chroma on every request.
    """
    persist_path = settings.chroma_persist_path

    if persist_path not in _vector_store_cache:
        _vector_store_cache[persist_path] = ChromaVectorStore(
            persist_path=Path(persist_path),
            collection_name=settings.chroma_collection_name,
        )

    return _vector_store_cache[persist_path]


def get_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
) -> RAGService | None:
    """Get the RAG service if fully configured.

    Returns None if LLM or embeddings are not configured.
    """
    if llm_provider is None:
        return None

    if settings.embedding_api_key is None:
        return None

    embedding_provider = OpenAIEmbeddingProvider(
        api_key=settings.embedding_api_key.get_secret_value(),
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        timeout_seconds=settings.embedding_timeout_seconds,
        circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
        circuit_breaker_timeout=settings.circuit_breaker_timeout,
    )

    return RAGService(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    """Render the main chat page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.post("/ask", response_class=HTMLResponse)
@limiter.limit(get_rate_limit_string)
async def ask(
    request: Request,
    question: Annotated[str, Form(min_length=1, max_length=MAX_QUESTION_LENGTH)],
    rag_service: Annotated[RAGService | None, Depends(get_rag_service)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
) -> Response:
    """Handle a question submission and return the answer fragment.

    Uses RAG if configured and documents are indexed, otherwise falls back
    to direct LLM or hardcoded responses.
    """
    # If no LLM provider configured, use fallback response
    if llm_provider is None:
        logger.warning("llm_not_configured", message="Using fallback response")
        answer = (
            "Hello! I'm GoodPuppy, the volunteer assistant. "
            "I'll be able to answer questions about shelter policies and procedures "
            "once I'm fully set up. (LLM not configured)"
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={"question": question, "answer": answer},
        )

    try:
        # Try RAG if available
        if rag_service is not None:
            response = await rag_service.ask(question)

            # Include sources in the answer for transparency
            chunks_used = response.chunks_used
            if chunks_used:
                sources = list({c.source for c in chunks_used})
                sources_text = f"\n\n(Sources: {', '.join(sources)})"
                answer = response.answer + sources_text
            else:
                answer = response.answer

            return templates.TemplateResponse(
                request=request,
                name="partials/message_pair.html",
                context={"question": question, "answer": answer},
            )

        # Fall back to direct LLM (no RAG)
        logger.info("rag_not_available", message="Using direct LLM")
        answer = await llm_provider.complete(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_message=question,
        )

        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={"question": question, "answer": answer},
        )

    except LLMProviderError as e:
        logger.error(
            "llm_error",
            error=str(e),
            provider=e.provider,
            question_length=len(question),
        )

        return templates.TemplateResponse(
            request=request,
            name="partials/error_message.html",
            context={
                "question": question,
                "error_message": "Sorry, I'm having trouble connecting right now. Please try again in a moment.",
            },
        )
