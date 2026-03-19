"""Tests for the Construct Designer agent."""

import pytest


@pytest.mark.skip(reason="Agent creation not yet wired up")
def test_construct_designer_creation():
    from biosensor_architect.agents.construct_designer import create_construct_designer

    agent = create_construct_designer()
    assert agent is not None
