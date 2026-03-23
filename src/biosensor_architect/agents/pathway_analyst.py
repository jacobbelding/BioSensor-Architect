"""Pathway Analyst agent — identifies biological sensing pathways for a target signal."""

SYSTEM_MESSAGE = """You are a plant biology expert specializing in signal transduction pathways.
Given a target environmental signal (e.g., "nitrate deficiency", "drought stress",
"heavy metal contamination"), identify candidate biological sensing pathways.

For each pathway, provide:
1. The receptor or sensor protein
2. The signal transduction chain
3. Candidate promoters responsive to this signal
4. Relevant transcription factors
5. The target organism

Draw on knowledge of plant molecular biology, particularly well-characterized
pathways in Arabidopsis thaliana and crop species. Prioritize pathways with
published experimental validation.

Use the search_promoters and get_pathway tools to query the parts database.
"""


def create_pathway_analyst():
    """Create and return the Pathway Analyst agent."""
    from biosensor_architect.tools.pathway_db import get_pathway, search_promoters

    from .base import create_agent

    return create_agent(
        name="PathwayAnalyst",
        system_message=SYSTEM_MESSAGE,
        tools=[search_promoters, get_pathway],
        description="Identifies biological sensing pathways and candidate promoters for a target environmental signal.",
    )
