"""Tests for ingestion components."""

import io

from dalil.ingestion.chunker import chunk_text
from dalil.ingestion.csv_loader import load_csv
from dalil.ingestion.normalizer import normalize_tags, normalize_text


def test_normalize_text():
    raw = "  Hello   world  \n\n\n\n  foo  "
    result = normalize_text(raw)
    assert "  " not in result.replace("\n\n", "")
    assert "\n\n\n" not in result


def test_normalize_tags():
    tags = ["Fintech", "FINTECH", " churn ", "Churn", "onboarding"]
    result = normalize_tags(tags)
    assert result == ["fintech", "churn", "onboarding"]


def test_chunk_text_short():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_long():
    text = "A" * 500 + "\n\n" + "B" * 500 + "\n\n" + "C" * 500
    chunks = chunk_text(text, chunk_size=600, chunk_overlap=100)
    assert len(chunks) >= 2


def test_csv_loader():
    csv_content = io.StringIO(
        "title,content,tags,industry\n"
        "Test Case,Some content about fintech churn,fintech,fintech\n"
        "Another Case,Healthcare engagement,healthcare,healthcare\n"
    )
    cases = load_csv(csv_content)
    assert len(cases) == 2
    assert cases[0].title == "Test Case"
    assert cases[1].industry == "healthcare"


def test_csv_loader_preserves_source_fields():
    """Source data fields (entities, summary) pass through without heuristic enrichment."""
    csv_content = io.StringIO(
        "title,content,summary,industry\n"
        "Case A,Content about banking,Banking summary,banking\n"
    )
    cases = load_csv(csv_content)
    assert len(cases) == 1
    assert cases[0].summary == "Banking summary"
    assert cases[0].industry == "banking"
    # No heuristic entities should be injected
    assert cases[0].entities == []


def test_csv_loader_default_tags():
    """Default tags are merged with row-level tags."""
    csv_content = io.StringIO(
        "title,content,tags\n"
        "Case,Some content,fintech\n"
    )
    cases = load_csv(csv_content, default_tags=["imported"])
    assert "imported" in cases[0].tags
    assert "fintech" in cases[0].tags


def test_chunk_text_single_char_boundary():
    """Chunk text that has no paragraph or sentence boundaries."""
    text = "x" * 2000
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 4
    # All original content should be recoverable
    assert all(len(c) <= 500 for c in chunks)


def test_normalize_text_empty():
    """Empty and whitespace-only strings normalize to empty."""
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""
    assert normalize_text("\n\n\n") == ""


def test_normalize_tags_empty():
    """Empty and whitespace-only tags are filtered out."""
    assert normalize_tags([]) == []
    assert normalize_tags(["", "  ", "\t"]) == []
