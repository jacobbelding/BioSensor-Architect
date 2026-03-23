"""Paper ingestion — fetch papers by PMID/DOI and extract genetic parts + pathways.

Standalone ETL: fetch metadata → LLM extracts structured parts/pathways
→ deduplicate → append to JSON catalogs.

Usage via CLI:
    bsa ingest "PMID:11050181"
    bsa ingest "DOI:10.1038/s41477-021-00866-5"
    bsa ingest "PMID:11050181,PMID:17259264"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from biosensor_architect.config import settings
from biosensor_architect.tools.pubmed_search import fetch_abstract

PARTS_FILE = Path(__file__).resolve().parents[3] / "mcp_servers" / "parts_db_server" / "data" / "parts_catalog.json"
PATHWAYS_FILE = Path(__file__).resolve().parents[3] / "mcp_servers" / "parts_db_server" / "data" / "pathways.json"

# Example part schema (shown to the LLM as a template)
_PART_SCHEMA_EXAMPLE = """{
  "id": "pAtNRT2.1",
  "name": "AtNRT2.1 promoter",
  "type": "promoter",
  "organism": "Arabidopsis thaliana",
  "signal_responsive_to": "nitrate",
  "references": ["PMID:11050181"],
  "notes": "Nitrate-inducible promoter from the high-affinity nitrate transporter NRT2.1."
}"""

_PATHWAY_SCHEMA_EXAMPLE = """{
  "signal": "nitrate",
  "organism": "Arabidopsis thaliana",
  "description": "Nitrate sensing pathway via NRT1.1/NLP7",
  "receptor": "NRT1.1 (CHL1/NPF6.3)",
  "transduction_chain": ["step 1", "step 2", "..."],
  "candidate_promoters": ["pAtNRT2.1"],
  "transcription_factors": ["NLP7"],
  "key_references": ["PMID:11050181"],
  "notes": "Brief notes about the pathway."
}"""

EXTRACTION_SYSTEM_PROMPT = f"""You are a synthetic biology knowledge extractor. Given a paper's
abstract and metadata, extract any genetic parts (promoters, reporters, terminators,
regulatory elements) and signal transduction pathways described in the paper.

Output a JSON object with two arrays: "parts" and "pathways".
Each part must follow this schema:
{_PART_SCHEMA_EXAMPLE}

Valid part types: "promoter", "reporter", "terminator", "regulatory"

Each pathway must follow this schema:
{_PATHWAY_SCHEMA_EXAMPLE}

Rules:
- Only extract parts/pathways with clear experimental evidence in the paper.
- Use standard gene nomenclature (e.g., "AtNRT2.1" not "nitrate transporter").
- Include the paper's PMID in the references array.
- If the paper does not describe any extractable parts or pathways, return
  {{"parts": [], "pathways": []}}.
- For part IDs, use the format: "p" prefix for promoters, "t" prefix for terminators,
  gene name for reporters/regulatory (e.g., "pAtRD29A", "tNOS", "GFP").
- Respond ONLY with the JSON object. No markdown fencing, no explanations.
"""


def resolve_identifier(identifier: str) -> dict:
    """Parse and resolve a paper identifier (PMID or DOI) to metadata.

    Args:
        identifier: String like "PMID:11050181" or "DOI:10.1038/..."

    Returns:
        Dict with keys: pmid, doi, title, authors, abstract, journal, year.
    """
    identifier = identifier.strip()

    # PMID
    pmid_match = re.match(r"(?:PMID[:\s]*)?(\d{6,9})$", identifier, re.IGNORECASE)
    if pmid_match:
        pmid = pmid_match.group(1)
        result = json.loads(fetch_abstract(pmid))
        if "error" not in result:
            result["doi"] = ""
            return result
        raise ValueError(f"Could not fetch PMID {pmid}: {result.get('error')}")

    # DOI
    doi_match = re.match(r"(?:DOI[:\s]*)?(10\.\d{4,}/\S+)$", identifier, re.IGNORECASE)
    if doi_match:
        doi = doi_match.group(1)
        return _resolve_doi(doi)

    raise ValueError(
        f"Unrecognized identifier format: '{identifier}'. "
        "Expected 'PMID:12345' or 'DOI:10.1234/...'"
    )


def _resolve_doi(doi: str) -> dict:
    """Resolve a DOI via CrossRef and, if possible, fetch from PubMed."""
    headers = {
        "User-Agent": f"BioSensor-Architect/0.1 (mailto:{settings.crossref_email})",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("message", {})
    except (requests.RequestException, ValueError) as e:
        raise ValueError(f"CrossRef lookup failed for DOI {doi}: {e}") from e

    title = " ".join(data.get("title", ["Unknown"]))
    authors = [
        f"{a.get('family', '')} {a.get('given', '')}".strip()
        for a in data.get("author", [])
    ]
    year = str(data.get("published-print", data.get("published-online", {}))
               .get("date-parts", [[""]])[0][0])

    # Try to find a PMID via CrossRef's alternative-id or NCBI ID converter
    pmid = ""
    for alt_id in data.get("alternative-id", []):
        if alt_id.isdigit() and len(alt_id) >= 6:
            pmid = alt_id
            break

    # If we found a PMID, fetch the full abstract from PubMed
    if pmid:
        pubmed_data = json.loads(fetch_abstract(pmid))
        if "error" not in pubmed_data:
            pubmed_data["doi"] = doi
            return pubmed_data

    return {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "authors": authors[:10],
        "journal": data.get("container-title", [""])[0] if data.get("container-title") else "",
        "year": year,
        "abstract": data.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", ""),
    }


async def extract_parts_from_paper(
    metadata: dict,
    model: str | None = None,
) -> dict:
    """Use an LLM to extract genetic parts and pathways from a paper.

    Args:
        metadata: Paper metadata dict (from resolve_identifier).
        model: Optional LLM model override.

    Returns:
        Dict with "parts" and "pathways" arrays.
    """
    from autogen_core.models import SystemMessage, UserMessage

    from biosensor_architect.agents.base import _get_model_client

    client = _get_model_client(model)

    paper_text = (
        f"Title: {metadata.get('title', 'Unknown')}\n"
        f"Authors: {', '.join(metadata.get('authors', []))}\n"
        f"Journal: {metadata.get('journal', 'Unknown')}\n"
        f"Year: {metadata.get('year', 'Unknown')}\n"
        f"PMID: {metadata.get('pmid', 'N/A')}\n"
        f"DOI: {metadata.get('doi', 'N/A')}\n\n"
        f"Abstract:\n{metadata.get('abstract', 'No abstract available.')}"
    )

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        UserMessage(content=f"Extract parts and pathways from this paper:\n\n{paper_text}", source="user"),
    ]

    response = await client.create(messages=messages)

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(str(part) for part in raw)
    raw = str(raw)

    # Parse JSON response
    try:
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"parts": [], "pathways": []}
    except json.JSONDecodeError:
        data = {"parts": [], "pathways": []}

    # Ensure required structure
    data.setdefault("parts", [])
    data.setdefault("pathways", [])

    return data


def deduplicate_parts(new_parts: list[dict], existing_parts: list[dict]) -> list[dict]:
    """Filter out parts that already exist in the catalog.

    Matches on id or name (case-insensitive).
    """
    existing_ids = {p.get("id", "").lower() for p in existing_parts}
    existing_names = {p.get("name", "").lower() for p in existing_parts}

    unique = []
    for part in new_parts:
        pid = part.get("id", "").lower()
        pname = part.get("name", "").lower()
        if pid not in existing_ids and pname not in existing_names:
            unique.append(part)

    return unique


def deduplicate_pathways(new_pathways: list[dict], existing_pathways: list[dict]) -> list[dict]:
    """Filter out pathways that already exist in the database.

    Matches on (signal, organism) pair (case-insensitive).
    """
    existing_keys = {
        (p.get("signal", "").lower(), p.get("organism", "").lower())
        for p in existing_pathways
    }

    unique = []
    for pathway in new_pathways:
        key = (pathway.get("signal", "").lower(), pathway.get("organism", "").lower())
        if key not in existing_keys:
            unique.append(pathway)

    return unique


def load_catalog() -> list[dict]:
    """Load the current parts catalog."""
    with open(PARTS_FILE) as f:
        return json.load(f)


def load_pathways() -> list[dict]:
    """Load the current pathways database."""
    with open(PATHWAYS_FILE) as f:
        return json.load(f)


def append_to_catalog(parts: list[dict]) -> int:
    """Append new parts to the catalog and return the count added."""
    if not parts:
        return 0

    catalog = load_catalog()
    catalog.extend(parts)
    with open(PARTS_FILE, "w") as f:
        json.dump(catalog, f, indent=2)
        f.write("\n")

    # Invalidate lru_cache in pathway_db
    from biosensor_architect.tools.pathway_db import _load_parts
    _load_parts.cache_clear()

    return len(parts)


def append_to_pathways(pathways: list[dict]) -> int:
    """Append new pathways to the database and return the count added."""
    if not pathways:
        return 0

    existing = load_pathways()
    existing.extend(pathways)
    with open(PATHWAYS_FILE, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")

    # Invalidate lru_cache in pathway_db
    from biosensor_architect.tools.pathway_db import _load_pathways
    _load_pathways.cache_clear()

    return len(pathways)
