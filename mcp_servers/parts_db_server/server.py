"""MCP server exposing a curated database of plant genetic parts.

Tools exposed:
- search_promoters(signal, organism?) -> list of matching promoters
- search_reporters(output_type?) -> list of reporter genes
- search_terminators(organism?) -> list of terminators
- get_part_details(part_id) -> full part record
"""

import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

PARTS_FILE = Path(__file__).parent / "data" / "parts_catalog.json"

app = Server("parts-db")


def load_parts() -> list[dict]:
    """Load the parts catalog from JSON."""
    with open(PARTS_FILE) as f:
        return json.load(f)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_promoters",
            description="Search for promoters responsive to a given signal",
            inputSchema={
                "type": "object",
                "properties": {
                    "signal": {"type": "string", "description": "Target signal to sense"},
                    "organism": {"type": "string", "description": "Target organism (optional)"},
                },
                "required": ["signal"],
            },
        ),
        Tool(
            name="search_reporters",
            description="Search for reporter genes by output type",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_type": {
                        "type": "string",
                        "description": "Reporter output type: color, fluorescence, luminescence",
                    },
                },
            },
        ),
        Tool(
            name="search_terminators",
            description="Search for terminator sequences",
            inputSchema={
                "type": "object",
                "properties": {
                    "organism": {"type": "string", "description": "Target organism (optional)"},
                },
            },
        ),
        Tool(
            name="get_part_details",
            description="Get full details for a specific genetic part by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "part_id": {"type": "string", "description": "Part identifier"},
                },
                "required": ["part_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    parts = load_parts()

    if name == "search_promoters":
        signal = arguments["signal"].lower()
        organism = arguments.get("organism", "").lower()
        results = [
            p for p in parts
            if p["type"] == "promoter"
            and (signal in (p.get("signal_responsive_to") or "").lower())
            and (not organism or organism in p.get("organism", "").lower())
        ]
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "search_reporters":
        output_type = arguments.get("output_type", "").lower()
        results = [
            p for p in parts
            if p["type"] == "reporter"
            and (not output_type or output_type in p.get("notes", "").lower())
        ]
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "search_terminators":
        organism = arguments.get("organism", "").lower()
        results = [
            p for p in parts
            if p["type"] == "terminator"
            and (not organism or organism in p.get("organism", "").lower())
        ]
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "get_part_details":
        part_id = arguments["part_id"]
        result = next((p for p in parts if p["id"] == part_id), None)
        if result:
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        return [TextContent(type="text", text=f"Part '{part_id}' not found")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
