"""Tests for PMID validation and report QC."""

from biosensor_architect.orchestration.report_qc import (
    extract_pmids_from_html,
    get_pmid_validation_summary,
    validate_report_pmids,
)
from biosensor_architect.tools.pubmed_search import (
    _register_pmid,
    get_verified_pmids,
    reset_verified_pmids,
)


def test_pmid_registry_lifecycle():
    """Registry should accumulate PMIDs and clear on reset."""
    reset_verified_pmids()
    assert get_verified_pmids() == {}

    _register_pmid("11050181", "NRT2.1 paper")
    _register_pmid("17259264", "NLP7 paper")
    assert len(get_verified_pmids()) == 2
    assert "11050181" in get_verified_pmids()

    reset_verified_pmids()
    assert get_verified_pmids() == {}


def test_pmid_registry_ignores_invalid():
    """Registry should reject non-numeric PMIDs."""
    reset_verified_pmids()
    _register_pmid("", "")
    _register_pmid("not-a-pmid", "")
    assert get_verified_pmids() == {}


def test_extract_pmids_from_html():
    html = """
    <p>See PMID:11050181 and PMID: 17259264 for details.</p>
    <a href="https://pubmed.ncbi.nlm.nih.gov/33574609">betanin paper</a>
    """
    pmids = extract_pmids_from_html(html)
    assert "11050181" in pmids
    assert "17259264" in pmids
    assert "33574609" in pmids


def test_extract_pmids_empty_html():
    assert extract_pmids_from_html("") == set()
    assert extract_pmids_from_html("<p>No citations here.</p>") == set()


def test_validate_report_pmids_all_verified():
    """If all PMIDs are in the registry, HTML should be unchanged."""
    reset_verified_pmids()
    _register_pmid("11050181", "NRT2.1")

    html = '<p>Reference: PMID:11050181</p>'
    result = validate_report_pmids(html, verify_unknown=False)
    assert result == html  # No changes


def test_validate_report_pmids_flags_unverified():
    """Unverified PMIDs should be annotated with warning style."""
    reset_verified_pmids()
    # Don't register anything — all PMIDs will be "unverified"

    html = '<p>See PMID:99999999</p>'
    result = validate_report_pmids(html, verify_unknown=False)
    assert "unverified" in result
    assert "line-through" in result


def test_get_pmid_validation_summary():
    reset_verified_pmids()
    _register_pmid("11050181", "NRT2.1")

    html = '<p>PMID:11050181 and PMID:99999999</p>'
    summary = get_pmid_validation_summary(html)
    assert summary["total_cited"] == 2
    assert summary["verified"] == 1
    assert summary["unverified"] == 1
    assert "11050181" in summary["pmids_verified"]
    assert "99999999" in summary["pmids_unverified"]
