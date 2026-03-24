"""Tests for the design verification module."""

from biosensor_architect.orchestration.design_verifier import (
    CrossReactivityHit,
    VerificationResult,
    VerificationIssue,
    _analyze_cross_reactivity,
    _extract_gene_names_from_html,
    _extract_target_signal_from_html,
    _find_promoter_cis_elements,
    _identify_promoter_in_html,
    inject_specificity_report,
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


# ── Cross-reactivity and specificity report tests ──


class TestIdentifyPromoterInHtml:
    def test_finds_promoter_by_name_pattern(self):
        html = "<h3>RD29A Promoter</h3><p>Details about this promoter</p>"
        assert _identify_promoter_in_html(html) is not None
        assert "rd29a" in _identify_promoter_in_html(html).lower()

    def test_finds_promoter_pid_format(self):
        html = "<p>The construct uses pAtRD29A driving GFP</p>"
        result = _identify_promoter_in_html(html)
        assert result is not None
        assert "RD29A" in result

    def test_returns_none_when_no_promoter(self):
        html = "<p>Just some text about a plant experiment</p>"
        assert _identify_promoter_in_html(html) is None


class TestFindPromoterCisElements:
    def test_direct_match(self):
        elements = _find_promoter_cis_elements("rd29a")
        assert "CRT/DRE (CCGAC)" in elements
        assert "ABRE" in elements

    def test_partial_match(self):
        elements = _find_promoter_cis_elements("AtRD29A")
        assert "CRT/DRE (CCGAC)" in elements

    def test_no_elements(self):
        """Promoters with no known shared cis-elements return empty list."""
        elements = _find_promoter_cis_elements("nrt2")
        assert elements == []

    def test_unknown_promoter(self):
        elements = _find_promoter_cis_elements("totally_unknown_xyz")
        assert elements == []


class TestAnalyzeCrossReactivity:
    def test_rd29a_drought_detects_cold(self):
        """RD29A has CRT/DRE, so targeting drought should flag cold cross-reactivity."""
        hits = _analyze_cross_reactivity("rd29a", "drought", [])
        confounding = [h.confounding_signal for h in hits]
        assert "cold" in confounding or "freezing" in confounding

    def test_rd29a_drought_severity(self):
        """CRT/DRE overlap should be flagged as severe."""
        hits = _analyze_cross_reactivity("rd29a", "drought", [])
        crt_hits = [h for h in hits if "CRT/DRE" in h.shared_element]
        assert len(crt_hits) > 0
        assert all(h.severity == "severe" for h in crt_hits)

    def test_rd29a_drought_abre_moderate(self):
        """ABRE overlap should be flagged as moderate."""
        hits = _analyze_cross_reactivity("rd29a", "drought", [])
        abre_hits = [h for h in hits if "ABRE" in h.shared_element]
        assert len(abre_hits) > 0
        assert all(h.severity == "moderate" for h in abre_hits)

    def test_no_cross_reactivity_for_clean_promoter(self):
        """Promoter with no shared cis-elements should have no hits."""
        hits = _analyze_cross_reactivity("nrt2", "nitrate", [])
        assert len(hits) == 0

    def test_pathway_db_overlap(self):
        """Promoter listed in multiple pathways should be flagged."""
        # Use nrt2 (no cis-element hits) so pathway DB overlap is the only source
        pathways = [
            {
                "signal": "phosphorus",
                "candidate_promoters": ["nrt2", "pht1"],
            },
        ]
        hits = _analyze_cross_reactivity("nrt2", "nitrate", pathways)
        pathway_hits = [h for h in hits if h.shared_element == "Pathway database"]
        assert len(pathway_hits) > 0
        assert pathway_hits[0].confounding_signal == "phosphorus"

    def test_skips_target_signal_pathway(self):
        """Should not flag the target signal's own pathway as cross-reactive."""
        pathways = [
            {
                "signal": "drought",
                "candidate_promoters": ["rd29a"],
            },
        ]
        hits = _analyze_cross_reactivity("rd29a", "drought", pathways)
        pathway_hits = [h for h in hits if h.shared_element == "Pathway database"]
        assert len(pathway_hits) == 0


class TestSpecificityGrade:
    def test_unknown_when_no_hits(self):
        result = VerificationResult()
        assert result.specificity_grade == "UNKNOWN"

    def test_high_with_only_minor(self):
        result = VerificationResult(
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="test", target_signal="drought",
                    confounding_signal="osmotic", shared_element="X",
                    severity="minor", explanation="",
                ),
            ]
        )
        assert result.specificity_grade == "HIGH"

    def test_moderate_with_moderate_hit(self):
        result = VerificationResult(
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="test", target_signal="drought",
                    confounding_signal="salt", shared_element="ABRE",
                    severity="moderate", explanation="",
                ),
            ]
        )
        assert result.specificity_grade == "MODERATE"

    def test_low_with_severe_hit(self):
        result = VerificationResult(
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="test", target_signal="drought",
                    confounding_signal="cold", shared_element="CRT/DRE",
                    severity="severe", explanation="",
                ),
            ]
        )
        assert result.specificity_grade == "LOW"

    def test_severe_overrides_moderate(self):
        result = VerificationResult(
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="test", target_signal="drought",
                    confounding_signal="salt", shared_element="ABRE",
                    severity="moderate", explanation="",
                ),
                CrossReactivityHit(
                    promoter="test", target_signal="drought",
                    confounding_signal="cold", shared_element="CRT/DRE",
                    severity="severe", explanation="",
                ),
            ]
        )
        assert result.specificity_grade == "LOW"


class TestInjectSpecificityReport:
    def test_injects_panel_before_footer(self):
        html = "<html><body><p>Content</p><footer>Footer</footer></body></html>"
        result = VerificationResult(
            promoter_name="RD29A",
            target_signal="Drought",
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="RD29A", target_signal="Drought",
                    confounding_signal="Cold", shared_element="CRT/DRE (CCGAC)",
                    severity="severe", explanation="CRT/DRE motif shared.",
                ),
            ],
        )
        output = inject_specificity_report(html, result)
        assert "Specificity Report Card" in output
        assert "RD29A" in output
        assert "Cold" in output
        # Panel should appear before footer
        assert output.index("Specificity Report Card") < output.index("<footer")

    def test_injects_before_body_close_when_no_footer(self):
        html = "<html><body><p>Content</p></body></html>"
        result = VerificationResult(
            promoter_name="RD29A",
            target_signal="Drought",
            cross_reactivity=[],
        )
        output = inject_specificity_report(html, result)
        assert "Specificity Report Card" in output
        assert "No known cross-reactivity detected" in output

    def test_no_injection_when_no_data(self):
        html = "<html><body><p>Content</p></body></html>"
        result = VerificationResult()
        output = inject_specificity_report(html, result)
        assert output == html  # Unchanged

    def test_severe_hits_show_mitigation(self):
        html = "<html><body><p>Content</p></body></html>"
        result = VerificationResult(
            promoter_name="RD29A",
            target_signal="Drought",
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="RD29A", target_signal="Drought",
                    confounding_signal="Cold", shared_element="CRT/DRE (CCGAC)",
                    severity="severe", explanation="Shared motif.",
                ),
            ],
        )
        output = inject_specificity_report(html, result)
        assert "Mitigation recommended" in output
        assert "CRISPRi" in output

    def test_grade_badge_colors(self):
        html = "<html><body><p>Content</p></body></html>"
        # LOW grade should have red-ish color
        result = VerificationResult(
            promoter_name="RD29A",
            target_signal="Drought",
            cross_reactivity=[
                CrossReactivityHit(
                    promoter="RD29A", target_signal="Drought",
                    confounding_signal="Cold", shared_element="CRT/DRE",
                    severity="severe", explanation="test",
                ),
            ],
        )
        output = inject_specificity_report(html, result)
        assert "#ffebee" in output or "#d32f2f" in output  # red colors for LOW grade
