"""Tests for the design critic module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from biosensor_architect.orchestration.critic import CritiqueResult, critique_design


@pytest.fixture
def mock_llm_response():
    """Mock LLM response with a valid critique JSON."""
    return json.dumps({
        "approved": False,
        "overall_score": 6,
        "scores": {
            "biological_soundness": 7,
            "literature_support": 5,
            "construct_design": 6,
            "characterization_plan": 6,
            "report_quality": 7,
        },
        "strengths": ["Good promoter selection", "Appropriate reporter"],
        "weaknesses": ["Weak literature support", "Missing controls"],
        "feedback": "Add specificity controls for ammonium and urea.",
    })


async def test_critique_parses_valid_json(mock_llm_response):
    """Critic should parse well-formed JSON from the LLM."""
    mock_response = MagicMock()
    mock_response.content = mock_llm_response

    mock_client = AsyncMock()
    mock_client.create = AsyncMock(return_value=mock_response)

    with patch("biosensor_architect.orchestration.critic._get_model_client", return_value=mock_client):
        result = await critique_design("<html>Test report</html>", round_num=1)

    assert isinstance(result, CritiqueResult)
    assert result.approved is False
    assert result.overall_score == 6
    assert "ammonium" in result.feedback
    assert len(result.strengths) == 2
    assert len(result.weaknesses) == 2


async def test_critique_handles_malformed_json():
    """Critic should handle LLM responses that aren't valid JSON."""
    mock_response = MagicMock()
    mock_response.content = "I think the design is okay. Score: 7/10."

    mock_client = AsyncMock()
    mock_client.create = AsyncMock(return_value=mock_response)

    with patch("biosensor_architect.orchestration.critic._get_model_client", return_value=mock_client):
        result = await critique_design("<html>Test report</html>", round_num=1)

    assert isinstance(result, CritiqueResult)
    # Should fall back to raw response as feedback
    assert "7/10" in result.feedback
    assert result.approved is False  # Default when parsing fails


async def test_critique_approved_design():
    """Critic should set approved=True for high-scoring designs."""
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "approved": True,
        "overall_score": 9,
        "scores": {},
        "strengths": ["Excellent design"],
        "weaknesses": [],
        "feedback": "Design approved.",
    })

    mock_client = AsyncMock()
    mock_client.create = AsyncMock(return_value=mock_response)

    with patch("biosensor_architect.orchestration.critic._get_model_client", return_value=mock_client):
        result = await critique_design("<html>Great report</html>", round_num=1)

    assert result.approved is True
    assert result.overall_score == 9
