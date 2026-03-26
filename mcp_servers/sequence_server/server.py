"""MCP server for DNA sequence manipulation tools.

Tools exposed:
- reverse_complement(sequence) -> reverse complement of a DNA sequence
- estimate_construct_size(parts) -> total estimated size in base pairs
- format_genbank_features(construct) -> simplified GenBank feature table

Usage:
    python -m mcp_servers.sequence_server.server
    # or via MCP client with stdio transport
"""

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

app = Server("sequence")

# --- Sequence logic (mirrors biosensor_architect.tools.sequence_utils) ---

_COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N"}


def _reverse_complement(sequence: str) -> str:
    return "".join(_COMPLEMENT.get(b.upper(), "N") for b in reversed(sequence))


def _estimate_construct_size(parts: list[dict]) -> int:
    total = 0
    for part in parts:
        if seq := part.get("sequence"):
            total += len(seq)
        elif size := part.get("estimated_size_bp"):
            total += size
    return total


def _format_genbank_features(construct: dict) -> str:
    from datetime import date

    name = construct.get("name", "unnamed_construct")
    today = date.today().strftime("%d-%b-%Y").upper()

    features = []
    pos = 1

    # Promoter
    promoter = construct.get("promoter", {})
    p_name = promoter.get("name", promoter.get("id", "unknown_promoter"))
    p_size = promoter.get("estimated_size_bp", 1500)
    features.append(("promoter", pos, pos + p_size - 1, p_name))
    pos += p_size

    # Regulatory elements
    for reg in construct.get("regulatory_elements", []):
        r_name = reg.get("name", reg.get("id", "regulatory"))
        r_size = reg.get("estimated_size_bp", 100)
        features.append(("regulatory", pos, pos + r_size - 1, r_name))
        pos += r_size

    # Reporter CDS
    reporter = construct.get("reporter", {})
    r_name = reporter.get("name", reporter.get("id", "unknown_reporter"))
    r_size = reporter.get("estimated_size_bp", 2000)
    features.append(("CDS", pos, pos + r_size - 1, r_name))
    pos += r_size

    # Terminator
    terminator = construct.get("terminator", {})
    t_name = terminator.get("name", terminator.get("id", "unknown_terminator"))
    t_size = terminator.get("estimated_size_bp", 250)
    features.append(("terminator", pos, pos + t_size - 1, t_name))
    pos += t_size

    total_size = pos - 1

    lines = []
    lines.append(f"LOCUS       {name[:16]:<16} {total_size:>6} bp    DNA     linear   SYN {today}")
    lines.append(f"DEFINITION  {name} — synthetic reporter construct.")
    lines.append("FEATURES             Location/Qualifiers")
    for feat_type, start, end, label in features:
        lines.append(f"     {feat_type:<16}{start}..{end}")
        lines.append(f'                     /label="{label}"')
    lines.append("//")
    return "\n".join(lines)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="reverse_complement",
            description="Return the reverse complement of a DNA sequence",
            inputSchema={
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": "DNA sequence (A/T/G/C/N)",
                    },
                },
                "required": ["sequence"],
            },
        ),
        Tool(
            name="estimate_construct_size",
            description="Estimate total construct size in base pairs from a list of genetic parts",
            inputSchema={
                "type": "object",
                "properties": {
                    "parts": {
                        "type": "array",
                        "description": "List of parts, each with 'sequence' or 'estimated_size_bp'",
                        "items": {"type": "object"},
                    },
                },
                "required": ["parts"],
            },
        ),
        Tool(
            name="format_genbank_features",
            description="Generate a simplified GenBank feature table for a construct",
            inputSchema={
                "type": "object",
                "properties": {
                    "construct": {
                        "type": "object",
                        "description": "Construct dict with name, promoter, reporter, terminator, and optional regulatory_elements",
                    },
                },
                "required": ["construct"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "reverse_complement":
        seq = arguments["sequence"]
        result = _reverse_complement(seq)
        return [TextContent(type="text", text=json.dumps({
            "input": seq,
            "reverse_complement": result,
            "length": len(seq),
        }, indent=2))]

    elif name == "estimate_construct_size":
        parts = arguments["parts"]
        size = _estimate_construct_size(parts)
        return [TextContent(type="text", text=json.dumps({
            "estimated_size_bp": size,
            "num_parts": len(parts),
        }, indent=2))]

    elif name == "format_genbank_features":
        construct = arguments["construct"]
        table = _format_genbank_features(construct)
        return [TextContent(type="text", text=table)]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
