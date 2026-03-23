"""Direct-call tool functions for querying the plant parts & pathway database.

These functions load the parts catalog JSON directly (same data as the
parts_db MCP server) so that AutoGen agents can call them as plain
Python callables without needing MCP stdio transport at runtime.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PARTS_FILE = Path(__file__).resolve().parents[3] / "mcp_servers" / "parts_db_server" / "data" / "parts_catalog.json"
PATHWAYS_FILE = Path(__file__).resolve().parents[3] / "mcp_servers" / "parts_db_server" / "data" / "pathways.json"


@lru_cache(maxsize=1)
def _load_parts() -> list[dict]:
    """Load and cache the parts catalog."""
    with open(PARTS_FILE) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_pathways() -> list[dict]:
    """Load and cache the curated pathway knowledge base."""
    with open(PATHWAYS_FILE) as f:
        return json.load(f)


def search_promoters(signal: str, organism: str | None = None) -> str:
    """Search for promoters responsive to a given environmental signal.

    Args:
        signal: Target signal to sense (e.g., "nitrate", "drought", "heavy metals").
        organism: Optional organism filter (e.g., "Arabidopsis").

    Returns:
        JSON string listing matching promoters with metadata.
    """
    signal_lower = signal.lower()
    organism_lower = (organism or "").lower()
    results = [
        p for p in _load_parts()
        if p["type"] == "promoter"
        and signal_lower in (p.get("signal_responsive_to") or "").lower()
        and (not organism_lower or organism_lower in p.get("organism", "").lower())
    ]
    if not results:
        return json.dumps({"message": f"No promoters found for signal '{signal}'", "results": []})
    return json.dumps(results, indent=2)


def search_reporters(output_type: str | None = None) -> str:
    """Search for reporter genes, optionally filtered by output type.

    Args:
        output_type: Optional filter: "color", "fluorescence", "luminescence",
                     "histochemical".

    Returns:
        JSON string listing matching reporter genes.
    """
    output_lower = (output_type or "").lower()
    results = [
        p for p in _load_parts()
        if p["type"] == "reporter"
        and (not output_lower or output_lower in p.get("notes", "").lower())
    ]
    return json.dumps(results, indent=2)


def search_terminators(organism: str | None = None) -> str:
    """Search for terminator sequences, optionally filtered by organism.

    Args:
        organism: Optional organism filter (e.g., "Arabidopsis", "Agrobacterium").

    Returns:
        JSON string listing matching terminators.
    """
    organism_lower = (organism or "").lower()
    results = [
        p for p in _load_parts()
        if p["type"] == "terminator"
        and (not organism_lower or organism_lower in p.get("organism", "").lower())
    ]
    return json.dumps(results, indent=2)


def get_pathway(organism: str, signal: str) -> str:
    """Look up a curated signal transduction pathway.

    Args:
        organism: Target organism (e.g., "Arabidopsis thaliana").
        signal: Environmental signal (e.g., "nitrate", "drought").

    Returns:
        JSON string with pathway details, or a message if not found.
    """
    signal_lower = signal.lower()
    organism_lower = organism.lower()

    for pathway in _load_pathways():
        if (
            signal_lower in pathway.get("signal", "").lower()
            and organism_lower in pathway.get("organism", "").lower()
        ):
            return json.dumps(pathway, indent=2)

    # Fuzzy fallback: match on signal alone
    for pathway in _load_pathways():
        if signal_lower in pathway.get("signal", "").lower():
            return json.dumps(pathway, indent=2)

    return json.dumps({
        "message": f"No curated pathway found for '{signal}' in '{organism}'. "
                   "The LLM should reason from known biology."
    })
