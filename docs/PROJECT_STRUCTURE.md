# Project Structure

## Directory Layout

```
dalil/                    # Main package
├── __main__.py          # CLI entry point
├── __init__.py
├── cli.py               # Command-line interface
│
├── api/                 # REST API (FastAPI)
│   ├── main.py         # Endpoints: health, consult, feedback, ingest, entities, traversal
│   └── models.py       # Pydantic models for request/response
│
├── services/           # Business logic layer
│   ├── consult_service.py       # Consultation orchestration
│   ├── ingest_service.py        # Ingestion orchestration
│   ├── prompt_builder.py        # LLM prompt construction
│   ├── response_formatter.py    # Response formatting
│   └── __init__.py
│
├── ingestion/          # Loaders for data sources
│   ├── chunker.py               # Text chunking (PDF, Confluence)
│   ├── normalizer.py            # Case normalization
│   ├── csv_loader.py            # CSV ingestion
│   ├── pdf_loader.py            # PDF ingestion
│   ├── confluence_loader.py     # Confluence ingestion
│   └── __init__.py
│
├── memory/             # MuninnDB integration
│   ├── muninn_adapter.py        # MuninnDB REST/MCP client
│   ├── backend.py               # Vault storage abstraction
│   ├── cases_schema.py          # ConsultingCase dataclass
│   └── __init__.py
│
├── llm/                # LLM providers
│   ├── factory.py               # Provider factory pattern
│   ├── interface.py             # LLM interface (abstract)
│   ├── api_llm.py               # API-based providers (OpenAI, Anthropic, etc.)
│   ├── local_llm.py             # Local providers (Ollama)
│   └── __init__.py
│
├── config/             # Configuration management
│   ├── settings.py              # Settings dataclass, env vars
│   └── __init__.py
│
├── analytics/          # Logging & observability
│   ├── events.py                # Event types (ConsultEvent, IngestEvent)
│   ├── logger.py                # Event logger
│   ├── metrics.py               # Metrics collection
│   └── __init__.py
│
├── scripts/
│   └── bootstrap_muninn.sh       # MuninnDB setup (vaults, initial data)
│
└── tests/              # Unit tests (pytest)
    ├── test_ingestion.py
    ├── test_prompt_builder.py
    ├── test_response_formatter.py
    ├── test_cases_schema.py
    └── __init__.py

config.json                     # Active config (copy from template)
dalil/config/config.example.json # Config template

docs/                   # Documentation (this directory)
├── ARCHITECTURE.md           # MuninnDB integration, data model
├── CONFIGURATION.md          # config.json schema, providers
├── LLM_PROVIDERS.md          # LLM/embedding setup
├── API_REFERENCE.md          # Full endpoint reference
├── PROJECT_STRUCTURE.md      # This file
└── DEVELOPMENT.md            # Roadmap, limitations, development notes

scripts/                # External scripts
└── muninndb-entrypoint.sh # Docker entrypoint for MuninnDB

.dalil/                 # Local vault storage (Git-ignored)
└── vaults.json        # Vault registry + keys

.env                    # Environment variables (Git-ignored)
Dockerfile              # Multi-stage build for Dalil API
docker-compose.yml      # MuninnDB + Dalil API containers
pyproject.toml          # Poetry dependencies & metadata
requirements.txt        # pip dependencies (fall-back)
SETUP.md               # Installation & quick-start guide
README.md              # Project overview (condensed)
```

---

## Key Modules

### API Layer (`dalil/api/`)

**main.py**
- FastAPI application with 18 REST endpoints
- Middleware for logging, error handling
- Startup/shutdown hooks for MuninnDB health checks

**models.py**
- Pydantic models for all request/response payloads
- Validation, type hints, documentation strings

### Business Logic (`dalil/services/`)

**consult_service.py**
- Orchestrates consultation pipeline
- Validates vault, queries MuninnDB, formats results
- Optional LLM synthesis if configured

**ingest_service.py**
- Orchestrates ingestion from CSV, PDF, Confluence
- Normalizes data into `ConsultingCase` objects
- Sends to MuninnDB for enrichment and storage

**prompt_builder.py**
- Constructs LLM prompts from retrieved cases + original query
- Handles context windows, truncation, formatting

**response_formatter.py**
- Formats MuninnDB results and LLM synthesis into client-friendly JSON
- Handles confidence scoring, metadata, timestamps

### Memory Layer (`dalil/memory/`)

**muninn_adapter.py**
- HTTP client to MuninnDB (REST + MCP endpoints)
- Wraps MuninnDB tools: `muninn_remember`, `muninn_recall`, `muninn_feedback`, etc.
- Handles failover, retries, error parsing

**cases_schema.py**
- `ConsultingCase` dataclass — the universal case schema
- Supports consulting engagements, playbooks, lessons learned, how-to guides, etc.
- Structured + unstructured fields for flexibility

**backend.py**
- Vault storage abstraction layer
- Tracks vault metadata and access

### Ingestion Layer (`dalil/ingestion/`)

**csv_loader.py**, **pdf_loader.py**, **confluence_loader.py**
- Source-specific loaders
- Extract raw data from each source

**normalizer.py**
- Transform raw data into `ConsultingCase` objects
- Standarize fields, entity extraction, relationship inference

**chunker.py**
- Split long documents into properly-sized chunks
- Preserve semantic boundaries, handle overlap

### LLM Layer (`dalil/llm/`)

**interface.py**
- Abstract `LLMProvider` interface

**factory.py**
- Factory pattern: instantiate the right provider from `config.json`

**api_llm.py**
- OpenAI API, Anthropic API, DeepSeek, Cohere, Azure, etc.

**local_llm.py**
- Ollama (local LLM with HTTP fallback)

---

## Configuration Files

### `config.json`

Required at startup. Schema:

```json
{
  "muninn": {
    "base_url": "http://localhost:8475",
    "mcp_url": "http://localhost:8750/mcp",
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
    "chunk_overlap": 200
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

See [CONFIGURATION.md](CONFIGURATION.md) for full reference.

### `.env`

Store API keys (Git-ignored):

```bash
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

Automatically loaded by `dalil/config/settings.py`.

### `docker-compose.yml`

Defines MuninnDB + Dalil API services.
- MuninnDB: port 8475 (REST), 8476 (Web UI), 8477 (gRPC), 8750 (MCP)
- Dalil API: port 8000

---

## Entry Points

### CLI

```bash
python -m dalil --help
python -m dalil vault create myproject
python -m dalil vault list
```

See `dalil/cli.py` for commands.

### API Server

```bash
python -m dalil serve  # Starts FastAPI on 0.0.0.0:8000
```

Or via Docker:

```bash
docker compose up
```

---

## Testing

Unit tests in `dalil/tests/`:

```bash
pytest dalil/tests/
```

**Coverage:**
- Ingestion (CSV parsing, normalization)
- Prompt building (context windows, formatting)
- Response formatting (error handling, timestamps)
- Data schema validation

**Note:** Test suite does NOT require external services (MuninnDB, LLM API). Mocked where necessary.

---

## Dependencies

See `pyproject.toml` for the full list. Key dependencies:

- **fastapi**: REST framework
- **pydantic**: Data validation
- **httpx**: HTTP client
- **python-dotenv**: Environment variable loader
- **requests**: HTTP library
- **pypdf**: PDF parsing
- **python-multipart**: File upload handling
- **ollama**: Local LLM client
- Additional provider SDKs (openai, anthropic, etc.)

---

## Development Workflow

1. **Install**: `poetry install` or `pip install -r requirements.txt`
2. **Configure**: Copy `dalil/config/config.example.json` to `config.json`, edit for your environment
3. **Set environment variables**: Create `.env` with API keys
4. **Run tests**: `pytest dalil/tests/`
5. **Start MuninnDB**: `docker compose up muninndb` or use hosted instance
6. **Run Dalil**: `python -m dalil serve` or `python -m dalil vault create test`
7. **Test endpoints**: Use Postman collection (`Dalil.postman_collection.json`) or curl

---

## Code Style

- **Type hints** throughout (Python 3.9+)
- **Pydantic models** for all I/O
- **Logging** via Python's `logging` module
- **Error handling** with try-except and custom exceptions
- **docstrings** on public functions/classes

No strict linting configured, but code follows PEP 8 conventions and type safety best practices.
