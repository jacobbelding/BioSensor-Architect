"""Tests for the Parts Database MCP server."""

import json
from pathlib import Path

import pytest

PARTS_FILE = Path(__file__).parent.parent.parent / "mcp_servers" / "parts_db_server" / "data" / "parts_catalog.json"


def test_parts_catalog_is_valid_json():
    """Parts catalog should be valid JSON."""
    with open(PARTS_FILE) as f:
        parts = json.load(f)
    assert isinstance(parts, list)
    assert len(parts) > 0


def test_parts_have_required_fields():
    """Each part should have id, name, type, and organism fields."""
    with open(PARTS_FILE) as f:
        parts = json.load(f)
    for part in parts:
        assert "id" in part, f"Part missing 'id': {part}"
        assert "name" in part, f"Part missing 'name': {part}"
        assert "type" in part, f"Part missing 'type': {part}"
        assert "organism" in part, f"Part missing 'organism': {part}"


def test_parts_have_valid_types():
    """Part types should be one of: promoter, reporter, terminator, regulatory."""
    valid_types = {"promoter", "reporter", "terminator", "regulatory"}
    with open(PARTS_FILE) as f:
        parts = json.load(f)
    for part in parts:
        assert part["type"] in valid_types, f"Invalid type '{part['type']}' for part {part['id']}"
