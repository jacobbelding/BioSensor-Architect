"""Tests for PubMed search tool functions."""

import json
from unittest.mock import MagicMock, patch

import pytest

from biosensor_architect.tools.pubmed_search import (
    fetch_abstract,
    fetch_related,
    search_papers,
)


# ---------------------------------------------------------------------------
# Mock-based unit tests (no network required)
# ---------------------------------------------------------------------------

MOCK_ESEARCH_RESPONSE = {
    "esearchresult": {"idlist": ["11050181", "17259264"]}
}

MOCK_ESUMMARY_RESPONSE = {
    "result": {
        "uids": ["11050181", "17259264"],
        "11050181": {
            "title": "AtNRT2.1 nitrate transporter gene",
            "authors": [{"name": "Filleur S"}, {"name": "Daniel-Vedele F"}],
            "pubdate": "2001 Jan",
            "source": "Plant J",
        },
        "17259264": {
            "title": "NLP7 nitrate signaling",
            "authors": [{"name": "Castaings L"}],
            "pubdate": "2009",
            "source": "Plant Cell",
        },
    }
}


def test_search_papers_mock():
    """search_papers returns structured results from mocked NCBI API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # esearch
            mock_resp.json.return_value = MOCK_ESEARCH_RESPONSE
        else:  # esummary
            mock_resp.json.return_value = MOCK_ESUMMARY_RESPONSE
        return mock_resp

    with patch("biosensor_architect.tools.pubmed_search.requests.get", side_effect=side_effect):
        with patch("biosensor_architect.tools.pubmed_search.time.sleep"):
            result = json.loads(search_papers("nitrate biosensor Arabidopsis"))

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["pmid"] == "11050181"
    assert "NRT2.1" in result[0]["title"]


MOCK_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <ArticleTitle>The AtNRT2.1 gene</ArticleTitle>
        <AuthorList>
          <Author><LastName>Filleur</LastName><ForeName>Sophie</ForeName></Author>
        </AuthorList>
        <Journal><Title>Plant Journal</Title></Journal>
        <Abstract>
          <AbstractText>NRT2.1 is a high-affinity nitrate transporter.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData><History><PubMedPubDate><Year>2001</Year></PubMedPubDate></History></PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


def test_fetch_abstract_mock():
    """fetch_abstract parses XML and returns structured result."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = MOCK_EFETCH_XML

    with patch("biosensor_architect.tools.pubmed_search.requests.get", return_value=mock_resp):
        with patch("biosensor_architect.tools.pubmed_search.time.sleep"):
            result = json.loads(fetch_abstract("11050181"))

    assert result["pmid"] == "11050181"
    assert "NRT2.1" in result["title"]
    assert "Filleur" in result["authors"][0]
    assert "nitrate transporter" in result["abstract"]


def test_search_papers_network_error():
    """search_papers handles network errors gracefully."""
    import requests as req

    with patch(
        "biosensor_architect.tools.pubmed_search.requests.get",
        side_effect=req.ConnectionError("no network"),
    ):
        with patch("biosensor_architect.tools.pubmed_search.time.sleep"):
            result = json.loads(search_papers("test"))

    assert "error" in result


# ---------------------------------------------------------------------------
# Integration tests (require network — skip in CI)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(True, reason="Network test — run manually with: pytest -m integration")
def test_search_papers_live():
    results = json.loads(search_papers("nitrate biosensor Arabidopsis", max_results=3))
    assert isinstance(results, list)
    assert len(results) > 0
    assert "pmid" in results[0]


@pytest.mark.integration
@pytest.mark.skipif(True, reason="Network test — run manually with: pytest -m integration")
def test_fetch_abstract_live():
    result = json.loads(fetch_abstract("11050181"))
    assert result.get("pmid") == "11050181"
    assert len(result.get("abstract", "")) > 50
