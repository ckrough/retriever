"""Chroma vector store implementation."""

import os
from pathlib import Path
from typing import Any

# Disable Chroma telemetry (fixes posthog capture() error in v0.5.x)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
import structlog
from chromadb.config import Settings as ChromaSettings

from src.infrastructure.observability import get_tracer
from src.infrastructure.vectordb.exceptions import (
    VectorStoreConfigurationError,
    VectorStoreError,
)
from src.infrastructure.vectordb.protocol import DocumentChunk, RetrievalResult

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class ChromaVectorStore:
    """Vector store using ChromaDB in embedded/persistent mode.

    ChromaDB runs in-process and persists data to the filesystem,
    making it ideal for single-instance deployments.
    """

    PROVIDER_NAME = "chroma"

    def __init__(
        self,
        persist_path: str | Path,
        collection_name: str = "documents",
    ) -> None:
        """Initialize the Chroma vector store.

        Args:
            persist_path: Directory path for persistent storage.
            collection_name: Name of the collection to use.

        Raises:
            VectorStoreConfigurationError: If initialization fails.
        """
        self._persist_path = Path(persist_path)
        self._collection_name = collection_name

        try:
            # Ensure the persist directory exists
            self._persist_path.mkdir(parents=True, exist_ok=True)

            # Initialize Chroma client in persistent mode
            self._client = chromadb.PersistentClient(
                path=str(self._persist_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,  # Allow clearing the collection
                ),
            )

            # Get or create the collection
            # We store embeddings pre-computed, so no embedding function
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )

            logger.info(
                "chroma_initialized",
                provider=self.PROVIDER_NAME,
                persist_path=str(self._persist_path),
                collection=collection_name,
                count=self._collection.count(),
            )

        except Exception as e:
            logger.error(
                "chroma_init_failed",
                provider=self.PROVIDER_NAME,
                persist_path=str(self._persist_path),
                error=str(e),
            )
            raise VectorStoreConfigurationError(
                f"Failed to initialize Chroma: {e}",
                provider=self.PROVIDER_NAME,
            ) from e

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Add document chunks with embeddings to the store.

        Args:
            chunks: List of chunks with embeddings and metadata.

        Raises:
            VectorStoreError: If addition fails.
        """
        if not chunks:
            return

        with tracer.start_as_current_span("vectordb.add_chunks") as span:
            span.set_attribute("vectordb.provider", self.PROVIDER_NAME)
            span.set_attribute("vectordb.chunk_count", len(chunks))

            try:
                # ChromaDB expects separate lists for each component
                ids = [chunk.id for chunk in chunks]
                documents = [chunk.content for chunk in chunks]
                embeddings = [chunk.embedding for chunk in chunks]
                metadatas: list[dict[str, Any]] = [chunk.metadata for chunk in chunks]

                self._collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )

                total_count = self._collection.count()
                span.set_attribute("vectordb.total_count", total_count)

                logger.debug(
                    "chroma_chunks_added",
                    provider=self.PROVIDER_NAME,
                    count=len(chunks),
                    total_count=total_count,
                )

            except Exception as e:
                span.record_exception(e)
                logger.error(
                    "chroma_add_failed",
                    provider=self.PROVIDER_NAME,
                    error=str(e),
                    chunk_count=len(chunks),
                )
                raise VectorStoreError(
                    f"Failed to add chunks: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e

    async def query(
        self,
        embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Query for similar chunks.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of retrieval results with similarity scores.

        Raises:
            VectorStoreError: If query fails.
        """
        with tracer.start_as_current_span("vectordb.query") as span:
            span.set_attribute("vectordb.provider", self.PROVIDER_NAME)
            span.set_attribute("vectordb.top_k", top_k)
            span.set_attribute("vectordb.collection_size", self._collection.count())

            try:
                results = self._collection.query(
                    query_embeddings=[embedding],
                    n_results=min(top_k, self._collection.count()),
                    include=["documents", "metadatas", "distances"],
                )

                # Convert Chroma results to RetrievalResult objects
                retrieval_results: list[RetrievalResult] = []

                # Chroma returns lists of lists (one per query), we only have one query
                # All fields can be None if not included
                ids_list = results.get("ids") or [[]]
                ids = ids_list[0] if ids_list else []

                docs_list = results.get("documents") or [[]]
                documents = docs_list[0] if docs_list else []

                meta_list = results.get("metadatas") or [[]]
                metadatas = meta_list[0] if meta_list else []

                dist_list = results.get("distances") or [[]]
                distances = dist_list[0] if dist_list else []

                for i, doc_id in enumerate(ids):
                    # Chroma returns distance; convert to similarity score
                    # For cosine, distance = 1 - similarity
                    distance = distances[i] if i < len(distances) else 0.0
                    score = 1.0 - float(distance)

                    # Convert metadata values to strings for our protocol
                    raw_meta = metadatas[i] if i < len(metadatas) else {}
                    str_meta: dict[str, str] = {
                        k: str(v) for k, v in (raw_meta or {}).items()
                    }

                    retrieval_results.append(
                        RetrievalResult(
                            id=doc_id,
                            content=documents[i] if i < len(documents) else "",
                            metadata=str_meta,
                            score=score,
                        )
                    )

                span.set_attribute("vectordb.results_count", len(retrieval_results))
                if retrieval_results:
                    span.set_attribute("vectordb.top_score", retrieval_results[0].score)

                logger.debug(
                    "chroma_query_success",
                    provider=self.PROVIDER_NAME,
                    top_k=top_k,
                    results_count=len(retrieval_results),
                )

                return retrieval_results

            except Exception as e:
                span.record_exception(e)
                logger.error(
                    "chroma_query_failed",
                    provider=self.PROVIDER_NAME,
                    error=str(e),
                )
                raise VectorStoreError(
                    f"Failed to query: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e

    async def clear(self) -> None:
        """Clear all data from the store.

        Raises:
            VectorStoreError: If clearing fails.
        """
        with tracer.start_as_current_span("vectordb.clear") as span:
            span.set_attribute("vectordb.provider", self.PROVIDER_NAME)
            span.set_attribute("vectordb.collection", self._collection_name)

            try:
                # Delete and recreate the collection
                self._client.delete_collection(name=self._collection_name)
                self._collection = self._client.create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )

                logger.info(
                    "chroma_cleared",
                    provider=self.PROVIDER_NAME,
                    collection=self._collection_name,
                )

            except Exception as e:
                span.record_exception(e)
                logger.error(
                    "chroma_clear_failed",
                    provider=self.PROVIDER_NAME,
                    error=str(e),
                )
                raise VectorStoreError(
                    f"Failed to clear collection: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e

    def count(self) -> int:
        """Return the number of chunks in the store."""
        return self._collection.count()
