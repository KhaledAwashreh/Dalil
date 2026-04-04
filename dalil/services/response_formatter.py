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
    score_breakdowns: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Build the structured JSON response for /consult."""
    similar_cases: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    seen_sources: set[str] = set()

    for i, case in enumerate(cases or []):
        case_data = {
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
        }
        
        if case.activate_why:
            case_data["reasoning"] = case.activate_why
        if case.activate_score > 0:
            case_data["cognitive_score"] = round(case.activate_score, 3)
        
        similar_cases.append(case_data)

        source_key = f"{case.source_type.value}:{case.source_uri}"
        if source_key not in seen_sources and case.source_uri:
            seen_sources.add(source_key)
            sources.append({
                "type": case.source_type.value,
                "uri": case.source_uri,
                "title": case.title,
            })

    confidence = 0.0
    if cases and scores:
        confidence = round(
            sum(scores) / len(scores), 2
        )
    elif cases:
        confidence = round(
            sum(c.confidence for c in cases) / len(cases), 2
        )

    # Extract reasoning summary (first paragraph of recommendation)
    reasoning = recommendation.split("\n\n")[0] if recommendation else ""
    if len(reasoning) > 300:
        reasoning = reasoning[:297] + "..."

    result: dict[str, Any] = {
        "request_id": request_id,
        "recommendation": recommendation,
        "similar_cases": similar_cases,
        "sources": sources,
        "tools_used": tools_used or [],
        "confidence": confidence,
        "reasoning_summary": reasoning,
    }
    if score_breakdowns is not None:
        result["score_breakdowns"] = score_breakdowns
    return result
