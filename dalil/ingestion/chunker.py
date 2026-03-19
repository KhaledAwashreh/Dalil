"""
Content chunker — splits long documents into sized chunks with overlap.
"""

from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks by character count.

    Tries to break on paragraph boundaries first, then sentence boundaries,
    then falls back to hard character splits.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try to find a paragraph break near the end
        para_break = text.rfind("\n\n", start + chunk_size // 2, end)
        if para_break != -1:
            end = para_break + 2
        else:
            # Try sentence boundary
            for sep in (". ", ".\n", "? ", "! "):
                sent_break = text.rfind(sep, start + chunk_size // 2, end)
                if sent_break != -1:
                    end = sent_break + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap if end - chunk_overlap > start else end

    return chunks
