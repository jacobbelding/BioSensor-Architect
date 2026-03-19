"""Tests for PubMed search tool functions."""

import pytest


@pytest.mark.skip(reason="MCP client not yet wired up")
async def test_search_papers():
    from biosensor_architect.tools.pubmed_search import search_papers

    results = await search_papers("nitrate biosensor Arabidopsis")
    assert isinstance(results, list)
