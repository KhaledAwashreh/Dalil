"""
PDF ingestion loader.

Extracts text from PDF files using pypdf, then chunks and enriches
into ConsultingCase objects.
"""

from __future__ import annotations

import logging
from pathlib import Path

from dalil.ingestion.chunker import chunk_text
from dalil.ingestion.normalizer import normalize_tags, normalize_text
from dalil.memory.cases_schema import ConsultingCase, SourceType

logger = logging.getLogger(__name__)


def load_pdf(
    file_path: str | Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    default_tags: list[str] | None = None,
    source_uri: str = "",
) -> list[ConsultingCase]:
    """Extract text from a PDF and return chunked ConsultingCase objects."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf not installed. Install with: pip install pypdf")

    path = Path(file_path)
    source_uri = source_uri or str(path)
    reader = PdfReader(path)

    # Extract all text
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    full_text = normalize_text("\n\n".join(pages_text))

    if not full_text.strip():
        logger.warning("No text extracted from PDF: %s", path)
        return []

    # Chunk the document
    chunks = chunk_text(full_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pdf_title = path.stem.replace("_", " ").replace("-", " ").title()

    cases: list[ConsultingCase] = []
    for i, chunk in enumerate(chunks):
        title = f"{pdf_title} (Part {i + 1}/{len(chunks)})" if len(chunks) > 1 else pdf_title

        case = ConsultingCase(
            title=title,
            content=chunk,
            tags=normalize_tags(default_tags or []),
            source="pdf",
            source_type=SourceType.PDF,
            source_uri=source_uri,
            metadata={"page_count": len(reader.pages), "chunk_index": i},
        )
        cases.append(case)

    logger.info("Loaded %d chunks from PDF: %s", len(cases), path)
    return cases
