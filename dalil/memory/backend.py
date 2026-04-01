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
    async def health_check(self) -> bool:
        """Return True if the backend is reachable and operational."""
        ...

    async def close(self) -> None:
        """Cleanup resources. Override if needed."""
        pass
