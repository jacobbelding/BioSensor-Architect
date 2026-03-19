"""MCP server for sequence manipulation tools (stretch goal).

Tools planned:
- reverse_complement(sequence) -> reverse complement
- check_restriction_sites(sequence) -> restriction enzyme cut sites
- assemble_construct(parts) -> assembled sequence with junctions
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("sequence")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="reverse_complement",
            description="Return the reverse complement of a DNA sequence",
            inputSchema={
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "DNA sequence"},
                },
                "required": ["sequence"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # TODO: Implement sequence tools
    return [TextContent(type="text", text=f"Tool '{name}' not yet implemented")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
