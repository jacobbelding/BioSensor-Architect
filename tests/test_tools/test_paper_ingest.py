"""Tests for the paper ingestion module."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from biosensor_architect.tools.paper_ingest import (
    append_to_catalog,
    deduplicate_parts,
    deduplicate_pathways,
    resolve_identifier,
    PARTS_FILE,
)


def test_resolve_pmid_format():
    """resolve_identifier should accept various PMID formats."""
    # These call the real fetch_abstract which needs network, so mock it
    mock_result = json.dumps({
        "pmid": "11050181",
        "title": "Test paper",
        "authors": ["Author A"],
        "journal": "Test Journal",
        "year": "2001",
        "abstract": "Test abstract.",
    })
    with patch("biosensor_architect.tools.paper_ingest.fetch_abstract", return_value=mock_result):
        # Format: PMID:12345
        result = resolve_identifier("PMID:11050181")
        assert result["pmid"] == "11050181"

        # Format: bare number
        result = resolve_identifier("11050181")
        assert result["pmid"] == "11050181"

        # Format: PMID 12345 (with space)
        result = resolve_identifier("PMID 11050181")
        assert result["pmid"] == "11050181"


def test_resolve_invalid_identifier():
    """resolve_identifier should raise ValueError for unknown formats."""
    with pytest.raises(ValueError, match="Unrecognized identifier"):
        resolve_identifier("not-a-valid-id")


def test_deduplicate_parts_filters_existing():
    existing = [
        {"id": "GFP", "name": "Green Fluorescent Protein", "type": "reporter"},
        {"id": "pAtNRT2.1", "name": "AtNRT2.1 promoter", "type": "promoter"},
    ]
    new_parts = [
        {"id": "GFP", "name": "GFP", "type": "reporter"},  # Duplicate by ID
        {"id": "newReporter", "name": "Green Fluorescent Protein", "type": "reporter"},  # Duplicate by name
        {"id": "pNewPromoter", "name": "New promoter", "type": "promoter"},  # Unique
    ]

    unique = deduplicate_parts(new_parts, existing)
    assert len(unique) == 1
    assert unique[0]["id"] == "pNewPromoter"


def test_deduplicate_parts_empty():
    assert deduplicate_parts([], []) == []
    assert deduplicate_parts([{"id": "x", "name": "x"}], []) == [{"id": "x", "name": "x"}]


def test_deduplicate_pathways_filters_existing():
    existing = [
        {"signal": "nitrate", "organism": "Arabidopsis thaliana"},
    ]
    new_pathways = [
        {"signal": "nitrate", "organism": "Arabidopsis thaliana"},  # Duplicate
        {"signal": "drought", "organism": "Arabidopsis thaliana"},  # Unique
    ]

    unique = deduplicate_pathways(new_pathways, existing)
    assert len(unique) == 1
    assert unique[0]["signal"] == "drought"


def test_append_to_catalog_with_tmpfile(tmp_path):
    """append_to_catalog should write new parts to JSON file."""
    # Create a temporary catalog file
    catalog_file = tmp_path / "parts_catalog.json"
    catalog_file.write_text('[{"id": "existing", "name": "Existing Part"}]')

    new_parts = [{"id": "new_part", "name": "New Part", "type": "reporter"}]

    # Patch PARTS_FILE and the cache clear to use our temp file
    with patch("biosensor_architect.tools.paper_ingest.PARTS_FILE", catalog_file):
        with patch("biosensor_architect.tools.pathway_db._load_parts") as mock_cache:
            mock_cache.cache_clear = lambda: None
            count = append_to_catalog(new_parts)

    assert count == 1
    data = json.loads(catalog_file.read_text())
    assert len(data) == 2
    assert data[1]["id"] == "new_part"
