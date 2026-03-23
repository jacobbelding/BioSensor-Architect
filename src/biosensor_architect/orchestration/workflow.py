"""AutoGen SelectorGroupChat workflow wiring all agents together.

The Orchestrator coordinates specialist agents in a structured pipeline:
  User query → Orchestrator → PathwayAnalyst → ConstructDesigner
             → LiteratureValidator → (revision loop?) → CharacterizationPlanner
             → Documenter → DONE

A custom ``selector_func`` enforces the pipeline order and enables the
LiteratureValidator → ConstructDesigner revision loop (up to 2 revisions).
"""

from __future__ import annotations

from typing import Sequence

from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import SelectorGroupChat

from biosensor_architect.agents.base import _get_model_client

# Agent pipeline order
PIPELINE = [
    "Orchestrator",
    "PathwayAnalyst",
    "ConstructDesigner",
    "LiteratureValidator",
    "CharacterizationPlanner",
    "Documenter",
]

MAX_REVISIONS = 2


def _selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """Deterministic pipeline routing with revision loop support.

    Returns the name of the next agent to speak, or None to let the
    SelectorGroupChat's LLM-based selector decide (fallback).
    """
    if not messages:
        return "Orchestrator"

    last = messages[-1]
    source = getattr(last, "source", None)

    # Count how many times ConstructDesigner has spoken (tracks revisions)
    designer_turns = sum(
        1 for m in messages if getattr(m, "source", None) == "ConstructDesigner"
    )

    # Pipeline routing
    if source == "Orchestrator":
        return "PathwayAnalyst"

    if source == "PathwayAnalyst":
        return "ConstructDesigner"

    if source == "ConstructDesigner":
        return "LiteratureValidator"

    if source == "LiteratureValidator":
        # Check if the validator flagged issues needing revision
        content = getattr(last, "content", "")
        if isinstance(content, str):
            needs_revision = any(
                keyword in content.upper()
                for keyword in ["REVISE", "REVISION NEEDED", "REDESIGN", "MAJOR CONCERN"]
            )
            if needs_revision and designer_turns <= MAX_REVISIONS:
                return "ConstructDesigner"
        return "CharacterizationPlanner"

    if source == "CharacterizationPlanner":
        return "Documenter"

    if source == "Documenter":
        # Pipeline complete — TextMentionTermination("DESIGN COMPLETE")
        # should fire from the Documenter's output. If it doesn't,
        # don't route to anyone else — return None to let termination
        # conditions handle it.
        return None

    # Fallback: let the LLM selector decide
    return None


async def build_workflow(model: str | None = None) -> SelectorGroupChat:
    """Build and return the multi-agent SelectorGroupChat team.

    Args:
        model: Optional LLM model override (e.g., "gpt-4o-mini" for dev).

    Returns:
        Configured SelectorGroupChat team ready for ``team.run(task=...)``.
    """
    from biosensor_architect.agents.characterization_planner import create_characterization_planner
    from biosensor_architect.agents.construct_designer import create_construct_designer
    from biosensor_architect.agents.documenter import create_documenter
    from biosensor_architect.agents.literature_validator import create_literature_validator
    from biosensor_architect.agents.orchestrator import create_orchestrator
    from biosensor_architect.agents.pathway_analyst import create_pathway_analyst

    # Create all agents
    orchestrator = create_orchestrator()
    pathway_analyst = create_pathway_analyst()
    construct_designer = create_construct_designer()
    literature_validator = create_literature_validator()
    characterization_planner = create_characterization_planner()
    documenter = create_documenter()

    participants = [
        orchestrator,
        pathway_analyst,
        construct_designer,
        literature_validator,
        characterization_planner,
        documenter,
    ]

    # Termination conditions (first to trigger wins):
    # 1. Documenter explicitly says DESIGN COMPLETE (instructed in its system prompt)
    # 2. Documenter outputs closing </html> tag (backup — catches HTML output even
    #    if the model forgets the DESIGN COMPLETE signal)
    # 3. Hard cap at 25 messages to prevent runaway token burn
    termination = (
        TextMentionTermination("DESIGN COMPLETE", sources=["Documenter"])
        | TextMentionTermination("</html>", sources=["Documenter"])
        | MaxMessageTermination(max_messages=25)
    )

    team = SelectorGroupChat(
        participants=participants,
        model_client=_get_model_client(model),
        selector_func=_selector_func,
        termination_condition=termination,
        allow_repeated_speaker=True,  # ConstructDesigner may speak twice in revision loop
    )

    return team


def _extract_html(messages) -> str:
    """Extract the HTML report from a list of agent messages.

    Priority order:
      1. Any message containing <!DOCTYPE or <html (the actual report)
      2. The longest Documenter message
      3. The longest message from any agent (last resort)
    """
    html_content = ""
    documenter_content = ""
    longest_content = ""

    for msg in messages:
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        source = getattr(msg, "source", "")

        if ("<!doctype" in content.lower() or "<html" in content.lower()) and len(content) > len(html_content):
            html_content = content
        if source == "Documenter" and len(content) > len(documenter_content):
            documenter_content = content
        if len(content) > len(longest_content):
            longest_content = content

    final = html_content or documenter_content or longest_content

    # Strip anything after closing </html> (e.g., "DESIGN COMPLETE" signal)
    if "</html>" in final.lower():
        idx = final.lower().index("</html>") + len("</html>")
        final = final[:idx]

    return final


async def _run_single_round(
    query: str,
    model: str | None = None,
) -> tuple[str, object]:
    """Run one pass of the design pipeline.

    Returns:
        (html_output, raw_team_result) tuple.
    """
    team = await build_workflow(model=model)
    result = await team.run(task=query)
    html = _extract_html(result.messages)
    return html, result


async def run_workflow(
    query: str,
    model: str | None = None,
    rounds: int | None = None,
) -> str:
    """Run the full design workflow, optionally with multiple critique rounds.

    Args:
        query: Natural language design request, e.g.,
               "Design a nitrate sensor for Arabidopsis thaliana".
        model: Optional LLM model override.
        rounds: Number of design rounds (default from DESIGN_ROUNDS env var).
                Each round after the first includes critic feedback.

    Returns:
        The final HTML report with PMID citations validated.
    """
    from biosensor_architect.config import settings
    from biosensor_architect.orchestration.critic import critique_design
    from biosensor_architect.orchestration.report_qc import validate_report_pmids
    from biosensor_architect.tools.pubmed_search import reset_verified_pmids

    num_rounds = rounds if rounds is not None else settings.design_rounds

    # Clear PMID registry from any prior run
    reset_verified_pmids()

    current_query = query
    final_html = ""

    for round_num in range(1, num_rounds + 1):
        final_html, _result = await _run_single_round(current_query, model=model)

        # Last round — no critique needed
        if round_num >= num_rounds:
            break

        # Critique the design
        critique = await critique_design(final_html, round_num=round_num, model=model)

        if critique.approved:
            break  # Design is good enough, stop early

        # Inject feedback into the next round's query
        current_query = (
            f"{query}\n\n"
            f"--- CRITIC FEEDBACK FROM ROUND {round_num} "
            f"(score: {critique.overall_score}/10) ---\n"
            f"{critique.feedback}\n"
            f"---\n"
            f"Address the above feedback in this design round."
        )

    # Post-processing: validate cited PMIDs
    if final_html:
        final_html = validate_report_pmids(final_html, verify_unknown=True)

    return final_html
