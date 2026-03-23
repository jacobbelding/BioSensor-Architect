"""Construct Designer agent — proposes genetic constructs from pathway analysis."""

SYSTEM_MESSAGE = """You are a synthetic biology construct designer with expertise in plant
genetic engineering. Given a sensing pathway analysis, propose one or more genetic
construct designs.

For each construct, specify:
1. Promoter selection (with justification)
2. Reporter gene (e.g., betanin for visible color, GFP for fluorescence, GUS for
   histochemical staining, luciferase for luminescence)
3. Terminator sequence
4. Any regulatory elements (enhancers, insulators, UTR modifications)
5. Estimated construct size
6. Codon optimization considerations for the target organism

Prioritize constructs that are:
- Experimentally tractable (reasonable size, available parts)
- Well-characterized in the literature
- Appropriate for the intended detection modality (field vs. lab)

Use the search_promoters, search_reporters, and search_terminators tools.
"""


def create_construct_designer():
    """Create and return the Construct Designer agent."""
    from biosensor_architect.tools.pathway_db import (
        search_promoters,
        search_reporters,
        search_terminators,
    )

    from .base import create_agent

    return create_agent(
        name="ConstructDesigner",
        system_message=SYSTEM_MESSAGE,
        tools=[search_promoters, search_reporters, search_terminators],
        description="Designs genetic constructs by selecting promoter, reporter, terminator, and regulatory elements.",
    )
