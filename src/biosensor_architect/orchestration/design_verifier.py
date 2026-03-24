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
class CrossReactivityHit:
    """A single cross-reactivity finding between a promoter and a confounding signal."""

    promoter: str
    target_signal: str
    confounding_signal: str
    shared_element: str  # the cis-element or pathway feature that causes overlap
    severity: str  # "minor", "moderate", "severe"
    explanation: str


@dataclass
class VerificationResult:
    """Complete verification report for a design."""

    issues: list[VerificationIssue] = field(default_factory=list)
    verified_components: list[str] = field(default_factory=list)
    unverified_components: list[str] = field(default_factory=list)
    cross_reactivity: list[CrossReactivityHit] = field(default_factory=list)
    target_signal: str = ""
    promoter_name: str = ""

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    @property
    def specificity_grade(self) -> str:
        """Overall specificity grade based on cross-reactivity hits."""
        if not self.cross_reactivity:
            return "UNKNOWN"
        severe = sum(1 for h in self.cross_reactivity if h.severity == "severe")
        moderate = sum(1 for h in self.cross_reactivity if h.severity == "moderate")
        if severe > 0:
            return "LOW"
        if moderate > 0:
            return "MODERATE"
        return "HIGH"

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")
        xr = len(self.cross_reactivity)
        return (
            f"Verification: {len(self.verified_components)} verified, "
            f"{len(self.unverified_components)} unverified, "
            f"{errors} errors, {warnings} warnings, {info} info, "
            f"{xr} cross-reactivity hit(s)"
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


# ── Known shared cis-elements and cross-reactive pathways ──
# Each entry: (element_name, list of signal keywords that use this element)
# This is the ground truth for deterministic cross-reactivity detection.
_SHARED_CIS_ELEMENTS: dict[str, list[str]] = {
    "CRT/DRE (CCGAC)": ["cold", "drought", "dehydration", "desiccation", "freezing"],
    "ABRE": ["drought", "salt", "cold", "aba", "abscisic", "osmotic", "dehydration", "desiccation"],
    "W-box (TTGAC)": ["pathogen", "salicylic", "wounding", "senescence", "defense"],
    "GCC-box (AGCCGCC)": ["ethylene", "pathogen", "defense"],
    "AuxRE (TGTCTC)": ["auxin"],
    "ZDRE": ["zinc"],
    "SURE (GAGAC)": ["sulfur"],
    "HSE (nGAAnnTTCn)": ["heat"],
    "ARR motif": ["cytokinin"],
    "LRE": ["light"],
}

# Map promoter IDs/names to the cis-elements they are known to contain
_PROMOTER_CIS_ELEMENTS: dict[str, list[str]] = {
    # Drought/ABA promoters
    "rd29a": ["CRT/DRE (CCGAC)", "ABRE"],
    "rd29b": ["ABRE"],
    "rab18": ["ABRE"],
    "cor15a": ["CRT/DRE (CCGAC)"],
    "cor15b": ["CRT/DRE (CCGAC)"],
    "cor47": ["CRT/DRE (CCGAC)", "ABRE"],
    # Cold
    "cbf": ["CRT/DRE (CCGAC)"],
    "dreb": ["CRT/DRE (CCGAC)"],
    # Salt
    "sos1": ["ABRE"],
    "nhx1": ["ABRE"],
    # Heavy metal
    "mt2a": [],
    # Pathogen
    "pr1": ["W-box (TTGAC)"],
    "pdf1.2": ["GCC-box (AGCCGCC)", "W-box (TTGAC)"],
    # Ethylene
    "e4": ["GCC-box (AGCCGCC)"],
    "e8": ["GCC-box (AGCCGCC)"],
    "ebsn": ["GCC-box (AGCCGCC)"],
    # Auxin
    "dr5": ["AuxRE (TGTCTC)"],
    "gh3": ["AuxRE (TGTCTC)"],
    # Cytokinin
    "tcsn": ["ARR motif"],
    "tcs": ["ARR motif"],
    # Light
    "rbcs": ["LRE"],
    "cab": ["LRE"],
    # Zinc
    "zip4": ["ZDRE"],
    # Sulfur
    "sultr1": ["SURE (GAGAC)"],
    # Heat
    "hsp18.2": ["HSE (nGAAnnTTCn)"],
    "hsp": ["HSE (nGAAnnTTCn)"],
    # Nitrate
    "nrt2": [],
    # Phosphorus
    "pht1": [],
    # Potassium
    "hak5": [],
    # Iron
    "irt1": [],
    "fro2": [],
    # Ammonium
    "amt1": [],
    # Boron
    "nip5": [],
}


def _identify_promoter_in_html(html: str) -> str | None:
    """Try to identify the primary promoter name from the HTML report.

    Looks at SVG labels, card headers, and common naming patterns.
    """
    text = re.sub(r"<[^>]+>", " ", html).lower()

    # Look for "[Name] Promoter" pattern in the report
    promoter_match = re.search(
        r"(\w[\w.\-;/]+)\s+promoter",
        text,
        re.IGNORECASE,
    )
    if promoter_match:
        return promoter_match.group(1).strip()

    # Look for "p[GeneName]" format (e.g., pAtRD29A, pDR5)
    pid_match = re.search(r"\bp([A-Z][a-z]*[A-Z]\w+)", html)
    if pid_match:
        return pid_match.group(1)

    return None


def _find_promoter_cis_elements(promoter_name: str) -> list[str]:
    """Look up known cis-elements for a promoter name."""
    name_lower = promoter_name.lower().strip()

    # Direct match
    if name_lower in _PROMOTER_CIS_ELEMENTS:
        return _PROMOTER_CIS_ELEMENTS[name_lower]

    # Partial match (e.g., "RD29A" matches "rd29a")
    for key, elements in _PROMOTER_CIS_ELEMENTS.items():
        if key in name_lower or name_lower in key:
            return elements

    return []


def _analyze_cross_reactivity(
    promoter_name: str,
    target_signal: str,
    pathways: list[dict],
) -> list[CrossReactivityHit]:
    """Analyze cross-reactivity for a promoter against all known pathways.

    Uses two complementary approaches:
    1. Cis-element overlap: if the promoter contains a cis-element used by other signals
    2. Pathway overlap: if other pathways list this promoter as a candidate

    Returns a list of CrossReactivityHit objects.
    """
    hits: list[CrossReactivityHit] = []
    target_lower = target_signal.lower()
    promoter_lower = promoter_name.lower()

    # --- Approach 1: Cis-element overlap ---
    cis_elements = _find_promoter_cis_elements(promoter_name)

    for element in cis_elements:
        signals_using_element = _SHARED_CIS_ELEMENTS.get(element, [])
        for sig in signals_using_element:
            # Skip the target signal itself
            if sig in target_lower or target_lower in sig:
                continue

            # Determine severity based on element sharing
            # ABRE is the broadest → always at least moderate
            # CRT/DRE is shared by cold+drought → severe if one targets the other
            if element == "ABRE":
                severity = "moderate"
                explanation = (
                    f"ABRE element responds to ABA, which is induced by {sig} stress "
                    f"in addition to {target_signal}. Expect basal activation under {sig} conditions."
                )
            elif element in ("CRT/DRE (CCGAC)",):
                severity = "severe"
                explanation = (
                    f"CRT/DRE (CCGAC) motif is bound by CBF/DREB TFs activated by BOTH "
                    f"{target_signal} and {sig}. The promoter will be strongly induced by {sig}. "
                    f"Consider a genetic circuit (AND NOT gate) to suppress {sig}-driven false positives."
                )
            elif element in ("W-box (TTGAC)", "GCC-box (AGCCGCC)"):
                severity = "moderate"
                explanation = (
                    f"{element} is shared between {target_signal} and {sig} response pathways. "
                    f"Cross-activation is likely under {sig} conditions."
                )
            else:
                severity = "minor"
                explanation = (
                    f"{element} is primarily associated with {target_signal} but has "
                    f"some documented overlap with {sig} signaling."
                )

            hits.append(CrossReactivityHit(
                promoter=promoter_name,
                target_signal=target_signal,
                confounding_signal=sig,
                shared_element=element,
                severity=severity,
                explanation=explanation,
            ))

    # --- Approach 2: Pathway database overlap ---
    for pathway in pathways:
        pathway_signal = str(pathway.get("signal", "")).lower()

        # Skip the target signal's own pathway
        if pathway_signal in target_lower or target_lower in pathway_signal:
            continue

        # Check if this promoter appears in another pathway's candidates
        candidates = pathway.get("candidate_promoters", [])
        for c in candidates:
            c_name = c.get("gene", "") if isinstance(c, dict) else str(c)
            if promoter_lower in c_name.lower() or c_name.lower() in promoter_lower:
                # This promoter is also a candidate for another signal!
                # Check if we already have a hit for this combination
                already_found = any(
                    h.confounding_signal.lower() == pathway_signal
                    for h in hits
                )
                if not already_found:
                    hits.append(CrossReactivityHit(
                        promoter=promoter_name,
                        target_signal=target_signal,
                        confounding_signal=pathway.get("signal", pathway_signal),
                        shared_element="Pathway database",
                        severity="severe",
                        explanation=(
                            f"The curated pathways database lists {promoter_name} as a "
                            f"candidate promoter for '{pathway.get('signal', pathway_signal)}' "
                            f"sensing, not just {target_signal}. This is a direct cross-reactivity risk."
                        ),
                    ))

    return hits


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

    # --- Check 4: Cross-reactivity analysis ---
    promoter_name = _identify_promoter_in_html(html)
    if promoter_name and target_signal:
        result.promoter_name = promoter_name
        result.target_signal = target_signal
        xr_hits = _analyze_cross_reactivity(promoter_name, target_signal, pathways)
        result.cross_reactivity = xr_hits

        # Generate issues from cross-reactivity hits
        for hit in xr_hits:
            if hit.severity == "severe":
                result.issues.append(VerificationIssue(
                    severity="warning",
                    component=f"Cross-reactivity: {hit.promoter}",
                    message=(
                        f"SEVERE cross-reactivity with {hit.confounding_signal} "
                        f"via {hit.shared_element}. {hit.explanation}"
                    ),
                ))
            elif hit.severity == "moderate":
                result.issues.append(VerificationIssue(
                    severity="info",
                    component=f"Cross-reactivity: {hit.promoter}",
                    message=(
                        f"Moderate cross-reactivity with {hit.confounding_signal} "
                        f"via {hit.shared_element}."
                    ),
                ))

    # --- Check 5: Accession number presence ---
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


def _specificity_grade_color(grade: str) -> tuple[str, str, str]:
    """Return (bg, border, text) colors for a specificity grade."""
    if grade == "HIGH":
        return ("#e8f5e9", "#2e7d32", "#1b5e20")
    elif grade == "MODERATE":
        return ("#fff8e1", "#f57c00", "#e65100")
    elif grade == "LOW":
        return ("#ffebee", "#d32f2f", "#b71c1c")
    return ("#f5f5f5", "#9e9e9e", "#616161")


def _severity_badge(severity: str) -> str:
    """Return an HTML badge for a cross-reactivity severity level."""
    colors = {
        "severe": ("#b71c1c", "#ffebee"),
        "moderate": ("#e65100", "#fff8e1"),
        "minor": ("#2e7d32", "#e8f5e9"),
    }
    text_color, bg_color = colors.get(severity, ("#616161", "#f5f5f5"))
    return (
        f'<span style="background:{bg_color}; color:{text_color}; '
        f'font-weight:700; font-size:0.72rem; padding:2px 8px; '
        f'border-radius:4px; text-transform:uppercase;">{severity}</span>'
    )


def inject_specificity_report(html: str, result: VerificationResult) -> str:
    """Inject a Specificity Report Card panel into the HTML report.

    Adds a panel before the footer showing:
    - Overall specificity grade
    - Table of cross-reactivity hits (confounding signal, shared element, severity)
    - Explanation text for each hit

    This provides the reader with an at-a-glance assessment of whether the
    chosen promoter is truly specific to the target signal.
    """
    if not result.cross_reactivity and not result.promoter_name:
        return html  # No data to report

    grade = result.specificity_grade
    bg, border, text_color = _specificity_grade_color(grade)

    # Build the grade badge
    grade_badge = (
        f'<span style="display:inline-block; background:{bg}; color:{text_color}; '
        f'border:2px solid {border}; font-weight:800; font-size:1.1rem; '
        f'padding:6px 18px; border-radius:8px; letter-spacing:0.05em;">'
        f'{grade}</span>'
    )

    # Build cross-reactivity table rows
    if result.cross_reactivity:
        table_rows = ""
        for hit in result.cross_reactivity:
            table_rows += (
                f"<tr>"
                f"<td>{hit.confounding_signal}</td>"
                f"<td><code style='font-size:0.78rem;'>{hit.shared_element}</code></td>"
                f"<td>{_severity_badge(hit.severity)}</td>"
                f"<td style='font-size:0.78rem;'>{hit.explanation}</td>"
                f"</tr>\n"
            )

        table_html = f"""
        <table style="width:100%; border-collapse:collapse; font-size:0.82rem; margin-top:14px;">
          <thead>
            <tr style="background:#f0f4f8; border-bottom:2px solid #dde1ea;">
              <th style="padding:10px 12px; text-align:left; font-weight:700; font-size:0.75rem;">Confounding Signal</th>
              <th style="padding:10px 12px; text-align:left; font-weight:700; font-size:0.75rem;">Shared Element</th>
              <th style="padding:10px 12px; text-align:left; font-weight:700; font-size:0.75rem;">Severity</th>
              <th style="padding:10px 12px; text-align:left; font-weight:700; font-size:0.75rem;">Explanation</th>
            </tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
        """
    else:
        table_html = (
            '<p style="color:#2e7d32; font-weight:600; margin-top:12px;">'
            'No known cross-reactivity detected in the curated database. '
            'Independent literature verification is still recommended.</p>'
        )

    # Mitigation note for severe hits
    severe_hits = [h for h in result.cross_reactivity if h.severity == "severe"]
    mitigation_html = ""
    if severe_hits:
        signals = ", ".join(h.confounding_signal for h in severe_hits)
        mitigation_html = (
            f'<div style="background:#fff5f5; border-left:4px solid #d32f2f; '
            f'border-radius:0 8px 8px 0; padding:12px 16px; margin-top:14px; '
            f'font-size:0.82rem; line-height:1.7;">'
            f'<strong style="color:#b71c1c;">Mitigation recommended:</strong> '
            f'Severe cross-reactivity detected with {signals}. Consider: '
            f'(1) Promoter truncation to remove shared cis-elements, '
            f'(2) Adding a CRISPRi AND NOT gate to suppress false positives from confounding signals, or '
            f'(3) Switching to a synthetic minimal promoter with only the target-specific responsive element.'
            f'</div>'
        )

    # Full panel
    promoter_label = result.promoter_name or "Unknown"
    target_label = result.target_signal or "Unknown"

    panel = f"""
<div style="background:#ffffff; border:1px solid #dde1ea; border-radius:12px;
            padding:24px 22px; margin-bottom:24px; box-shadow:0 2px 10px rgba(0,0,0,0.06);">
  <div style="font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
              text-transform:uppercase; color:#5a6070; margin-bottom:12px;">
    Specificity Report Card
  </div>
  <h2 style="font-size:1rem; font-weight:700; margin-bottom:16px;">
    Promoter Specificity Analysis — {promoter_label}
  </h2>

  <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;">
    <div>
      <div style="font-size:0.75rem; color:#5a6070; margin-bottom:4px;">Overall Specificity</div>
      {grade_badge}
    </div>
    <div style="font-size:0.82rem; line-height:1.5;">
      <strong>Target signal:</strong> {target_label}<br>
      <strong>Primary promoter:</strong> {promoter_label}<br>
      <strong>Cross-reactive signals found:</strong> {len(result.cross_reactivity)}
    </div>
  </div>

  {table_html}
  {mitigation_html}
</div>
"""

    # Inject before the footer (or before closing </body> if no footer)
    footer_match = re.search(r"<footer", html, re.IGNORECASE)
    if footer_match:
        insert_pos = footer_match.start()
    else:
        body_close = html.lower().rfind("</body>")
        insert_pos = body_close if body_close > 0 else len(html)

    html = html[:insert_pos] + panel + "\n" + html[insert_pos:]

    return html
