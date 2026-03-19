"""
MuninnDB adapter implementing the MemoryBackend interface.

Talks directly to the MuninnDB REST API on port 8475.
Endpoints: POST /api/engrams, POST /api/activate, GET /api/engrams/{id}.
MuninnDB handles embeddings internally.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from dalil.memory.backend import MemoryBackend, RetrievalResult
from dalil.memory.cases_schema import ConsultingCase

logger = logging.getLogger(__name__)


class MuninnBackend(MemoryBackend):
    """MuninnDB-backed memory store using direct REST API calls."""

    def __init__(
        self,
        base_url: str = "http://localhost:8476",
        token: str | None = None,
        default_vault: str = "default",
        timeout: float = 10.0,
    ):
        self.base_url = base_url
        self.rest_url = base_url.replace(":8476", ":8475")
        self.token = token
        self.default_vault = default_vault
        self.timeout = timeout
        self._http: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.rest_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._http

    async def add_case(self, case: ConsultingCase, vault: str = "default") -> str:
        v = vault or self.default_vault
        http = await self._get_http()
        payload = case.to_engram_payload(vault=v)
        resp = await http.post("/api/engrams", json=payload)
        resp.raise_for_status()
        data = resp.json()
        engram_id = data.get("id", str(data))
        logger.info("Stored case '%s' as engram %s in vault '%s'", case.title, engram_id, v)
        return engram_id

    async def add_cases(
        self, cases: list[ConsultingCase], vault: str = "default"
    ) -> list[str]:
        v = vault or self.default_vault
        ids: list[str] = []
        http = await self._get_http()
        # Write one by one with retry on rate limit (429)
        for i, case in enumerate(cases):
            payload = case.to_engram_payload(vault=v)
            for attempt in range(5):
                resp = await http.post("/api/engrams", json=payload)
                if resp.status_code == 429:
                    wait = min(2 ** attempt, 10)
                    logger.warning("Rate limited on case %d, retrying in %ds", i, wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                ids.append(data.get("id", str(data)))
                break
            else:
                resp.raise_for_status()
            if i > 0 and i % 100 == 0:
                logger.info("Ingested %d/%d cases into vault '%s'", i, len(cases), v)
        logger.info("Stored %d cases in vault '%s'", len(ids), v)
        return ids

    async def query_cases(
        self,
        query: str,
        vault: str = "default",
        max_results: int = 10,
        tags: list[str] | None = None,
        threshold: float = 0.1,
    ) -> RetrievalResult:
        v = vault or self.default_vault
        http = await self._get_http()

        payload: dict[str, Any] = {
            "vault": v,
            "context": [query],
            "max_results": max_results,
            "threshold": threshold,
        }

        resp = await http.post("/api/activate", json=payload)
        resp.raise_for_status()
        data = resp.json()

        activations = data if isinstance(data, list) else data.get("activations", [])
        cases: list[ConsultingCase] = []
        scores: list[float] = []

        for act in activations:
            engram_dict = {
                "id": act.get("id", ""),
                "concept": act.get("concept", ""),
                "content": act.get("content", ""),
                "tags": act.get("tags", []),
                "confidence": act.get("confidence", 0.8),
                "entities": act.get("entities", []),
            }
            case = ConsultingCase.from_engram(engram_dict)

            if tags and not any(t in case.tags for t in tags):
                continue

            cases.append(case)
            scores.append(act.get("score", 0.0))

        return RetrievalResult(
            cases=cases,
            scores=scores,
            total_found=data.get("total_found", len(cases)) if isinstance(data, dict) else len(cases),
            latency_ms=data.get("latency_ms", 0.0) if isinstance(data, dict) else 0.0,
        )

    async def get_case(self, case_id: str, vault: str = "default") -> ConsultingCase | None:
        v = vault or self.default_vault
        http = await self._get_http()
        try:
            resp = await http.get(f"/api/engrams/{case_id}", params={"vault": v})
            resp.raise_for_status()
            data = resp.json()
            engram_dict = {
                "id": data.get("id", case_id),
                "concept": data.get("concept", ""),
                "content": data.get("content", ""),
                "tags": data.get("tags", []),
                "confidence": data.get("confidence", 0.8),
                "entities": data.get("entities", []),
            }
            return ConsultingCase.from_engram(engram_dict)
        except Exception as e:
            logger.warning("Failed to read case %s: %s", case_id, e)
            return None

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"{self.rest_url}/api/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._http is not None:
            try:
                await self._http.aclose()
            except Exception:
                pass
            self._http = None
