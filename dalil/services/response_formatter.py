"""
Response formatter — structures the LLM output into the API response shape.
"""

from __future__ import annotations

from typing import Any

from dalil.memory.cases_schema import ConsultingCase


def format_response(
    request_id: str,
    recommendation: str,
    cases: list[ConsultingCase] | None = None,
    scores: list[float] | None = None,
    tools_used: list[str] | None = None,
) -> dict[str, Any]:
    """Build the structured JSON response for /consult."""
    similar_cases: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    seen_sources: set[str] = set()

    for i, case in enumerate(cases or []):
        similar_cases.append({
            "id": case.id,
            "title": case.title,
            "type": case.type.value,
            "industry": case.industry,
            "score": (scores[i] if scores and i < len(scores) else 0.0),
            "content": case.content,
            "summary": case.summary,
            "problem": case.problem,
            "solution": case.solution,
            "outcome": case.outcome,
            "context": case.context,
            "tags": case.tags,
            "metadata": case.metadata,
        })

        source_key = f"{case.source_type.value}:{case.source_uri}"
        if source_key not in seen_sources and case.source_uri:
            seen_sources.add(source_key)
            sources.append({
                "type": case.source_type.value,
                "uri": case.source_uri,
                "title": case.title,
            })

    # Simple confidence heuristic: based on number and quality of cases
    confidence = 0.0
    if cases:
        avg_score = sum(scores or [0.0]) / max(len(scores or []), 1)
        coverage = min(len(cases) / 5.0, 1.0)  # 5+ cases = full coverage
        confidence = round(0.4 * avg_score + 0.6 * coverage, 2)

    # Extract reasoning summary (first paragraph of recommendation)
    reasoning = recommendation.split("\n\n")[0] if recommendation else ""
    if len(reasoning) > 300:
        reasoning = reasoning[:297] + "..."

    return {
        "request_id": request_id,
        "recommendation": recommendation,
        "similar_cases": similar_cases,
        "sources": sources,
        "tools_used": tools_used or [],
        "confidence": confidence,
        "reasoning_summary": reasoning,
    }
