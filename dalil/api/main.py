"""
Dalil — FastAPI application entry point.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from dalil.api.models import (
    CloneVaultRequest,
    CloneVaultResponse,
    ConsolidateCasesRequest,
    ConsolidateCasesResponse,
    ConsultRequest,
    ConsultResponse,
    CreateVaultRequest,
    CreateVaultResponse,
    DeleteVaultRequest,
    DeleteVaultResponse,
    EntityCasesResponse,
    EntityDetailResponse,
    EntityListResponse,
    EntityTimelineResponse,
    EvolveCaseRequest,
    EvolveCaseResponse,
    FeedbackRequest,
    FeedbackResponse,
    GetVaultKeyResponse,
    HealthResponse,
    IngestConfluenceRequest,
    IngestCSVRequest,
    IngestPDFRequest,
    IngestResponse,
    ListVaultsResponse,
    RecentMemoriesResponse,
    SetCaseStateRequest,
    SetCaseStateResponse,
    TraverseRequest,
    TraverseResponse,
    VaultStatsResponse,
)
from dalil.config.settings import Settings, load_settings, resolve_muninn_embed_env
from dalil.llm.factory import create_llm
from dalil.llm.interface import LLMInterface
from dalil.memory.backend import MemoryBackend
from dalil.memory.muninn_adapter import MuninnBackend
from dalil.services.consult_service import ConsultService
from dalil.services.ingest_service import IngestService

logger = logging.getLogger(__name__)

# --- Application state (initialized at startup) ---
settings: Settings = None  # type: ignore
memory: MemoryBackend = None  # type: ignore
llm: LLMInterface = None  # type: ignore
consult_service: ConsultService = None  # type: ignore
ingest_service: IngestService = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down application dependencies."""
    global settings, memory, llm, consult_service, ingest_service

    # Load config
    config_path = os.environ.get("DALIL_CONFIG", None)
    settings = load_settings(config_path)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # Initialize memory backend
    memory = MuninnBackend(
        base_url=settings.muninn.base_url,
        mcp_url=settings.muninn.mcp_url,
        token=settings.muninn.token or None,
        default_vault=settings.muninn.default_vault,
        timeout=settings.muninn.timeout,
    )

    # Log embedding provider
    embed_env = resolve_muninn_embed_env(settings)
    if embed_env:
        logger.info("Embedding provider: %s", settings.embeddings.provider)
    else:
        logger.info("No embedding provider configured — MuninnDB will use its default")

    # Initialize LLM (optional — Dalil can run retrieval-only without one)
    llm = None
    if settings.llm and settings.llm.model:
        try:
            llm = create_llm(settings.llm)
            logger.info("LLM configured: %s (%s)", llm.__class__.__name__, llm.model_name)
        except Exception as e:
            logger.warning("LLM init failed — running in retrieval-only mode: %s", e)
    else:
        logger.info("No LLM configured — running in retrieval-only mode")

    # Fetch vault guide (best-effort, non-blocking)
    guide = None
    try:
        guide = await asyncio.wait_for(
            memory.get_guide(settings.muninn.default_vault),
            timeout=5.0,
        )
        if guide:
            logger.info("MuninnDB vault guide for '%s': %s", settings.muninn.default_vault, guide)
        else:
            logger.info("No guide returned for vault '%s'", settings.muninn.default_vault)
    except asyncio.TimeoutError:
        logger.warning("muninn_guide timed out — continuing startup")
    except Exception as e:
        logger.warning("muninn_guide failed — continuing startup: %s", e)
    app.state.vault_guide = guide

    # Initialize services
    consult_service = ConsultService(
        memory=memory,
        llm=llm,
        default_vault=settings.muninn.default_vault,
    )
    ingest_service = IngestService(memory=memory, settings=settings)

    logger.info("Consultant Memory System started")
    yield

    # Cleanup
    await memory.close()
    logger.info("Consultant Memory System stopped")


app = FastAPI(
    title="Dalil",
    description="Knowledge-centric consulting memory system powered by MuninnDB",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health():
    muninn_ok = await memory.health_check()
    return HealthResponse(
        status="ok" if muninn_ok else "degraded",
        muninn_connected=muninn_ok,
        llm_provider=llm.__class__.__name__ if llm else "none",
        llm_model=llm.model_name if llm else "none",
    )


@app.post("/consult", response_model=ConsultResponse)
async def consult(req: ConsultRequest):
    try:
        result = await consult_service.consult(
            problem=req.problem,
            context=req.context,
            tags=req.tags,
            vault=req.vault,
        )
        return ConsultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Consult failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/csv", response_model=IngestResponse)
async def ingest_csv(req: IngestCSVRequest):
    try:
        result = await ingest_service.ingest_csv(
            file_path=req.file_path,
            vault=req.vault,
            default_tags=req.tags or None,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.exception("CSV ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(req: IngestPDFRequest):
    try:
        result = await ingest_service.ingest_pdf(
            file_path=req.file_path,
            vault=req.vault,
            default_tags=req.tags or None,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.exception("PDF ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/csv/upload", response_model=IngestResponse)
async def ingest_csv_upload(
    file: UploadFile = File(...),
    vault: str = Form("default"),
    tags: str = Form(""),
):
    """Ingest a CSV via multipart file upload."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] or None
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        result = await ingest_service.ingest_csv(
            file_path=tmp_path, vault=vault, default_tags=tag_list,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.exception("CSV upload ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/ingest/pdf/upload", response_model=IngestResponse)
async def ingest_pdf_upload(
    file: UploadFile = File(...),
    vault: str = Form("default"),
    tags: str = Form(""),
):
    """Ingest a PDF via multipart file upload."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] or None
    suffix = Path(file.filename or "upload.pdf").suffix or ".pdf"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        result = await ingest_service.ingest_pdf(
            file_path=tmp_path, vault=vault, default_tags=tag_list,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.exception("PDF upload ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/ingest/confluence", response_model=IngestResponse)
async def ingest_confluence(req: IngestConfluenceRequest):
    try:
        result = await ingest_service.ingest_confluence(
            url=req.url,
            page_id=req.page_id,
            space_key=req.space_key,
            vault=req.vault,
            limit=req.limit,
            default_tags=req.tags or None,
        )
        return IngestResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Confluence ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    """Provide feedback on a consultation to improve future results.

    Accepts two formats:
    - New: ``results`` list with per-case ``{case_id, relevant}`` signals.
    - Legacy: ``signal`` ('useful'/'not_useful') + optional ``case_ids``.
    """
    # Look up cached consultation data (case_ids, vault, query)
    cached = consult_service.get_request_cases(req.request_id)

    # Build the per-case relevance list — new format takes priority
    if req.results:
        results = [{"id": r.case_id, "relevant": r.relevant} for r in req.results]
    elif req.signal:
        # Legacy format: convert bulk signal to per-case relevance
        if req.signal not in ("useful", "not_useful"):
            raise HTTPException(status_code=400, detail="signal must be 'useful' or 'not_useful'")
        case_ids = req.case_ids or (cached[0] if cached else [])
        if not case_ids:
            raise HTTPException(
                status_code=404,
                detail="request_id not found in cache and no case_ids provided",
            )
        is_relevant = req.signal == "useful"
        results = [{"id": cid, "relevant": is_relevant} for cid in case_ids]
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'results' (preferred) or 'signal' field",
        )

    vault = cached[1] if cached else "default"
    query = cached[2] if cached else ""

    if not query:
        raise HTTPException(
            status_code=404,
            detail="Original query not found in cache — request_id may have expired",
        )

    # Delegate to the memory backend
    actions = await memory.handle_feedback(
        vault=vault,
        query=query,
        results=results,
        comment=req.comment or None,
    )

    return FeedbackResponse(
        request_id=req.request_id,
        cases_affected=len(results),
        actions_taken=actions,
    )


# --- Case lifecycle (evolve, consolidate, state) ---


@app.put("/cases/{case_id}", response_model=EvolveCaseResponse)
async def evolve_case(case_id: str, req: EvolveCaseRequest):
    """Update a case in place, archiving the previous version."""
    try:
        result = await memory.evolve_case(
            vault=req.vault,
            case_id=case_id,
            content=req.content,
            concept=req.concept,
        )
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to evolve case")
        return EvolveCaseResponse(case_id=case_id, vault=req.vault, result=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("evolve_case failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/consolidate", response_model=ConsolidateCasesResponse)
async def consolidate_cases(req: ConsolidateCasesRequest):
    """Merge multiple cases into one."""
    if len(req.case_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 case_ids required")
    try:
        result = await memory.consolidate_cases(
            vault=req.vault,
            case_ids=req.case_ids,
            concept=req.concept,
        )
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to consolidate cases")
        merged_id = result.get("id", result.get("merged_id", ""))
        return ConsolidateCasesResponse(
            vault=req.vault, merged_id=merged_id, result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("consolidate_cases failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/cases/{case_id}/state", response_model=SetCaseStateResponse)
async def set_case_state(case_id: str, req: SetCaseStateRequest):
    """Change the lifecycle state of a case."""
    try:
        success = await memory.set_case_state(
            vault=req.vault,
            case_id=case_id,
            state=req.state,
        )
        return SetCaseStateResponse(case_id=case_id, state=req.state, success=success)
    except Exception as e:
        logger.exception("set_case_state failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/stats", response_model=VaultStatsResponse)
async def vault_stats(vault: str = "default"):
    """Get knowledge health metrics for a vault."""
    try:
        # Fetch stats and contradictions in parallel (independent calls)
        stats_task = asyncio.create_task(memory.get_vault_stats(vault=vault))
        contradictions_task = asyncio.create_task(
            memory.get_contradictions(vault=vault)
        )

        stats: dict = {}
        contradictions: list[dict] = []

        try:
            stats = await stats_task
        except Exception as e:
            logger.warning("muninn_status unavailable: %s", e)

        try:
            contradictions = await contradictions_task
        except Exception as e:
            logger.warning("muninn_contradictions unavailable: %s", e)

        return VaultStatsResponse(
            vault=vault,
            engram_count=stats.get("engram_count", 0),
            storage_bytes=stats.get("storage_bytes", 0),
            coherence_score=stats.get("coherence_score", 0.0),
            orphan_ratio=stats.get("orphan_ratio", 0.0),
            duplication_pressure=stats.get("duplication_pressure", 0.0),
            contradiction_count=stats.get("contradiction_count", len(contradictions)),
            contradictions=contradictions,
            confidence_distribution=stats.get("confidence_distribution", {}),
        )
    except Exception as e:
        logger.exception("Failed to get vault stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vault/create", response_model=CreateVaultResponse)
async def create_vault(req: CreateVaultRequest):
    """Create a new vault for client/project isolation."""
    try:
        result = await memory.create_vault(
            vault_name=req.name,
            description=req.description,
        )
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create vault '{req.name}'",
            )
        return CreateVaultResponse(
            vault_name=req.name,
            created=True,
            message=f"Vault '{req.name}' created successfully",
            details=result if isinstance(result, dict) else {},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create vault")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/list", response_model=ListVaultsResponse)
async def list_vaults():
    """List all available vaults."""
    try:
        vaults = await memory.list_vaults()
        return ListVaultsResponse(vaults=vaults, count=len(vaults))
    except Exception as e:
        logger.exception("Failed to list vaults")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/vault/{vault_name}", response_model=DeleteVaultResponse)
async def delete_vault(vault_name: str, force: bool = False):
    """Delete a vault and all its memories."""
    try:
        success = await memory.delete_vault(vault_name, force=force)
        return DeleteVaultResponse(
            vault_name=vault_name,
            deleted=success,
            message=f"Vault '{vault_name}' deleted" if success else f"Failed to delete vault '{vault_name}'",
        )
    except Exception as e:
        logger.exception("Failed to delete vault")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vault/clone", response_model=CloneVaultResponse)
async def clone_vault(req: CloneVaultRequest):
    """Clone a vault into a new one."""
    try:
        result = await memory.clone_vault(req.source, req.dest)
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clone vault '{req.source}' to '{req.dest}'",
            )
        return CloneVaultResponse(
            source=req.source,
            dest=req.dest,
            cloned=True,
            message=f"Vault '{req.source}' cloned to '{req.dest}' successfully",
            details=result if isinstance(result, dict) else {},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to clone vault")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/{vault_name}/key", response_model=GetVaultKeyResponse)
async def get_vault_key(vault_name: str):
    """Get the stored API key for a vault."""
    try:
        token = memory.get_vault_key(vault_name)
        if token:
            # Mask the token in response for security
            masked = token[:6] + "..." + token[-4:]
            return GetVaultKeyResponse(
                vault_name=vault_name,
                token=masked,
                found=True,
            )
        return GetVaultKeyResponse(
            vault_name=vault_name,
            found=False,
        )
    except Exception as e:
        logger.exception("Failed to get vault key")
        raise HTTPException(status_code=500, detail=str(e))


# --- Graph Traversal ---


@app.post("/traverse", response_model=TraverseResponse)
async def traverse(req: TraverseRequest):
    """BFS graph traversal from a starting engram."""
    try:
        result = await memory.traverse(
            vault=req.vault,
            start_id=req.start_id,
            max_depth=req.max_depth,
            relation_filter=req.relation_filter,
        )
        return TraverseResponse(start_id=req.start_id, vault=req.vault, result=result)
    except Exception as e:
        logger.exception("Traverse failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Session Continuity ---


@app.get("/session/recent", response_model=RecentMemoriesResponse)
async def session_recent(vault: str = "default", limit: int = 5):
    """Return most recently accessed memories for session continuity."""
    try:
        memories = await memory.where_left_off(vault=vault, limit=limit)
        return RecentMemoriesResponse(vault=vault, memories=memories)
    except Exception as e:
        logger.exception("where_left_off failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Entity Graph ---


@app.get("/vault/entities", response_model=EntityListResponse)
async def list_entities(vault: str = "default"):
    """List all entities in a vault's entity graph."""
    try:
        entities = await memory.list_entities(vault=vault)
        return EntityListResponse(vault=vault, entities=entities)
    except Exception as e:
        logger.exception("list_entities failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/entities/{entity_name}", response_model=EntityDetailResponse)
async def get_entity(entity_name: str, vault: str = "default"):
    """Get details for a specific entity."""
    try:
        detail = await memory.get_entity(vault=vault, entity_name=entity_name)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")
        return EntityDetailResponse(vault=vault, entity_name=entity_name, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_entity failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/entities/{entity_name}/timeline", response_model=EntityTimelineResponse)
async def get_entity_timeline(entity_name: str, vault: str = "default"):
    """Get temporal history of an entity."""
    try:
        timeline = await memory.get_entity_timeline(vault=vault, entity_name=entity_name)
        return EntityTimelineResponse(vault=vault, entity_name=entity_name, timeline=timeline)
    except Exception as e:
        logger.exception("get_entity_timeline failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault/entities/{entity_name}/cases", response_model=EntityCasesResponse)
async def get_entity_cases(entity_name: str, vault: str = "default"):
    """Find all cases/engrams linked to an entity."""
    try:
        cases = await memory.find_by_entity(vault=vault, entity_name=entity_name)
        return EntityCasesResponse(vault=vault, entity_name=entity_name, cases=cases)
    except Exception as e:
        logger.exception("find_by_entity failed")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    import uvicorn

    os.environ.setdefault("DALIL_CONFIG", "config.json")
    uvicorn.run("dalil.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
