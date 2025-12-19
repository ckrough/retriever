"""RAG service orchestrating retrieval and generation."""

import uuid
from pathlib import Path

import structlog

from src.infrastructure.embeddings import EmbeddingProvider
from src.infrastructure.llm import LLMProvider
from src.infrastructure.vectordb import DocumentChunk, VectorStore
from src.modules.rag.chunker import ChunkingConfig, chunk_document
from src.modules.rag.loader import (
    DocumentLoadError,
    LoadedDocument,
    list_documents,
    load_document,
)
from src.modules.rag.prompts import FALLBACK_SYSTEM_PROMPT, build_rag_prompt
from src.modules.rag.schemas import ChunkWithScore, IndexingResult, RAGResponse

logger = structlog.get_logger()


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
        top_k: int = 5,
        chunk_size: int = 1500,
        chunk_overlap: int = 800,
    ) -> None:
        """Initialize the RAG service.

        Args:
            llm_provider: Provider for generating answers.
            embedding_provider: Provider for generating embeddings.
            vector_store: Store for document chunks.
            top_k: Number of chunks to retrieve per query.
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Overlap between chunks in characters.
        """
        self._llm = llm_provider
        self._embeddings = embedding_provider
        self._store = vector_store
        self._top_k = top_k
        self._chunking_config = ChunkingConfig(
            max_size=chunk_size,
            overlap=chunk_overlap,
        )

    async def ask(self, question: str) -> RAGResponse:
        """Answer a question using RAG.

        Args:
            question: The user's question.

        Returns:
            RAGResponse with answer and retrieved chunks.
        """
        # Check if we have any documents indexed
        if self._store.count() == 0:
            logger.info("rag_no_documents", question_length=len(question))
            answer = await self._llm.complete(
                system_prompt=FALLBACK_SYSTEM_PROMPT,
                user_message=question,
            )
            return RAGResponse(
                answer=answer,
                chunks_used=[],
                question=question,
            )

        # Embed the question
        logger.debug("rag_embedding_question", question_length=len(question))
        query_embedding = await self._embeddings.embed(question)

        # Retrieve relevant chunks
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
        )
        answer = await self._llm.complete(
            system_prompt=system_prompt,
            user_message=question,
        )

        logger.info(
            "rag_answer_generated",
            question_length=len(question),
            answer_length=len(answer),
            chunks_used=len(chunks_used),
        )

        return RAGResponse(
            answer=answer,
            chunks_used=chunks_used,
            question=question,
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
        """Clear all indexed documents."""
        await self._store.clear()
        logger.info("rag_index_cleared")

    def get_document_count(self) -> int:
        """Get the number of chunks in the index."""
        return self._store.count()
