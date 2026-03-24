"""Tests for the design verification module."""

from biosensor_architect.orchestration.design_verifier import (
    VerificationResult,
    VerificationIssue,
    _extract_gene_names_from_html,
    _extract_target_signal_from_html,
    inject_verification_banner,
    verify_design,
)


def test_extract_gene_names_from_card_headers():
    html = """
    <div class="card">
        <h3>KAT1 Promoter</h3>
        <p>Details</p>
    </div>
    <div class="card">
        <h4>GFP Reporter</h4>
    </div>
    """
    names = _extract_gene_names_from_html(html)
    assert "KAT1 Promoter" in names
    assert "GFP Reporter" in names


def test_extract_gene_names_from_table():
    html = """
    <table>
        <tr><td>pAtNRT2.1</td><td>Nitrate-responsive promoter</td></tr>
        <tr><td>GFP</td><td>Reporter output</td></tr>
    </table>
    """
    names = _extract_gene_names_from_html(html)
    assert "pAtNRT2.1" in names
    assert "GFP" in names


def test_extract_target_signal():
    html = '<p><strong>Target Signal:</strong> Nitrate</p>'
    assert _extract_target_signal_from_html(html) == "Nitrate"


def test_extract_target_signal_missing():
    html = "<p>No relevant info here</p>"
    assert _extract_target_signal_from_html(html) is None


def test_verify_design_flags_missing_svg():
    """A report without an SVG should get a structural warning."""
    html = """<!DOCTYPE html><html><body>
    <p>Target Signal: nitrate</p>
    <h3>pAtNRT2.1 Promoter</h3>
    <p>Some component info</p>
    <p>characterization plan here</p>
    <p>PMID 12345678</p>
    </body></html>"""
    result = verify_design(html)
    messages = [i.message for i in result.issues]
    assert any("SVG" in m for m in messages)


def test_verify_design_detects_accession():
    """Report with TAIR accession should not flag missing accessions."""
    html = """<!DOCTYPE html><html><body>
    <svg><rect/></svg>
    <p>component specifications</p>
    <p>characterization plan</p>
    <p>PMID 12345678</p>
    <p>AT1G12110</p>
    </body></html>"""
    result = verify_design(html)
    messages = [i.message for i in result.issues]
    assert not any("accession" in m.lower() for m in messages)


def test_verify_design_flags_missing_accession():
    """Report without any accession numbers should get a warning."""
    html = """<!DOCTYPE html><html><body>
    <svg><rect/></svg>
    <p>component info here</p>
    <p>characterization</p>
    <p>PMID 12345678</p>
    </body></html>"""
    result = verify_design(html)
    messages = [i.message for i in result.issues]
    assert any("accession" in m.lower() for m in messages)


def test_inject_banner_no_issues():
    html = "<html><body><p>Content</p></body></html>"
    result = VerificationResult()
    output = inject_verification_banner(html, result)
    assert "verified" in output.lower()
    assert "#e8f5e9" in output  # green


def test_inject_banner_with_warnings():
    html = "<html><body><p>Content</p></body></html>"
    result = VerificationResult(
        issues=[
            VerificationIssue(severity="warning", component="X", message="test warning")
        ],
        unverified_components=["SomeGene"],
    )
    output = inject_verification_banner(html, result)
    assert "warning" in output.lower()
    assert "#fffde7" in output  # amber


def test_inject_banner_with_errors():
    html = "<html><body><p>Content</p></body></html>"
    result = VerificationResult(
        issues=[
            VerificationIssue(severity="error", component="X", message="bad component")
        ],
    )
    output = inject_verification_banner(html, result)
    assert "error" in output.lower()
    assert "#fff5f5" in output  # red


def test_verification_result_properties():
    result = VerificationResult()
    assert not result.has_errors
    assert not result.has_warnings

    result.issues.append(
        VerificationIssue(severity="warning", component="X", message="warn")
    )
    assert not result.has_errors
    assert result.has_warnings

    result.issues.append(
        VerificationIssue(severity="error", component="Y", message="err")
    )
    assert result.has_errors


def test_verification_result_summary():
    result = VerificationResult(
        verified_components=["A", "B"],
        unverified_components=["C"],
        issues=[
            VerificationIssue(severity="warning", component="X", message="w"),
        ],
    )
    summary = result.summary()
    assert "2 verified" in summary
    assert "1 unverified" in summary
    assert "1 warnings" in summary
