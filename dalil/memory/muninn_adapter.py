"""
MuninnDB adapter implementing the MemoryBackend interface.

Ingestion uses MCP (JSON-RPC 2.0 on port 8750) to trigger MuninnDB's
enrichment pipeline (entity extraction, knowledge graph edges).
Retrieval uses the REST API (port 8475) for the 6-phase ACTIVATE pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from dalil.memory.backend import MemoryBackend, RetrievalResult
from dalil.memory.cases_schema import ConsultingCase

logger = logging.getLogger(__name__)

_MCP_BATCH_SIZE = 50  # MuninnDB limit for muninn_remember_batch


def _extract_ids(result: Any) -> list[str]:
    """Extract engram IDs from a muninn_remember_batch MCP response.

    MuninnDB may return:
      - a list of dicts with "id" keys
      - a list of content blocks with "text" containing IDs
      - a dict with "ids" or "content" keys
      - a single string with newline-separated IDs
    """
    ids: list[str] = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                if "id" in item:
                    ids.append(item["id"])
                elif "text" in item:
                    # Text block may contain multiple IDs (newline or comma separated)
                    text = item["text"]
                    for line in text.replace(",", "\n").splitlines():
                        line = line.strip()
                        if line and not line.startswith(("Stored", "OK", "{")):
                            ids.append(line)
            elif isinstance(item, str) and item.strip():
                ids.append(item.strip())
    elif isinstance(result, dict):
        if "ids" in result:
            ids.extend(result["ids"])
        elif "content" in result and isinstance(result["content"], list):
            ids.extend(_extract_ids(result["content"]))
        elif "id" in result:
            ids.append(result["id"])
    elif isinstance(result, str):
        for line in result.splitlines():
            line = line.strip()
            if line:
                ids.append(line)
    return ids
_VAULTS_PATHS = [
    Path(".dalil") / "vaults.json",       # local dev (CWD)
    Path("/app/.dalil") / "vaults.json",  # Docker container mount
]


def _load_vault_keys() -> dict[str, str]:
    """Load vault name -> token mapping from .dalil/vaults.json."""
    for path in _VAULTS_PATHS:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return {name: info["token"] for name, info in data.items() if "token" in info}
            except (json.JSONDecodeError, KeyError):
                continue
    return {}


class MuninnBackend(MemoryBackend):
    """MuninnDB-backed memory store using MCP for writes, REST for reads."""

    def __init__(
        self,
        base_url: str = "http://localhost:8476",
        mcp_url: str = "http://localhost:8750/mcp",
        token: str | None = None,
        default_vault: str = "default",
        timeout: float = 10.0,
    ):
        self.base_url = base_url
        self.rest_url = base_url.replace(":8476", ":8475")
        self.mcp_url = mcp_url
        self.token = token
        self.default_vault = default_vault
        self.timeout = timeout
        self._http: httpx.AsyncClient | None = None
        self._mcp_id = 0
        self._vault_keys = _load_vault_keys()

    def _token_for_vault(self, vault: str | None = None) -> str | None:
        """Resolve the API key for a vault: vault-specific key > global token > None."""
        v = vault or self.default_vault
        return self._vault_keys.get(v) or self.token or None

    def _headers(self, vault: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        token = self._token_for_vault(vault)
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get_http(self, vault: str | None = None) -> httpx.AsyncClient:
        """Get an HTTP client with the right auth for the given vault.

        For vaults using the default token, reuses a persistent client.
        For vaults with their own key, creates a fresh client (caller should
        close it via ``async with`` or ``await client.aclose()`` when done,
        but non-closure is tolerable — httpx cleans up on GC).
        """
        token = self._token_for_vault(vault)
        default_token = self._token_for_vault(self.default_vault)
        if token == default_token:
            if self._http is None or self._http.is_closed:
                self._http = httpx.AsyncClient(
                    base_url=self.rest_url,
                    headers=self._headers(vault),
                    timeout=self.timeout,
                )
            return self._http
        return httpx.AsyncClient(
            base_url=self.rest_url,
            headers=self._headers(vault),
            timeout=self.timeout,
        )

    # ── MCP helper ──────────────────────────────────────────────────

    async def _mcp_call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Send a JSON-RPC 2.0 call to MuninnDB's MCP endpoint."""
        self._mcp_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": self._mcp_id,
        }
        vault = arguments.get("vault")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self.mcp_url,
                json=payload,
                headers=self._headers(vault),
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(
                    f"MCP {tool_name} failed: {data['error'].get('message', data['error'])}"
                )
            return data.get("result")

    # ── Ingestion (MCP) ────────────────────────────────────────────

    async def add_case(self, case: ConsultingCase, vault: str = "default") -> str:
        v = vault or self.default_vault
        args = case.to_mcp_arguments(vault=v)
        result = await self._mcp_call("muninn_remember", args)
        engram_id = ""
        if isinstance(result, dict):
            engram_id = result.get("id", str(result))
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    engram_id = item.get("text", str(result))
                    break
            if not engram_id:
                engram_id = str(result)
        else:
            engram_id = str(result)
        logger.info("Stored case '%s' as engram %s in vault '%s'", case.title, engram_id, v)
        return engram_id

    async def add_cases(
        self, cases: list[ConsultingCase], vault: str = "default"
    ) -> list[str]:
        v = vault or self.default_vault
        ids: list[str] = []

        # Process in batches of 50 using muninn_remember_batch
        for batch_start in range(0, len(cases), _MCP_BATCH_SIZE):
            batch = cases[batch_start : batch_start + _MCP_BATCH_SIZE]
            memories = []
            for case in batch:
                memories.append({
                    "concept": case.title[:512],
                    "content": case.to_engram_content(),
                    "tags": case.tags,
                    "confidence": case.confidence,
                })
            result = await self._mcp_call("muninn_remember_batch", {
                "vault": v,
                "memories": memories,
            })
            logger.debug("muninn_remember_batch raw result: %s", result)
            # Extract IDs from batch result — MCP returns varied formats
            batch_ids = _extract_ids(result)
            if batch_ids:
                ids.extend(batch_ids)
            else:
                # Fallback: assume all memories were stored
                ids.extend([f"batch-{batch_start + i}" for i in range(len(batch))])

            if batch_start > 0 and batch_start % 100 == 0:
                logger.info("Ingested %d/%d cases into vault '%s'", batch_start, len(cases), v)

        logger.info("Stored %d cases in vault '%s'", len(ids), v)
        return ids

    # ── Retrieval (REST) ────────────────────────────────────────────

    async def query_cases(
        self,
        query: str,
        vault: str = "default",
        max_results: int = 10,
        tags: list[str] | None = None,
        threshold: float = 0.1,
        max_hops: int = 2,
    ) -> RetrievalResult:
        v = vault or self.default_vault
        http = await self._get_http(v)

        payload: dict[str, Any] = {
            "vault": v,
            "context": [query],
            "max_results": max_results,
            "threshold": threshold,
            "max_hops": max_hops,
        }
        if tags:
            payload["tags"] = tags

        resp = await http.post("/api/activate", json=payload)
        resp.raise_for_status()
        data = resp.json()

        logger.info("MuninnDB raw response type=%s keys=%s", type(data).__name__, list(data.keys()) if isinstance(data, dict) else "N/A")
        activations = data if isinstance(data, list) else data.get("activations", [])
        logger.info("MuninnDB returned %d activations for vault '%s'", len(activations), v)
        if activations:
            logger.debug("First activation keys: %s", list(activations[0].keys()) if isinstance(activations[0], dict) else type(activations[0]))
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
        http = await self._get_http(v)
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

    # ── Feedback (MCP) ──────────────────────────────────────────────

    async def link_cases(
        self,
        source_id: str,
        target_id: str,
        relation: str = "supports",
        vault: str = "default",
        weight: float = 0.8,
    ) -> None:
        """Create a weighted association between two engrams."""
        v = vault or self.default_vault
        await self._mcp_call("muninn_link", {
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
            "vault": v,
            "weight": weight,
        })
        logger.info("Linked %s -> %s (%s, weight=%.1f)", source_id, target_id, relation, weight)

    async def archive_case(
        self, case_id: str, vault: str = "default", reason: str = ""
    ) -> None:
        """Mark an engram as archived via state transition."""
        v = vault or self.default_vault
        await self._mcp_call("muninn_state", {
            "id": case_id,
            "state": "archived",
            "vault": v,
            "reason": reason or "Marked not useful via feedback",
        })
        logger.info("Archived case %s in vault '%s'", case_id, v)

    async def re_activate(
        self, query: str, vault: str = "default", case_ids: list[str] | None = None
    ) -> None:
        """Re-activate cases to boost their temporal priority."""
        v = vault or self.default_vault
        if case_ids:
            for cid in case_ids:
                try:
                    await self._mcp_call("muninn_read", {"id": cid, "vault": v})
                except Exception as e:
                    logger.warning("Failed to re-activate %s: %s", cid, e)

    # ── Stats (REST + MCP) ──────────────────────────────────────────

    async def get_stats(self, vault: str = "default") -> dict[str, Any]:
        """Get vault statistics from MuninnDB."""
        v = vault or self.default_vault
        http = await self._get_http(v)
        resp = await http.get("/api/stats", params={"vault": v})
        resp.raise_for_status()
        return resp.json()

    async def get_contradictions(self, vault: str = "default") -> list[dict[str, Any]]:
        """Get engrams linked with 'contradicts' relation."""
        v = vault or self.default_vault
        result = await self._mcp_call("muninn_contradictions", {"vault": v})
        if isinstance(result, list):
            return result
        return []

    # ── Lifecycle ───────────────────────────────────────────────────

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
