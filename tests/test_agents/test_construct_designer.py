"""Tests for the Construct Designer agent."""

from unittest.mock import patch

import pytest

import biosensor_architect.agents.base as base_mod


def test_construct_designer_creation():
    base_mod._model_client = None  # Reset cached client
    from biosensor_architect.agents.construct_designer import create_construct_designer

    with patch.object(base_mod.settings, "default_model", "gpt-4o-mini"), \
         patch.object(base_mod.settings, "openai_api_key", "test-key"):
        agent = create_construct_designer()
    assert agent is not None
    assert agent.name == "ConstructDesigner"
    base_mod._model_client = None
