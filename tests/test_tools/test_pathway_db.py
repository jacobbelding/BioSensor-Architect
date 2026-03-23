"""Tests for pathway_db tool functions (direct parts catalog queries)."""

import json

from biosensor_architect.tools.pathway_db import (
    get_pathway,
    search_promoters,
    search_reporters,
    search_terminators,
)


def test_search_promoters_nitrate():
    result = json.loads(search_promoters("nitrate"))
    assert isinstance(result, list)
    assert len(result) >= 1
    ids = [p["id"] for p in result]
    assert "pAtNRT2.1" in ids


def test_search_promoters_drought():
    result = json.loads(search_promoters("drought"))
    assert any(p["id"] == "pRD29A" for p in result)


def test_search_promoters_with_organism_filter():
    result = json.loads(search_promoters("nitrate", organism="Arabidopsis"))
    assert len(result) >= 1
    result_other = json.loads(search_promoters("nitrate", organism="Oryza"))
    assert len(result_other) == 0 or isinstance(result_other, dict)


def test_search_promoters_no_match():
    result = json.loads(search_promoters("xenon_gas"))
    # Should return a message dict or empty list
    assert isinstance(result, (list, dict))


def test_search_reporters_all():
    result = json.loads(search_reporters())
    assert len(result) >= 4  # GFP, GUS, betanin, luciferase, anthocyanin


def test_search_reporters_color():
    result = json.loads(search_reporters("color"))
    ids = [p["id"] for p in result]
    assert "betanin" in ids


def test_search_reporters_fluorescence():
    result = json.loads(search_reporters("fluorescence"))
    ids = [p["id"] for p in result]
    assert "GFP" in ids


def test_search_terminators_all():
    result = json.loads(search_terminators())
    assert len(result) >= 3


def test_search_terminators_arabidopsis():
    result = json.loads(search_terminators("Arabidopsis"))
    ids = [p["id"] for p in result]
    assert "tHSP18.2" in ids


def test_get_pathway_nitrate():
    result = json.loads(get_pathway("Arabidopsis thaliana", "nitrate"))
    assert result.get("signal") == "nitrate"
    assert "NRT1.1" in result.get("receptor", "")
    assert "NLP7" in result.get("transcription_factors", [])


def test_get_pathway_drought():
    result = json.loads(get_pathway("Arabidopsis thaliana", "drought"))
    assert result.get("signal") == "drought"
    assert "pRD29A" in result.get("candidate_promoters", [])


def test_get_pathway_fuzzy_match():
    """Should match on signal alone if organism doesn't match exactly."""
    result = json.loads(get_pathway("tomato", "nitrate"))
    assert result.get("signal") == "nitrate"


def test_get_pathway_not_found():
    result = json.loads(get_pathway("Arabidopsis thaliana", "sound_waves"))
    assert "message" in result
