"""Design Critic — evaluates completed construct designs between rounds.

This is NOT an AutoGen agent in the SelectorGroupChat pipeline.  It is
a standalone LLM call made between design rounds to provide structured
feedback that the next round's Orchestrator can incorporate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from biosensor_architect.agents.base import _get_model_client

CRITIC_SYSTEM_MESSAGE = """You are a senior synthetic biology reviewer evaluating a genetic
construct design report. Assess the design across these dimensions:

1. **Biological soundness** — Is the promoter appropriate for the target signal?
   Is the reporter suitable for the application? Is the pathway well-supported?
2. **Literature support** — Are citations real and relevant? Are concerns addressed?
3. **Construct design** — Are regulatory elements appropriate? Is construct size
   reasonable? Any obvious cloning issues?
4. **Characterization plan** — Are controls adequate? Is the dose-response range
   sensible? Are the proposed experiments feasible?
5. **Report quality** — Is the information complete and clearly presented?

Respond ONLY with a JSON object (no markdown fencing) with this exact structure:
{
  "approved": true/false,
  "overall_score": 1-10,
  "scores": {
    "biological_soundness": 1-10,
    "literature_support": 1-10,
    "construct_design": 1-10,
    "characterization_plan": 1-10,
    "report_quality": 1-10
  },
  "strengths": ["..."],
  "weaknesses": ["..."],
  "feedback": "Specific, actionable feedback for the next design round. Focus on the most critical issues."
}

Set "approved" to true only if overall_score >= 7 and no dimension scores below 5.
Be specific and technical. Reference specific parts/genes/pathways by name.
"""


@dataclass
class CritiqueResult:
    """Structured output from a design critique."""

    approved: bool = False
    overall_score: int = 0
    scores: dict[str, int] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    feedback: str = ""
    round_num: int = 0
    raw_response: str = ""


async def critique_design(
    html: str,
    round_num: int = 1,
    model: str | None = None,
) -> CritiqueResult:
    """Evaluate a completed design report and return structured feedback.

    Args:
        html: The HTML report from the Documenter.
        round_num: Current design round number.
        model: Optional LLM model override.

    Returns:
        CritiqueResult with scores, feedback, and approval status.
    """
    from autogen_core.models import SystemMessage, UserMessage

    client = _get_model_client(model)

    # Strip HTML tags for the critic — it only needs the text content
    # (keeps the prompt shorter and cheaper)
    import re
    text_content = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text_content = re.sub(r"<[^>]+>", " ", text_content)
    text_content = re.sub(r"\s+", " ", text_content).strip()

    # Cap at ~8000 chars to avoid blowing context
    if len(text_content) > 8000:
        text_content = text_content[:8000] + "\n\n[... truncated for review ...]"

    messages = [
        SystemMessage(content=CRITIC_SYSTEM_MESSAGE),
        UserMessage(
            content=f"Please evaluate this genetic construct design report (Round {round_num}):\n\n{text_content}",
            source="user",
        ),
    ]

    response = await client.create(messages=messages)

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(str(part) for part in raw)
    raw = str(raw)

    # Parse JSON response
    try:
        # Try to extract JSON from the response (model may wrap in markdown)
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {}
    except json.JSONDecodeError:
        data = {}

    return CritiqueResult(
        approved=data.get("approved", False),
        overall_score=data.get("overall_score", 0),
        scores=data.get("scores", {}),
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        feedback=data.get("feedback", raw),  # Fall back to raw response if parsing fails
        round_num=round_num,
        raw_response=raw,
    )
