"""
API request/response models — Pydantic schemas for FastAPI endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ALLOWED_STATES = (
    "planning", "active", "paused", "blocked",
    "completed", "cancelled", "archived", "soft_deleted",
)


# --- Consult ---

class ConsultRequest(BaseModel):
    problem: str = Field(..., description="The consulting problem or question")
    context: str = Field("", description="Additional context about the client/situation")
    tags: list[str] = Field(default_factory=list, description="Focus area tags")
    vault: str = Field("default", description="Client vault for isolation")


class SimilarCase(BaseModel):
    id: str
    title: str
    type: str
    industry: str
    score: float
    content: str = ""
    summary: str = ""
    problem: str = ""
    solution: str = ""
    outcome: str = ""
    context: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Source(BaseModel):
    type: str
    uri: str
    title: str


class ConsultResponse(BaseModel):
    request_id: str
    recommendation: str
    similar_cases: list[SimilarCase]
    sources: list[Source]
    tools_used: list[str]
    confidence: float
    reasoning_summary: str
    score_breakdowns: dict[str, dict] | None = None


# --- Ingestion ---

class IngestCSVRequest(BaseModel):
    file_path: str
    vault: str = "default"
    tags: list[str] = Field(default_factory=list)


class IngestPDFRequest(BaseModel):
    file_path: str
    vault: str = "default"
    tags: list[str] = Field(default_factory=list)


class IngestConfluenceRequest(BaseModel):
    url: str | None = Field(None, description="Full Confluence page URL")
    page_id: str | None = Field(None, description="Confluence page ID")
    space_key: str | None = Field(None, description="Confluence space key (ingests all pages)")
    vault: str = "default"
    limit: int = 25
    tags: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    request_id: str
    source_type: str
    cases_created: int
    vault: str


class HealthResponse(BaseModel):
    status: str
    muninn_connected: bool
    llm_provider: str
    llm_model: str


# --- Feedback ---

class CaseRelevance(BaseModel):
    """Per-case relevance signal for the new feedback format."""
    case_id: str = Field(..., description="The case/engram ID")
    relevant: bool = Field(..., description="Whether this case was relevant to the query")


class FeedbackRequest(BaseModel):
    request_id: str = Field(..., description="The consultation request ID to give feedback on")
    # New format: per-case relevance signals
    results: list[CaseRelevance] = Field(default_factory=list, description="Per-case relevance signals (preferred)")
    # Legacy format: bulk signal + case_ids
    signal: str = Field("", description="(Legacy) 'useful' or 'not_useful'")
    case_ids: list[str] = Field(default_factory=list, description="(Legacy) Specific case IDs")
    comment: str = Field("", description="Optional reason for feedback")


class FeedbackResponse(BaseModel):
    request_id: str
    cases_affected: int
    actions_taken: list[str]


# --- Vault Stats ---

class VaultStatsResponse(BaseModel):
    vault: str
    engram_count: int = 0
    storage_bytes: int = 0
    coherence_score: float = 0.0
    orphan_ratio: float = 0.0
    duplication_pressure: float = 0.0
    contradiction_count: int = 0
    contradictions: list[dict] = Field(default_factory=list)
    confidence_distribution: dict = Field(default_factory=dict)


# --- Graph Traversal ---

class TraverseRequest(BaseModel):
    start_id: str = Field(..., description="Engram ID to start traversal from")
    max_depth: int = Field(3, description="Maximum BFS depth")
    relation_filter: list[str] | None = Field(None, description="Filter by relation types")
    vault: str = Field("default", description="Vault to traverse")


class TraverseResponse(BaseModel):
    start_id: str
    vault: str
    result: dict = Field(default_factory=dict)


# --- Session Continuity ---

class RecentMemoriesResponse(BaseModel):
    vault: str
    memories: list[dict] = Field(default_factory=list)


# --- Entity Graph ---

class EntityListResponse(BaseModel):
    vault: str
    entities: list[dict] = Field(default_factory=list)


class EntityDetailResponse(BaseModel):
    vault: str
    entity_name: str
    detail: dict | None = None


class EntityTimelineResponse(BaseModel):
    vault: str
    entity_name: str
    timeline: list[dict] = Field(default_factory=list)


class EntityCasesResponse(BaseModel):
    vault: str
    entity_name: str
    cases: list[dict] = Field(default_factory=list)


# --- Evolve ---

class EvolveCaseRequest(BaseModel):
    case_id: str = Field(..., description="The case/engram ID to evolve")
    content: str = Field(..., description="New content for the case")
    concept: str | None = Field(None, description="Optional new title/concept")
    vault: str = Field("default", description="Vault containing the case")


class EvolveCaseResponse(BaseModel):
    case_id: str
    vault: str
    result: dict = Field(default_factory=dict)


# --- Consolidate ---

class ConsolidateCasesRequest(BaseModel):
    case_ids: list[str] = Field(..., description="List of case/engram IDs to merge")
    concept: str | None = Field(None, description="Optional title for the merged result")
    vault: str = Field("default", description="Vault containing the cases")


class ConsolidateCasesResponse(BaseModel):
    vault: str
    merged_id: str
    result: dict = Field(default_factory=dict)


# --- Set State ---

class SetCaseStateRequest(BaseModel):
    case_id: str = Field(..., description="The case/engram ID")
    state: Literal[
        "planning", "active", "paused", "blocked",
        "completed", "cancelled", "archived", "soft_deleted",
    ] = Field(..., description="Target lifecycle state")
    vault: str = Field("default", description="Vault containing the case")


class SetCaseStateResponse(BaseModel):
    case_id: str
    state: str
    success: bool
