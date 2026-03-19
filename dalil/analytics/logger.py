"""
Analytics logger — structured JSON logging for all pipeline events.

Writes to both the Python logger (structured JSON) and an append-only
local log file for post-hoc analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dalil.analytics.events import ConsultEvent, IngestEvent

logger = logging.getLogger("dalil.analytics")

# Default log file location
_LOG_DIR = Path("logs")
_CONSULT_LOG = _LOG_DIR / "consult_events.jsonl"
_INGEST_LOG = _LOG_DIR / "ingest_events.jsonl"


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_consult_event(event: ConsultEvent) -> None:
    """Log a consultation event."""
    data = event.to_dict()
    logger.info("consult_event: %s", json.dumps(data))

    _ensure_log_dir()
    with open(_CONSULT_LOG, "a") as f:
        f.write(json.dumps(data) + "\n")


def log_ingest_event(event: IngestEvent) -> None:
    """Log an ingestion event."""
    data = event.to_dict()
    logger.info("ingest_event: %s", json.dumps(data))

    _ensure_log_dir()
    with open(_INGEST_LOG, "a") as f:
        f.write(json.dumps(data) + "\n")
