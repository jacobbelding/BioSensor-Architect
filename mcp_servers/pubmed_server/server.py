"""MCP server wrapping NCBI E-utilities API for PubMed searches.

This server exposes PubMed search functionality over the Model Context
Protocol (MCP) via stdio transport.  It can be used standalone by any
MCP-compatible client, or as a demonstration of MCP server development.

Tools exposed:
- search_pubmed(query, max_results?) -> list of paper summaries
- fetch_abstract(pmid) -> paper abstract and metadata
- fetch_related(pmid, max_results?) -> related papers

Usage:
    python -m mcp_servers.pubmed_server.server
    # or via MCP client with stdio transport
"""

import json
import os
import time
import xml.etree.ElementTree as ET

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

app = Server("pubmed")

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

# Rate limiting: 3 req/sec without key, 10 req/sec with key
_REQUEST_DELAY = 0.15 if NCBI_API_KEY else 0.35
_last_request_time = 0.0


def _throttle() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _REQUEST_DELAY:
        time.sleep(_REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def _base_params() -> dict:
    params: dict[str, str] = {}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_pubmed",
            description="Search PubMed for papers matching a query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_abstract",
            description="Fetch abstract and metadata for a PubMed ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {"type": "string", "description": "PubMed ID"},
                },
                "required": ["pmid"],
            },
        ),
        Tool(
            name="fetch_related",
            description="Fetch papers related to a given PubMed ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {"type": "string", "description": "PubMed ID"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5,
                    },
                },
                "required": ["pmid"],
            },
        ),
    ]


def _search_pubmed(query: str, max_results: int = 10) -> str:
    """Search PubMed and return paper summaries as JSON."""
    # Step 1: esearch
    _throttle()
    params = {**_base_params(), "db": "pubmed", "term": query, "retmax": str(max_results), "retmode": "json"}
    try:
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})

    if not pmids:
        return json.dumps({"message": f"No results for: {query}", "results": []})

    # Step 2: esummary
    _throttle()
    params = {**_base_params(), "db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    try:
        resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        summary = resp.json()
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})

    results = []
    for pmid in pmids:
        article = summary.get("result", {}).get(pmid, {})
        if not article or isinstance(article, str):
            continue
        authors = [a.get("name", "") for a in article.get("authors", [])]
        results.append({
            "pmid": pmid,
            "title": article.get("title", ""),
            "authors": authors[:5],
            "year": article.get("pubdate", "")[:4],
            "source": article.get("source", ""),
        })
    return json.dumps(results, indent=2)


def _fetch_abstract(pmid: str) -> str:
    """Fetch abstract for a PMID and return as JSON."""
    _throttle()
    params = {**_base_params(), "db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "xml"}
    try:
        resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        return json.dumps({"error": str(e)})

    article = root.find(".//PubmedArticle")
    if article is None:
        return json.dumps({"error": f"No article found for PMID {pmid}"})

    title_el = article.find(".//ArticleTitle")
    title = title_el.text if title_el is not None and title_el.text else ""

    authors = []
    for author in article.findall(".//Author"):
        last = author.findtext("LastName", "")
        first = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {first}".strip())

    journal = article.findtext(".//Journal/Title", "")
    year = article.findtext(".//PubDate/Year", "")
    if not year:
        year = (article.findtext(".//PubDate/MedlineDate", "") or "")[:4]

    abstract_parts = []
    for at in article.findall(".//AbstractText"):
        label = at.get("Label", "")
        text = "".join(at.itertext())
        abstract_parts.append(f"{label}: {text}" if label else text)

    return json.dumps({
        "pmid": pmid,
        "title": title,
        "authors": authors[:10],
        "journal": journal,
        "year": year,
        "abstract": " ".join(abstract_parts),
    }, indent=2)


def _fetch_related(pmid: str, max_results: int = 5) -> str:
    """Fetch related papers for a PMID."""
    _throttle()
    params = {**_base_params(), "dbfrom": "pubmed", "db": "pubmed", "id": pmid, "cmd": "neighbor_score", "retmode": "json"}
    try:
        resp = requests.get(f"{EUTILS_BASE}/elink.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})

    related_pmids = []
    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            if linksetdb.get("linkname") == "pubmed_pubmed":
                for link in linksetdb.get("links", [])[:max_results]:
                    related_pmids.append(str(link.get("id", "")))
                break

    if not related_pmids:
        return json.dumps({"message": f"No related papers for PMID {pmid}", "results": []})

    # Fetch summaries
    _throttle()
    params = {**_base_params(), "db": "pubmed", "id": ",".join(related_pmids), "retmode": "json"}
    try:
        resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        summary = resp.json()
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})

    results = []
    for rpid in related_pmids:
        article = summary.get("result", {}).get(rpid, {})
        if not article or isinstance(article, str):
            continue
        authors = [a.get("name", "") for a in article.get("authors", [])]
        results.append({
            "pmid": rpid,
            "title": article.get("title", ""),
            "authors": authors[:5],
            "year": article.get("pubdate", "")[:4],
            "source": article.get("source", ""),
        })
    return json.dumps(results, indent=2)


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_pubmed":
        text = _search_pubmed(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10),
        )
    elif name == "fetch_abstract":
        text = _fetch_abstract(pmid=arguments["pmid"])
    elif name == "fetch_related":
        text = _fetch_related(
            pmid=arguments["pmid"],
            max_results=arguments.get("max_results", 5),
        )
    else:
        text = json.dumps({"error": f"Unknown tool: {name}"})

    return [TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
