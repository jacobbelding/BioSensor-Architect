"""Shared pytest fixtures for BioSensor-Architect tests."""

import pytest

from biosensor_architect.models import GeneticConstruct, GeneticPart, SensingPathway


@pytest.fixture
def sample_promoter():
    return GeneticPart(
        id="pAtNRT2.1",
        name="AtNRT2.1 promoter",
        type="promoter",
        organism="Arabidopsis thaliana",
        signal_responsive_to="nitrate",
        notes="Nitrate-inducible promoter from high-affinity nitrate transporter",
    )


@pytest.fixture
def sample_reporter():
    return GeneticPart(
        id="betanin",
        name="Betanin biosynthesis cassette",
        type="reporter",
        organism="Beta vulgaris",
        notes="Visible color reporter; produces red-violet pigment",
    )


@pytest.fixture
def sample_terminator():
    return GeneticPart(
        id="tNOS",
        name="NOS terminator",
        type="terminator",
        organism="Agrobacterium tumefaciens",
        notes="Widely used terminator in plant transformation vectors",
    )


@pytest.fixture
def sample_pathway(sample_promoter):
    return SensingPathway(
        target_signal="nitrate",
        organism="Arabidopsis thaliana",
        receptor="NRT1.1 (CHL1)",
        transduction_chain=["NRT1.1", "CIPK23", "NLP7", "NRT2.1 promoter activation"],
        candidate_promoters=[sample_promoter.id],
        transcription_factors=["NLP7", "TGA1"],
        confidence=0.85,
        references=["PMC6542345"],
    )


@pytest.fixture
def sample_construct(sample_promoter, sample_reporter, sample_terminator):
    return GeneticConstruct(
        name="NRT2.1p::Betanin::tNOS",
        target_signal="nitrate",
        organism="Arabidopsis thaliana",
        promoter=sample_promoter,
        reporter=sample_reporter,
        terminator=sample_terminator,
        estimated_size_bp=4500,
    )
