"""
ConsultService — the main orchestrator for consultation requests.

Plain Python, no workflow engine, no graph library.
Executes a deterministic pipeline:

  1. validate request
  2. normalize input
  3. select tools
  4. retrieve memory and/or structured data
  5. log analytics event
  6. build prompt
  7. call LLM
  8. format response
  9. return structured JSON
"""

from __future__ import annotations

import logging
import time
import uuid

from dalil.analytics.events import ConsultEvent
from dalil.analytics.logger import log_consult_event
from dalil.analytics.metrics import metrics
from dalil.ingestion.normalizer import normalize_text
from dalil.llm.interface import LLMInterface
from dalil.memory.backend import MemoryBackend, RetrievalResult
from dalil.services.prompt_builder import build_consult_prompt
from dalil.services.response_formatter import format_response
from dalil.tools.selector import select_tool

logger = logging.getLogger(__name__)


class ConsultService:
    """Orchestrates the full consultation pipeline."""

    def __init__(
        self,
        memory: MemoryBackend,
        llm: LLMInterface,
        default_vault: str = "default",
    ):
        self.memory = memory
        self.llm = llm
        self.default_vault = default_vault
        # Cache request_id → (case_ids, vault) for feedback lookup
        self._request_cases: dict[str, tuple[list[str], str]] = {}

    def get_request_cases(self, request_id: str) -> tuple[list[str], str] | None:
        """Look up cached case IDs and vault for a request."""
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

            # 3. Select tool
            tool_choice = select_tool(query_with_context)
            tools_used: list[str] = [tool_choice]
            event.selected_tools = [tool_choice]

            # 4. Retrieve from MuninnDB
            cases_result = await self.memory.query_cases(
                query=query_with_context,
                vault=vault,
                max_results=10,
                tags=tags,
            )
            tools_used = ["muninn_memory"]
            event.memory_hits = len(cases_result.cases)
            event.retrieval_count = cases_result.total_found
            metrics.increment("memory_queries")
            metrics.increment("memory_hits", len(cases_result.cases))

            # Cache case IDs for feedback
            case_ids = [c.id for c in cases_result.cases]
            self._request_cases[request_id] = (case_ids, vault)

            # Track sources
            event.sources_used = list({c.source_type.value for c in cases_result.cases})

            # 5. Log analytics (pre-LLM)
            event.llm_provider = self.llm.__class__.__name__
            event.llm_model = self.llm.model_name

            # 6. Build prompt
            prompt = build_consult_prompt(
                problem=problem,
                context=context,
                cases=cases_result.cases,
                tags=tags,
            )

            # 7. Call LLM
            recommendation = await self.llm.generate(prompt)
            metrics.increment("llm_calls")

            # 8. Format response
            result = format_response(
                request_id=request_id,
                recommendation=recommendation,
                cases=cases_result.cases,
                scores=cases_result.scores,
                tools_used=tools_used,
            )

            # 9. Finalize analytics
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
