"""
CSV ingestion loader.

Reads a CSV file and converts rows into ConsultingCase objects.
Expects either:
  (a) a CSV with columns matching ConsultingCase fields, or
  (b) a CSV with at least a 'title' and 'content' column

Additional columns are stored in case metadata.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from dalil.ingestion.enricher import enrich
from dalil.ingestion.normalizer import normalize_tags, normalize_text
from dalil.memory.cases_schema import (
    CaseType,
    ConsultingCase,
    SourceType,
)

logger = logging.getLogger(__name__)

# Columns we map directly to ConsultingCase fields
KNOWN_FIELDS = {
    "title", "content", "summary", "context", "problem", "solution",
    "outcome", "industry", "client_name", "tags", "type",
}


def load_csv(
    source: str | Path | io.StringIO,
    source_uri: str = "",
    default_tags: list[str] | None = None,
) -> list[ConsultingCase]:
    """Load consulting cases from a CSV file or string buffer."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        source_uri = source_uri or str(path)
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        reader = csv.DictReader(source)
        rows = list(reader)

    cases: list[ConsultingCase] = []

    for i, row in enumerate(rows):
        title = row.get("title", "").strip()
        content = row.get("content", "").strip()

        if not title and not content:
            logger.debug("Skipping empty row %d", i)
            continue

        if not title:
            title = content[:100] + ("..." if len(content) > 100 else "")

        content = normalize_text(content) if content else title

        # Parse tags from CSV (comma-separated in a single column)
        raw_tags = row.get("tags", "")
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        tags = normalize_tags(tags + (default_tags or []))

        # Enrich
        enrichment = enrich(content, existing_tags=tags, existing_industry=row.get("industry", ""))

        # Collect extra columns as metadata
        metadata = {
            k: str(v) for k, v in row.items()
            if k and k not in KNOWN_FIELDS and v is not None and str(v).strip()
        }

        case_type_str = row.get("type", "")
        try:
            case_type = CaseType(case_type_str) if case_type_str else enrichment["case_type"]
        except ValueError:
            case_type = enrichment["case_type"]

        case = ConsultingCase(
            type=case_type,
            title=title,
            content=content,
            summary=row.get("summary", ""),
            context=row.get("context", ""),
            problem=row.get("problem", ""),
            solution=row.get("solution", ""),
            outcome=row.get("outcome", ""),
            tags=enrichment["tags"],
            entities=enrichment["entities"],
            industry=enrichment["industry"],
            client_name=row.get("client_name", ""),
            source="csv",
            source_type=SourceType.CSV,
            source_uri=source_uri,
            metadata=metadata,
        )
        cases.append(case)

    logger.info("Loaded %d cases from CSV: %s", len(cases), source_uri)
    return cases
