<h1 align="center">Dalil (دليل)</h1>

<p align="center">
  <em>Arabic for "guide" and "evidence"</em>
</p>

<p align="center">
  A knowledge-centric consulting memory system that ingests domain knowledge,<br>
  stores it as structured cases in <a href="https://github.com/scrypster/muninndb">MuninnDB</a>,<br>
  and delivers grounded consulting advice through a pluggable LLM layer.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/framework-FastAPI-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/memory-MuninnDB-purple" alt="MuninnDB">
  <img src="https://img.shields.io/badge/LLM-provider--agnostic-orange" alt="Provider Agnostic">
</p>

---

## What This Is

A **thin orchestrator on MuninnDB** — not a chatbot, not a persona, not an agent graph.

| Stage | What happens |
|-------|-------------|
| **Ingest** | Confluence, CSV, PDF → normalized, chunked |
| **Store** | Cases → MuninnDB via MCP (`muninn_remember`) — MuninnDB handles enrichment (entities, graph edges) |
| **Retrieve** | MuninnDB ACTIVATE pipeline (semantic + full-text hybrid search, graph traversal) |
| **Log** | Every request tracked with structured analytics |
| **Synthesize** | Provider-agnostic LLM (optional — runs retrieval-only without one) |
| **Deliver** | FastAPI → structured JSON with full case content, sources, confidence, reasoning |

---

## Architecture

### Consultation Flow

```mermaid
flowchart TD
    Client([Client]) --> API[FastAPI API Layer]

    API --> |POST /consult| CS[ConsultService]

    CS --> V[1. Validate & Normalize]
    V --> MDB[(2. MuninnDB<br>Memory Retrieval)]

    MDB --> AN[3. Log Analytics Event]
    AN --> PB[4. Prompt Builder]
    PB --> LLM[5. LLM Adapter<br><small>optional</small>]
    LLM --> RF[6. Response Formatter]
    RF --> RES([Structured JSON Response<br><small>full case content included</small>])

    style Client fill:#f9f9f9,stroke:#333
    style API fill:#009688,color:#fff
    style CS fill:#1565c0,color:#fff
    style MDB fill:#7b1fa2,color:#fff
    style LLM fill:#e65100,color:#fff
    style RES fill:#f9f9f9,stroke:#333
```

### Ingestion Flow

```mermaid
flowchart LR
    PDF[PDF] --> L[Loader]
    CSV_F[CSV] --> L
    CONF[Confluence] --> L

    L --> N[Normalizer]
    N --> CH[Chunker]
    CH --> CASE[ConsultingCase]
    CASE --> MB[(MuninnDB<br>Vault<br><small>enrichment, entities,<br>graph edges</small>)]

    style MB fill:#7b1fa2,color:#fff
    style CASE fill:#1565c0,color:#fff
```

### Vault Isolation

```mermaid
flowchart TD
    D[Dalil API] --> VA[(Vault: client_alpha)]
    D --> VB[(Vault: client_beta)]
    D --> VC[(Vault: client_gamma)]

    VA -.- NA[Isolated memory,<br>indexes & associations]
    VB -.- NB[Isolated memory,<br>indexes & associations]
    VC -.- NC[Isolated memory,<br>indexes & associations]

    style D fill:#009688,color:#fff
    style VA fill:#7b1fa2,color:#fff
    style VB fill:#7b1fa2,color:#fff
    style VC fill:#7b1fa2,color:#fff
```

---

## Why No LangGraph

Dalil uses **plain Python orchestration**. The consultation pipeline is a sequential, deterministic flow — not a graph, not an agent loop. Every step is explicit, readable, and debuggable.

No workflow engine framework is needed or used.

---

## Documentation

- **[SETUP.md](SETUP.md)** — Installation, MuninnDB setup, quick-start walkthrough
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Deep dive: MuninnDB integration, communication protocols, ACTIVATE pipeline, data model
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — config.json schema, environment variables, vault management CLI, Docker setup
- **[docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md)** — LLM & embedding provider setup (OpenAI, Anthropic, Ollama, DeepSeek, etc.)
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** — Full REST API endpoint reference with examples
- **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** — Directory layout, key modules, code organization, testing strategy
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Limitations, roadmap, ADRs, debugging tips, monitoring, CI/CD setup

---

## Quick Start

### 1. Install MuninnDB

```bash
# Docker Compose (recommended)
docker compose up
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .  # CLI support
```

### 3. Configure

```bash
cp dalil/config/config.example.json config.json
# Edit config.json for your LLM/embedding provider
```

### 4. Create vault & ingest

```bash
dalil vault create my-project
curl -X POST http://localhost:8475/ingest/csv \
  -F "file=@data.csv" \
  -F "vault=my-project"
```

### 5. Query

```bash
curl -X POST http://localhost:8475/consult \
  -H "Content-Type: application/json" \
  -d '{"query": "Your question", "vault": "my-project"}'
```

See **[SETUP.md](SETUP.md)** for full walkthrough.

---

## CLI

```bash
dalil vault create <client>        # Create a vault
dalil vault list                   # List vaults
dalil vault stats --vault <name>   # Vault statistics
dalil vault key --vault <name>     # Get API key
dalil vault clone --source <s> --destination <d>  # Clone vault
dalil vault delete --vault <name>  # Delete vault
```

---

## 18 REST API Endpoints

**Consultation:**
- `POST /consult` — Query & synthesize
- `POST /feedback` — Log relevance feedback

**Vault Management:**
- `GET /vault/stats` — Knowledge statistics
- `GET /vault/health` — Vault health check
- `GET /vault/recent` — Recently accessed cases

**Ingestion:**
- `POST /ingest/csv` — Ingest CSV
- `POST /ingest/pdf` — Ingest PDF
- `POST /ingest/confluence` — Ingest Confluence

**Entity Management:**
- `GET /entities` — List entities
- `POST /entities/merge` — Merge duplicates
- `DELETE /entities/{id}` — Delete entity

**Traversal:**
- `POST /traverse` — Graph traversal

**Health:**
- `GET /health` — System health

Full reference: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## License

MIT License (see LICENSE file)
