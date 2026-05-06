"""
Confluence ingestion loader.

Fetches pages from Atlassian Confluence via REST API v2, extracts body
content (HTML -> plain text), and converts to ConsultingCase objects.

Supports both API token auth and OAuth Bearer token auth.
"""

from __future__ import annotations

import html
import logging
import re
from urllib.parse import urlparse
from typing import Any, Optional

import httpx

from dalil.ingestion.chunker import chunk_text
from dalil.ingestion.normalizer import normalize_tags, normalize_text
from dalil.memory.cases_schema import ConsultingCase, SourceType

logger = logging.getLogger(__name__)


def _strip_html(raw_html: str) -> str:
    """Crude HTML tag removal. Sufficient for Confluence body content."""
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr|h\d)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return text


def parse_confluence_url(url: str) -> dict[str, str]:
    """Parse a Confluence page URL into its components.

    Supports formats:
      - https://org.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title
      - https://org.atlassian.net/wiki/spaces/SPACE/pages/123456

    Returns dict with keys: base_url, space_key, page_id, title (if present).
    Raises ValueError if the URL doesn't match a known Confluence pattern.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/wiki"

    # Match: /wiki/spaces/SPACE/pages/PAGE_ID/Optional+Title
    match = re.match(
        r"/wiki/spaces/([^/]+)/pages/(\d+)(?:/(.+))?",
        parsed.path,
    )
    if match:
        return {
            "base_url": base_url,
            "space_key": match.group(1),
            "page_id": match.group(2),
            "title": (match.group(3) or "").replace("+", " "),
        }

    raise ValueError(
        f"Could not parse Confluence URL: {url}. "
        "Expected format: https://org.atlassian.net/wiki/spaces/SPACE/pages/PAGE_ID/Title"
    )


class ConfluenceLoader:
    """Loads pages from Confluence REST API.

    Supports both API token auth (email + token) and OAuth Bearer token auth.
    """

    def __init__(
        self,
        base_url: str,
        email: str = "",
        token: str = "",
        oauth_token: Optional[str] = None,
        cloud_id: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.token = token
        self.oauth_token = oauth_token
        self.cloud_id = cloud_id
        self.timeout = timeout

    @property
    def _api_base(self) -> str:
        """API base URL — uses Atlassian cloud proxy for OAuth, direct URL otherwise."""
        if self.oauth_token and self.cloud_id:
            return f"https://api.atlassian.com/ex/confluence/{self.cloud_id}"
        return self.base_url

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers based on configured auth method."""
        if self.oauth_token:
            return {"Authorization": f"Bearer {self.oauth_token}"}
        return {}

    def _get_auth(self):
        """Get auth tuple for httpx if using API token auth."""
        if self.email and self.token and not self.oauth_token:
            return (self.email, self.token)
        return None

    async def fetch_page(self, page_id: str) -> dict[str, Any]:
        """Fetch a single page by ID using v2 API for OAuth, v1 for token auth."""
        headers = self._get_headers()
        auth = self._get_auth()
        async with httpx.AsyncClient(auth=auth, timeout=self.timeout) as client:
            if self.oauth_token and self.cloud_id:
                resp = await client.get(
                    f"{self._api_base}/wiki/api/v2/pages/{page_id}",
                    params={"body-format": "storage"},
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
            else:
                resp = await client.get(
                    f"{self._api_base}/rest/api/content/{page_id}",
                    params={"expand": "body.storage,metadata.labels"},
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()

    async def fetch_page_labels(self, page_id: str) -> list[str]:
        """Fetch labels for a page (v2 only, returns empty for v1)."""
        if not (self.oauth_token and self.cloud_id):
            return []
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self._api_base}/wiki/api/v2/pages/{page_id}/labels",
                headers=headers,
            )
            if resp.is_success:
                return [l.get("name", "") for l in resp.json().get("results", [])]
            return []

    async def load_page(
        self,
        page_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        default_tags: list[str] | None = None,
    ) -> list[ConsultingCase]:
        """Load a single page by ID and convert to ConsultingCase objects."""
        page = await self.fetch_page(page_id)
        labels = await self.fetch_page_labels(page_id)
        return self._page_to_cases(
            page,
            extra_labels=labels,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            default_tags=default_tags,
        )

    async def fetch_pages(self, space_key: str, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch pages from a Confluence space."""
        headers = self._get_headers()
        auth = self._get_auth()
        async with httpx.AsyncClient(auth=auth, timeout=self.timeout) as client:
            if self.oauth_token and self.cloud_id:
                space_resp = await client.get(
                    f"{self._api_base}/wiki/api/v2/spaces",
                    params={"keys": space_key},
                    headers=headers,
                )
                space_resp.raise_for_status()
                spaces = space_resp.json().get("results", [])
                if not spaces:
                    raise ValueError(f"Space '{space_key}' not found")
                space_id = spaces[0]["id"]

                resp = await client.get(
                    f"{self._api_base}/wiki/api/v2/pages",
                    params={"space-id": space_id, "body-format": "storage", "limit": limit},
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
            else:
                resp = await client.get(
                    f"{self._api_base}/rest/api/content",
                    params={
                        "spaceKey": space_key,
                        "type": "page",
                        "expand": "body.storage,metadata.labels",
                        "limit": limit,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json().get("results", [])

    def _page_to_cases(
        self,
        page: dict[str, Any],
        extra_labels: list[str] | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        default_tags: list[str] | None = None,
    ) -> list[ConsultingCase]:
        """Convert a Confluence page dict (v1 or v2 format) into ConsultingCase objects."""
        title = page.get("title", "Untitled")
        page_id = str(page.get("id", ""))

        body_html = page.get("body", {}).get("storage", {}).get("value", "")

        labels = list(extra_labels or [])
        v1_labels = page.get("metadata", {}).get("labels", {}).get("results", [])
        labels.extend(lbl.get("name", "") for lbl in v1_labels)

        raw_text = _strip_html(body_html)
        text = normalize_text(raw_text)

        if not text.strip():
            return []

        source_uri = f"{self.base_url}/pages/{page_id}"

        cases: list[ConsultingCase] = []
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for i, chunk in enumerate(chunks):
            chunk_title = (
                f"{title} (Part {i + 1}/{len(chunks)})" if len(chunks) > 1 else title
            )
            case = ConsultingCase(
                title=chunk_title,
                content=chunk,
                tags=normalize_tags(labels + (default_tags or [])),
                source="confluence",
                source_type=SourceType.CONFLUENCE,
                source_uri=source_uri,
                metadata={
                    "confluence_page_id": page_id,
                    "chunk_index": i,
                },
            )
            cases.append(case)

        return cases

    async def load_space(
        self,
        space_key: str,
        limit: int = 25,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        default_tags: list[str] | None = None,
    ) -> list[ConsultingCase]:
        """Load all pages from a space and convert to ConsultingCase objects."""
        pages = await self.fetch_pages(space_key, limit=limit)
        cases: list[ConsultingCase] = []

        for page in pages:
            page_id = str(page.get("id", ""))
            labels = await self.fetch_page_labels(page_id) if (self.oauth_token and self.cloud_id) else []
            cases.extend(self._page_to_cases(
                page,
                extra_labels=labels,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                default_tags=default_tags,
            ))

        logger.info(
            "Loaded %d cases from Confluence space '%s'", len(cases), space_key
        )
        return cases
