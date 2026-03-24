# BioSensor-Architect — Upgrade Roadmap

## Tier 1: High Impact — Directly Improves Output Quality

### A. Cross-Reactivity Verifier (deterministic, zero LLM cost)
- **Status:** DONE
- `design_verifier.py`: static knowledge base of 10 shared cis-elements mapped across 30+ promoters
- Dual detection: cis-element overlap + pathway database overlap
- Severity grading: minor / moderate / severe
- Wired into post-processing pipeline (runs after every design)
- Example: RD29A contains CRT/DRE → flags cold, freezing as severe cross-reactivity

### B. Verbose Agent Trace (`--verbose` improvements)
- **Status:** TODO
- Rich-formatted real-time trace showing each agent's contribution with timing
- Structured panel output per agent (not raw message dump)
- Useful for debugging and portfolio demos

### C. Specificity Report Card in HTML Output
- **Status:** DONE
- `inject_specificity_report()` generates a full HTML panel with:
  - Overall grade badge (HIGH/MODERATE/LOW/UNKNOWN) with color coding
  - Cross-reactivity table: confounding signal, shared element, severity badge, explanation
  - Mitigation recommendations for severe hits (CRISPRi, promoter truncation, synthetic promoters)
- Injected before `<footer>` in every generated report

## Tier 2: Medium Impact — Broadens Capability

### D. RAG Literature Retrieval (ChromaDB)
- **Status:** TODO (scaffolded in `src/biosensor_architect/rag/`)
- **Jacob's tasks to enable this:**
  1. Collect full-text PDFs or abstracts for the ~40 papers from the Gemini Deep
     Research results (PMIDs are in `prompts/gemini_deep_research_parts_expansion.md`)
  2. Place them in a `papers/` directory (PDF or plain text)
  3. Decide on chunking strategy: per-abstract vs. per-section for full papers
  4. Review ChromaDB storage location (currently `./data/literature_index/` in config)
- **Coding tasks (after Jacob's prep):**
  - Implement `rag/indexer.py`: PDF/text → chunks → embeddings → ChromaDB
  - Implement `rag/retriever.py`: query → top-k chunks with metadata
  - Add `search_literature` tool to LiteratureValidator (supplements PubMed search)
  - Wire `bsa index-papers` CLI command (currently a stub)
  - Consider using a local embedding model (e.g., `all-MiniLM-L6-v2`) to avoid
    embedding API costs

### E. `bsa compare` Command
- **Status:** TODO
- Takes two HTML report files, produces side-by-side comparison
- Highlights differences in component selection, literature citations, specificity
- Useful for evaluating model changes (gpt-4o-mini vs Sonnet) or round count effects

### F. Batch Design Mode
- **Status:** TODO
- `bsa batch signals.txt` — run designs for a list of signals in sequence
- Produce a comparative summary table across all designs
- Good for portfolio demonstrations and systematic evaluation

## Tier 3: Polish & Portfolio

### G. Interactive HTML Report
- **Status:** TODO
- Collapsible sections (CSS-only accordion or minimal JS)
- Dark mode toggle via CSS custom properties
- "Copy construct sequence" button
- Makes reports feel like a real tool, not a static document

### H. Cost/Token Tracking
- **Status:** TODO
- Log total tokens (input + output) and estimated cost per run
- Display in CLI output and optionally in HTML report footer
- Shows production AI cost awareness (good for portfolio)
- AutoGen may expose token counts via result metadata

### I. GitHub Actions CI
- **Status:** TODO
- Workflow: run `pytest` on push/PR
- Matrix: Python 3.11, 3.12, 3.13
- Skip integration tests (marked with `@pytest.mark.integration`)
- Badge in README

### J. Sequence Validation Tools
- **Status:** TODO (scaffolded in `tools/sequence_utils.py`)
- Validate restriction sites don't conflict with cloning strategy
- Check for internal stop codons in reporter CDS
- Verify Kozak consensus around start codon
- Estimate mRNA secondary structure at 5'UTR (folding energy)
