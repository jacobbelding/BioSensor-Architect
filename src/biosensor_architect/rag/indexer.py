"""Index papers and abstracts into ChromaDB for RAG retrieval.

Supports PDF files (via PyMuPDF) and plain text files. Text is chunked
into ~500-token passages with overlap, then embedded and stored in a
persistent ChromaDB collection.

ChromaDB uses its built-in default embedding model (all-MiniLM-L6-v2
via onnxruntime) so there is no external embedding API cost.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import chromadb

from biosensor_architect.config import settings

# Target chunk size in characters (~500 tokens ≈ 2000 chars for English text)
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using PyMuPDF."""
    import fitz

    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def _extract_text_from_file(file_path: Path) -> str:
    """Extract text from a supported file type."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    elif suffix in (".txt", ".md", ".text"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _clean_text(text: str) -> str:
    """Clean extracted text — normalize whitespace, remove control chars."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _extract_pmid_from_text(text: str) -> str | None:
    """Try to extract a PMID from the text (e.g., from citation headers)."""
    match = re.search(r"PMID[:\s]+(\d{7,8})", text[:5000])
    if match:
        return match.group(1)
    return None


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Splits on double-newlines first, then subdivides long paragraphs.
    """
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # If a single paragraph is larger than chunk_size, split it
            if len(para) > chunk_size:
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= chunk_size:
                        current = (current + " " + word).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = para

    if current:
        chunks.append(current)

    # Add overlap: prepend the tail of the previous chunk to each chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(prev_tail + " " + chunks[i])
        chunks = overlapped

    return chunks


def _get_collection(collection_name: str = "literature") -> chromadb.Collection:
    """Get or create a persistent ChromaDB collection."""
    persist_dir = str(settings.chroma_persist_dir)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def index_file(
    file_path: Path,
    collection_name: str = "literature",
) -> int:
    """Index a single file into ChromaDB.

    Args:
        file_path: Path to a PDF or text file.
        collection_name: ChromaDB collection name.

    Returns:
        Number of chunks indexed.
    """
    text = _extract_text_from_file(file_path)
    text = _clean_text(text)

    if len(text) < 100:
        return 0  # Too short to be useful

    pmid = _extract_pmid_from_text(text)
    chunks = _chunk_text(text)

    if not chunks:
        return 0

    collection = _get_collection(collection_name)

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        # Deterministic ID based on file + chunk index
        chunk_id = hashlib.sha256(f"{file_path.name}::{i}".encode()).hexdigest()[:16]
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "source": file_path.name,
            "chunk_index": i,
            "total_chunks": len(chunks),
            **({"pmid": pmid} if pmid else {}),
        })

    # ChromaDB handles embedding automatically with its default model
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return len(chunks)


def index_directory(
    papers_dir: Path,
    collection_name: str = "literature",
) -> tuple[int, int]:
    """Index all supported files in a directory into ChromaDB.

    Args:
        papers_dir: Path to directory containing PDFs or text files.
        collection_name: ChromaDB collection name.

    Returns:
        (files_indexed, total_chunks) tuple.
    """
    supported = (".pdf", ".txt", ".md", ".text")
    files = sorted(
        f for f in papers_dir.iterdir()
        if f.is_file() and f.suffix.lower() in supported
    )

    files_indexed = 0
    total_chunks = 0

    for f in files:
        try:
            n = index_file(f, collection_name)
            if n > 0:
                files_indexed += 1
                total_chunks += n
        except Exception as e:
            print(f"Warning: Failed to index {f.name}: {e}", file=sys.stderr)

    return files_indexed, total_chunks


def get_index_stats(collection_name: str = "literature") -> dict:
    """Get stats about the current index."""
    collection = _get_collection(collection_name)
    count = collection.count()

    if count > 0:
        results = collection.get(include=["metadatas"], limit=count)
        sources = set()
        for m in (results.get("metadatas") or []):
            if m and "source" in m:
                sources.add(m["source"])
        return {"total_chunks": count, "files_indexed": len(sources), "sources": sorted(sources)}

    return {"total_chunks": 0, "files_indexed": 0, "sources": []}
