# Dalil — Setup Guide

Step-by-step instructions to get Dalil running from scratch.

## Prerequisites

- **Python 3.10+**
- **MuninnDB** (installed below)
- **An LLM provider** — one of:
  - [Ollama](https://ollama.com) (free, local — recommended for getting started)
  - OpenAI API key
  - Any OpenAI-compatible endpoint (vLLM, LM Studio, Together AI, Groq, etc.)
  - Local HuggingFace model (requires GPU + `transformers` + `torch`)

## Step 1: Install MuninnDB

MuninnDB is a single Go binary with zero dependencies. Pick one method:

### Option A: Install script (macOS / Linux)

```bash
curl -sSL https://muninndb.com/install.sh | sh
```

### Option B: PowerShell (Windows)

```powershell
irm https://muninndb.com/install.ps1 | iex
```

> Requires Visual C++ Redistributable for the bundled embedder.

### Option C: Docker

```bash
docker run -d \
  --name muninndb \
  -p 8474:8474 \
  -p 8475:8475 \
  -p 8476:8476 \
  -p 8477:8477 \
  -p 8750:8750 \
  -v muninndb-data:/data \
  ghcr.io/scrypster/muninndb:latest
```

### Option D: Bootstrap script (included)

```bash
chmod +x dalil/scripts/bootstrap_muninn.sh
./dalil/scripts/bootstrap_muninn.sh
```

This script installs, initializes, and starts MuninnDB in one step.

## Step 2: Initialize and start MuninnDB

Skip this if you used Docker or the bootstrap script.

```bash
# Guided setup — creates admin credentials, auto-detects AI tools
muninn init

# Start the server
muninn start

# Verify it's running
muninn status
```

**Save the admin credentials** shown during `muninn init` — they're displayed once.

After startup, MuninnDB exposes:

| Port | Service |
|------|---------|
| 8475 | REST API |
| 8476 | Web UI / Dashboard |
| 8477 | gRPC |
| 8750 | MCP (for AI tool integration) |

Verify health:

```bash
curl http://localhost:8476/api/health
```

## Step 3: Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, uvicorn, pydantic, httpx, muninn-python SDK, pypdf.

### Optional dependencies

Uncomment in `requirements.txt` if needed:

```bash
# Local embeddings (not needed — MuninnDB handles embeddings)
pip install sentence-transformers

# Local LLM via HuggingFace (requires GPU)
pip install transformers torch
```

## Step 4: Set up your LLM provider

### Ollama (recommended for local development)

```bash
# Install Ollama: https://ollama.com
ollama pull mistral
```

Ollama runs on `http://localhost:11434` and exposes an OpenAI-compatible API at `/v1`.

### OpenAI

Get an API key from https://platform.openai.com/api-keys.

### Other providers

Any service that exposes an OpenAI-compatible `/v1/chat/completions` endpoint works: vLLM, LM Studio, Together AI, Groq, etc. You just need the `base_url`.

## Step 5: Configure

```bash
cp dalil/config/config.example.json config.json
```

Edit `config.json`:

```json
{
  "muninn": {
    "base_url": "http://localhost:8476",
    "token": "",
    "default_vault": "default",
    "timeout": 10.0
  },
  "llm": {
    "type": "api",
    "provider": "ollama",
    "model": "mistral",
    "api_key": "",
    "base_url": "http://localhost:11434/v1",
    "temperature": 0.3,
    "max_tokens": 2048
  },
  "ingestion": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "confluence_base_url": "",
    "confluence_token": "",
    "confluence_email": ""
  },
  "embeddings": {
    "enabled": false,
    "model_name": "all-MiniLM-L6-v2"
  },
  "log_level": "INFO",
  "api_host": "0.0.0.0",
  "api_port": 8000
}
```

### Configuration reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `muninn.base_url` | string | `http://localhost:8476` | MuninnDB REST endpoint |
| `muninn.token` | string | `""` | Vault API key (`mk_...` format). Leave empty for local dev with default vault. |
| `muninn.default_vault` | string | `"default"` | Default vault name for requests that don't specify one |
| `muninn.timeout` | float | `10.0` | Request timeout in seconds |
| `llm.type` | string | `"api"` | `"api"` for remote/Ollama, `"local"` for HuggingFace transformers |
| `llm.provider` | string | `"openai"` | Provider hint: `"ollama"`, `"openai"`, `"anthropic"`, or any string |
| `llm.model` | string | `"gpt-4o"` | Model identifier |
| `llm.api_key` | string | `""` | API key (not needed for Ollama) |
| `llm.base_url` | string | `""` | API base URL. Auto-detected from provider if empty. |
| `llm.temperature` | float | `0.3` | Generation temperature |
| `llm.max_tokens` | int | `2048` | Max output tokens |
| `ingestion.chunk_size` | int | `1000` | Max characters per chunk for PDF/Confluence |
| `ingestion.chunk_overlap` | int | `200` | Overlap between chunks |
| `ingestion.confluence_*` | string | `""` | Confluence connection (base URL, API token, email) |
| `embeddings.enabled` | bool | `false` | Enable optional local SentenceTransformers (MuninnDB handles embeddings by default) |
| `log_level` | string | `"INFO"` | Python log level |

### Environment variable overrides

These take priority over the config file:

| Variable | Overrides |
|----------|-----------|
| `DALIL_CONFIG` | Path to config JSON file |
| `MUNINN_URL` | `muninn.base_url` |
| `MUNINN_TOKEN` | `muninn.token` |
| `LLM_API_KEY` | `llm.api_key` |
| `LLM_BASE_URL` | `llm.base_url` |
| `LLM_MODEL` | `llm.model` |

## Step 6: Run the server

```bash
DALIL_CONFIG=config.json uvicorn dalil.api.main:app --host 0.0.0.0 --port 8000
```

On Windows (cmd):

```cmd
set DALIL_CONFIG=config.json
uvicorn dalil.api.main:app --host 0.0.0.0 --port 8000
```

On Windows (PowerShell):

```powershell
$env:DALIL_CONFIG = "config.json"
uvicorn dalil.api.main:app --host 0.0.0.0 --port 8000
```

Verify the server is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "muninn_connected": true,
  "llm_provider": "APILLM",
  "llm_model": "mistral"
}
```

The interactive API docs are at **http://localhost:8000/docs** (Swagger UI).

## Step 7: Ingest some data

### Ingest a CSV file (server path)

```bash
curl -X POST http://localhost:8000/ingest/csv \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/cases.csv",
    "vault": "client_acme",
    "tags": ["fintech"]
  }'
```

CSV format — at minimum a `title` and `content` column:

```csv
title,content,tags,industry
Fintech Onboarding,Reduced churn 12% via simplified KYC flow,"fintech,onboarding",fintech
SaaS Pricing Review,Restructured pricing tiers to improve retention,"saas,pricing",saas
```

Additional recognized columns: `summary`, `context`, `problem`, `solution`, `outcome`, `client_name`, `type`. Extra columns are stored as metadata.

### Ingest a CSV file (upload)

```bash
curl -X POST http://localhost:8000/ingest/csv/upload \
  -F "file=@cases.csv" \
  -F "vault=client_acme" \
  -F "tags=fintech,onboarding"
```

### Ingest a PDF (server path)

```bash
curl -X POST http://localhost:8000/ingest/pdf \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/report.pdf",
    "vault": "client_acme",
    "tags": ["quarterly_review"]
  }'
```

### Ingest a PDF (upload)

```bash
curl -X POST http://localhost:8000/ingest/pdf/upload \
  -F "file=@report.pdf" \
  -F "vault=client_acme" \
  -F "tags=quarterly_review"
```

### Ingest from Confluence

Requires `confluence_base_url`, `confluence_email`, and `confluence_token` in config.

```bash
curl -X POST http://localhost:8000/ingest/confluence \
  -H "Content-Type: application/json" \
  -d '{
    "space_key": "CONSULTING",
    "vault": "client_acme",
    "limit": 50,
    "tags": ["internal"]
  }'
```

### Ingestion response

All ingestion endpoints return:

```json
{
  "request_id": "a1b2c3d4-...",
  "source_type": "csv",
  "cases_created": 42,
  "vault": "client_acme"
}
```

## Step 8: Query the system

```bash
curl -X POST http://localhost:8000/consult \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "What retention strategies worked for fintech clients with onboarding churn above 15%?",
    "context": "Client is mid-market fintech. Budget is limited.",
    "tags": ["fintech", "churn", "onboarding"],
    "vault": "client_acme"
  }'
```

Response:

```json
{
  "request_id": "a1b2c3d4-...",
  "recommendation": "Based on similar engagements, the most effective retention strategies for mid-market fintech clients with high onboarding churn involve...",
  "similar_cases": [
    {
      "id": "...",
      "title": "Fintech Onboarding Optimization",
      "type": "engagement",
      "industry": "fintech",
      "score": 0.87
    }
  ],
  "sources": [
    {"type": "csv", "uri": "/path/to/cases.csv", "title": "Fintech Onboarding Optimization"}
  ],
  "tools_used": ["muninn_memory"],
  "confidence": 0.72,
  "reasoning_summary": "Based on similar engagements, the most effective retention strategies..."
}
```

## Step 9: Run tests

```bash
pytest dalil/tests/ -v
```

All 21 tests pass without any external services running (tests cover schema, ingestion, prompt building, and tool selection — not MuninnDB or LLM integration).

## Vault Isolation

Each client gets their own MuninnDB vault. Vaults are completely isolated — separate memory, indexes, associations, and coherence metrics.

Pass `vault` on every API call:

```json
{"problem": "...", "vault": "client_acme"}
```

Vaults are **not auto-provisioned** — create them through the MuninnDB admin UI at `http://localhost:8476` or via the MuninnDB admin API before first use.

## LLM Provider Examples

### Ollama (local, free)

```json
{
  "llm": {
    "type": "api",
    "provider": "ollama",
    "model": "mistral",
    "base_url": "http://localhost:11434/v1"
  }
}
```

### OpenAI

```json
{
  "llm": {
    "type": "api",
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "sk-..."
  }
}
```

### Anthropic (Claude)

```json
{
  "llm": {
    "type": "api",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key": "sk-ant-..."
  }
}
```

### vLLM / LM Studio / any OpenAI-compatible

```json
{
  "llm": {
    "type": "api",
    "model": "my-model",
    "base_url": "http://localhost:8000/v1"
  }
}
```

### Local HuggingFace model (offline, requires GPU)

```json
{
  "llm": {
    "type": "local",
    "model": "mistralai/Mistral-7B-Instruct-v0.2"
  }
}
```

Requires: `pip install transformers torch`

## Analytics & Logging

Every request is logged as structured JSON to:

- Python logger (`dalil.analytics`)
- Append-only files in `logs/consult_events.jsonl` and `logs/ingest_events.jsonl`

Each event includes: request ID, raw query, selected tools, retrieval counts, memory hits/misses, sources, LLM provider/model, response latency, and errors.

In-memory metrics (request counts, latencies) are available at runtime and ready for a Prometheus exporter in a future iteration.

## Troubleshooting

### `muninn_connected: false` in /health

MuninnDB isn't running or isn't reachable at the configured URL. Check:

```bash
muninn status
curl http://localhost:8476/api/health
```

### LLM returns empty responses

Check that your LLM provider is running and the model is pulled:

```bash
# Ollama
ollama list
curl http://localhost:11434/v1/models
```

### Import errors for muninn-python

```bash
pip install muninn-python
```

### PDF ingestion returns 0 cases

The PDF may be image-based (scanned). `pypdf` only extracts text-based PDFs. For scanned documents, you'd need OCR (not included in this MVP).
