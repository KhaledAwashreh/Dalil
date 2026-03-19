"""
Analytics event definitions — structured data objects for every
tracked event in the consultation pipeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsultEvent:
    """Full analytics record for a single /consult request."""

    request_id: str
    raw_query: str
    normalized_query: str = ""
    selected_tools: list[str] = field(default_factory=list)
    retrieval_count: int = 0
    memory_hits: int = 0
    memory_misses: int = 0
    sources_used: list[str] = field(default_factory=list)
    llm_provider: str = ""
    llm_model: str = ""
    response_latency_ms: float = 0.0
    error: str = ""
    vault: str = "default"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "selected_tools": self.selected_tools,
            "retrieval_count": self.retrieval_count,
            "memory_hits": self.memory_hits,
            "memory_misses": self.memory_misses,
            "sources_used": self.sources_used,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "response_latency_ms": self.response_latency_ms,
            "error": self.error,
            "vault": self.vault,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class IngestEvent:
    """Analytics record for an ingestion operation."""

    request_id: str
    source_type: str
    source_uri: str = ""
    cases_created: int = 0
    vault: str = "default"
    latency_ms: float = 0.0
    error: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "cases_created": self.cases_created,
            "vault": self.vault,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "timestamp": self.timestamp,
        }
