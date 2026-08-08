"""
Knowledge base indexer.

Reads all Markdown files from the knowledge-base directory, chunks them on
'---' horizontal-rule boundaries (as recommended in DATA_SCHEMA.md), preserves
heading hierarchy as metadata, embeds with sentence-transformers, and stores
in a local ChromaDB collection.
"""

import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import KB_DIR, CHROMA_PERSIST_DIR, EMBEDDING_MODEL, RAG_COLLECTION_NAME


def _extract_heading_path(text: str) -> str:
    """Extract the deepest heading from a chunk for metadata."""
    headings = re.findall(r"^(#{1,4})\s+(.+)$", text, re.MULTILINE)
    if headings:
        return " > ".join(h[1].strip() for h in headings)
    return ""


def _chunk_markdown(filepath: Path) -> list[dict]:
    """
    Split a Markdown file into chunks on '---' boundaries.
    Each chunk retains source file and heading hierarchy as metadata.
    """
    content = filepath.read_text(encoding="utf-8")

    # Split on horizontal rules (--- on its own line)
    raw_chunks = re.split(r"\n---\n", content)

    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text or len(chunk_text) < 20:
            continue

        heading_path = _extract_heading_path(chunk_text)
        source_file = filepath.relative_to(KB_DIR)

        # Determine the category from the directory structure
        parts = source_file.parts
        category = parts[0] if len(parts) > 1 else "general"

        chunks.append(
            {
                "id": f"{source_file.stem}__chunk_{i}",
                "text": chunk_text,
                "metadata": {
                    "source_file": str(source_file),
                    "category": category,
                    "heading_path": heading_path,
                    "chunk_index": i,
                },
            }
        )

    return chunks


def _collect_all_chunks() -> list[dict]:
    """Walk the knowledge-base directory and chunk all Markdown files."""
    all_chunks = []
    for md_file in sorted(KB_DIR.rglob("*.md")):
        all_chunks.extend(_chunk_markdown(md_file))
    return all_chunks


class KnowledgeBaseIndexer:
    """Indexes the knowledge base into ChromaDB for retrieval."""

    def __init__(self):
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    def index(self, force_rebuild: bool = False) -> int:
        """
        Index the knowledge base. Returns the number of chunks indexed.

        If the collection already exists and force_rebuild is False,
        skips indexing and returns the existing count.
        """
        existing_collections = [c.name for c in self.client.list_collections()]

        if RAG_COLLECTION_NAME in existing_collections and not force_rebuild:
            collection = self.client.get_collection(RAG_COLLECTION_NAME)
            count = collection.count()
            if count > 0:
                return count

        # Delete existing collection if rebuilding
        if RAG_COLLECTION_NAME in existing_collections:
            self.client.delete_collection(RAG_COLLECTION_NAME)

        collection = self.client.create_collection(
            name=RAG_COLLECTION_NAME,
            metadata={"description": "Product knowledge base for support triage"},
        )

        chunks = _collect_all_chunks()
        if not chunks:
            return 0

        # Embed all chunks
        texts = [c["text"] for c in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        # Add to ChromaDB
        collection.add(
            ids=[c["id"] for c in chunks],
            embeddings=[e.tolist() for e in embeddings],
            documents=texts,
            metadatas=[c["metadata"] for c in chunks],
        )

        return len(chunks)


def build_index(force_rebuild: bool = False) -> int:
    """Convenience function to build the knowledge base index."""
    indexer = KnowledgeBaseIndexer()
    return indexer.index(force_rebuild=force_rebuild)
