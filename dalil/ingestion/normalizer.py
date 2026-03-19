"""
Content normalizer — cleans and standardizes raw text from any source.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Clean raw extracted text into a consistent format."""
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Collapse excessive whitespace but preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Remove null bytes and control chars (except newline/tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def normalize_tags(tags: list[str]) -> list[str]:
    """Lowercase, deduplicate, strip whitespace."""
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        t = tag.strip().lower()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result
