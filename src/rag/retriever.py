"""
Knowledge base retriever.

Queries the ChromaDB vector store to find knowledge-base chunks relevant
to a given ticket's text. Returns ranked results with source metadata.
"""

from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, RAG_COLLECTION_NAME, RAG_TOP_K


@dataclass
class RetrievalResult:
    """A single retrieval result from the knowledge base."""

    text: str
    source_file: str
    heading_path: str
    category: str
    relevance_score: float  # Lower distance = more relevant


class KnowledgeBaseRetriever:
    """Retrieves relevant knowledge-base chunks for a given query."""

    def __init__(self):
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        """
        Search the knowledge base for chunks relevant to the query.

        Args:
            query: The search text (typically ticket subject + body).
            top_k: Number of results to return (defaults to RAG_TOP_K).

        Returns:
            List of RetrievalResult objects sorted by relevance.
        """
        top_k = top_k or RAG_TOP_K

        try:
            collection = self.client.get_collection(RAG_COLLECTION_NAME)
        except Exception:
            return []

        if collection.count() == 0:
            return []

        # Embed the query
        query_embedding = self.embedding_model.encode(query).tolist()

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # Build result objects
        retrieval_results = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                retrieval_results.append(
                    RetrievalResult(
                        text=doc,
                        source_file=meta.get("source_file", ""),
                        heading_path=meta.get("heading_path", ""),
                        category=meta.get("category", ""),
                        relevance_score=dist,
                    )
                )

        return retrieval_results


def retrieve_for_ticket(subject: str, body: str, top_k: int | None = None) -> list[RetrievalResult]:
    """
    Convenience function to retrieve KB context for a ticket.

    Combines subject and body into a single query for better retrieval.
    """
    retriever = KnowledgeBaseRetriever()
    query = f"{subject}\n\n{body}"
    return retriever.retrieve(query, top_k=top_k)
