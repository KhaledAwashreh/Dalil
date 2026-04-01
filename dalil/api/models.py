"""
API request/response models — Pydantic schemas for FastAPI endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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

class FeedbackRequest(BaseModel):
    request_id: str = Field(..., description="The consultation request ID to give feedback on")
    signal: str = Field(..., description="'useful' or 'not_useful'")
    case_ids: list[str] = Field(default_factory=list, description="Specific case IDs (optional, defaults to all cases from the request)")
    comment: str = Field("", description="Optional reason for feedback")


class FeedbackResponse(BaseModel):
    request_id: str
    signal: str
    cases_affected: int
    actions_taken: list[str]


# --- Vault Stats ---

class VaultStatsResponse(BaseModel):
    vault: str
    engram_count: int = 0
    storage_bytes: int = 0
    confidence_distribution: dict = Field(default_factory=dict)
    coherence_scores: dict = Field(default_factory=dict)
    contradiction_count: int = 0
