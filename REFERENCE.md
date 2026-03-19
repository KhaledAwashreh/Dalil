# Dalil — Technology Reference Guide

Everything you need to understand, recreate, and modify the Dalil codebase.

---

## Table of Contents

1. [Python & Language Features](#1-python--language-features)
2. [FastAPI](#2-fastapi)
3. [Pydantic](#3-pydantic)
4. [httpx](#4-httpx)
5. [MuninnDB](#5-muninndb)
6. [LLM Integration (OpenAI-Compatible APIs)](#6-llm-integration-openai-compatible-apis)
7. [Ollama](#7-ollama)
8. [Confluence REST API](#8-confluence-rest-api)
9. [PDF Extraction (pypdf)](#9-pdf-extraction-pypdf)
10. [Uvicorn](#10-uvicorn)
11. [Design Patterns Used](#11-design-patterns-used)
12. [Data Flow & Architecture](#12-data-flow--architecture)
13. [Testing (pytest)](#13-testing-pytest)
14. [File-by-File Walkthrough](#14-file-by-file-walkthrough)
15. [Key Concepts to Internalize](#15-key-concepts-to-internalize)

---

## 1. Python & Language Features

**Version**: 3.10+

Language features used throughout the codebase that you should be comfortable with:

### `from __future__ import annotations`
Enables PEP 604 union syntax (`str | None`) on Python 3.9. Every module imports this. It defers annotation evaluation so `list[str]` and `dict[str, Any]` work as type hints without runtime cost.

### `async` / `await`
The entire application is asynchronous. All service methods, memory operations, and HTTP handlers are `async def`. This is required by FastAPI (which runs on an async event loop via uvicorn).

**What to learn**: Python's `asyncio` module, coroutines, `async with` (context managers), `async for`.

**Key resource**: https://docs.python.org/3/library/asyncio.html

### `@dataclass`
Used in `dalil/analytics/events.py` and `dalil/memory/backend.py` for simple data containers (like `ConsultEvent`, `IngestEvent`, `RetrievalResult`). These auto-generate `__init__`, `__repr__`, etc. from field declarations.

### Type Hints
Used everywhere: `list[str]`, `dict[str, Any]`, `str | None`, `Optional[...]`. Not enforced at runtime — they're for readability and IDE support.

### Context Managers (`@asynccontextmanager`)
The FastAPI application lifecycle (`lifespan` in `main.py`) uses an async context manager to initialize and tear down dependencies (memory backend, LLM, services) on startup/shutdown.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: init dependencies
    yield
    # shutdown: cleanup
```

### Abstract Base Classes (`ABC`, `abstractmethod`)
Used in `dalil/memory/backend.py` and `dalil/llm/interface.py` to define contracts that concrete implementations must fulfill.

---

## 2. FastAPI

**What it is**: A modern async Python web framework for building APIs. It auto-generates OpenAPI (Swagger) docs and validates request/response data via Pydantic.

**How Dalil uses it**: All API endpoints (`/consult`, `/ingest/*`, `/health`) are FastAPI route handlers.

**Key concepts to learn**:

| Concept | Where Used | What It Does |
|---------|-----------|--------------|
| `@app.get()` / `@app.post()` | `main.py` | Declares HTTP routes |
| `response_model=...` | Every endpoint | Auto-validates and serializes responses |
| `File(...)`, `Form(...)` | Upload endpoints | Extracts multipart form data |
| `UploadFile` | `/ingest/*/upload` | Handles file uploads with streaming |
| `HTTPException` | Error paths | Returns HTTP error codes with messages |
| `lifespan` | App initialization | Startup/shutdown lifecycle hook |
| Dependency Injection | Not used yet | FastAPI's DI system (future auth, etc.) |

**Swagger UI**: When the server runs, visit `http://localhost:8000/docs` for interactive API testing.

**Resources**:
- Official tutorial: https://fastapi.tiangolo.com/tutorial/
- Specifically read: First Steps, Path Parameters, Request Body, Response Model, File Uploads, Lifespan Events

---

## 3. Pydantic

**What it is**: Data validation library. FastAPI uses it to parse and validate all request/response JSON.

**How Dalil uses it**:

1. **API models** (`dalil/api/models.py`) — `ConsultRequest`, `ConsultResponse`, `IngestResponse`, etc.
2. **Case schema** (`dalil/memory/cases_schema.py`) — `ConsultingCase` is the core data model

**Key concepts**:

| Concept | Example in Codebase |
|---------|-------------------|
| `BaseModel` | All request/response classes inherit from it |
| Field validation | `problem: str` is required, `context: str = ""` has default |
| `model_dump()` | Converts model to dict (used in `to_engram_payload()`) |
| `model_validate()` | Constructs model from dict (used in `from_engram()`) |
| `Enum` subclasses | `CaseType`, `SourceType` — constrained string values |
| Optional fields | `vault: str = "default"` — defaults if not provided |
| Nested models | `SimilarCase`, `SourceInfo` nested in `ConsultResponse` |

**Pydantic v2** is used (v2.6+). The API changed significantly from v1 — `.dict()` became `.model_dump()`, `.parse_obj()` became `.model_validate()`.

**Resources**:
- Pydantic v2 docs: https://docs.pydantic.dev/latest/
- Migration guide (v1 → v2): https://docs.pydantic.dev/latest/migration/

---

## 4. httpx

**What it is**: An async HTTP client (like `requests` but supports `async`/`await`). Required because all MuninnDB communication is async.

**How Dalil uses it**: `MuninnBackend` (`dalil/memory/muninn_adapter.py`) makes all REST calls to MuninnDB via `httpx.AsyncClient`.

**Key patterns in the codebase**:

```python
# Persistent client (connection pooling)
self._http = httpx.AsyncClient(
    base_url="http://localhost:8475",
    headers={"Content-Type": "application/json"},
    timeout=10.0,
)

# POST request
resp = await self._http.post("/api/engrams", json=payload)
resp.raise_for_status()  # raises on 4xx/5xx
data = resp.json()

# GET request with query params
resp = await self._http.get(f"/api/engrams/{id}", params={"vault": v})

# One-off client (for health checks)
async with httpx.AsyncClient(timeout=5.0) as http:
    resp = await http.get("http://localhost:8475/api/health")
```

**Why httpx instead of `requests`**: `requests` is synchronous and would block the async event loop. `httpx` is the async-native equivalent.

**Why httpx instead of `muninn-python` SDK**: The `muninn-python` PyPI package (v0.2.5) ships broken — metadata only, no actual Python module files. Direct REST calls via httpx work perfectly and give full control.

**Resources**:
- httpx docs: https://www.python-httpx.org/
- Specifically: AsyncClient, Request/Response, Error handling

---

## 5. MuninnDB

**What it is**: A cognitive memory database written in Go. It stores "engrams" (memory units) with built-in embedding generation, semantic search, and graph relationships.

**Why it matters**: MuninnDB is Dalil's **only data store**. Everything — consulting cases, search, retrieval — goes through it.

### Architecture

MuninnDB runs as a single binary exposing multiple ports:

| Port | Service | Used By Dalil |
|------|---------|---------------|
| 8475 | REST API | Yes — all CRUD and search |
| 8476 | Web UI / Dashboard | No (admin use only) |
| 8477 | gRPC | No |
| 8750 | MCP (AI tool integration) | No (used by Claude Code MCP) |

### REST API Endpoints Used

**Store an engram** — `POST /api/engrams`
```json
{
  "vault": "default",
  "concept": "Case title (max 512 bytes)",
  "content": "Full case content with JSON metadata",
  "tags": ["fintech", "churn"],
  "type_label": "engagement",
  "confidence": 0.8,
  "entities": [{"name": "Acme Corp", "type": "company"}]
}
```
Returns: `{"id": "engram-uuid-here"}`

**Semantic search** — `POST /api/activate`
```json
{
  "vault": "default",
  "context": ["What retention strategies work for fintech?"],
  "max_results": 10,
  "threshold": 0.1
}
```
Returns a list of activations (engrams ranked by relevance score). Each activation includes the engram's `id`, `concept`, `content`, `tags`, `score`, `confidence`, `entities`.

**Read single engram** — `GET /api/engrams/{id}?vault=default`

**Health check** — `GET /api/health`

### Vaults

Vaults provide complete data isolation. Think of them as separate databases:

- `"default"` vault is always available without authentication
- Custom vaults require API keys (`mk_...` format) passed as `Authorization: Bearer mk_...`
- Each vault has its own embeddings, indexes, associations

### Embeddings

MuninnDB generates embeddings internally (bundled `all-MiniLM-L6-v2` by default). You do **not** need to compute embeddings in Python — just send text and MuninnDB handles vectorization.

### How Dalil Maps Data to MuninnDB

| ConsultingCase field | MuninnDB Engram field |
|---------------------|----------------------|
| `title` | `concept` |
| Structured fields (problem, solution, outcome, etc.) | `content` (packed as JSON) |
| `tags` | `tags` |
| `type` (engagement, playbook, etc.) | `type_label` |
| `entities` | `entities` |
| `confidence` | `confidence` |

The `to_engram_payload()` method on `ConsultingCase` handles this conversion. On retrieval, `from_engram()` unpacks the JSON content back into structured fields.

**Resources**:
- MuninnDB GitHub: https://github.com/scrypster/muninndb
- REST API: explore via Web UI at `http://localhost:8476` after running `muninn start`

---

## 6. LLM Integration (OpenAI-Compatible APIs)

**What it is**: Dalil talks to language models via the OpenAI chat completions API format. This is a de facto standard — Ollama, vLLM, LM Studio, Together AI, Groq all expose the same interface.

### The API Contract

**Endpoint**: `POST {base_url}/v1/chat/completions`

**Request**:
```json
{
  "model": "mistral",
  "messages": [
    {"role": "system", "content": "You are a consulting advisor..."},
    {"role": "user", "content": "What retention strategies..."}
  ],
  "temperature": 0.3,
  "max_tokens": 2048
}
```

**Response**:
```json
{
  "choices": [
    {
      "message": {
        "content": "Based on similar engagements..."
      }
    }
  ]
}
```

### Anthropic Exception

Claude models use a different API format (`/v1/messages` with `content` blocks instead of `choices`). The `APILLM` class detects Anthropic endpoints and switches formats automatically.

### How Dalil Implements This

- `LLMInterface` (abstract) defines `generate(prompt) -> str`
- `APILLM` implements it for remote APIs (OpenAI-compatible + Anthropic)
- `LocalLLM` implements it for HuggingFace transformers (local GPU)
- `create_llm(settings)` factory picks the right implementation

**The prompt itself** is built by `PromptBuilder.build()` — it assembles the user's question, context, and retrieved consulting cases into a structured prompt that asks the LLM to be an evidence-grounded consulting advisor.

**Resources**:
- OpenAI API reference: https://platform.openai.com/docs/api-reference/chat/create
- This is the format you need to understand — every compatible provider uses it

---

## 7. Ollama

**What it is**: A local LLM inference server. Run open-source models (Mistral, Llama, DeepSeek, etc.) on your own machine.

**How Dalil uses it**: As the default LLM provider. Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`.

**Key commands**:
```bash
ollama pull mistral          # Download a model
ollama list                  # See installed models
ollama run mistral           # Interactive chat (testing)
ollama serve                 # Start the server (usually auto-starts)
```

**Configuration in Dalil**:
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

**Resources**:
- Ollama: https://ollama.com
- Model library: https://ollama.com/library

---

## 8. Confluence REST API

**What it is**: Atlassian's API for reading/writing Confluence wiki pages programmatically.

**How Dalil uses it**: `ConfluenceLoader` (`dalil/ingestion/confluence_loader.py`) fetches pages, converts HTML to text, chunks them, and ingests as consulting cases.

### Authentication

HTTP Basic Auth with email + API token:
```python
auth = (email, api_token)
```
Generate tokens at: https://id.atlassian.com/manage-profile/security/api-tokens

### Endpoints Used

**Get pages in a space** — `GET {base_url}/wiki/api/v2/spaces/{space_id}/pages`
- Query params: `limit`, `body-format=storage`
- Returns list of pages with HTML content

**Get single page** — `GET {base_url}/wiki/api/v2/pages/{page_id}`
- Query params: `body-format=storage`

### HTML to Text

Confluence stores page content as HTML (`storage` format). The loader strips HTML tags using Python's `html.parser` to extract plain text, then normalizes and chunks it.

**Resources**:
- Confluence REST API v2: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- API tokens: https://id.atlassian.com/manage-profile/security/api-tokens

---

## 9. PDF Extraction (pypdf)

**What it is**: A pure-Python library for reading PDF files.

**How Dalil uses it**: `load_pdf()` in `dalil/ingestion/pdf_loader.py` extracts text from each page, normalizes it, then chunks it.

```python
from pypdf import PdfReader

reader = PdfReader(file_path)
for page in reader.pages:
    text += page.extract_text() or ""
```

**Limitation**: Only works on text-based PDFs. Scanned/image PDFs return empty text (would need OCR).

**Resources**:
- pypdf: https://pypdf.readthedocs.io/

---

## 10. Uvicorn

**What it is**: An ASGI server that runs FastAPI applications.

**How to run**:
```bash
uvicorn dalil.api.main:app --host 0.0.0.0 --port 8000
```

Or via the Python entry point:
```bash
python -m dalil
```

**What `dalil.api.main:app` means**: Module path `dalil.api.main`, variable name `app` (the FastAPI instance).

**Resources**:
- Uvicorn: https://www.uvicorn.org/

---

## 11. Design Patterns Used

Understanding these patterns is key to understanding why the code is structured the way it is.

### Abstract Interface + Concrete Implementation (Strategy Pattern)

**Where**: `MemoryBackend` (abstract) → `MuninnBackend` (concrete)
**Where**: `LLMInterface` (abstract) → `APILLM` / `LocalLLM` (concrete)

**Why**: The rest of the application depends on the abstract interface, not the implementation. You could swap MuninnDB for PostgreSQL or swap Ollama for OpenAI without changing any service code.

```
ConsultService → MemoryBackend (abstract)
                      ↓
                MuninnBackend (talks to MuninnDB REST API)
```

### Factory Pattern

**Where**: `create_llm(settings)` in `dalil/llm/factory.py`

**Why**: The caller doesn't need to know which LLM class to instantiate. Pass settings, get back an `LLMInterface`.

### Pipeline Pattern

**Where**: `ConsultService.consult()` in `dalil/services/consult_service.py`

**Flow**: Validate → Normalize → Select Tool → Retrieve Memory → Log Event → Build Prompt → Call LLM → Format Response

Each step is a distinct function call. The pipeline is sequential and deterministic — no branching, no agent loops, no graph execution. This is intentional (see "Why No LangGraph" in README).

### Adapter Pattern

**Where**: `MuninnBackend` adapts MuninnDB's REST API to the `MemoryBackend` interface. `ConsultingCase.to_engram_payload()` / `from_engram()` converts between Dalil's domain model and MuninnDB's data format.

### Singleton Pattern

**Where**: `MetricsCollector` in `dalil/analytics/metrics.py` — thread-safe single instance for collecting counters and histograms.

---

## 12. Data Flow & Architecture

### Consultation Flow (what happens on `POST /consult`)

```
1. FastAPI receives JSON body → validates via ConsultRequest (Pydantic)
2. ConsultService.consult() is called
3. Input normalized (unicode, whitespace cleanup)
4. Tool selector picks "memory" (currently always memory)
5. MuninnBackend.query_cases() → POST /api/activate to MuninnDB
   - MuninnDB generates embedding from query text
   - Returns ranked engrams (consulting cases) by semantic similarity
6. Results filtered by tags if provided
7. Analytics event logged (JSONL + Python logger)
8. PromptBuilder assembles prompt with:
   - System instruction (consulting advisor role)
   - User's problem + context
   - Retrieved cases formatted as evidence
9. APILLM.generate() → POST to LLM API (Ollama/OpenAI/etc.)
10. ResponseFormatter structures the LLM output:
    - Extracts similar cases with scores
    - Gathers sources
    - Calculates confidence score
11. Returns ConsultResponse JSON
```

### Ingestion Flow (what happens on `POST /ingest/*`)

```
1. FastAPI receives request (file path or upload)
2. IngestService calls appropriate loader:
   - CSV: parse rows → map columns to ConsultingCase fields
   - PDF: extract text → chunk → create cases per chunk
   - Confluence: fetch pages via REST API → HTML to text → chunk → create cases
3. Each case goes through enricher:
   - Industry detection (keyword matching)
   - Case type classification
   - Entity extraction (metrics, dollar amounts)
   - Auto-tagging (topic keywords)
4. MuninnBackend.add_cases() stores all cases:
   - Each case converted to engram payload
   - POST /api/engrams one by one
   - Rate limit retry with exponential backoff
5. Analytics event logged
6. Returns IngestResponse with count
```

### Configuration Flow

```
1. config.json loaded by load_settings()
2. Environment variables override specific fields:
   MUNINN_URL → muninn.base_url
   MUNINN_TOKEN → muninn.token
   LLM_API_KEY → llm.api_key
   LLM_BASE_URL → llm.base_url
   LLM_MODEL → llm.model
3. Settings object passed to constructors during lifespan startup
```

---

## 13. Testing (pytest)

**Framework**: pytest + pytest-asyncio

**How to run**:
```bash
pytest dalil/tests/ -v
```

**What's tested** (21 tests, no external services needed):
- Pydantic model validation (request/response schemas)
- ConsultingCase serialization (to_engram_payload / from_engram round-trip)
- CSV loading and field mapping
- PDF chunking logic
- Text normalization
- Tag normalization
- Prompt building with various inputs
- Tool selection routing
- Enricher (industry detection, entity extraction, auto-tagging)
- Analytics event creation

**What's NOT tested** (would need running services):
- MuninnDB integration (actual REST calls)
- LLM integration (actual API calls)
- End-to-end API (full request lifecycle)

**Resources**:
- pytest: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

---

## 14. File-by-File Walkthrough

```
dalil/
├── __main__.py              # Entry point for `python -m dalil`
├── api/
│   ├── main.py              # FastAPI app, lifespan, all route handlers
│   └── models.py            # Pydantic request/response models
├── config/
│   ├── settings.py          # Dataclass settings, JSON loader, env overrides
│   └── config.example.json  # Template config file
├── services/
│   ├── consult_service.py   # Main orchestrator: query → retrieve → LLM → respond
│   ├── ingest_service.py    # Orchestrates CSV/PDF/Confluence ingestion
│   ├── prompt_builder.py    # Assembles LLM prompts from cases + context
│   └── response_formatter.py # Structures LLM output into API response
├── memory/
│   ├── backend.py           # Abstract MemoryBackend interface + RetrievalResult
│   ├── cases_schema.py      # ConsultingCase model (core domain object)
│   └── muninn_adapter.py    # MuninnDB REST API implementation
├── ingestion/
│   ├── normalizer.py        # Unicode/whitespace text normalization
│   ├── chunker.py           # Intelligent text splitting with overlap
│   ├── csv_loader.py        # CSV → ConsultingCase list
│   ├── pdf_loader.py        # PDF → chunked ConsultingCase list
│   ├── confluence_loader.py # Confluence REST API → ConsultingCase list
│   └── enricher.py          # Auto-tagging, industry detection, entity extraction
├── llm/
│   ├── interface.py         # Abstract LLMInterface
│   ├── factory.py           # create_llm() factory function
│   └── api_llm.py           # APILLM (OpenAI-compatible + Anthropic)
├── tools/
│   └── selector.py          # Tool routing (currently stub, returns "memory")
├── analytics/
│   ├── events.py            # ConsultEvent / IngestEvent dataclasses
│   ├── logger.py            # JSONL file logging
│   └── metrics.py           # In-memory counters and histograms
├── tests/                   # 21 unit tests
└── scripts/
    └── bootstrap_muninn.sh  # MuninnDB install + init + start script
```

---

## 15. Key Concepts to Internalize

### 1. The ConsultingCase is the Central Domain Object
Everything revolves around `ConsultingCase`. CSV rows become cases. PDF chunks become cases. Confluence pages become cases. Cases are stored as engrams. Cases are retrieved and fed to the LLM. Understand `cases_schema.py` thoroughly.

### 2. MuninnDB Does the Heavy Lifting
You don't compute embeddings. You don't build search indexes. You don't manage vector similarity. MuninnDB handles all of this internally. You just POST text and GET results.

### 3. The Adapter Isolates the Database
All MuninnDB-specific logic lives in `muninn_adapter.py`. The rest of the app only sees the abstract `MemoryBackend` interface. If you wanted to swap in PostgreSQL + pgvector, you'd write a new adapter — nothing else changes.

### 4. The LLM is Pluggable
Same principle: `LLMInterface` is the contract, `APILLM`/`LocalLLM` are implementations. Swap providers by changing config, not code.

### 5. Ingestion is a Pipeline
Source (CSV/PDF/Confluence) → Load → Normalize → Chunk → Enrich → Store. Each step is a separate function. Adding a new source (e.g., Notion, Google Docs) means writing a new loader — the rest of the pipeline stays the same.

### 6. No Framework Magic
There's no LangChain, no LangGraph, no agent framework. The consultation flow is a sequential function with explicit steps. Each step is a plain Python function call. This makes it easy to debug, test, and modify.

### 7. Confidence Scoring
The confidence score in responses is calculated as: `0.4 * avg_retrieval_score + 0.6 * coverage`. Coverage is `min(cases_found / max_results, 1.0)`. This is a simple heuristic, not a statistical measure.

### 8. Rate Limiting Strategy
When bulk-ingesting into MuninnDB, the adapter retries on HTTP 429 with exponential backoff: wait `2^attempt` seconds (capped at 10s), up to 5 attempts per case.

---

## Learning Path (Recommended Order)

If you're starting from scratch, learn these in order:

1. **Python async** — `async`/`await`, `asyncio` basics
2. **Pydantic v2** — `BaseModel`, validation, serialization
3. **FastAPI** — routes, request models, response models, lifespan
4. **httpx** — async HTTP client (replaces `requests`)
5. **MuninnDB** — install it, use the Web UI, understand engrams and vaults
6. **OpenAI chat completions API format** — the universal LLM interface
7. **Read the code** — start with `cases_schema.py` → `muninn_adapter.py` → `consult_service.py` → `main.py`

With these foundations, you can understand every line in the codebase and extend it in any direction.
