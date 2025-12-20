"""RAG service orchestrating retrieval and generation."""

import json
import uuid
from pathlib import Path

import structlog

from src.infrastructure.cache import SemanticCache
from src.infrastructure.embeddings import EmbeddingProvider
from src.infrastructure.llm import LLMProvider
from src.infrastructure.safety import (
    ConfidenceScorer,
    SafetyService,
    SafetyViolationType,
)
from src.infrastructure.vectordb import DocumentChunk, VectorStore
from src.modules.rag.chunker import ChunkingConfig, chunk_document
from src.modules.rag.loader import (
    DocumentLoadError,
    LoadedDocument,
    list_documents,
    load_document,
)
from src.modules.rag.prompts import FALLBACK_SYSTEM_PROMPT, build_rag_prompt
from src.modules.rag.retriever import HybridRetriever, IndexedDocument
from src.modules.rag.schemas import ChunkWithScore, IndexingResult, RAGResponse

logger = structlog.get_logger()


def _serialize_chunks(chunks: list[ChunkWithScore]) -> str:
    """Serialize chunks to JSON for caching."""
    return json.dumps(
        [
            {
                "content": c.content,
                "source": c.source,
                "section": c.section,
                "score": c.score,
                "title": c.title,
            }
            for c in chunks
        ]
    )


def _deserialize_chunks(chunks_json: str) -> list[ChunkWithScore]:
    """Deserialize chunks from JSON cache."""
    data = json.loads(chunks_json)
    return [
        ChunkWithScore(
            content=c["content"],
            source=c["source"],
            section=c["section"],
            score=c["score"],
            title=c.get("title", ""),
        )
        for c in data
    ]


class RAGService:
    """Orchestrates the RAG pipeline: retrieve relevant chunks, generate answer.

    The RAG service coordinates:
    - Document indexing (load, chunk, embed, store)
    - Question answering (embed query, retrieve, generate)
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        semantic_cache: SemanticCache | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        safety_service: SafetyService | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        top_k: int = 5,
        chunk_size: int = 1500,
        chunk_overlap: int = 800,
    ) -> None:
        """Initialize the RAG service.

        Args:
            llm_provider: Provider for generating answers.
            embedding_provider: Provider for generating embeddings.
            vector_store: Store for document chunks.
            semantic_cache: Optional cache for similar question lookups.
                When provided, similar questions return cached answers
                (~50ms vs ~3s), reducing LLM costs by ~40%.
            hybrid_retriever: Optional hybrid retriever combining semantic
                and keyword search. When provided, improves retrieval
                accuracy by 10-15% using BM25 + RRF fusion.
            safety_service: Optional safety service for content moderation
                and hallucination detection. When provided, blocks unsafe
                content and flags low-confidence answers.
            confidence_scorer: Optional scorer for answer confidence.
                When provided, calculates confidence based on retrieval
                quality and grounding.
            top_k: Number of chunks to retrieve per query.
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Overlap between chunks in characters.
        """
        self._llm = llm_provider
        self._embeddings = embedding_provider
        self._store = vector_store
        self._cache = semantic_cache
        self._retriever = hybrid_retriever
        self._safety = safety_service
        self._confidence_scorer = confidence_scorer or ConfidenceScorer()
        self._top_k = top_k
        self._chunking_config = ChunkingConfig(
            max_size=chunk_size,
            overlap=chunk_overlap,
        )
        # Track indexed documents for keyword index rebuilding
        self._indexed_docs: list[IndexedDocument] = []

    async def ask(
        self,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> RAGResponse:
        """Answer a question using RAG with optional conversation history.

        Args:
            question: The user's question.
            conversation_history: Optional list of prior messages as
                [{"role": "user"|"assistant", "content": "..."}].
                When provided, enables multi-turn conversation context.

        Returns:
            RAGResponse with answer and retrieved chunks.
        """
        # Check input safety first (if enabled)
        if self._safety is not None:
            safety_result = await self._safety.check_input(question)
            if not safety_result.is_safe:
                logger.warning(
                    "rag_input_blocked",
                    violation_type=safety_result.violation_type.value,
                    question_length=len(question),
                )
                return RAGResponse(
                    answer=safety_result.message,
                    chunks_used=[],
                    question=question,
                    confidence_level="low",
                    confidence_score=0.0,
                    blocked=True,
                    blocked_reason=safety_result.violation_type.value,
                )

        # Check semantic cache first (if enabled)
        if self._cache is not None:
            cached = await self._cache.get(question)
            if cached is not None:
                logger.info(
                    "rag_cache_hit",
                    question_length=len(question),
                    similarity=cached.similarity_score,
                )
                return RAGResponse(
                    answer=cached.answer,
                    chunks_used=_deserialize_chunks(cached.chunks_json),
                    question=question,
                )

        # Check if we have any documents indexed
        if self._store.count() == 0:
            logger.info("rag_no_documents", question_length=len(question))
            if conversation_history:
                messages = conversation_history.copy()
                messages.append({"role": "user", "content": question})
                answer = await self._llm.complete_with_history(
                    system_prompt=FALLBACK_SYSTEM_PROMPT,
                    messages=messages,
                )
            else:
                answer = await self._llm.complete(
                    system_prompt=FALLBACK_SYSTEM_PROMPT,
                    user_message=question,
                )
            # Don't cache fallback responses (no context)
            return RAGResponse(
                answer=answer,
                chunks_used=[],
                question=question,
            )

        # Retrieve relevant chunks (hybrid or semantic-only)
        if self._retriever is not None:
            # Use hybrid retrieval (semantic + keyword search with RRF)
            logger.debug(
                "rag_hybrid_retrieving",
                top_k=self._top_k,
                keyword_index_size=self._retriever.get_keyword_index_count(),
            )
            results = await self._retriever.retrieve(question, top_k=self._top_k)
        else:
            # Fall back to semantic-only search
            logger.debug("rag_embedding_question", question_length=len(question))
            query_embedding = await self._embeddings.embed(question)
            logger.debug("rag_retrieving", top_k=self._top_k)
            results = await self._store.query(query_embedding, top_k=self._top_k)

        # Convert to ChunkWithScore for response
        chunks_used = [
            ChunkWithScore(
                content=r.content,
                source=r.metadata.get("source", "unknown"),
                section=r.metadata.get("section", ""),
                score=r.score,
                title=r.metadata.get("title", ""),
            )
            for r in results
        ]

        # Build context for LLM
        context_tuples = [
            (r.content, r.metadata.get("source", "unknown"), r.score) for r in results
        ]
        system_prompt = build_rag_prompt(context_tuples)

        # Generate answer
        logger.debug(
            "rag_generating",
            context_chunks=len(results),
            question_length=len(question),
            has_history=conversation_history is not None,
            history_length=len(conversation_history) if conversation_history else 0,
        )

        if conversation_history:
            # Multi-turn: include conversation history
            messages = conversation_history.copy()
            messages.append({"role": "user", "content": question})
            answer = await self._llm.complete_with_history(
                system_prompt=system_prompt,
                messages=messages,
            )
        else:
            # Single-turn: no history
            answer = await self._llm.complete(
                system_prompt=system_prompt,
                user_message=question,
            )

        # Calculate confidence score
        scores = [c.score for c in chunks_used]
        chunk_texts = [c.content for c in chunks_used]
        sources_used = list({c.source for c in chunks_used})

        # Check for hallucination and get grounding ratio
        grounding_ratio: float | None = None
        if self._safety is not None and chunks_used:
            hallucination_result = self._safety.check_hallucination(
                answer=answer,
                chunks=chunk_texts,
                sources=[c.source for c in chunks_used],
            )
            if not hallucination_result.is_safe:
                # Hallucination detected - return low confidence response
                logger.warning(
                    "rag_hallucination_detected",
                    question_length=len(question),
                )
                return RAGResponse(
                    answer=hallucination_result.message,
                    chunks_used=chunks_used,
                    question=question,
                    confidence_level="low",
                    confidence_score=0.0,
                    blocked=True,
                    blocked_reason=SafetyViolationType.HALLUCINATION.value,
                )
            # Get grounding ratio for confidence scoring
            details = self._safety.get_hallucination_details(
                answer=answer,
                chunks=chunk_texts,
            )
            grounding_ratio = details.support_ratio

        # Calculate confidence
        confidence = self._confidence_scorer.score(
            chunk_scores=scores,
            grounding_ratio=grounding_ratio,
        )

        # Log quality metrics for observability
        logger.info(
            "rag_answer_generated",
            question_length=len(question),
            answer_length=len(answer),
            chunks_used=len(chunks_used),
            sources_used=sources_used,
            top_score=max(scores) if scores else 0.0,
            min_score=min(scores) if scores else 0.0,
            avg_score=sum(scores) / len(scores) if scores else 0.0,
            confidence_level=confidence.level.value,
            confidence_score=confidence.score,
        )

        # Store in cache (only high/medium confidence answers with context)
        if self._cache is not None and chunks_used and not confidence.needs_review:
            await self._cache.set(
                question=question,
                answer=answer,
                chunks_json=_serialize_chunks(chunks_used),
            )

        return RAGResponse(
            answer=answer,
            chunks_used=chunks_used,
            question=question,
            confidence_level=confidence.level.value,
            confidence_score=confidence.score,
        )

    async def index_document(self, file_path: Path) -> IndexingResult:
        """Index a document into the vector store.

        Args:
            file_path: Path to the document file.

        Returns:
            IndexingResult with status and chunk count.
        """
        try:
            # Load the document
            doc: LoadedDocument = load_document(file_path)

            # Chunk the document
            chunks = chunk_document(
                doc.content,
                source=doc.source,
                config=self._chunking_config,
                title=doc.title,
            )

            if not chunks:
                return IndexingResult(
                    source=doc.source,
                    chunks_created=0,
                    success=True,
                )

            # Generate embeddings for all chunks
            logger.debug(
                "rag_embedding_chunks",
                source=doc.source,
                chunk_count=len(chunks),
            )
            contents = [chunk.content for chunk in chunks]
            embeddings = await self._embeddings.embed_batch(contents)

            # Create DocumentChunk objects for storage
            doc_chunks = [
                DocumentChunk(
                    id=f"{doc.source}:{chunk.position}:{uuid.uuid4().hex[:8]}",
                    content=chunk.content,
                    embedding=embedding,
                    metadata=chunk.metadata,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]

            # Store in vector DB
            await self._store.add_chunks(doc_chunks)

            # Track documents for keyword index
            for doc_chunk in doc_chunks:
                self._indexed_docs.append(
                    IndexedDocument(
                        id=doc_chunk.id,
                        content=doc_chunk.content,
                        metadata=doc_chunk.metadata,
                    )
                )

            # Rebuild keyword index if hybrid retriever is enabled
            if self._retriever is not None:
                self._retriever.build_keyword_index(self._indexed_docs)
                logger.debug(
                    "rag_keyword_index_rebuilt",
                    document_count=len(self._indexed_docs),
                )

            logger.info(
                "rag_document_indexed",
                source=doc.source,
                chunks_created=len(doc_chunks),
            )

            return IndexingResult(
                source=doc.source,
                chunks_created=len(doc_chunks),
                success=True,
            )

        except DocumentLoadError as e:
            logger.error(
                "rag_load_error",
                file_path=str(file_path),
                error=str(e),
            )
            return IndexingResult(
                source=file_path.name,
                chunks_created=0,
                success=False,
                error_message=str(e),
            )

        except Exception as e:
            logger.error(
                "rag_index_error",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return IndexingResult(
                source=file_path.name,
                chunks_created=0,
                success=False,
                error_message=f"Indexing failed: {e}",
            )

    async def index_all_documents(self, documents_path: Path) -> list[IndexingResult]:
        """Index all documents in a directory.

        Args:
            documents_path: Directory containing documents.

        Returns:
            List of IndexingResult for each document.
        """
        documents = list_documents(documents_path)

        if not documents:
            logger.warning(
                "rag_no_documents_found",
                path=str(documents_path),
            )
            return []

        results: list[IndexingResult] = []

        for doc_path in documents:
            result = await self.index_document(doc_path)
            results.append(result)

        total_chunks = sum(r.chunks_created for r in results if r.success)
        success_count = sum(1 for r in results if r.success)

        logger.info(
            "rag_index_all_complete",
            documents_processed=len(documents),
            documents_succeeded=success_count,
            total_chunks=total_chunks,
        )

        return results

    async def clear_index(self) -> None:
        """Clear all indexed documents and invalidate cache."""
        await self._store.clear()

        # Clear keyword index and tracked documents
        self._indexed_docs = []
        if self._retriever is not None:
            self._retriever.clear_keyword_index()
            logger.info("rag_keyword_index_cleared")

        # Invalidate cache when documents change
        if self._cache is not None:
            await self._cache.clear()
            logger.info("rag_cache_invalidated")

        logger.info("rag_index_cleared")

    async def clear_cache(self) -> None:
        """Clear only the semantic cache, keeping indexed documents."""
        if self._cache is not None:
            await self._cache.clear()
            logger.info("rag_cache_cleared")

    def get_cache_count(self) -> int:
        """Get the number of cached entries."""
        if self._cache is None:
            return 0
        return self._cache.count()

    def get_document_count(self) -> int:
        """Get the number of chunks in the index."""
        return self._store.count()

    def get_keyword_index_count(self) -> int:
        """Get the number of documents in the keyword index."""
        if self._retriever is None:
            return 0
        return self._retriever.get_keyword_index_count()

    def is_hybrid_enabled(self) -> bool:
        """Check if hybrid retrieval is enabled."""
        return self._retriever is not None
