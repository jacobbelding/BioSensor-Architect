"""Base agent class for BioSensor-Architect agents."""

from autogen_agentchat.agents import AssistantAgent


def create_agent(name: str, system_message: str, tools: list | None = None) -> AssistantAgent:
    """Create an AutoGen AssistantAgent with the given configuration.

    Args:
        name: Agent name used in GroupChat.
        system_message: System prompt defining agent behavior.
        tools: Optional list of tool functions the agent can call.

    Returns:
        Configured AssistantAgent instance.
    """
    # TODO: Configure model client and tool bindings
    raise NotImplementedError("Agent creation not yet wired up")
