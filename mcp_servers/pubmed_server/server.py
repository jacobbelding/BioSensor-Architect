"""MCP server wrapping NCBI E-utilities API for PubMed searches.

Tools exposed:
- search_pubmed(query, max_results?) -> list of paper summaries
- fetch_abstract(pmid) -> paper abstract and metadata
- fetch_related(pmid, max_results?) -> related papers
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("pubmed")

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_pubmed",
            description="Search PubMed for papers matching a query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_abstract",
            description="Fetch abstract and metadata for a PubMed ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {"type": "string", "description": "PubMed ID"},
                },
                "required": ["pmid"],
            },
        ),
        Tool(
            name="fetch_related",
            description="Fetch papers related to a given PubMed ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {"type": "string", "description": "PubMed ID"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5,
                    },
                },
                "required": ["pmid"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # TODO: Implement NCBI E-utilities API calls using requests
    # Will need NCBI_API_KEY from environment for rate limiting
    return [TextContent(type="text", text=f"Tool '{name}' not yet implemented")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
