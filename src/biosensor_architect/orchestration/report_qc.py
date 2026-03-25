"""Post-processing QC for HTML reports.

Validates PMID citations in the Documenter's HTML output against the
verified PMID registry (populated during the workflow) and NCBI.
Annotates or removes hallucinated citations — zero LLM token cost.
"""

from __future__ import annotations

import json
import re

from biosensor_architect.tools.pubmed_search import (
    _register_pmid,
    fetch_abstract,
    get_verified_pmids,
)

# Patterns that match PubMed IDs in HTML content
_PMID_PATTERNS = [
    re.compile(r"PMID[:\s]*(\d{6,9})", re.IGNORECASE),
    re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", re.IGNORECASE),
    re.compile(r"pubmed/(\d{6,9})", re.IGNORECASE),
]


def extract_pmids_from_html(html: str) -> set[str]:
    """Extract all PMID strings from an HTML document."""
    pmids: set[str] = set()
    for pattern in _PMID_PATTERNS:
        for match in pattern.finditer(html):
            pmids.add(match.group(1))
    return pmids


def validate_report_pmids(html: str, verify_unknown: bool = True) -> str:
    """Validate PMID citations in the HTML report.

    1. Extracts all PMIDs mentioned in the report.
    2. Checks each against the verified registry (populated by tool calls
       during the workflow — guaranteed real).
    3. For unknown PMIDs, optionally calls NCBI to verify they exist.
    4. Annotates unverified/invalid PMIDs in the HTML with a warning style.

    Args:
        html: The HTML report string.
        verify_unknown: If True, query NCBI for PMIDs not in the registry.
                        If False, only check the registry (faster, no network).

    Returns:
        The HTML with invalid PMIDs annotated.
    """
    cited_pmids = extract_pmids_from_html(html)
    if not cited_pmids:
        return html

    verified = get_verified_pmids()
    invalid_pmids: set[str] = set()
    newly_verified: dict[str, str] = {}

    for pmid in cited_pmids:
        if pmid in verified:
            continue  # Known good

        if verify_unknown:
            # Try to verify against NCBI
            result_str = fetch_abstract(pmid)
            try:
                result = json.loads(result_str)
            except json.JSONDecodeError:
                invalid_pmids.add(pmid)
                continue

            if "error" in result or not result.get("title"):
                invalid_pmids.add(pmid)
            else:
                # Real PMID — register it
                _register_pmid(pmid, result.get("title", ""))
                newly_verified[pmid] = result.get("title", "")
        else:
            # Without verification, flag as unverified
            invalid_pmids.add(pmid)

    if not invalid_pmids:
        return html

    # Annotate invalid PMIDs in the HTML
    for pmid in invalid_pmids:
        # Replace bare PMID references with a warning-styled version
        html = re.sub(
            rf"(PMID[:\s]*{pmid})",
            r'<span style="color: #c0392b; text-decoration: line-through;" '
            r'title="Unverified PMID — could not confirm on PubMed">\1</span>'
            r' <span style="color: #c0392b; font-size: 0.8em;">[unverified]</span>',
            html,
            flags=re.IGNORECASE,
        )
        # Also fix broken PubMed links
        html = re.sub(
            rf'(href="[^"]*pubmed[^"]*{pmid}[^"]*")',
            r'\1 style="color: #c0392b; text-decoration: line-through;"',
            html,
            flags=re.IGNORECASE,
        )

    return html


def get_pmid_validation_summary(html: str) -> dict:
    """Return a summary of PMID validation results for logging.

    Returns:
        Dict with keys: total_cited, verified, unverified, invalid.
    """
    cited = extract_pmids_from_html(html)
    verified = get_verified_pmids()

    verified_set = cited & set(verified.keys())
    unverified_set = cited - verified_set

    return {
        "total_cited": len(cited),
        "verified": len(verified_set),
        "unverified": len(unverified_set),
        "pmids_verified": sorted(verified_set),
        "pmids_unverified": sorted(unverified_set),
    }
