"""Index papers and abstracts into ChromaDB for RAG retrieval."""

from pathlib import Path


async def index_directory(papers_dir: Path, collection_name: str = "literature") -> int:
    """Index all papers in a directory into ChromaDB.

    Args:
        papers_dir: Path to directory containing PDFs or text files.
        collection_name: ChromaDB collection name.

    Returns:
        Number of documents indexed.
    """
    # TODO: Implement PDF parsing, chunking, embedding, and ChromaDB insertion
    raise NotImplementedError


async def index_pubmed_results(pmids: list[str], collection_name: str = "literature") -> int:
    """Fetch and index PubMed abstracts by PMID.

    Args:
        pmids: List of PubMed IDs to fetch and index.
        collection_name: ChromaDB collection name.

    Returns:
        Number of abstracts indexed.
    """
    # TODO: Fetch abstracts via NCBI API and index into ChromaDB
    raise NotImplementedError
