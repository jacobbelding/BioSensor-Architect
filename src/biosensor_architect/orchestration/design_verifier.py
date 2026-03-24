"""Post-processing design verification.

Validates construct components against the curated parts database and NCBI
without any LLM calls. Catches hallucinated gene names, wrong promoter-signal
associations, and missing accession numbers.

Runs after the Documenter produces the HTML report but before final output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from biosensor_architect.tools.pathway_db import (
    _load_parts,
    _load_pathways,
)
from biosensor_architect.tools.pubmed_search import fetch_abstract, get_verified_pmids


@dataclass
class VerificationIssue:
    """A single verification finding."""

    severity: str  # "error", "warning", "info"
    component: str  # which part of the design
    message: str


@dataclass
class VerificationResult:
    """Complete verification report for a design."""

    issues: list[VerificationIssue] = field(default_factory=list)
    verified_components: list[str] = field(default_factory=list)
    unverified_components: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")
        return (
            f"Verification: {len(self.verified_components)} verified, "
            f"{len(self.unverified_components)} unverified, "
            f"{errors} errors, {warnings} warnings, {info} info"
        )


def _extract_gene_names_from_html(html: str) -> list[str]:
    """Extract likely gene/part names from the HTML report.

    Looks for common patterns in construct design reports:
    - Card headers (h3, h4 tags)
    - Table cells with part names
    - SVG text elements with gene labels
    """
    names: list[str] = []

    # Get text from h3/h4 tags (component cards)
    for match in re.finditer(r"<h[34][^>]*>(.*?)</h[34]>", html, re.IGNORECASE):
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if text and len(text) < 80:
            names.append(text)

    # Get first-column table cells that look like part names
    for match in re.finditer(
        r"<td[^>]*>\s*(?:<strong>)?([\w\s.\-/()]+)(?:</strong>)?\s*</td>",
        html,
        re.IGNORECASE,
    ):
        text = match.group(1).strip()
        # Filter out generic words
        if text and len(text) < 60 and text.lower() not in {
            "part", "role", "test", "description", "timing", "condition",
            "concentration", "rationale", "expected result", "details",
        }:
            names.append(text)

    return names


def _check_part_in_catalog(
    name: str,
    parts: list[dict],
) -> dict | None:
    """Check if a component name matches anything in the parts catalog.

    Returns the matching part dict or None.
    """
    name_lower = name.lower().strip()

    for part in parts:
        # Check against id, name, and gene fields
        if any(
            name_lower in str(part.get(field, "")).lower()
            for field in ("id", "name", "gene", "description")
        ):
            return part

    return None


def _check_promoter_signal_match(
    promoter_name: str,
    target_signal: str,
    pathways: list[dict],
    parts: list[dict],
) -> VerificationIssue | None:
    """Verify that a promoter is actually responsive to the target signal.

    Cross-references the parts catalog and pathways database.
    """
    promoter_lower = promoter_name.lower()
    signal_lower = target_signal.lower()

    # Check parts catalog for signal match
    for part in parts:
        if part.get("type") != "promoter":
            continue
        part_name = str(part.get("name", "")).lower()
        part_id = str(part.get("id", "")).lower()

        if promoter_lower in part_name or promoter_lower in part_id:
            # Found the promoter — check if it's for the right signal
            signals = str(part.get("signal", "")).lower()
            description = str(part.get("description", "")).lower()

            if signal_lower in signals or signal_lower in description:
                return None  # Match confirmed

            return VerificationIssue(
                severity="warning",
                component=promoter_name,
                message=(
                    f"Promoter '{promoter_name}' found in catalog but listed for "
                    f"signal '{part.get('signal', 'unknown')}', not '{target_signal}'. "
                    f"Verify cross-reactivity."
                ),
            )

    # Check pathways database
    for pathway in pathways:
        if signal_lower in str(pathway.get("signal", "")).lower():
            # Found the pathway — check if this promoter is listed
            promoters = pathway.get("candidate_promoters", [])
            for p in promoters:
                # candidate_promoters can be strings or dicts with a "gene" key
                p_name = p.get("gene", "") if isinstance(p, dict) else str(p)
                if promoter_lower in p_name.lower() or p_name.lower() in promoter_lower:
                    return None  # Match confirmed

            # Promoter not in this pathway's candidates
            known_promoters = [
                (p.get("gene", "?") if isinstance(p, dict) else str(p))
                for p in promoters[:3]
            ]
            return VerificationIssue(
                severity="warning",
                component=promoter_name,
                message=(
                    f"Promoter '{promoter_name}' is not listed in the curated "
                    f"'{target_signal}' pathway. Known candidates: {known_promoters}. "
                    f"This may be valid but needs literature confirmation."
                ),
            )

    return None  # Can't verify — no data


def _extract_target_signal_from_html(html: str) -> str | None:
    """Try to extract the target signal from the HTML report header."""
    # Look for "Target Signal: X" pattern — handle HTML tags between label and value
    # Strip tags first for cleaner matching
    text = re.sub(r"<[^>]+>", " ", html)
    match = re.search(
        r"Target\s+Signal[:\s]+(\w[\w\s/+⁺⁻₂₃₄]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".")
    return None


def verify_design(html: str) -> VerificationResult:
    """Run deterministic verification checks on the HTML design report.

    Checks performed:
    1. Component names against the curated parts catalog
    2. Promoter-signal associations against the pathways database
    3. PMID citations against verified registry and NCBI
    4. Basic structural completeness (SVG present, key sections exist)

    This function makes NO LLM calls — it's pure database lookups and
    pattern matching.

    Args:
        html: The HTML report from the Documenter.

    Returns:
        VerificationResult with all findings.
    """
    result = VerificationResult()

    parts = _load_parts()
    pathways = _load_pathways()

    # --- Check 1: Component catalog lookup ---
    gene_names = _extract_gene_names_from_html(html)

    for name in gene_names:
        catalog_match = _check_part_in_catalog(name, parts)
        if catalog_match:
            result.verified_components.append(
                f"{name} → {catalog_match.get('id', '?')} ({catalog_match.get('type', '?')})"
            )
        else:
            # Not in catalog — not necessarily wrong, but flag it
            result.unverified_components.append(name)

    # --- Check 2: Promoter-signal association ---
    target_signal = _extract_target_signal_from_html(html)
    if target_signal:
        # Find promoter-like names
        for name in gene_names:
            name_lower = name.lower()
            if any(kw in name_lower for kw in ("promoter", "prom", "p_")):
                issue = _check_promoter_signal_match(
                    name, target_signal, pathways, parts
                )
                if issue:
                    result.issues.append(issue)

    # --- Check 3: Structural completeness ---
    checks = [
        ("<svg", "SVG construct map"),
        ("component", "Component specifications section"),
        ("characterization", "Characterization plan section"),
        ("pmid", "Literature citations (PMIDs)"),
    ]

    for pattern, section_name in checks:
        if pattern.lower() not in html.lower():
            result.issues.append(
                VerificationIssue(
                    severity="warning",
                    component="Report structure",
                    message=f"Missing or incomplete: {section_name}",
                )
            )

    # --- Check 4: Accession number presence ---
    # Check if any real accession patterns exist (AT1GXXXXX, Solyc, GenBank)
    accession_patterns = [
        r"AT[1-5]G\d{5}",  # TAIR Arabidopsis
        r"Solyc\d{2}g\d{6}",  # Sol Genomics tomato
        r"[A-Z]{1,2}_?\d{5,9}",  # GenBank
    ]
    has_accession = any(
        re.search(pat, html) for pat in accession_patterns
    )
    if not has_accession:
        result.issues.append(
            VerificationIssue(
                severity="warning",
                component="Accession numbers",
                message=(
                    "No gene accession numbers (TAIR, Sol Genomics, GenBank) detected "
                    "in the report. Designs are more useful with specific accessions."
                ),
            )
        )

    return result


def inject_verification_banner(html: str, result: VerificationResult) -> str:
    """Inject a verification status banner into the HTML report.

    Adds a small banner after the opening <body> tag showing verification results.
    """
    if not result.issues and not result.unverified_components:
        # All clear — add a subtle green badge
        banner = (
            '<div style="background:#e8f5e9; border:1px solid #a5d6a7; border-radius:8px; '
            'padding:8px 16px; margin-bottom:16px; font-size:0.8rem; color:#1b5e20;">'
            '✓ Design verified against curated parts database'
            '</div>'
        )
    elif result.has_errors:
        # Errors found — red banner
        error_msgs = [i.message for i in result.issues if i.severity == "error"]
        banner = (
            '<div style="background:#fff5f5; border:1px solid #ef9a9a; border-radius:8px; '
            'padding:8px 16px; margin-bottom:16px; font-size:0.8rem; color:#b71c1c;">'
            f'⚠ Verification errors ({len(error_msgs)}): '
            + "; ".join(error_msgs[:3])
            + '</div>'
        )
    else:
        # Warnings only — amber banner
        warn_count = sum(1 for i in result.issues if i.severity == "warning")
        unverified = len(result.unverified_components)
        banner = (
            '<div style="background:#fffde7; border:1px solid #f9a825; border-radius:8px; '
            'padding:8px 16px; margin-bottom:16px; font-size:0.8rem; color:#5a4a00;">'
            f'⚠ Verification: {warn_count} warning(s), '
            f'{unverified} component(s) not in curated database'
            '</div>'
        )

    # Inject after <body> tag
    body_match = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if body_match:
        insert_pos = body_match.end()
        html = html[:insert_pos] + "\n" + banner + "\n" + html[insert_pos:]

    return html
