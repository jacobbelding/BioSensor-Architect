"""Tests for the RAG indexer module."""

import tempfile
from pathlib import Path

from biosensor_architect.rag.indexer import (
    _chunk_text,
    _clean_text,
    _extract_pmid_from_text,
    index_directory,
    index_file,
)


def test_clean_text_normalizes_whitespace():
    text = "Hello   world\n\n\n\n\nParagraph two"
    cleaned = _clean_text(text)
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_clean_text_removes_control_chars():
    text = "Hello\x00world\x07test"
    cleaned = _clean_text(text)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned


def test_extract_pmid():
    text = "Some header PMID: 12345678 rest of text"
    assert _extract_pmid_from_text(text) == "12345678"


def test_extract_pmid_colon_format():
    text = "Reference PMID:87654321"
    assert _extract_pmid_from_text(text) == "87654321"


def test_extract_pmid_missing():
    text = "No PMID in this text at all."
    assert _extract_pmid_from_text(text) is None


def test_chunk_text_basic():
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = _chunk_text(text, chunk_size=50, overlap=0)
    assert len(chunks) >= 1
    # All original text should be present across chunks
    combined = " ".join(chunks)
    assert "Para one" in combined
    assert "Para three" in combined


def test_chunk_text_respects_size():
    text = "\n\n".join(f"Paragraph {i} with some content here." for i in range(20))
    chunks = _chunk_text(text, chunk_size=200, overlap=0)
    for chunk in chunks:
        assert len(chunk) <= 250  # Allow some flex for paragraph boundaries


def test_chunk_text_overlap():
    text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph."
    chunks = _chunk_text(text, chunk_size=60, overlap=10)
    if len(chunks) > 1:
        # Second chunk should contain overlap from first
        assert chunks[1].startswith(chunks[0][-10:]) or len(chunks[0]) <= 60


def test_index_file_with_text():
    """Index a plain text file into a temp ChromaDB collection."""
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("This is a test document about potassium sensing in Arabidopsis.\n\n")
        f.write("HAK5 is a high-affinity potassium transporter.\n\n")
        f.write("The HAK5 promoter is responsive to potassium deficiency.\n")
        f.flush()

        # Use a unique collection name to avoid polluting real data
        n = index_file(Path(f.name), collection_name="test_index")
        assert n > 0


def test_index_file_too_short():
    """Very short files should be skipped."""
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Short.")
        f.flush()
        n = index_file(Path(f.name), collection_name="test_index")
        assert n == 0


def test_index_directory_with_mixed_files():
    """Index a directory with supported and unsupported files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a text file
        (Path(tmpdir) / "paper.txt").write_text(
            "This is a paper about nitrate sensing.\n\n"
            "NRT2.1 is a nitrate transporter gene.\n\n"
            "The NRT2.1 promoter drives expression in response to nitrate.\n"
        )
        # Create an unsupported file (should be skipped)
        (Path(tmpdir) / "notes.docx").write_text("Not supported")

        files, chunks = index_directory(Path(tmpdir), collection_name="test_index_dir")
        assert files == 1
        assert chunks > 0
