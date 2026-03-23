"""Tool functions for searching PubMed via NCBI E-utilities.

These are direct HTTP calls (no MCP transport) so AutoGen agents can
invoke them as plain Python callables.  The PubMed MCP server in
``mcp_servers/pubmed_server/`` exposes the same logic over MCP stdio
for standalone demonstration.
"""

from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET

import requests

from biosensor_architect.config import settings

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Polite delay between NCBI requests (3/sec without key, 10/sec with key)
_REQUEST_DELAY = 0.15 if settings.ncbi_api_key else 0.35
_last_request_time = 0.0


def _throttle() -> None:
    """Enforce minimum delay between NCBI requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _REQUEST_DELAY:
        time.sleep(_REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def _eutils_params() -> dict:
    """Base query params including API key if available."""
    params: dict[str, str] = {}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


def search_papers(query: str, max_results: int = 10) -> str:
    """Search PubMed for papers matching a query.

    Args:
        query: Search query (supports PubMed query syntax).
        max_results: Maximum number of results to return (default 10).

    Returns:
        JSON string with a list of paper summaries (pmid, title, authors, year, source).
    """
    # Step 1: esearch to get PMIDs
    _throttle()
    params = {
        **_eutils_params(),
        "db": "pubmed",
        "term": query,
        "retmax": str(max_results),
        "retmode": "json",
    }
    try:
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        return json.dumps({"error": f"PubMed search failed: {e}", "results": []})

    pmids = data.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return json.dumps({"message": f"No results for query: {query}", "results": []})

    # Step 2: esummary to get metadata for the PMIDs
    _throttle()
    params = {
        **_eutils_params(),
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    try:
        resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        summary_data = resp.json()
    except (requests.RequestException, ValueError) as e:
        return json.dumps({"error": f"PubMed summary fetch failed: {e}", "results": []})

    results = []
    for pmid in pmids:
        article = summary_data.get("result", {}).get(pmid, {})
        if not article or isinstance(article, str):
            continue
        authors = [a.get("name", "") for a in article.get("authors", [])]
        results.append({
            "pmid": pmid,
            "title": article.get("title", ""),
            "authors": authors[:5],  # Limit to first 5 authors
            "year": article.get("pubdate", "")[:4],
            "source": article.get("source", ""),
        })

    return json.dumps(results, indent=2)


def fetch_abstract(pmid: str) -> str:
    """Fetch the abstract and metadata for a given PubMed ID.

    Args:
        pmid: PubMed identifier (e.g., "11050181").

    Returns:
        JSON string with title, authors, journal, year, and abstract text.
    """
    _throttle()
    params = {
        **_eutils_params(),
        "db": "pubmed",
        "id": pmid,
        "rettype": "abstract",
        "retmode": "xml",
    }
    try:
        resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return json.dumps({"error": f"Failed to fetch abstract for PMID {pmid}: {e}"})

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        return json.dumps({"error": f"Failed to parse XML for PMID {pmid}: {e}"})

    article = root.find(".//PubmedArticle")
    if article is None:
        return json.dumps({"error": f"No article found for PMID {pmid}"})

    # Extract title
    title_el = article.find(".//ArticleTitle")
    title = title_el.text if title_el is not None and title_el.text else ""

    # Extract authors
    authors = []
    for author in article.findall(".//Author"):
        last = author.findtext("LastName", "")
        first = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {first}".strip())

    # Extract journal & year
    journal = article.findtext(".//Journal/Title", "")
    year = article.findtext(".//PubDate/Year", "")
    if not year:
        medline_date = article.findtext(".//PubDate/MedlineDate", "")
        year = medline_date[:4] if medline_date else ""

    # Extract abstract
    abstract_parts = []
    for abstract_text in article.findall(".//AbstractText"):
        label = abstract_text.get("Label", "")
        text = "".join(abstract_text.itertext())
        if label:
            abstract_parts.append(f"{label}: {text}")
        else:
            abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    return json.dumps({
        "pmid": pmid,
        "title": title,
        "authors": authors[:10],
        "journal": journal,
        "year": year,
        "abstract": abstract,
    }, indent=2)


def fetch_related(pmid: str, max_results: int = 5) -> str:
    """Fetch papers related to a given PubMed ID.

    Args:
        pmid: Source PubMed ID.
        max_results: Maximum number of related papers to return.

    Returns:
        JSON string with related paper summaries.
    """
    _throttle()
    params = {
        **_eutils_params(),
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "cmd": "neighbor_score",
        "retmode": "json",
    }
    try:
        resp = requests.get(f"{EUTILS_BASE}/elink.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        return json.dumps({"error": f"Failed to fetch related papers: {e}", "results": []})

    # Extract related PMIDs
    related_pmids = []
    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            if linksetdb.get("linkname") == "pubmed_pubmed":
                for link in linksetdb.get("links", [])[:max_results]:
                    related_pmids.append(str(link.get("id", "")))
                break

    if not related_pmids:
        return json.dumps({"message": f"No related papers found for PMID {pmid}", "results": []})

    # Fetch summaries for related PMIDs (reuse search_papers logic)
    _throttle()
    params = {
        **_eutils_params(),
        "db": "pubmed",
        "id": ",".join(related_pmids),
        "retmode": "json",
    }
    try:
        resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        summary_data = resp.json()
    except (requests.RequestException, ValueError) as e:
        return json.dumps({"error": f"Related paper summary fetch failed: {e}", "results": []})

    results = []
    for rpid in related_pmids:
        article = summary_data.get("result", {}).get(rpid, {})
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
