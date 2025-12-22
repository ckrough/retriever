"""Web routes for server-rendered pages."""

from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from src.api.rate_limit import get_rate_limit_string, limiter
from src.config import Settings, get_settings
from src.infrastructure.cache import ChromaSemanticCache
from src.infrastructure.database import get_database
from src.infrastructure.embeddings import OpenAIEmbeddingProvider
from src.infrastructure.llm import LLMProviderError, OpenRouterProvider
from src.infrastructure.llm.openrouter import DEFAULT_SYSTEM_PROMPT
from src.infrastructure.vectordb import ChromaVectorStore
from src.modules.rag import HybridRetriever, RAGService
from src.modules.rag.message_store import MessageStore
from src.web.dependencies import require_auth
from src.web.templates import templates

logger = structlog.get_logger()

router = APIRouter()

# Input constraints
MAX_QUESTION_LENGTH = 2000

# Singletons (per process)
_vector_store_cache: dict[str, ChromaVectorStore] = {}
_semantic_cache_instance: dict[str, ChromaSemanticCache] = {}
_hybrid_retriever_instance: dict[str, HybridRetriever] = {}


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


def get_semantic_cache(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChromaSemanticCache | None:
    """Get or create the semantic cache singleton.

    Returns None if caching is disabled or embeddings aren't configured.
    """
    if not settings.cache_enabled:
        return None

    if settings.embedding_api_key is None:
        return None

    persist_path = settings.chroma_persist_path

    if persist_path not in _semantic_cache_instance:
        embedding_provider = OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key.get_secret_value(),
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            timeout_seconds=settings.embedding_timeout_seconds,
            circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
            circuit_breaker_timeout=settings.circuit_breaker_timeout,
        )

        _semantic_cache_instance[persist_path] = ChromaSemanticCache(
            embedding_provider=embedding_provider,
            persist_path=Path(persist_path),
            similarity_threshold=settings.cache_similarity_threshold,
            ttl_hours=settings.cache_ttl_hours,
        )

    return _semantic_cache_instance[persist_path]


def get_hybrid_retriever(
    settings: Annotated[Settings, Depends(get_settings)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
) -> HybridRetriever | None:
    """Get or create the hybrid retriever singleton.

    Returns None if hybrid retrieval is disabled or embeddings aren't configured.
    """
    if not settings.hybrid_retrieval_enabled:
        return None

    if settings.embedding_api_key is None:
        return None

    persist_path = settings.chroma_persist_path

    if persist_path not in _hybrid_retriever_instance:
        embedding_provider = OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key.get_secret_value(),
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            timeout_seconds=settings.embedding_timeout_seconds,
            circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
            circuit_breaker_timeout=settings.circuit_breaker_timeout,
        )

        _hybrid_retriever_instance[persist_path] = HybridRetriever(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            semantic_weight=settings.hybrid_semantic_weight,
            keyword_weight=settings.hybrid_keyword_weight,
            rrf_k=settings.hybrid_rrf_k,
        )

    return _hybrid_retriever_instance[persist_path]


def get_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
    semantic_cache: Annotated[ChromaSemanticCache | None, Depends(get_semantic_cache)],
    hybrid_retriever: Annotated[HybridRetriever | None, Depends(get_hybrid_retriever)],
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
        semantic_cache=semantic_cache,
        hybrid_retriever=hybrid_retriever,
        top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    user: Annotated[dict[str, Any] | None, Depends(require_auth)],
) -> Response:
    """Render the main chat page.

    Requires authentication when enabled.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user},
    )


@router.post("/ask", response_class=HTMLResponse)
@limiter.limit(get_rate_limit_string)
async def ask(
    request: Request,
    question: Annotated[str, Form(min_length=1, max_length=MAX_QUESTION_LENGTH)],
    rag_service: Annotated[RAGService | None, Depends(get_rag_service)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
    user: Annotated[dict[str, Any] | None, Depends(require_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Handle a question submission and return the answer fragment.

    Uses RAG if configured and documents are indexed, otherwise falls back
    to direct LLM or hardcoded responses. Requires authentication when enabled.
    Includes conversation history for multi-turn context when user is authenticated.
    """
    # Get user ID for conversation history (if authenticated)
    user_id: UUID | None = None
    if user is not None:
        user_id = UUID(user["user_id"])

    # Load conversation history for context
    conversation_history: list[dict[str, str]] = []
    if user_id is not None:
        try:
            db = get_database()
            message_store = MessageStore(db)
            messages = await message_store.get_recent_messages(
                user_id, limit=settings.conversation_max_messages
            )
            conversation_history = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
        except Exception as e:
            logger.warning("conversation_history_load_error", error=str(e))
            # Continue without history on error

    # If no LLM provider configured, use fallback response
    if llm_provider is None:
        logger.warning("llm_not_configured", message="Using fallback response")
        answer = (
            "Hello! I'm Retriever, the volunteer assistant. "
            "I'll be able to answer questions about shelter policies and procedures "
            "once I'm fully set up. (LLM not configured)"
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={"question": question, "answer": answer, "chunks_used": []},
        )

    try:
        # Try RAG if available
        if rag_service is not None:
            response = await rag_service.ask(
                question,
                conversation_history=conversation_history
                if conversation_history
                else None,
            )
            answer = response.answer
            # Filter to high/medium relevance (≥0.5) and limit to top 3 for cleaner UX
            chunks_used = [c for c in response.chunks_used if c.score >= 0.5][:3]
        else:
            # Fall back to direct LLM (no RAG)
            logger.info("rag_not_available", message="Using direct LLM")
            if conversation_history:
                llm_messages = conversation_history.copy()
                llm_messages.append({"role": "user", "content": question})
                answer = await llm_provider.complete_with_history(
                    system_prompt=DEFAULT_SYSTEM_PROMPT,
                    messages=llm_messages,
                )
            else:
                answer = await llm_provider.complete(
                    system_prompt=DEFAULT_SYSTEM_PROMPT,
                    user_message=question,
                )
            chunks_used = []

        # Save messages to conversation history
        if user_id is not None:
            try:
                db = get_database()
                message_store = MessageStore(db)
                await message_store.save_message(user_id, "user", question)
                await message_store.save_message(user_id, "assistant", answer)
            except Exception as e:
                logger.warning("conversation_history_save_error", error=str(e))
                # Continue without saving on error

        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={
                "question": question,
                "answer": answer,
                "chunks_used": chunks_used,
            },
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


@router.get("/history", response_class=HTMLResponse)
async def get_history(
    request: Request,
    user: Annotated[dict[str, Any] | None, Depends(require_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Get conversation history for the current user.

    Returns HTML fragments for all messages to load on page refresh.
    Requires authentication.
    """
    if user is None:
        # No user, return empty
        return templates.TemplateResponse(
            request=request,
            name="partials/message_history.html",
            context={"messages": []},
        )

    user_id = UUID(user["user_id"])

    try:
        db = get_database()
        message_store = MessageStore(db)
        messages = await message_store.get_recent_messages(
            user_id, limit=settings.conversation_max_messages
        )

        # Group messages into pairs for display
        message_pairs: list[dict[str, str]] = []
        i = 0
        while i < len(messages):
            if messages[i].role == "user":
                question = messages[i].content
                answer = ""
                # Look for the assistant response
                if i + 1 < len(messages) and messages[i + 1].role == "assistant":
                    answer = messages[i + 1].content
                    i += 2
                else:
                    i += 1
                message_pairs.append({"question": question, "answer": answer})
            else:
                # Orphan assistant message, skip
                i += 1

        return templates.TemplateResponse(
            request=request,
            name="partials/message_history.html",
            context={"message_pairs": message_pairs},
        )

    except Exception as e:
        logger.warning("conversation_history_load_error", error=str(e))
        return templates.TemplateResponse(
            request=request,
            name="partials/message_history.html",
            context={"message_pairs": []},
        )


@router.get("/clear-chat", response_class=HTMLResponse)
async def clear_chat(
    user: Annotated[dict[str, Any] | None, Depends(require_auth)],
) -> Response:
    """Clear conversation history for the current user.

    Deletes all messages and returns empty chat container.
    Requires authentication.
    """
    if user is not None:
        user_id = UUID(user["user_id"])
        try:
            db = get_database()
            message_store = MessageStore(db)
            deleted = await message_store.clear_messages(user_id)
            logger.info("chat_cleared", user_id=str(user_id), messages_deleted=deleted)
        except Exception as e:
            logger.warning("clear_chat_error", error=str(e))

    # Return empty container
    return Response(
        content="",
        media_type="text/html",
    )
