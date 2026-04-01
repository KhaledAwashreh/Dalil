"""
Retrieval helpers — thin convenience layer over the MemoryBackend.

Provides query building, tag filtering, and result ranking utilities
that sit between the tool selector and the raw backend.
"""

from __future__ import annotations

from dalil.memory.backend import MemoryBackend, RetrievalResult


async def retrieve_similar_cases(
    backend: MemoryBackend,
    query: str,
    vault: str = "default",
    max_results: int = 10,
    tags: list[str] | None = None,
    threshold: float = 0.1,
    max_hops: int = 2,
) -> RetrievalResult:
    """Standard semantic retrieval from memory backend with graph traversal."""
    return await backend.query_cases(
        query=query,
        vault=vault,
        max_results=max_results,
        tags=tags,
        threshold=threshold,
        max_hops=max_hops,
    )


async def retrieve_by_industry(
    backend: MemoryBackend,
    industry: str,
    query: str,
    vault: str = "default",
    max_results: int = 10,
    max_hops: int = 2,
) -> RetrievalResult:
    """Retrieve cases filtered to a specific industry."""
    result = await backend.query_cases(
        query=query,
        vault=vault,
        max_results=max_results * 2,  # over-fetch to compensate for filtering
        tags=[industry],
        max_hops=max_hops,
    )
    # Post-filter by industry field in case tags aren't sufficient
    filtered_cases = []
    filtered_scores = []
    for case, score in zip(result.cases, result.scores):
        if case.industry.lower() == industry.lower() or industry.lower() in [
            t.lower() for t in case.tags
        ]:
            filtered_cases.append(case)
            filtered_scores.append(score)
        if len(filtered_cases) >= max_results:
            break

    return RetrievalResult(
        cases=filtered_cases,
        scores=filtered_scores,
        total_found=len(filtered_cases),
        latency_ms=result.latency_ms,
    )
