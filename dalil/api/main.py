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
    HealthResponse,
    IngestConfluenceRequest,
    IngestCSVRequest,
    IngestPDFRequest,
    IngestResponse,
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


