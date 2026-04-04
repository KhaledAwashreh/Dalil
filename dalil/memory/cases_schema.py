"""
Consulting Case schema — the core memory unit of the system.

A ConsultingCase is the normalized, structured representation of any piece
of consulting knowledge (past engagement, lesson learned, metric, playbook
entry, etc.) that gets persisted into MuninnDB as an Engram.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    ENGAGEMENT = "engagement"
    LESSON_LEARNED = "lesson_learned"
    PLAYBOOK = "playbook"
    METRIC = "metric"
    BENCHMARK = "benchmark"
    RECOMMENDATION = "recommendation"
    RISK_ASSESSMENT = "risk_assessment"
    FRAMEWORK = "framework"
    OTHER = "other"


class SourceType(str, Enum):
    CONFLUENCE = "confluence"
    CSV = "csv"
    PDF = "pdf"
    DATABASE = "database"
    MANUAL = "manual"


class Entity(BaseModel):
    name: str
    type: str  # e.g. "person", "company", "technology", "industry"


class Relationship(BaseModel):
    target_id: str
    relation: str  # e.g. "depends_on", "supports", "contradicts"
    weight: float = 0.5


class ConsultingCase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CaseType = CaseType.OTHER
    title: str
    content: str
    summary: str = ""
    context: str = ""
    problem: str = ""
    solution: str = ""
    outcome: str = ""
    tags: list[str] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    industry: str = ""
    client_name: str = ""
    source: str = ""
    source_type: SourceType = SourceType.MANUAL
    source_uri: str = ""
    relationships: list[Relationship] = Field(default_factory=list)
    confidence: float = 0.8
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # G1: Store MuninnDB ACTIVATE response metadata for ranking and explanation
    activate_score: float = 0.0  # Composite score from BM25 + temporal + Hebbian + graph
    activate_why: str = ""  # Score breakdown: "BM25(0.78) + hebbian_boost(0.16) + assoc_depth1(0.06)"

    def get_structured_tags(self) -> list[str]:
        """Generate structured tags for MuninnDB filtering.
        
        Returns tags in format 'key:value' that enable fast pre-filtering
        in ACTIVATE without requiring content parsing.
        """
        structured = list(self.tags)  # Include existing tags
        
        # Add categorical filters
        if self.type != CaseType.OTHER:
            structured.append(f"type:{self.type.value}")
        if self.industry:
            structured.append(f"industry:{self.industry}")
        if self.source_type != SourceType.MANUAL:
            structured.append(f"source:{self.source_type.value}")
        if self.client_name:
            structured.append(f"client:{self.client_name}")
        
        return structured

    def to_engram_content(self) -> str:
        """Serialize case data into engram content string."""
        import json

        case_body: dict[str, Any] = {
            "case_id": self.id,
            "type": self.type.value,
            "summary": self.summary,
            "context": self.context,
            "problem": self.problem,
            "solution": self.solution,
            "outcome": self.outcome,
            "industry": self.industry,
            "client_name": self.client_name,
            "source": self.source,
            "source_type": self.source_type.value,
            "source_uri": self.source_uri,
            "metadata": self.metadata,
        }
        if self.entities:
            case_body["entities"] = [
                {"name": e.name, "type": e.type} for e in self.entities
            ]
        if self.relationships:
            case_body["relationships"] = [
                {"target_id": r.target_id, "relation": r.relation, "weight": r.weight}
                for r in self.relationships
            ]
        return f"{self.content}\n\n---\n{json.dumps(case_body)}"

    def to_mcp_arguments(self, vault: str = "default") -> dict[str, Any]:
        """Convert to MCP muninn_remember arguments.

        Includes inline enrichment fields (summary, entities, relationships)
        when populated, so MuninnDB can skip its own extraction for those.
        Uses structured tags for filtering (industry:fintech, type:engagement, etc.)
        """
        args: dict[str, Any] = {
            "vault": vault,
            "concept": self.title[:512],
            "content": self.to_engram_content()[:16384],
            "tags": self.get_structured_tags(),  # ← G4: Use structured tags instead of raw tags
            "confidence": self.confidence,
        }
        if self.summary:
            args["summary"] = self.summary
        if self.entities:
            args["entities"] = [
                {"name": e.name, "type": e.type} for e in self.entities
            ]
        if self.relationships:
            args["relationships"] = [
                {"target_id": r.target_id, "relation": r.relation, "weight": r.weight}
                for r in self.relationships
            ]
        return args

    def to_engram_payload(self, vault: str = "default") -> dict[str, Any]:
        """Convert to MuninnDB REST engram write payload (legacy)."""
        engram: dict[str, Any] = {
            "vault": vault,
            "concept": self.title[:512],
            "content": self.to_engram_content()[:16384],
            "tags": self.get_structured_tags(),
            "type_label": self.type.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }

        if self.entities:
            engram["entities"] = [
                {"name": e.name, "type": e.type} for e in self.entities
            ]

        if self.relationships:
            engram["relationships"] = [
                {
                    "target_id": r.target_id,
                    "relation": r.relation,
                    "weight": r.weight,
                }
                for r in self.relationships
            ]

        return engram

    @staticmethod
    def from_engram(engram: dict[str, Any]) -> ConsultingCase:
        """Reconstruct a ConsultingCase from a MuninnDB engram response."""
        import json

        content = engram.get("content", "")
        case_body: dict[str, Any] = {}

        # Try to parse structured data from content
        if "\n\n---\n" in content:
            parts = content.split("\n\n---\n", 1)
            raw_content = parts[0]
            try:
                case_body = json.loads(parts[1])
            except (json.JSONDecodeError, IndexError):
                raw_content = content
        else:
            raw_content = content

        entities_raw = engram.get("entities", [])
        entities = [
            Entity(name=e.get("name", ""), type=e.get("type", ""))
            for e in entities_raw
            if isinstance(e, dict)
        ]

        case = ConsultingCase(
            id=case_body.get("case_id", engram.get("id", "")),
            type=CaseType(case_body.get("type", "other")),
            title=engram.get("concept", ""),
            content=raw_content,
            summary=case_body.get("summary", ""),
            context=case_body.get("context", ""),
            problem=case_body.get("problem", ""),
            solution=case_body.get("solution", ""),
            outcome=case_body.get("outcome", ""),
            tags=engram.get("tags", []),
            entities=entities,
            industry=case_body.get("industry", ""),
            client_name=case_body.get("client_name", ""),
            source=case_body.get("source", ""),
            source_type=SourceType(case_body.get("source_type", "manual")),
            source_uri=case_body.get("source_uri", ""),
            confidence=engram.get("confidence", 0.8),
            metadata=case_body.get("metadata", {}),
        )
        
        case.activate_score = engram.get("score", 0.0)
        case.activate_why = engram.get("why", "")
        
        return case
