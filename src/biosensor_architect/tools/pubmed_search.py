"""MCP client functions for the PubMed search server."""


async def search_papers(query: str, max_results: int = 10) -> list[dict]:
    """Search PubMed for papers matching the query."""
    # TODO: Connect to pubmed MCP server
    raise NotImplementedError


async def fetch_abstract(pmid: str) -> dict | None:
    """Fetch the abstract and metadata for a given PubMed ID."""
    # TODO: Connect to pubmed MCP server
    raise NotImplementedError


async def fetch_related(pmid: str, max_results: int = 5) -> list[dict]:
    """Fetch papers related to a given PubMed ID."""
    # TODO: Connect to pubmed MCP server
    raise NotImplementedError
