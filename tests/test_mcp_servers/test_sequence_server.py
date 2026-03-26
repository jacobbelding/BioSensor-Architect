"""Tests for the Sequence MCP server."""

import json

import pytest

from mcp_servers.sequence_server.server import (
    _estimate_construct_size,
    _format_genbank_features,
    _reverse_complement,
    call_tool,
)


class TestReverseComplement:
    def test_basic(self):
        assert _reverse_complement("ATGC") == "GCAT"

    def test_palindrome(self):
        assert _reverse_complement("AATT") == "AATT"

    def test_single_base(self):
        assert _reverse_complement("A") == "T"

    def test_unknown_bases(self):
        assert _reverse_complement("ATXGC") == "GCNAT"

    def test_lowercase_input(self):
        assert _reverse_complement("atgc") == "GCAT"

    def test_empty_string(self):
        assert _reverse_complement("") == ""

    def test_with_n(self):
        assert _reverse_complement("ANGC") == "GCNT"


class TestEstimateConstructSize:
    def test_from_sequences(self):
        parts = [{"sequence": "ATGCATGC"}, {"sequence": "AAAA"}]
        assert _estimate_construct_size(parts) == 12

    def test_from_estimated_size(self):
        parts = [{"estimated_size_bp": 1500}, {"estimated_size_bp": 2000}]
        assert _estimate_construct_size(parts) == 3500

    def test_mixed(self):
        parts = [{"sequence": "ATGC"}, {"estimated_size_bp": 100}]
        assert _estimate_construct_size(parts) == 104

    def test_empty(self):
        assert _estimate_construct_size([]) == 0

    def test_missing_fields(self):
        parts = [{"name": "unknown"}]
        assert _estimate_construct_size(parts) == 0


class TestFormatGenbankFeatures:
    def test_basic_construct(self):
        construct = {
            "name": "test_construct",
            "promoter": {"name": "pAtNRT2.1", "estimated_size_bp": 1000},
            "reporter": {"name": "GFP", "estimated_size_bp": 720},
            "terminator": {"name": "tNOS", "estimated_size_bp": 250},
        }
        result = _format_genbank_features(construct)
        assert "LOCUS" in result
        assert "test_construct" in result
        assert "pAtNRT2.1" in result
        assert "GFP" in result
        assert "tNOS" in result
        assert "//" in result

    def test_with_regulatory_elements(self):
        construct = {
            "name": "enhanced_construct",
            "promoter": {"name": "pRD29A", "estimated_size_bp": 1500},
            "reporter": {"name": "GUS", "estimated_size_bp": 1800},
            "terminator": {"name": "t35S", "estimated_size_bp": 200},
            "regulatory_elements": [
                {"name": "Omega_enhancer", "estimated_size_bp": 67},
            ],
        }
        result = _format_genbank_features(construct)
        assert "Omega_enhancer" in result
        assert "regulatory" in result

    def test_defaults_for_missing_sizes(self):
        construct = {
            "name": "minimal",
            "promoter": {},
            "reporter": {},
            "terminator": {},
        }
        result = _format_genbank_features(construct)
        assert "LOCUS" in result
        assert "//" in result


class TestCallTool:
    @pytest.mark.asyncio
    async def test_reverse_complement_tool(self):
        result = await call_tool("reverse_complement", {"sequence": "ATGC"})
        data = json.loads(result[0].text)
        assert data["reverse_complement"] == "GCAT"
        assert data["length"] == 4

    @pytest.mark.asyncio
    async def test_estimate_construct_size_tool(self):
        parts = [{"estimated_size_bp": 1000}, {"estimated_size_bp": 720}]
        result = await call_tool("estimate_construct_size", {"parts": parts})
        data = json.loads(result[0].text)
        assert data["estimated_size_bp"] == 1720

    @pytest.mark.asyncio
    async def test_format_genbank_tool(self):
        construct = {
            "name": "test",
            "promoter": {"name": "pTest", "estimated_size_bp": 500},
            "reporter": {"name": "GFP", "estimated_size_bp": 720},
            "terminator": {"name": "tNOS", "estimated_size_bp": 250},
        }
        result = await call_tool("format_genbank_features", {"construct": construct})
        assert "LOCUS" in result[0].text
        assert "pTest" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await call_tool("nonexistent", {})
        data = json.loads(result[0].text)
        assert "error" in data
