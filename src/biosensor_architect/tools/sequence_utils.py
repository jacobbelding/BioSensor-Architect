"""Local utility functions for sequence manipulation."""


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
    """Format a construct as a simple GenBank feature table."""
    # TODO: Implement GenBank formatting
    raise NotImplementedError
