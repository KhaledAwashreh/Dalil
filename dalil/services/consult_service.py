"""
ConsultService — thin orchestrator for consultation requests.

Plain Python, no workflow engine, no graph library.
Trusts MuninnDB's 6-phase ACTIVATE pipeline for scoring, ranking,
filtering, and deduplication.  Pipeline:

  1. validate request
  2. normalize input
  3. query MuninnDB (ACTIVATE pipeline)
  4. explain scores (<=10 cases)
  5. build prompt
  6. call LLM
  7. format response
  8. log analytics & return
"""

from __future__ import annotations

import logging
import time
import uuid

from dalil.analytics.events import ConsultEvent
from dalil.analytics.logger import log_consult_event
from dalil.analytics.metrics import metrics
from dalil.ingestion.normalizer import normalize_text
from dalil.llm.interface import LLMInterface, NoLLM
from dalil.memory.backend import MemoryBackend
from dalil.services.prompt_builder import build_consult_prompt
from dalil.services.response_formatter import format_response

logger = logging.getLogger(__name__)


class ConsultService:
    """Orchestrates the full consultation pipeline."""

    def __init__(
        self,
        memory: MemoryBackend,
        llm: LLMInterface | None = None,
        default_vault: str = "default",
    ):
        self.memory = memory
        self.llm = llm or NoLLM()
        self.default_vault = default_vault
        # Cache request_id -> (case_ids, vault, query) for feedback lookup
        self._request_cases: dict[str, tuple[list[str], str, str]] = {}

    def get_request_cases(self, request_id: str) -> tuple[list[str], str, str] | None:
        """Look up cached case IDs, vault, and original query for a request."""
        return self._request_cases.get(request_id)

    async def consult(
        self,
        problem: str,
        context: str = "",
        tags: list[str] | None = None,
        vault: str | None = None,
    ) -> dict:
        """Run the full consultation pipeline and return structured JSON."""
        request_id = str(uuid.uuid4())
        start = time.time()
        vault = vault or self.default_vault

        event = ConsultEvent(
            request_id=request_id,
            raw_query=problem,
            vault=vault,
        )

        try:
            # 1. Validate
            if not problem.strip():
                raise ValueError("Problem statement is required")

            # 2. Normalize
            normalized = normalize_text(problem)
            event.normalized_query = normalized
            query_with_context = f"{normalized} {context}".strip()

            # 3. Query MuninnDB (ACTIVATE pipeline)
            cases_result = await self.memory.query_cases(
                query=query_with_context,
                vault=vault,
                max_results=10,
                tags=tags,
            )
            tools_used = ["muninn_memory"]
            event.selected_tools = tools_used
            event.memory_hits = len(cases_result.cases)
            event.retrieval_count = cases_result.total_found
            metrics.increment("memory_queries")
            metrics.increment("memory_hits", len(cases_result.cases))

            ranked = sorted(
                zip(cases_result.cases, cases_result.scores),
                key=lambda x: x[1],
                reverse=True
            )
            cases_result.cases = [c for c, _ in ranked]
            cases_result.scores = [s for _, s in ranked]

            case_ids = [c.id for c in cases_result.cases]
            self._request_cases[request_id] = (case_ids, vault, query_with_context)

            # Track sources
            event.sources_used = list({c.source_type.value for c in cases_result.cases})

            # 4. Gather score explanations (<=10 cases)
            score_breakdowns: dict[str, dict] | None = None
            if cases_result.cases and len(cases_result.cases) <= 10:
                breakdowns: dict[str, dict] = {}
                for case in cases_result.cases:
                    breakdown = await self.memory.explain_score(vault, case.id)
                    if breakdown is not None:
                        breakdowns[case.id] = breakdown
                if breakdowns:
                    score_breakdowns = breakdowns

            # 5-6. Build prompt and call LLM (skipped if no LLM configured)
            event.llm_provider = self.llm.__class__.__name__
            event.llm_model = self.llm.model_name
            recommendation = ""
            if not isinstance(self.llm, NoLLM):
                prompt = build_consult_prompt(
                    problem=problem,
                    context=context,
                    cases=cases_result.cases,
                    tags=tags,
                )
                recommendation = await self.llm.generate(prompt)
                metrics.increment("llm_calls")

            # 7. Format response
            result = format_response(
                request_id=request_id,
                recommendation=recommendation,
                cases=cases_result.cases,
                scores=cases_result.scores,
                tools_used=tools_used,
                score_breakdowns=score_breakdowns,
            )

            # 8. Finalize analytics
            event.response_latency_ms = (time.time() - start) * 1000
            metrics.observe("consult_latency_ms", event.response_latency_ms)
            log_consult_event(event)

            return result

        except Exception as e:
            event.error = str(e)
            event.response_latency_ms = (time.time() - start) * 1000
            log_consult_event(event)
            metrics.increment("consult_errors")
            logger.exception("Consultation failed: %s", e)
            raise
