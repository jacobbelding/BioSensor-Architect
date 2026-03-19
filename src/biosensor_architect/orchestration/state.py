"""Shared state definitions for the multi-agent workflow."""

from dataclasses import dataclass, field

from biosensor_architect.models import (
    CharacterizationPlan,
    GeneticConstruct,
    SensingPathway,
    ValidationResult,
)


@dataclass
class WorkflowState:
    """Shared state passed through the agent workflow."""

    user_query: str = ""
    target_signal: str = ""
    target_organism: str = ""
    pathways: list[SensingPathway] = field(default_factory=list)
    constructs: list[GeneticConstruct] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    characterization_plan: CharacterizationPlan | None = None
    report_html: str | None = None
    current_step: str = "start"
    revision_count: int = 0
    max_revisions: int = 2
