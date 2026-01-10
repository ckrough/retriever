"""Hybrid retriever combining semantic and keyword search."""

from collections import defaultdict
from dataclasses import dataclass

import structlog
from rank_bm25 import BM25Okapi

from src.infrastructure.embeddings import EmbeddingProvider
from src.infrastructure.observability import get_tracer
from src.infrastructure.vectordb import RetrievalResult, VectorStore

logger = structlog.get_logger()
tracer = get_tracer(__name__)


@dataclass
class IndexedDocument:
    """A document stored in the BM25 index."""

    id: str
    content: str
    metadata: dict[str, str]


class HybridRetriever:
    """Retriever combining semantic search with BM25 keyword search.

    Hybrid retrieval improves accuracy by 10-15% over semantic-only search
    by catching both semantic matches ("sign in" = "check in") and
    exact keyword matches ("COVID-19 protocol").

    The results are merged using Reciprocal Rank Fusion (RRF), which
    combines rankings from multiple sources into a single ordered list.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5,
        rrf_k: int = 60,
    ) -> None:
        """Initialize the hybrid retriever.

        Args:
            embedding_provider: Provider for generating query embeddings.
            vector_store: Store for semantic search.
            semantic_weight: Weight for semantic search results (0-1).
            keyword_weight: Weight for keyword search results (0-1).
            rrf_k: Constant for Reciprocal Rank Fusion (default 60).
        """
        self._embeddings = embedding_provider
        self._vector_store = vector_store
        self._semantic_weight = semantic_weight
        self._keyword_weight = keyword_weight
        self._rrf_k = rrf_k

        # BM25 index (rebuilt when documents change)
        self._bm25: BM25Okapi | None = None
        self._indexed_docs: list[IndexedDocument] = []

    def build_keyword_index(self, documents: list[IndexedDocument]) -> None:
        """Build the BM25 index from documents.

        This should be called after indexing documents into the vector store.

        Args:
            documents: List of documents to index for keyword search.
        """
        self._indexed_docs = documents

        if not documents:
            self._bm25 = None
            logger.info("bm25_index_empty")
            return

        # Tokenize documents for BM25
        tokenized_corpus = [self._tokenize(doc.content) for doc in documents]

        self._bm25 = BM25Okapi(tokenized_corpus)

        logger.info(
            "bm25_index_built",
            document_count=len(documents),
            avg_doc_length=sum(len(t) for t in tokenized_corpus)
            / len(tokenized_corpus),
        )

    def clear_keyword_index(self) -> None:
        """Clear the BM25 keyword index."""
        self._bm25 = None
        self._indexed_docs = []
        logger.info("bm25_index_cleared")

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Retrieve documents using hybrid semantic + keyword search.

        Args:
            query: The search query.
            top_k: Number of results to return.

        Returns:
            List of retrieval results ordered by combined relevance.
        """
        with tracer.start_as_current_span("retrieval.hybrid") as span:
            span.set_attribute("retrieval.query_length", len(query))
            span.set_attribute("retrieval.top_k", top_k)

            # Get semantic results (over-retrieve for better fusion)
            semantic_k = min(top_k * 2, self._vector_store.count())
            if semantic_k == 0:
                span.set_attribute("retrieval.results_count", 0)
                return []

            with tracer.start_as_current_span("retrieval.semantic"):
                query_embedding = await self._embeddings.embed(query)
                semantic_results = await self._vector_store.query(
                    query_embedding, top_k=semantic_k
                )

            span.set_attribute("retrieval.semantic_count", len(semantic_results))

            logger.debug(
                "hybrid_semantic_results",
                count=len(semantic_results),
                top_score=semantic_results[0].score if semantic_results else 0,
            )

            # Get keyword results
            with tracer.start_as_current_span("retrieval.keyword"):
                keyword_results = self._keyword_search(query, top_k=top_k * 2)

            span.set_attribute("retrieval.keyword_count", len(keyword_results))

            logger.debug(
                "hybrid_keyword_results",
                count=len(keyword_results),
                top_score=keyword_results[0].score if keyword_results else 0,
            )

            # Merge results using Reciprocal Rank Fusion
            merged = self._reciprocal_rank_fusion(
                semantic_results,
                keyword_results,
            )

            # Return top_k results
            final_results = merged[:top_k]

            span.set_attribute("retrieval.merged_count", len(merged))
            span.set_attribute("retrieval.results_count", len(final_results))
            if final_results:
                span.set_attribute("retrieval.top_score", final_results[0].score)

            logger.info(
                "hybrid_retrieval_complete",
                query_length=len(query),
                semantic_count=len(semantic_results),
                keyword_count=len(keyword_results),
                merged_count=len(merged),
                returned_count=len(final_results),
            )

            return final_results

    def _keyword_search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Search using BM25 keyword matching.

        Args:
            query: The search query.
            top_k: Number of results to return.

        Returns:
            List of retrieval results with BM25 scores.
        """
        if self._bm25 is None or not self._indexed_docs:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # Get top_k document indices with highest scores
        scored_docs = list(enumerate(scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_docs = scored_docs[:top_k]

        results: list[RetrievalResult] = []
        for idx, score in top_docs:
            if score > 0:  # Only include docs with positive BM25 score
                doc = self._indexed_docs[idx]
                results.append(
                    RetrievalResult(
                        id=doc.id,
                        content=doc.content,
                        metadata=doc.metadata,
                        score=float(score),
                    )
                )

        return results

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[RetrievalResult],
        keyword_results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Merge results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each ranking list.
        This gives higher weight to documents ranked highly in multiple lists.

        Args:
            semantic_results: Results from semantic search.
            keyword_results: Results from keyword search.

        Returns:
            Merged results sorted by RRF score.
        """
        # Calculate RRF scores
        rrf_scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, RetrievalResult] = {}

        # Add semantic results
        for rank, result in enumerate(semantic_results):
            rrf_scores[result.id] += self._semantic_weight / (self._rrf_k + rank + 1)
            doc_map[result.id] = result

        # Add keyword results
        for rank, result in enumerate(keyword_results):
            rrf_scores[result.id] += self._keyword_weight / (self._rrf_k + rank + 1)
            # Prefer semantic result if we have both (has embedding-based score)
            if result.id not in doc_map:
                doc_map[result.id] = result

        # Sort by RRF score
        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )

        # Build result list with RRF score
        merged: list[RetrievalResult] = []
        for doc_id in sorted_ids:
            original = doc_map[doc_id]
            merged.append(
                RetrievalResult(
                    id=original.id,
                    content=original.content,
                    metadata=original.metadata,
                    score=rrf_scores[doc_id],  # Use RRF score as final score
                )
            )

        return merged

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple tokenization for BM25.

        Converts to lowercase and splits on whitespace/punctuation.

        Args:
            text: Text to tokenize.

        Returns:
            List of tokens.
        """
        # Simple tokenization: lowercase and split on non-alphanumeric
        import re

        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def get_keyword_index_count(self) -> int:
        """Return the number of documents in the keyword index."""
        return len(self._indexed_docs)
