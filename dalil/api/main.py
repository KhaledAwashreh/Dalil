"""
Dalil — FastAPI application entry point.
"""

from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from dalil.api.models import (
    ConsultRequest,
    ConsultResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    IngestConfluenceRequest,
    IngestCSVRequest,
    IngestPDFRequest,
    IngestResponse,
    VaultStatsResponse,
)
from dalil.config.settings import Settings, load_settings
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

    # Initialize LLM
    llm = create_llm(settings.llm)
    logger.info("LLM configured: %s (%s)", llm.__class__.__name__, llm.model_name)

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
        llm_provider=llm.__class__.__name__,
        llm_model=llm.model_name,
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
    """Provide feedback on a consultation to improve future results."""
    if req.signal not in ("useful", "not_useful"):
        raise HTTPException(status_code=400, detail="signal must be 'useful' or 'not_useful'")

    # Look up case IDs from the consultation
    cached = consult_service.get_request_cases(req.request_id)
    if not cached and not req.case_ids:
        raise HTTPException(
            status_code=404,
            detail="request_id not found in cache and no case_ids provided",
        )

    case_ids = req.case_ids or (cached[0] if cached else [])
    vault = cached[1] if cached else "default"
    actions: list[str] = []

    from dalil.memory.muninn_adapter import MuninnBackend

    if not isinstance(memory, MuninnBackend):
        raise HTTPException(status_code=501, detail="Feedback requires MuninnDB backend")

    if req.signal == "useful":
        # Re-activate cases to boost temporal priority
        await memory.re_activate(query="", vault=vault, case_ids=case_ids)
        actions.append(f"re-activated {len(case_ids)} cases")

        # Link co-useful cases together
        if len(case_ids) > 1:
            for i in range(len(case_ids) - 1):
                try:
                    await memory.link_cases(
                        source_id=case_ids[i],
                        target_id=case_ids[i + 1],
                        relation="supports",
                        vault=vault,
                    )
                except Exception as e:
                    logger.warning("Failed to link %s -> %s: %s", case_ids[i], case_ids[i + 1], e)
            actions.append(f"linked {len(case_ids)} cases with 'supports' relation")

    elif req.signal == "not_useful":
        for cid in case_ids:
            try:
                await memory.archive_case(
                    case_id=cid, vault=vault, reason=req.comment or "Not useful",
                )
            except Exception as e:
                logger.warning("Failed to archive %s: %s", cid, e)
        actions.append(f"archived {len(case_ids)} cases")

    return FeedbackResponse(
        request_id=req.request_id,
        signal=req.signal,
        cases_affected=len(case_ids),
        actions_taken=actions,
    )


@app.get("/vault/stats", response_model=VaultStatsResponse)
async def vault_stats(vault: str = "default"):
    """Get knowledge health metrics for a vault."""
    from dalil.memory.muninn_adapter import MuninnBackend

    if not isinstance(memory, MuninnBackend):
        raise HTTPException(status_code=501, detail="Vault stats requires MuninnDB backend")

    try:
        stats = await memory.get_stats(vault=vault)
        contradiction_count = 0
        try:
            contradictions = await memory.get_contradictions(vault=vault)
            contradiction_count = len(contradictions)
        except Exception:
            pass

        return VaultStatsResponse(
            vault=vault,
            engram_count=stats.get("engram_count", stats.get("count", 0)),
            storage_bytes=stats.get("storage_bytes", 0),
            confidence_distribution=stats.get("confidence_distribution", {}),
            coherence_scores=stats.get("coherence_scores", {}),
            contradiction_count=contradiction_count,
        )
    except Exception as e:
        logger.exception("Failed to get vault stats")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    import uvicorn

    os.environ.setdefault("DALIL_CONFIG", "config.json")
    uvicorn.run("dalil.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()

