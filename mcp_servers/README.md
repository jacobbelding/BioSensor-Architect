# MCP Servers

Standalone [Model Context Protocol](https://modelcontextprotocol.io/) servers that expose domain-specific tools to the AI agents. Each server can also be used independently with any MCP-compatible client (e.g., Claude Desktop, Cursor).

## Parts Database Server (`parts_db_server/`)

Serves a curated catalog of 44 plant genetic parts (promoters, reporters, terminators, regulatory elements) and 17 signal transduction pathways covering 15+ environmental signals. Data was curated from primary literature and expanded via Gemini Deep Research analysis of ~60 published papers.

**Tools:**
- `search_promoters(signal, organism?)` — Find promoters responsive to a signal
- `search_reporters(output_type?)` — Find reporter genes by output type (color, fluorescence, luminescence)
- `search_terminators(organism?)` — Find terminator sequences
- `get_part_details(part_id)` — Get full details for a part
- `get_pathway(organism, signal)` — Get signal transduction pathway with candidate promoters

**Data files:**
- `data/parts_catalog.json` — 44 curated genetic parts with accessions, literature references, and signal annotations
- `data/pathways.json` — 17 signal transduction pathways (receptor -> TF cascade -> candidate promoters)

**Run:** `python -m mcp_servers.parts_db_server.server`

## PubMed Server (`pubmed_server/`)

Wraps NCBI E-utilities API for real-time literature search and abstract retrieval. Used by the Literature Validator agent to ground-truth construct designs against published evidence.

**Tools:**
- `search_pubmed(query, max_results?)` — Search PubMed
- `fetch_abstract(pmid)` — Get abstract and metadata for a specific paper
- `fetch_related(pmid, max_results?)` — Get related papers via NCBI's link API

**Run:** `python -m mcp_servers.pubmed_server.server`

## Sequence Server (`sequence_server/`) — Planned

Sequence manipulation utilities for construct validation. Currently scaffolded; see [TODO.md](../TODO.md) (Tier 3, Item J) for the implementation plan.

**Planned tools:**
- `reverse_complement(sequence)` — DNA reverse complement
- `check_restriction_sites(sequence)` — Scan for restriction enzyme cut sites
- `assemble_construct(parts)` — In-silico assembly with junction sequences

**Run:** `python -m mcp_servers.sequence_server.server`
