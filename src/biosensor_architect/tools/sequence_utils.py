"""Local utility functions for sequence manipulation."""

from __future__ import annotations

from datetime import date


def reverse_complement(sequence: str) -> str:
    """Return the reverse complement of a DNA sequence."""
    complement = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N"}
    return "".join(complement.get(base.upper(), "N") for base in reversed(sequence))


def estimate_construct_size(parts: list[dict]) -> int:
    """Estimate total construct size in base pairs from a list of parts."""
    total = 0
    for part in parts:
        if seq := part.get("sequence"):
            total += len(seq)
        elif size := part.get("estimated_size_bp"):
            total += size
    return total


def format_genbank_features(construct: dict) -> str:
    """Format a construct as a simple GenBank-style feature table.

    Args:
        construct: Dict with keys: name, promoter, reporter, terminator,
                   and optionally regulatory_elements and estimated_size_bp.

    Returns:
        A string formatted as a simplified GenBank feature table.
    """
    name = construct.get("name", "unnamed_construct")
    size = construct.get("estimated_size_bp", 5000)
    today = date.today().strftime("%d-%b-%Y").upper()

    # Build feature list with cumulative positions
    features = []
    pos = 1

    # Promoter
    promoter = construct.get("promoter", {})
    p_name = promoter.get("name", promoter.get("id", "unknown_promoter"))
    p_size = promoter.get("estimated_size_bp", 1500)
    features.append(("promoter", pos, pos + p_size - 1, p_name))
    pos += p_size

    # Regulatory elements (5' UTR, enhancers)
    for reg in construct.get("regulatory_elements", []):
        r_name = reg.get("name", reg.get("id", "regulatory"))
        r_size = reg.get("estimated_size_bp", 100)
        features.append(("regulatory", pos, pos + r_size - 1, r_name))
        pos += r_size

    # Reporter CDS
    reporter = construct.get("reporter", {})
    r_name = reporter.get("name", reporter.get("id", "unknown_reporter"))
    r_size = reporter.get("estimated_size_bp", 2000)
    features.append(("CDS", pos, pos + r_size - 1, r_name))
    pos += r_size

    # Terminator
    terminator = construct.get("terminator", {})
    t_name = terminator.get("name", terminator.get("id", "unknown_terminator"))
    t_size = terminator.get("estimated_size_bp", 250)
    features.append(("terminator", pos, pos + t_size - 1, t_name))
    pos += t_size

    total_size = pos - 1

    # Format output
    lines = []
    lines.append(f"LOCUS       {name[:16]:<16} {total_size:>6} bp    DNA     linear   SYN {today}")
    lines.append(f"DEFINITION  {name} — synthetic reporter construct.")
    lines.append(f"FEATURES             Location/Qualifiers")

    for feat_type, start, end, label in features:
        lines.append(f"     {feat_type:<16}{start}..{end}")
        lines.append(f'                     /label="{label}"')

    lines.append("//")
    return "\n".join(lines)
