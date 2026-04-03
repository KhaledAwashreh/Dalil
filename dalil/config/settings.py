"""
Application settings — loaded from config file and/or environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MuninnSettings:
    base_url: str = "http://localhost:8476"
    mcp_url: str = "http://localhost:8750/mcp"
    token: str = ""
    default_vault: str = "default"
    timeout: float = 60.0


@dataclass
class LLMSettings:
    type: str = "api"  # "api" | "local"
    provider: str = "openai"  # openai, anthropic, ollama, custom
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""  # for ollama, vLLM, LM Studio, etc.
    temperature: float = 0.3
    max_tokens: int = 2048


@dataclass
class IngestionSettings:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    confluence_base_url: str = ""
    confluence_token: str = ""
    confluence_email: str = ""


@dataclass
class EmbeddingSettings:
    enabled: bool = False  # disabled by default — MuninnDB handles embeddings
    model_name: str = "all-MiniLM-L6-v2"


@dataclass
class Settings:
    muninn: MuninnSettings = field(default_factory=MuninnSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    ingestion: IngestionSettings = field(default_factory=IngestionSettings)
    embeddings: EmbeddingSettings = field(default_factory=EmbeddingSettings)
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


def load_settings(config_path: str | None = None) -> Settings:
    """Load settings from a JSON config file, with env var overrides."""
    settings = Settings()

    # Load from config file if provided
    path = config_path or os.environ.get("DALIL_CONFIG")
    if path and Path(path).exists():
        with open(path) as f:
            data = json.load(f)

        if "muninn" in data:
            m = data["muninn"]
            settings.muninn = MuninnSettings(
                base_url=m.get("base_url", settings.muninn.base_url),
                mcp_url=m.get("mcp_url", settings.muninn.mcp_url),
                token=m.get("token", settings.muninn.token),
                default_vault=m.get("default_vault", settings.muninn.default_vault),
                timeout=m.get("timeout", settings.muninn.timeout),
            )
        if "llm" in data:
            ll = data["llm"]
            settings.llm = LLMSettings(
                type=ll.get("type", settings.llm.type),
                provider=ll.get("provider", settings.llm.provider),
                model=ll.get("model", settings.llm.model),
                api_key=ll.get("api_key", settings.llm.api_key),
                base_url=ll.get("base_url", settings.llm.base_url),
                temperature=ll.get("temperature", settings.llm.temperature),
                max_tokens=ll.get("max_tokens", settings.llm.max_tokens),
            )
        if "ingestion" in data:
            ing = data["ingestion"]
            settings.ingestion = IngestionSettings(
                chunk_size=ing.get("chunk_size", settings.ingestion.chunk_size),
                chunk_overlap=ing.get("chunk_overlap", settings.ingestion.chunk_overlap),
                confluence_base_url=ing.get("confluence_base_url", ""),
                confluence_token=ing.get("confluence_token", ""),
                confluence_email=ing.get("confluence_email", ""),
            )
        if "embeddings" in data:
            emb = data["embeddings"]
            settings.embeddings = EmbeddingSettings(
                enabled=emb.get("enabled", settings.embeddings.enabled),
                model_name=emb.get("model_name", settings.embeddings.model_name),
            )

        settings.log_level = data.get("log_level", settings.log_level)
        settings.api_host = data.get("api_host", settings.api_host)
        settings.api_port = data.get("api_port", settings.api_port)

    # Environment variable overrides (highest priority, only if non-empty)
    settings.muninn.base_url = os.environ.get("MUNINN_URL") or settings.muninn.base_url
    settings.muninn.mcp_url = os.environ.get("MUNINN_MCP_URL") or settings.muninn.mcp_url
    settings.muninn.token = os.environ.get("MUNINN_TOKEN") or settings.muninn.token
    settings.llm.api_key = os.environ.get("LLM_API_KEY") or settings.llm.api_key
    settings.llm.base_url = os.environ.get("LLM_BASE_URL") or settings.llm.base_url
    settings.llm.model = os.environ.get("LLM_MODEL") or settings.llm.model

    return settings
