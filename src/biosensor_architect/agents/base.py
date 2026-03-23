"""Base agent factory for BioSensor-Architect agents.

Uses AutoGen 0.7's AssistantAgent with OpenAIChatCompletionClient.
All agents are created through create_agent() to ensure consistent
model client configuration.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import BaseTool

from biosensor_architect.config import settings

# Lazy-initialized model client (shared across agents to reuse connection pool)
_model_client = None


def _get_model_client(model: str | None = None):
    """Return a shared OpenAIChatCompletionClient instance.

    Lazily initialized on first call. If *model* is provided it overrides
    the default from settings; otherwise ``settings.default_model`` is used.
    """
    global _model_client

    from autogen_ext.models.openai import OpenAIChatCompletionClient

    target_model = model or settings.default_model

    # Re-create if the requested model differs from the cached one
    if _model_client is None or getattr(_model_client, "_resolved_model", None) != target_model:
        _model_client = OpenAIChatCompletionClient(
            model=target_model,
            api_key=settings.openai_api_key,
        )
        _model_client._resolved_model = target_model  # type: ignore[attr-defined]

    return _model_client


ToolType = BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]


def create_agent(
    name: str,
    system_message: str,
    tools: Sequence[ToolType] | None = None,
    *,
    model: str | None = None,
    description: str | None = None,
) -> AssistantAgent:
    """Create an AutoGen AssistantAgent with the given configuration.

    Args:
        name: Agent name used in GroupChat routing.
        system_message: System prompt defining agent behavior.
        tools: Optional list of tool callables the agent can invoke.
        model: Override the default LLM model for this agent.
        description: Short description shown to the SelectorGroupChat model
                     selector.  Defaults to the first line of *system_message*.

    Returns:
        Configured AssistantAgent instance.
    """
    client = _get_model_client(model)

    # AutoGen's SelectorGroupChat uses the description to pick the next speaker.
    # Default to first meaningful line of the system message.
    if description is None:
        description = system_message.strip().split("\n")[0][:200]

    return AssistantAgent(
        name=name,
        model_client=client,
        system_message=system_message,
        tools=list(tools) if tools else [],
        description=description,
    )
