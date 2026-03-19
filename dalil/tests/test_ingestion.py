"""Tests for ingestion components."""

import io

from dalil.ingestion.chunker import chunk_text
from dalil.ingestion.csv_loader import load_csv
from dalil.ingestion.enricher import auto_tag, detect_industry, enrich
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


def test_detect_industry():
    assert detect_industry("Our fintech client needed...") == "fintech"
    assert detect_industry("Healthcare provider...") == "healthcare"
    assert detect_industry("Generic text") == ""


def test_auto_tag():
    tags = auto_tag("The client faced high churn rates and needed a retention strategy.")
    assert "churn" in tags
    assert "retention" in tags


def test_enrich():
    result = enrich("Fintech company saw 15% churn reduction after onboarding changes.")
    assert result["industry"] == "fintech"
    assert "churn" in result["tags"]
    assert "onboarding" in result["tags"]


def test_csv_loader():
    csv_content = io.StringIO(
        "title,content,tags,industry\n"
        "Test Case,Some content about fintech churn,fintech;churn,fintech\n"
        "Another Case,Healthcare engagement,healthcare,healthcare\n"
    )
    cases = load_csv(csv_content)
    assert len(cases) == 2
    assert cases[0].title == "Test Case"
    assert cases[1].industry == "healthcare"
