"""Tests for the Pathway Analyst agent."""

from unittest.mock import patch

import pytest

import biosensor_architect.agents.base as base_mod


def test_pathway_analyst_creation():
    base_mod._model_client = None  # Reset cached client
    from biosensor_architect.agents.pathway_analyst import create_pathway_analyst

    with patch.object(base_mod.settings, "default_model", "gpt-4o-mini"), \
         patch.object(base_mod.settings, "openai_api_key", "test-key"):
        agent = create_pathway_analyst()
    assert agent is not None
    assert agent.name == "PathwayAnalyst"
    base_mod._model_client = None


@pytest.mark.skip(reason="Requires LLM API call — run manually")
async def test_pathway_analyst_identifies_nitrate_pathway():
    """Pathway Analyst should identify NRT pathway for nitrate signal."""
    pass
