"""
MuninnBackend — MuninnDB adapter implementing the MemoryBackend interface.

Uses the official muninn-python async SDK (MuninnClient) which talks to
the MuninnDB REST API on port 8476. All MuninnDB-specific logic is
isolated here.

MuninnDB stores memories as "engrams". We map ConsultingCase <-> Engram.
MuninnDB handles embeddings internally (bundled all-MiniLM-L6-v2), so we
do NOT need to compute or supply embeddings on write.
"""

from __future__ import annotations

import logging
from typing import Any

from dalil.memory.backend import MemoryBackend, RetrievalResult
from dalil.memory.cases_schema import ConsultingCase

logger = logging.getLogger(__name__)


class MuninnBackend(MemoryBackend):
    """MuninnDB-backed memory store using the official Python SDK."""

    def __init__(
        self,
        base_url: str = "http://localhost:8476",
        token: str | None = None,
        default_vault: str = "default",
        timeout: float = 10.0,
    ):
        self.base_url = base_url
        self.token = token
        self.default_vault = default_vault
        self.timeout = timeout
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Lazy-init the MuninnClient."""
        if self._client is None:
            try:
                from muninn import MuninnClient
            except ImportError:
                raise ImportError(
                    "muninn-python SDK not installed. "
                    "Install it with: pip install muninn-python"
                )
            self._client = MuninnClient(
                base_url=self.base_url,
                token=self.token or "",
                timeout=self.timeout,
            )
        return self._client

    async def add_case(self, case: ConsultingCase, vault: str = "default") -> str:
        v = vault or self.default_vault
        client = await self._get_client()
        payload = case.to_engram_payload(vault=v)
        resp = await client.write(**payload)
        engram_id = resp.id if hasattr(resp, "id") else str(resp)
        logger.info("Stored case '%s' as engram %s in vault '%s'", case.title, engram_id, v)
        return engram_id

    async def add_cases(
        self, cases: list[ConsultingCase], vault: str = "default"
    ) -> list[str]:
        v = vault or self.default_vault
        ids: list[str] = []
        # MuninnDB batch endpoint supports max 50 per request
        batch_size = 50
        client = await self._get_client()
        for i in range(0, len(cases), batch_size):
            batch = cases[i : i + batch_size]
            payloads = [c.to_engram_payload(vault=v) for c in batch]
            try:
                resp = await client.write_batch(payloads)
                batch_ids = [
                    r.id if hasattr(r, "id") else str(r) for r in resp
                ]
                ids.extend(batch_ids)
            except AttributeError:
                # Fallback: if SDK doesn't expose write_batch, write one by one
                for payload in payloads:
                    r = await client.write(**payload)
                    ids.append(r.id if hasattr(r, "id") else str(r))
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
        client = await self._get_client()

        activate_kwargs: dict[str, Any] = {
            "vault": v,
            "context": [query],
            "max_results": max_results,
            "threshold": threshold,
        }

        resp = await client.activate(**activate_kwargs)

        activations = resp.activations if hasattr(resp, "activations") else []
        cases: list[ConsultingCase] = []
        scores: list[float] = []

        for act in activations:
            engram_dict = {
                "id": act.id if hasattr(act, "id") else "",
                "concept": act.concept if hasattr(act, "concept") else "",
                "content": act.content if hasattr(act, "content") else "",
                "tags": act.tags if hasattr(act, "tags") else [],
                "confidence": act.confidence if hasattr(act, "confidence") else 0.8,
                "entities": act.entities if hasattr(act, "entities") else [],
            }
            case = ConsultingCase.from_engram(engram_dict)

            # Filter by tags if requested
            if tags and not any(t in case.tags for t in tags):
                continue

            cases.append(case)
            scores.append(act.score if hasattr(act, "score") else 0.0)

        return RetrievalResult(
            cases=cases,
            scores=scores,
            total_found=resp.total_found if hasattr(resp, "total_found") else len(cases),
            latency_ms=resp.latency_ms if hasattr(resp, "latency_ms") else 0.0,
        )

    async def get_case(self, case_id: str, vault: str = "default") -> ConsultingCase | None:
        v = vault or self.default_vault
        client = await self._get_client()
        try:
            resp = await client.read(id=case_id, vault=v)
            engram_dict = {
                "id": resp.id if hasattr(resp, "id") else case_id,
                "concept": resp.concept if hasattr(resp, "concept") else "",
                "content": resp.content if hasattr(resp, "content") else "",
                "tags": resp.tags if hasattr(resp, "tags") else [],
                "confidence": resp.confidence if hasattr(resp, "confidence") else 0.8,
                "entities": resp.entities if hasattr(resp, "entities") else [],
            }
            return ConsultingCase.from_engram(engram_dict)
        except Exception as e:
            logger.warning("Failed to read case %s: %s", case_id, e)
            return None

    async def health_check(self) -> bool:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"{self.base_url}/api/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
