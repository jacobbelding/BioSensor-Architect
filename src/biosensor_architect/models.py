"""Pydantic data models shared across all agents."""

from pydantic import BaseModel, ConfigDict


class GeneticPart(BaseModel):
    """A single genetic part (promoter, reporter, terminator, etc.)."""

    id: str
    name: str
    type: str  # "promoter", "reporter", "terminator", "regulatory"
    organism: str
    signal_responsive_to: str | None = None
    sequence: str | None = None
    references: list[str] = []
    notes: str = ""


class SensingPathway(BaseModel):
    """A biological sensing pathway identified by the Pathway Analyst."""

    target_signal: str
    organism: str
    receptor: str
    transduction_chain: list[str]
    candidate_promoters: list[str]
    transcription_factors: list[str]
    confidence: float
    references: list[str] = []


class GeneticConstruct(BaseModel):
    """A proposed genetic construct designed by the Construct Designer."""

    name: str
    target_signal: str
    organism: str
    promoter: GeneticPart
    reporter: GeneticPart
    terminator: GeneticPart
    regulatory_elements: list[GeneticPart] = []
    estimated_size_bp: int | None = None
    codon_optimized: bool = False
    notes: str = ""


class LiteratureReference(BaseModel):
    """A literature reference from the Literature Validator."""

    pmid: str
    title: str
    authors: list[str] = []
    year: int | None = None
    relevance_score: float
    summary: str
    flags: list[str] = []  # e.g., "promoter_leakiness", "reporter_toxicity"


class ValidationResult(BaseModel):
    """Output from the Literature Validator agent."""

    model_config = ConfigDict(populate_by_name=True)

    construct: GeneticConstruct
    supporting_references: list[LiteratureReference] = []
    concerns: list[str] = []
    suggested_modifications: list[str] = []
    overall_confidence: float


class Experiment(BaseModel):
    """A single proposed experiment."""

    name: str
    description: str
    controls: list[str]
    measurements: list[str]
    expected_outcome: str


class CharacterizationPlan(BaseModel):
    """Experimental characterization plan from the Characterization Planner."""

    model_config = ConfigDict(populate_by_name=True)

    construct: GeneticConstruct
    experiments: list[Experiment]
    timeline_weeks: int | None = None
    key_metrics: list[str] = []
    notes: str = ""
