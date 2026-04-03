"""
MemoryBackend — abstract interface for consulting case storage.

Every backend (MuninnDB, in-memory stub, future alternatives) implements
this interface so the rest of the codebase never couples to a specific store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from dalil.memory.cases_schema import ConsultingCase


@dataclass
class RetrievalResult:
    """Normalized result from a memory query."""

    cases: list[ConsultingCase]
    scores: list[float] = field(default_factory=list)
    total_found: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryBackend(ABC):
    """Abstract interface that all memory backends must implement."""

    @abstractmethod
    async def add_case(self, case: ConsultingCase, vault: str = "default") -> str:
        """Store a single case. Returns the stored ID."""
        ...

    @abstractmethod
    async def add_cases(
        self, cases: list[ConsultingCase], vault: str = "default"
    ) -> list[str]:
        """Store multiple cases. Returns list of stored IDs."""
        ...

    @abstractmethod
    async def query_cases(
        self,
        query: str,
        vault: str = "default",
        max_results: int = 10,
        tags: list[str] | None = None,
        threshold: float = 0.1,
        max_hops: int = 2,
    ) -> RetrievalResult:
        """Semantic + keyword search for relevant cases with graph traversal."""
        ...

    @abstractmethod
    async def get_case(self, case_id: str, vault: str = "default") -> ConsultingCase | None:
        """Retrieve a single case by ID."""
        ...

    @abstractmethod
    async def handle_feedback(
        self,
        vault: str,
        query: str,
        results: list[dict],
        comment: str | None = None,
    ) -> list[str]:
        """Process relevance feedback for a previous consultation.

        Args:
            vault: The vault that was queried.
            query: The original query from the consultation.
            results: List of dicts with ``id`` (str) and ``relevant`` (bool).
            comment: Optional free-text comment.

        Returns:
            List of action descriptions for the caller.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backend is reachable and operational."""
        ...

    # ── Graph traversal & session continuity ─────────────────────

    @abstractmethod
    async def traverse(
        self,
        vault: str,
        start_id: str,
        max_depth: int = 3,
        relation_filter: list[str] | None = None,
    ) -> dict:
        """BFS graph traversal from a starting engram. Returns connected engrams with paths."""
        ...

    @abstractmethod
    async def where_left_off(self, vault: str, limit: int = 5) -> list[dict]:
        """Return most recently accessed memories for session continuity."""
        ...

    # ── Entity graph ───────────────────────────────────────────

    @abstractmethod
    async def list_entities(self, vault: str) -> list[dict]:
        """List all entities in the vault's entity graph."""
        ...

    @abstractmethod
    async def get_entity(self, vault: str, entity_name: str) -> dict | None:
        """Get details for a specific entity."""
        ...

    @abstractmethod
    async def get_entity_timeline(self, vault: str, entity_name: str) -> list[dict]:
        """Get temporal history of an entity."""
        ...

    @abstractmethod
    async def find_by_entity(self, vault: str, entity_name: str) -> list[dict]:
        """Find all engrams linked to an entity."""
        ...

    # ── Score explanation ──────────────────────────────────────

    async def explain_score(self, vault: str, engram_id: str) -> dict | None:
        """Return MuninnDB score breakdown for an engram, or None on failure."""
        return None

    # ── Misc ───────────────────────────────────────────────────

    @abstractmethod
    async def get_vault_stats(self, vault: str = "default") -> dict[str, Any]:
        """Return vault health metrics (engram count, coherence, storage, etc.)."""
        ...

    @abstractmethod
    async def get_contradictions(
        self, vault: str = "default", limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return contradiction pairs found in the vault."""
        ...

    # ── Evolve, consolidate & state lifecycle ───────────────────

    @abstractmethod
    async def evolve_case(
        self, vault: str, case_id: str, content: str, concept: str | None = None
    ) -> dict | None:
        """Update a case in place, archiving the previous version."""
        ...

    @abstractmethod
    async def consolidate_cases(
        self, vault: str, case_ids: list[str], concept: str | None = None
    ) -> dict | None:
        """Merge multiple cases into one, combining content and associations."""
        ...

    @abstractmethod
    async def set_case_state(
        self, vault: str, case_id: str, state: str
    ) -> bool:
        """Change the lifecycle state of a case. Returns True on success."""
        ...

    async def get_guide(self, vault: str = "default") -> dict | None:
        """Return guide information from the memory backend, or None on failure."""
        return None

    async def close(self) -> None:
        """Cleanup resources. Override if needed."""
        pass
