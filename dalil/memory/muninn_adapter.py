"""
MuninnDB adapter implementing the MemoryBackend interface.

Ingestion uses MCP (JSON-RPC 2.0 on port 8750) to trigger MuninnDB's
enrichment pipeline (entity extraction, knowledge graph edges).
Retrieval uses the REST API (port 8475) for the 6-phase ACTIVATE pipeline.
"""

from __future__ import annotations

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
                memory: dict[str, Any] = {
                    "concept": case.title[:512],
                    "content": case.to_engram_content(),
                    "tags": case.tags,
                    "confidence": case.confidence,
                }
                if case.summary:
                    memory["summary"] = case.summary
                if case.entities:
                    memory["entities"] = [
                        {"name": e.name, "type": e.type} for e in case.entities
                    ]
                if case.relationships:
                    memory["relationships"] = [
                        {"target_id": r.target_id, "relation": r.relation, "weight": r.weight}
                        for r in case.relationships
                    ]
                memories.append(memory)
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
                "score": act.get("score", 0.0),
                "why": act.get("why", ""),
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

    async def handle_feedback(
        self,
        vault: str,
        query: str,
        results: list[dict],
        comment: str | None = None,
    ) -> list[str]:
        """Send relevance feedback to MuninnDB and link co-relevant cases."""
        v = vault or self.default_vault
        actions: list[str] = []

        # 1. Call muninn_feedback for SGD weight tuning
        feedback_args: dict = {
            "vault": v,
            "query": query,
            "results": [{"id": r["id"], "relevant": r["relevant"]} for r in results],
        }
        if comment:
            feedback_args["comment"] = comment
        try:
            await self._mcp_call("muninn_feedback", feedback_args)
            actions.append(f"sent relevance feedback for {len(results)} cases")
        except Exception as e:
            logger.warning("muninn_feedback failed: %s", e)
            actions.append(f"muninn_feedback failed: {e}")

        # 2. Link co-relevant cases with "supports" relation
        relevant_ids = [r["id"] for r in results if r.get("relevant")]
        if len(relevant_ids) > 1:
            linked = 0
            for i in range(len(relevant_ids) - 1):
                try:
                    await self.link_cases(
                        source_id=relevant_ids[i],
                        target_id=relevant_ids[i + 1],
                        relation="supports",
                        vault=v,
                    )
                    linked += 1
                except Exception as e:
                    logger.warning(
                        "Failed to link %s -> %s: %s",
                        relevant_ids[i], relevant_ids[i + 1], e,
                    )
            if linked:
                actions.append(f"linked {linked} pairs of co-relevant cases")

        return actions

    async def re_activate(
        self, query: str, vault: str = "default", case_ids: list[str] | None = None
    ) -> None:
        """Re-activate cases to boost their temporal priority (legacy)."""
        v = vault or self.default_vault
        if case_ids:
            for cid in case_ids:
                try:
                    await self._mcp_call("muninn_read", {"id": cid, "vault": v})
                except Exception as e:
                    logger.warning("Failed to re-activate %s: %s", cid, e)

    # ── Score explanation (MCP) ────────────────────────────────────

    async def explain_score(self, vault: str, engram_id: str) -> dict | None:
        """Return MuninnDB score breakdown for an engram via muninn_explain."""
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_explain", {
                "vault": v,
                "id": engram_id,
            })
            if isinstance(result, dict):
                return result
            # Handle text-block MCP responses
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            return json.loads(item["text"])
                        except (json.JSONDecodeError, TypeError):
                            pass
            return None
        except Exception as e:
            logger.warning("muninn_explain failed for %s: %s", engram_id, e)
            return None

    # ── Stats (MCP) ──────────────────────────────────────────────────

    async def get_vault_stats(self, vault: str = "default") -> dict[str, Any]:
        """Get vault health metrics via muninn_status MCP tool."""
        v = vault or self.default_vault
        result = await self._mcp_call("muninn_status", {"vault": v})
        if isinstance(result, dict):
            return result
        # Handle text-block responses from MCP
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    try:
                        return json.loads(item["text"])
                    except (json.JSONDecodeError, TypeError):
                        pass
        return {}

    async def get_contradictions(
        self, vault: str = "default", limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get contradiction pairs via muninn_contradictions MCP tool."""
        v = vault or self.default_vault
        result = await self._mcp_call(
            "muninn_contradictions", {"vault": v, "limit": limit},
        )
        if isinstance(result, list):
            return result
        # Handle text-block responses from MCP
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                return content
        return []

    # ── Graph traversal & session continuity (MCP) ──────────────

    async def traverse(
        self,
        vault: str,
        start_id: str,
        max_depth: int = 3,
        relation_filter: list[str] | None = None,
    ) -> dict:
        v = vault or self.default_vault
        args: dict[str, Any] = {
            "vault": v,
            "start_id": start_id,
            "max_depth": max_depth,
        }
        if relation_filter:
            args["relation_filter"] = relation_filter
        try:
            result = await self._mcp_call("muninn_traverse", args)
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as e:
            logger.warning("muninn_traverse failed: %s", e)
            return {}

    async def where_left_off(self, vault: str, limit: int = 5) -> list[dict]:
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_where_left_off", {
                "vault": v,
                "limit": limit,
            })
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning("muninn_where_left_off failed: %s", e)
            return []

    # ── Entity graph (MCP) ─────────────────────────────────────

    async def list_entities(self, vault: str) -> list[dict]:
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_entities", {"vault": v})
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning("muninn_entities failed: %s", e)
            return []

    async def get_entity(self, vault: str, entity_name: str) -> dict | None:
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_entity", {
                "vault": v,
                "entity_name": entity_name,
            })
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as e:
            logger.warning("muninn_entity failed for '%s': %s", entity_name, e)
            return None

    async def get_entity_timeline(self, vault: str, entity_name: str) -> list[dict]:
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_entity_timeline", {
                "vault": v,
                "entity_name": entity_name,
            })
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning("muninn_entity_timeline failed for '%s': %s", entity_name, e)
            return []

    async def find_by_entity(self, vault: str, entity_name: str) -> list[dict]:
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_find_by_entity", {
                "vault": v,
                "entity_name": entity_name,
            })
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning("muninn_find_by_entity failed for '%s': %s", entity_name, e)
            return []

    # ── Guide ─────────────────────────────────────────────────────

    async def get_guide(self, vault: str = "default") -> dict | None:
        """Call muninn_guide to get vault-aware best practices."""
        v = vault or self.default_vault
        try:
            result = await self._mcp_call("muninn_guide", {"vault": v})
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as e:
            logger.warning("muninn_guide call failed for vault '%s': %s", v, e)
            return None

    # ── Evolve, consolidate & state lifecycle (MCP) ─────────────

    async def evolve_case(
        self, vault: str, case_id: str, content: str, concept: str | None = None
    ) -> dict | None:
        v = vault or self.default_vault
        args: dict[str, Any] = {"vault": v, "id": case_id, "content": content}
        if concept is not None:
            args["concept"] = concept
        try:
            result = await self._mcp_call("muninn_evolve", args)
            logger.info("Evolved case %s in vault '%s'", case_id, v)
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as e:
            logger.warning("muninn_evolve failed for %s: %s", case_id, e)
            return None

    async def consolidate_cases(
        self, vault: str, case_ids: list[str], concept: str | None = None
    ) -> dict | None:
        v = vault or self.default_vault
        args: dict[str, Any] = {"vault": v, "ids": case_ids}
        if concept is not None:
            args["concept"] = concept
        try:
            result = await self._mcp_call("muninn_consolidate", args)
            logger.info("Consolidated %d cases in vault '%s'", len(case_ids), v)
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as e:
            logger.warning("muninn_consolidate failed: %s", e)
            return None

    async def set_case_state(
        self, vault: str, case_id: str, state: str
    ) -> bool:
        v = vault or self.default_vault
        try:
            await self._mcp_call("muninn_state", {
                "vault": v,
                "id": case_id,
                "state": state,
            })
            logger.info("Set state of %s to '%s' in vault '%s'", case_id, state, v)
            return True
        except Exception as e:
            logger.warning("muninn_state failed for %s: %s", case_id, e)
            return False

    # ── Vault Management ────────────────────────────────────────────

    def _load_vault_registry(self) -> dict:
        """Load full vault registry from .dalil/vaults.json."""
        for path in _VAULTS_PATHS:
            if path.exists():
                try:
                    return json.loads(path.read_text())
                except (json.JSONDecodeError, KeyError):
                    continue
        return {}

    def _save_vault_registry(self, vaults: dict) -> None:
        """Save vault registry to .dalil/vaults.json."""
        for path in _VAULTS_PATHS:
            # Try to write to the first writable path
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(vaults, indent=2) + "\n")
                logger.debug("Saved vault registry to %s", path)
                return
            except (OSError, IOError):
                continue

    async def list_vaults(self) -> list[str]:
        """List all vaults via MuninnDB MCP."""
        try:
            result = await self._mcp_call("muninn_list_vaults", {})
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                # Handle text-block MCP response
                if "content" in result and isinstance(result["content"], list):
                    vaults = []
                    for item in result["content"]:
                        if isinstance(item, dict) and "text" in item:
                            vaults.extend(item["text"].strip().split("\n"))
                    return [v.strip() for v in vaults if v.strip()]
                return list(result.get("vaults", []))
            return []
        except Exception as e:
            logger.warning("muninn_list_vaults failed: %s", e)
            return []

    async def create_vault(self, vault_name: str, description: str = "") -> dict | None:
        """Create a new vault via MuninnDB MCP."""
        try:
            result = await self._mcp_call("muninn_create_vault", {
                "name": vault_name,
                "description": description,
            })
            logger.info("Created vault '%s'", vault_name)
            return result if isinstance(result, dict) else {"name": vault_name}
        except Exception as e:
            logger.warning("muninn_create_vault failed for '%s': %s", vault_name, e)
            return None

    async def delete_vault(self, vault_name: str, force: bool = False) -> bool:
        """Delete a vault and remove from registry."""
        try:
            args = {"name": vault_name}
            if force:
                args["force"] = True
            await self._mcp_call("muninn_delete_vault", args)
            
            # Remove from vault registry
            vaults = self._load_vault_registry()
            vaults.pop(vault_name, None)
            self._save_vault_registry(vaults)
            
            logger.info("Deleted vault '%s'", vault_name)
            return True
        except Exception as e:
            logger.warning("muninn_delete_vault failed for '%s': %s", vault_name, e)
            return False

    async def clone_vault(self, source: str, dest: str) -> dict | None:
        """Clone a vault and generate API key for the new vault."""
        try:
            result = await self._mcp_call("muninn_clone_vault", {
                "source": source,
                "dest": dest,
            })
            logger.info("Cloned vault '%s' -> '%s'", source, dest)
            return result if isinstance(result, dict) else {"source": source, "dest": dest}
        except Exception as e:
            logger.warning("muninn_clone_vault failed: %s", e)
            return None

    def get_vault_key(self, vault_name: str) -> str | None:
        """Get stored API key for a vault from registry."""
        vaults = self._load_vault_registry()
        if vault_name in vaults and "token" in vaults[vault_name]:
            return vaults[vault_name]["token"]
        return None

    def set_vault_key(self, vault_name: str, token: str) -> bool:
        """Store API key for a vault in registry."""
        try:
            vaults = self._load_vault_registry()
            if vault_name not in vaults:
                vaults[vault_name] = {}
            vaults[vault_name]["token"] = token
            self._save_vault_registry(vaults)
            logger.debug("Stored API key for vault '%s'", vault_name)
            return True
        except Exception as e:
            logger.warning("Failed to store vault key: %s", e)
            return False

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
