"""MCP client functions for the Parts Database server."""


async def search_promoters(signal: str, organism: str | None = None) -> list[dict]:
    """Search the parts database for promoters responsive to a given signal."""
    # TODO: Connect to parts_db MCP server
    raise NotImplementedError


async def search_reporters(output_type: str | None = None) -> list[dict]:
    """Search the parts database for reporter genes."""
    # TODO: Connect to parts_db MCP server
    raise NotImplementedError


async def search_terminators(organism: str | None = None) -> list[dict]:
    """Search the parts database for terminator sequences."""
    # TODO: Connect to parts_db MCP server
    raise NotImplementedError


async def get_pathway(organism: str, signal: str) -> dict | None:
    """Get a known signal transduction pathway from the database."""
    # TODO: Connect to parts_db MCP server
    raise NotImplementedError
