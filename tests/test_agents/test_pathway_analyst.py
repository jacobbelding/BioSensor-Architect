"""Tests for the Pathway Analyst agent."""

import pytest


@pytest.mark.skip(reason="Agent creation not yet wired up")
def test_pathway_analyst_creation():
    from biosensor_architect.agents.pathway_analyst import create_pathway_analyst

    agent = create_pathway_analyst()
    assert agent is not None


@pytest.mark.skip(reason="Agent creation not yet wired up")
async def test_pathway_analyst_identifies_nitrate_pathway():
    """Pathway Analyst should identify NRT pathway for nitrate signal."""
    pass
