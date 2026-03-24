"""Tests for Anthropic model client support in base agent factory."""

from unittest.mock import patch

import pytest

from biosensor_architect.agents.base import _get_model_client, _is_anthropic_model


def test_is_anthropic_model():
    assert _is_anthropic_model("claude-sonnet-4-20250514")
    assert _is_anthropic_model("claude-3-haiku-20240307")
    assert _is_anthropic_model("claude-opus-4-20250514")
    assert not _is_anthropic_model("gpt-4o")
    assert not _is_anthropic_model("gpt-4o-mini")
    assert not _is_anthropic_model("o1-preview")


def test_get_model_client_creates_openai_for_gpt():
    """OpenAI models should use OpenAIChatCompletionClient."""
    # Reset cached client
    import biosensor_architect.agents.base as base_mod
    base_mod._model_client = None

    with patch.object(base_mod.settings, "openai_api_key", "test-key"):
        client = _get_model_client("gpt-4o-mini")

    from autogen_ext.models.openai import OpenAIChatCompletionClient
    assert isinstance(client, OpenAIChatCompletionClient)

    # Clean up
    base_mod._model_client = None


def test_get_model_client_creates_anthropic_for_claude():
    """Claude models should use AnthropicChatCompletionClient."""
    import biosensor_architect.agents.base as base_mod
    base_mod._model_client = None

    with patch.object(base_mod.settings, "anthropic_api_key", "test-key"):
        client = _get_model_client("claude-sonnet-4-20250514")

    from autogen_ext.models.anthropic import AnthropicChatCompletionClient
    assert isinstance(client, AnthropicChatCompletionClient)

    # Clean up
    base_mod._model_client = None


def test_get_model_client_raises_without_api_key():
    """Should raise ValueError if the required API key is missing."""
    import biosensor_architect.agents.base as base_mod
    base_mod._model_client = None

    with patch.object(base_mod.settings, "anthropic_api_key", ""):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            _get_model_client("claude-sonnet-4-20250514")

    base_mod._model_client = None

    with patch.object(base_mod.settings, "openai_api_key", ""):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _get_model_client("gpt-4o")

    base_mod._model_client = None


def test_get_model_client_caches_and_reuses():
    """Same model should return the same client instance."""
    import biosensor_architect.agents.base as base_mod
    base_mod._model_client = None

    with patch.object(base_mod.settings, "openai_api_key", "test-key"):
        client1 = _get_model_client("gpt-4o-mini")
        client2 = _get_model_client("gpt-4o-mini")

    assert client1 is client2

    base_mod._model_client = None


def test_get_model_client_recreates_on_model_change():
    """Different model should create a new client."""
    import biosensor_architect.agents.base as base_mod
    base_mod._model_client = None

    with patch.object(base_mod.settings, "openai_api_key", "test-key"):
        client1 = _get_model_client("gpt-4o-mini")

    with patch.object(base_mod.settings, "anthropic_api_key", "test-key"):
        client2 = _get_model_client("claude-sonnet-4-20250514")

    assert client1 is not client2

    base_mod._model_client = None
