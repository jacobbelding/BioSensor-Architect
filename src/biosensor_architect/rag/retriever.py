"""Query interface for the ChromaDB literature index.

Used by the ``search_literature`` tool function to provide RAG-augmented
context to the LiteratureValidator agent.
"""

from __future__ import annotations

import json

import chromadb

from biosensor_architect.config import settings


def _get_collection(collection_name: str = "literature") -> chromadb.Collection:
    """Get a persistent ChromaDB collection (read-only access)."""
    persist_dir = str(settings.chroma_persist_dir)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(
    query: str,
    k: int = 5,
    collection_name: str = "literature",
) -> list[dict]:
    """Retrieve relevant literature chunks from ChromaDB.

    Args:
        query: Natural language query.
        k: Number of results to return.
        collection_name: ChromaDB collection name.

    Returns:
        List of dicts with keys: text, source, score, chunk_index.
    """
    collection = _get_collection(collection_name)

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        hits.append({
            "text": doc,
            "source": meta.get("source", "unknown") if meta else "unknown",
            "pmid": meta.get("pmid") if meta else None,
            "chunk_index": meta.get("chunk_index", 0) if meta else 0,
            "score": round(1.0 - dist, 4),  # cosine distance → similarity
        })

    return hits


def search_literature(query: str, max_results: int = 5) -> str:
    """Search the indexed literature database for relevant passages.

    This is a tool function callable by AutoGen agents. Returns JSON-formatted
    results from the local ChromaDB vector store.

    Args:
        query: Natural language search query (e.g., "RD29A promoter drought specificity").
        max_results: Maximum number of passages to return (default 5).

    Returns:
        JSON string with matching literature passages and their sources.
    """
    hits = retrieve(query, k=max_results)

    if not hits:
        return json.dumps({
            "message": "No indexed literature available. Run 'bsa index-papers ./papers/' to populate the database.",
            "results": [],
        })

    results = []
    for hit in hits:
        results.append({
            "text": hit["text"][:1500],  # Cap length for LLM context
            "source": hit["source"],
            "relevance_score": hit["score"],
            **({"pmid": hit["pmid"]} if hit.get("pmid") else {}),
        })

    return json.dumps({"results": results}, indent=2)
