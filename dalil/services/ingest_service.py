"""
IngestService — orchestrates ingestion from any source into memory.
"""

from __future__ import annotations

import logging
import time
import uuid

from dalil.analytics.events import IngestEvent
from dalil.analytics.logger import log_ingest_event
from dalil.analytics.metrics import metrics
from dalil.config.settings import Settings
from dalil.memory.backend import MemoryBackend

logger = logging.getLogger(__name__)


class IngestService:
    """Ingests content from various sources and stores as consulting cases."""

    def __init__(self, memory: MemoryBackend, settings: Settings):
        self.memory = memory
        self.settings = settings

    async def ingest_csv(
        self,
        file_path: str,
        vault: str = "default",
        default_tags: list[str] | None = None,
    ) -> dict:
        """Ingest a CSV file into memory."""
        request_id = str(uuid.uuid4())
        start = time.time()

        from dalil.ingestion.csv_loader import load_csv

        cases = load_csv(file_path, default_tags=default_tags)
        ids = await self.memory.add_cases(cases, vault=vault)

        latency = (time.time() - start) * 1000
        metrics.increment("ingested_cases", len(ids))

        log_ingest_event(IngestEvent(
            request_id=request_id,
            source_type="csv",
            source_uri=file_path,
            cases_created=len(ids),
            vault=vault,
            latency_ms=latency,
        ))

        return {
            "request_id": request_id,
            "source_type": "csv",
            "cases_created": len(ids),
            "vault": vault,
        }

    async def ingest_pdf(
        self,
        file_path: str,
        vault: str = "default",
        default_tags: list[str] | None = None,
    ) -> dict:
        """Ingest a PDF file into memory."""
        request_id = str(uuid.uuid4())
        start = time.time()

        from dalil.ingestion.pdf_loader import load_pdf

        cases = load_pdf(
            file_path,
            chunk_size=self.settings.ingestion.chunk_size,
            chunk_overlap=self.settings.ingestion.chunk_overlap,
            default_tags=default_tags,
        )
        ids = await self.memory.add_cases(cases, vault=vault)

        latency = (time.time() - start) * 1000
        metrics.increment("ingested_cases", len(ids))

        log_ingest_event(IngestEvent(
            request_id=request_id,
            source_type="pdf",
            source_uri=file_path,
            cases_created=len(ids),
            vault=vault,
            latency_ms=latency,
        ))

        return {
            "request_id": request_id,
            "source_type": "pdf",
            "cases_created": len(ids),
            "vault": vault,
        }

    async def ingest_confluence(
        self,
        vault: str = "default",
        space_key: str | None = None,
        page_id: str | None = None,
        url: str | None = None,
        limit: int = 25,
        default_tags: list[str] | None = None,
    ) -> dict:
        """Ingest from Confluence — by URL, page ID, or space key."""
        request_id = str(uuid.uuid4())
        start = time.time()

        from dalil.ingestion.confluence_loader import (
            ConfluenceLoader,
            parse_confluence_url,
        )

        # If a URL is provided, parse it to get page_id and base_url
        source_uri = ""
        confluence_base_url = self.settings.ingestion.confluence_base_url
        if url:
            parsed = parse_confluence_url(url)
            page_id = parsed["page_id"]
            confluence_base_url = confluence_base_url or parsed["base_url"]
            source_uri = url

        if not confluence_base_url:
            raise ValueError(
                "No Confluence base URL configured. Provide a full page URL "
                "or set ingestion.confluence_base_url in config."
            )

        loader = ConfluenceLoader(
            base_url=confluence_base_url,
            email=self.settings.ingestion.confluence_email,
            token=self.settings.ingestion.confluence_token,
        )

        if page_id:
            # Single page ingestion
            cases = await loader.load_page(
                page_id=page_id,
                chunk_size=self.settings.ingestion.chunk_size,
                chunk_overlap=self.settings.ingestion.chunk_overlap,
                default_tags=default_tags,
            )
            source_uri = source_uri or f"{self.settings.ingestion.confluence_base_url}/pages/{page_id}"
        elif space_key:
            # Full space ingestion
            cases = await loader.load_space(
                space_key=space_key,
                limit=limit,
                chunk_size=self.settings.ingestion.chunk_size,
                chunk_overlap=self.settings.ingestion.chunk_overlap,
                default_tags=default_tags,
            )
            source_uri = f"{self.settings.ingestion.confluence_base_url}/spaces/{space_key}"
        else:
            raise ValueError("Provide one of: url, page_id, or space_key")

        ids = await self.memory.add_cases(cases, vault=vault)

        latency = (time.time() - start) * 1000
        metrics.increment("ingested_cases", len(ids))

        log_ingest_event(IngestEvent(
            request_id=request_id,
            source_type="confluence",
            source_uri=source_uri,
            cases_created=len(ids),
            vault=vault,
            latency_ms=latency,
        ))

        return {
            "request_id": request_id,
            "source_type": "confluence",
            "cases_created": len(ids),
            "vault": vault,
        }

