# MCP Servers

Model Context Protocol servers that expose domain-specific tools to the AI agents.

## Parts Database Server (`parts_db_server/`)
Serves a curated catalog of plant genetic parts (promoters, reporters, terminators, regulatory elements).

**Tools:**
- `search_promoters(signal, organism?)` — Find promoters responsive to a signal
- `search_reporters(output_type?)` — Find reporter genes by output type
- `search_terminators(organism?)` — Find terminator sequences
- `get_part_details(part_id)` — Get full details for a part

**Run:** `python -m mcp_servers.parts_db_server.server`

## PubMed Server (`pubmed_server/`)
Wraps NCBI E-utilities API for literature search and retrieval.

**Tools:**
- `search_pubmed(query, max_results?)` — Search PubMed
- `fetch_abstract(pmid)` — Get abstract and metadata
- `fetch_related(pmid, max_results?)` — Get related papers

**Run:** `python -m mcp_servers.pubmed_server.server`

## Sequence Server (`sequence_server/`) — Stretch Goal
Sequence manipulation utilities.

**Tools:**
- `reverse_complement(sequence)` — DNA reverse complement
- More planned...

**Run:** `python -m mcp_servers.sequence_server.server`
