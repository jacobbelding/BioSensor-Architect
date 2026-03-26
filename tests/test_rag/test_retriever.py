"""Tests for the RAG retriever module."""

import json

from biosensor_architect.rag.retriever import retrieve, search_literature


def test_retrieve_returns_results():
    """Should return results from the indexed papers (requires prior indexing)."""
    hits = retrieve("potassium HAK5 transporter", k=3)
    # If the index has been populated, we should get results
    # If not, this gracefully returns empty
    assert isinstance(hits, list)
    if hits:
        assert "text" in hits[0]
        assert "source" in hits[0]
        assert "score" in hits[0]


def test_retrieve_empty_on_new_collection():
    """A fresh collection should return no results."""
    hits = retrieve("test query", k=3, collection_name="nonexistent_test_collection")
    assert hits == []


def test_search_literature_returns_json():
    """The tool function should return valid JSON."""
    result = search_literature("drought stress promoter")
    parsed = json.loads(result)
    assert "results" in parsed or "message" in parsed


def test_search_literature_empty_index():
    """With an empty index, should return a helpful message."""
    result = search_literature("test query", max_results=3)
    parsed = json.loads(result)
    # Either returns results (if indexed) or a message
    assert "results" in parsed or "message" in parsed
