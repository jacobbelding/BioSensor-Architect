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

## Sequence Server (`sequence_server/`)

DNA sequence manipulation utilities for construct analysis and validation.

**Tools:**
- `reverse_complement(sequence)` — Return the reverse complement of a DNA sequence
- `estimate_construct_size(parts)` — Estimate total construct size in base pairs from a list of genetic parts
- `format_genbank_features(construct)` — Generate a simplified GenBank feature table for a construct

**Run:** `python -m mcp_servers.sequence_server.server` or `bsa serve sequence`
