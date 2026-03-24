# Data

Curated domain data for the BioSensor-Architect pipeline. The primary parts catalog and pathway definitions live in `mcp_servers/parts_db_server/data/` — this directory holds supporting data and indices.

## `example_constructs/`

Reference JSON showing the data model for a complete genetic construct design.

- `nitrogen_reporter.json` — Nitrate reporter construct based on the NRT2.1 promoter and betanin visible reporter system. Demonstrates the `GeneticConstruct` Pydantic model structure.

## `literature_index/`

ChromaDB vector store for the RAG-indexed literature collection. This directory is gitignored (only a `.gitkeep` is tracked).

Once the RAG pipeline is implemented, populate it with:
```bash
bsa index-papers path/to/papers/
```

See [TODO.md](../TODO.md) (Tier 2, Item D) for the RAG implementation roadmap.
