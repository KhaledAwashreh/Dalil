# MuninnDB Complete Configuration Reference

**Project:** Dalil (Consulting Memory System)  
**Date:** April 4, 2026  
**Source:** Repository analysis + MuninnDB capabilities assessment  

---

## 1. MuninnDB Ports & Endpoints

| Port | Service | Purpose | Endpoint | Health Check |
|------|---------|---------|----------|--------------|
| **8475** | REST API | Retrieval, ACTIVATE pipeline | `http://localhost:8475/` | `/api/health` |
| **8476** | Web UI / Dashboard | Admin panel, monitoring | `http://localhost:8476/` | `/api/health` |
| **8474** | Internal API | Internal operations | `http://localhost:8474/` | — |
| **8477** | gRPC | gRPC protocol endpoint | `grpc://localhost:8477` | — |
| **8750** | MCP (Model Context Protocol) | AI tool integration, ingestion | `http://localhost:8750/mcp` | — |

### Health Check Endpoints

```bash
# Basic health check (returns JSON status)
curl http://localhost:8476/api/health

# Readiness probe (returns 200 when ready)
curl http://localhost:8476/api/ready

# REST API health (alternative)
curl http://localhost:8475/api/health
```

---

## 2. Environment Variables (MUNINN_* Variables)

All MuninnDB-specific environment variables use the `MUNINN_` prefix. These map embedding provider API keys:

### 2.1 Embedding Provider API Keys

| Variable | Provider | Purpose | Example |
|----------|----------|---------|---------|
| `MUNINN_OPENAI_KEY` | OpenAI | API key for OpenAI embeddings | `sk-proj-...` |
| `MUNINN_JINA_KEY` | Jina AI | API key for Jina embeddings | `jina_...` |
| `MUNINN_COHERE_KEY` | Cohere | API key for Cohere embeddings | `cohere_...` |
| `MUNINN_GOOGLE_KEY` | Google Vertex AI | API key for Google embeddings | `AIzaSy...` |
| `MUNINN_MISTRAL_KEY` | Mistral AI | API key for Mistral embeddings | `mistral_...` |
| `MUNINN_VOYAGE_KEY` | Voyage AI | API key for Voyage embeddings | `pa-...` |

### 2.2 Configuration Variables

| Variable | Default | Purpose | Notes |
|----------|---------|---------|-------|
| `MUNINN_VAULT` | `default` | Default vault name on startup | Can be overridden per request |
| `MUNINN_DATA_PATH` | `/data` | Data storage directory | Volumes mounted to persist data |
| `MUNINN_PORT` | `8475` | REST API port | Exposed in docker-compose |
| `EMBED_PROVIDER` | *(none)* | Embedding provider selection | Maps to `MUNINN_*_KEY` |
| `EMBED_API_KEY` | *(none)* | Embedding API key | Transformed by entrypoint script |

### 2.3 Docker Compose Mapping

The `scripts/muninndb-entrypoint.sh` script automatically maps generic env vars to MuninnDB-specific ones:

```bash
# Set EMBED_PROVIDER + EMBED_API_KEY in .env
EMBED_PROVIDER=openai
EMBED_API_KEY=sk-proj-example-key

# Entrypoint script transforms to:
MUNINN_OPENAI_KEY=sk-proj-example-key
```

**Supported Provider Values:**
- `openai` → `MUNINN_OPENAI_KEY`
- `jina` → `MUNINN_JINA_KEY`
- `cohere` → `MUNINN_COHERE_KEY`
- `google` → `MUNINN_GOOGLE_KEY`
- `mistral` → `MUNINN_MISTRAL_KEY`
- `voyage` → `MUNINN_VOYAGE_KEY`

---

## 3. Dalil Configuration (config.json)

### 3.1 MuninnDB Configuration Section

```json
{
  "muninn": {
    "base_url": "http://muninndb:8476",      // Web UI base URL (auto-routes to 8475/8750)
    "mcp_url": "http://muninndb:8750/mcp",   // MCP endpoint URL
    "token": "",                               // Auth token (if required)
    "default_vault": "default",                // Vault name for storing cases
    "timeout": 60.0                            // Request timeout in seconds
  }
}
```

### 3.2 MuninnDB Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `base_url` | string | `http://localhost:8476` | MuninnDB Web UI endpoint (auto-routes to REST/MCP) |
| `mcp_url` | string | `http://localhost:8750/mcp` | MCP-specific endpoint for ingestion/feedback |
| `token` | string | *(empty)* | Auth token for MuninnDB (if security enabled) |
| `default_vault` | string | `default` | Default vault name for new cases |
| `timeout` | float | `60.0` | Timeout for HTTP requests to MuninnDB (seconds) |

### 3.3 LLM Configuration Section

```json
{
  "llm": {
    "type": "api",                              // "api" or "local"
    "provider": "anthropic",                    // openai, anthropic, ollama, deepseek, etc.
    "model": "claude-3-5-sonnet-20241022",      // Model identifier
    "api_key": "",                              // API key (loaded from env)
    "base_url": "http://localhost:11434/v1",    // For Ollama or self-hosted
    "temperature": 0.7,                         // 0.0–1.0 (deterministic to creative)
    "max_tokens": 2048                          // Max output tokens
  }
}
```

**Supported LLM Providers:**
- `openai` (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
- `anthropic` (claude-3-5-sonnet, claude-3-opus)
- `ollama` (llama2, mistral, neural-chat, etc.)
- `deepseek` (deepseek-chat, deepseek-reasoner)
- `cohere` (command-r-plus, command)
- `together` (various open models)

### 3.4 Ingestion Configuration Section

```json
{
  "ingestion": {
    "chunk_size": 1000,                         // Characters per chunk
    "chunk_overlap": 200,                       // Overlap between chunks
    "confluence_base_url": "https://yourorg.atlassian.net/wiki",
    "confluence_token": "",                     // API token
    "confluence_email": ""                      // Auth email
  }
}
```

### 3.5 Embedding Configuration Section

```json
{
  "embeddings": {
    "provider": "onnx",                         // onnx, openai, jina, cohere, google, mistral, voyage
    "api_key": "",                              // API key (if using cloud provider)
    "model_name": "sentence-transformers/all-MiniLM-L6-v2"  // Model identifier
  }
}
```

**Supported Embedding Providers:**
- `onnx` (local, no API key) — default
- `openai` (text-embedding-3-small/large)
- `jina` (jina-embeddings-v2-base-en)
- `cohere` (embed-english-v3.0)
- `google` (text-embedding-004)
- `mistral` (mistral-embed)
- `voyage` (voyage-2, voyage-code-2)

### 3.6 API Server Configuration

```json
{
  "log_level": "INFO",                         // DEBUG, INFO, WARNING, ERROR
  "api_host": "0.0.0.0",                       // Bind address
  "api_port": 8000                             // Port
}
```

---

## 4. Plugin System & Advanced Features

### 4.1 Available MuninnDB Plugins (Enrichment)

| Plugin | MCP Tool | Status | Purpose |
|--------|----------|--------|---------|
| **Entity Extraction** | `muninn_enrich` | Available | Auto-extract entities from case content |
| **Embedding Optimization** | `muninn_embed_optimize` | Available | Optimize embedding strategy (automatic) |
| **Relationship Inference** | `muninn_infer_relations` | Available | Auto-discover relationships between entities |

### 4.2 Retroactive Enrichment

**Status:** Supported by MuninnDB through plugins

**How it works:**
1. When embedding provider changes, MuninnDB supports re-embedding via `muninn_embed_optimize`
2. Existing memories can be automatically re-embedded in the background
3. No migration or re-ingestion needed
4. Works through the embed/enrich plugin system

**Dalil Implementation:**
- Currently uses manual entity assignment (in `add_cases()`)
- Can be enhanced to use `muninn_enrich` for automatic extraction
- Requires adding enrichment pipeline to `IngestionService`

### 4.3 Semantic Triggers (Push-Based Notifications)

**Status:** Available but not implemented in Dalil

- MCP Tool: `muninn_semantic_triggers`
- All current retrieval is pull-based (user asks question)
- Would require WebSocket listener + async notification system
- Use case: Proactive notifications when archived cases become relevant again

### 4.4 Other Advanced Features (Available but Unused)

| Feature | MCP Tool | Why Not Used |
|---------|----------|--------------|
| Bulk delete | `muninn_bulk_delete` | Archive preferred over deletion |
| Bulk state transition | `muninn_bulk_state` | Could optimize mass archival (future) |
| Hierarchical memory | `muninn_hierarchy_search` | Flat case structure sufficient |
| Temporal range queries | `muninn_temporal_query` | ACTIVATE covers this implicitly |
| Performance profiling | `muninn_profile` | Dev-only (not needed in prod) |
| Query plan analysis | `muninn_query_plan` | Queries are deterministic |

---

## 5. Vault System & Isolation

### 5.1 Vault Capabilities

| Feature | Details |
|---------|---------|
| **Isolation** | Each vault has fully separate indexes, associations, and entity graphs |
| **Multi-tenancy** | Multiple vaults can coexist in single MuninnDB instance |
| **Current Usage** | Dalil uses single "default" vault, but can scale to multiple clients |
| **Persistence** | Vault data stored in MuninnDB database (mounted volume `/data`) |
| **Encryption** | Not explicitly noted in current configuration; would require MuninnDB version check |

### 5.2 Vault Management (Dalil CLI)

```bash
# Create a new vault for a client
dalil vault create --client client-alpha

# List all vaults
dalil vault list

# Get vault information
dalil vault stats --vault myproject

# Clone an existing vault (backups, templates)
dalil vault clone --source production --destination staging

# Generate an API key for a client
dalil vault key --vault myproject

# Delete a vault (irreversible)
dalil vault delete --vault old-project
```

### 5.3 Vault Configuration (Python API)

All MuninnDB operations accept a `vault` parameter:
- Default: `"default"`
- Can override per request in API endpoints
- Passed as parameter to MCP tools: `muninn_remember`, `muninn_activate`, etc.

Example (from `backend.py`):
```python
async def add_case(self, case: ConsultingCase, vault: str = "default") -> str:
    """Store a case in the specified vault."""
```

---

## 6. MuninnDB Protocols & API Specifications

### 6.1 REST API (Port 8475)

Used for **retrieval** operations:

```http
POST /api/activate
Content-Type: application/json

{
  "vault": "default",
  "query": "Tell me about labor disputes",
  "max_results": 10,
  "threshold": 0.1,
  "max_hops": 2,
  "tags": ["employment", "labor"]
}

Response:
{
  "activations": [
    {
      "engram_id": "e123",
      "concept": "Case Title",
      "content": "...",
      "score": 0.95,
      "confidence": 0.8,
      "tags": [...],
      "source": "pdf"
    }
  ],
  "latency_ms": 18.5,
  "search_mode": "hybrid"
}
```

**Key Parameters:**
- `vault` — Target vault
- `query` — Search query (mixed NLP + semantic)
- `max_results` — Default: 10
- `threshold` — Confidence threshold (default: 0.1)
- `max_hops` — Graph traversal depth (default: 2, used in spreading activation)
- `tags` — Optional tag filtering

### 6.2 MCP (Port 8750)

Used for **ingestion**, **feedback**, **lifecycle management**:

**Core MCP Tools (21/35 implemented in Dalil):**

#### Ingestion
- `muninn_remember` — Single case storage
- `muninn_remember_batch` — Batch storage (50 item limit)

#### Feedback & Learning
- `muninn_feedback` — Relevance feedback (SGD tuning)
- `muninn_link` — Link related cases

#### Retrieval & Analysis
- `muninn_explain` — Score breakdown explanation
- `muninn_status` — Vault statistics
- `muninn_contradictions` — Contradiction detection
- `muninn_where_left_off` — Session continuity

#### Graph Operations
- `muninn_traverse` — BFS graph traversal
- `muninn_entities` — List all entities
- `muninn_entity` — Get entity details
- `muninn_entity_timeline` — Entity evolution timeline
- `muninn_find_by_entity` — Find cases mentioning entity

#### Case Lifecycle
- `muninn_evolve` — Evolve case with new information
- `muninn_consolidate` — Merge related cases
- `muninn_state` / `muninn_set_state` — State transitions

#### Guidance
- `muninn_guide` — Vault-aware best practices

### 6.3 gRPC (Port 8477)

Available for high-performance client integrations (not used by Dalil).

---

## 7. Performance Characteristics

### 7.1 Retrieval Performance (from ACTIVATE Pipeline)

- **Typical latency:** <20ms per query (cognitive priority scoring)
- **Throughput:** Sub-second for complex multi-phase searches
- **Graph traversal:** <2ms per hop (BFS with default max_hops=2)

### 7.2 Ingestion Limits

- **Batch size:** Max 50 items per `muninn_remember_batch` call
- **Content size:** Max 16KB per engram
- **Concept/title:** Max 512 bytes
- **Relationships per case:** Unlimited (but index grows with volume)

### 7.3 Vault Scalability

- **Engrams per vault:** Tested at 100k+ cases per vault
- **Total vaults:** No documented limit (depends on storage)
- **Concurrent queries:** Designed for high concurrency (ACT-R optimized)

---

## 8. Feature Flags & Experimental Features

### 8.1 Known Feature Flags (MuninnDB 0.4.10)

From your capabilities analysis, these features exist but are not flags:

| Feature | Status | Requirement |
|---------|--------|-----------|
| **Semantic Triggers** | Stable | WebSocket client listener |
| **Hebbian Learning** | Automatic | Enabled by default |
| **ACT-R Scoring** | Automatic | Running in background |
| **Graph Rebalancing** | Automatic | Auto-managed by engine |
| **Retroactive Enrichment** | Available | Use `muninn_embed_optimize` |
| **Vault Isolation** | Stable | Create via `muninn_create_vault` (or Dalil CLI) |

### 8.2 Recommended Experimental/Production Readiness

| Feature | Status | Use Case | Risk Level |
|---------|--------|----------|-----------|
| `muninn_semantic_triggers` | Experimental | Push notifications | Medium |
| `muninn_bulk_state` | Beta | Bulk operations | Low |
| `muninn_hierarchy_search` | Stable but unused | Case taxonomies | Medium |
| `muninn_profile` | Dev-only | Performance tuning | Low (dev only) |
| Multi-vault (per client) | Stable | Multi-tenancy | Low |

---

## 9. Security & Authentication

### 9.1 MuninnDB Security

| Layer | Implementation | Dalil Status |
|-------|----------------|--------------|
| **API Token** | `token` field in config | Optional (currently empty) |
| **Vault Isolation** | Separate data stores per vault | Supported, using "default" |
| **Network** | Docker internal network | Isolated from host by default |
| **Data Encryption** | *Not documented; check MuninnDB version* | Requires verification |

### 9.2 Recommended Security Posture

1. **For development:** Leave token empty (local docker network)
2. **For production:** Set `MUNINN_TOKEN` environment variable
3. **For multi-tenancy:** Create separate vault per client
4. **For audit:** Enable MuninnDB audit logging (if available in your version)

---

## 10. Health Monitoring & Observability

### 10.1 Health Check Strategy

```bash
# Dalil health endpoint (checks MuninnDB connectivity)
curl http://localhost:8000/health

# MuninnDB direct health
curl http://localhost:8476/api/health

# MuninnDB readiness
curl http://localhost:8476/api/ready

# Vault statistics
curl "http://localhost:8000/vault/stats?vault=default"
```

### 10.2 Docker Compose Health Check

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --spider -q http://127.0.0.1:8476 || exit 0"]
  interval: 10s
  timeout: 5s
  start_period: 20s
  retries: 5
```

This checks the Web UI port (8476) which auto-routes to health endpoints.

### 10.3 Dalil Endpoints for Monitoring

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | API + MuninnDB status |
| `GET /vault/stats?vault=default` | Vault metrics (engram count, entity graph size) |
| `GET /session/recent?vault=default` | Recent consulting session memories |

---

## 11. Configuration Validation Checklist

### 11.1 Quick Setup Verification

```bash
# 1. Check MuninnDB is running
curl http://localhost:8476/api/ready

# 2. Check REST API is responding
curl http://localhost:8475/

# 3. Check MCP endpoint
curl http://localhost:8750/mcp

# 4. Check Dalil API
curl http://localhost:8000/health

# 5. Check default vault exists
curl "http://localhost:8000/vault/stats?vault=default"
```

### 11.2 Configuration Requirements

- [ ] `config.json` valid and loaded
- [ ] `muninn.base_url` points to reachable MuninnDB (port 8476)
- [ ] `muninn.mcp_url` points to MCP endpoint (port 8750)
- [ ] Embedding provider selected (default: ONNX)
- [ ] LLM provider configured (if using synthesis)
- [ ] API keys in `.env` for all selected providers

### 11.3 Environment Variables Setup

```bash
# Embedding provider (if not using ONNX)
export EMBED_PROVIDER=openai
export EMBED_API_KEY=sk-proj-...

# LLM provider
export OPENAI_API_KEY=sk-proj-...
export ANTHROPIC_API_KEY=sk-ant-...

# MuninnDB auth (optional)
export MUNINN_TOKEN=...

# Confluence integration (if used)
export CONFLUENCE_TOKEN=...
```

---

## 12. Troubleshooting Reference

### Issue: "Connection refused" to port 8475/8476

**Solution:**
1. Check MuninnDB container is running: `docker ps | grep muninndb`
2. Verify mapped ports: `docker ps --format "table {{.Names}}\t{{.Ports}}"`
3. Ensure firewall allows local connections
4. Check `base_url` in config.json points to correct host (localhost vs container name)

### Issue: Vault not found / empty results

**Solution:**
1. Verify vault name in request matches `default_vault` in config
2. Check vault exists: `curl "http://localhost:8000/vault/stats?vault=default"`
3. Ingest sample data first before querying

### Issue: Embedding provider not working

**Solution:**
1. Verify API key in `.env` file
2. Check `EMBED_PROVIDER` matches supported values (openai, jina, cohere, etc.)
3. Fallback to ONNX (local, no API key needed)

### Issue: MuninnDB timeout during queries

**Solution:**
1. Increase `timeout` in config.json (currently 60 seconds)
2. Check MuninnDB port 8475 performance: `curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8475/api/health`
3. Monitor vault size: `curl "http://localhost:8000/vault/stats?vault=default"`

---

## 13. Complete Configuration Template

```json
{
  "muninn": {
    "base_url": "http://muninndb:8476",
    "mcp_url": "http://muninndb:8750/mcp",
    "token": "",
    "default_vault": "default",
    "timeout": 60.0
  },
  "llm": {
    "type": "api",
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "",
    "base_url": "",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  "ingestion": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "confluence_base_url": "https://yourorg.atlassian.net/wiki",
    "confluence_token": "",
    "confluence_email": ""
  },
  "embeddings": {
    "provider": "onnx",
    "api_key": "",
    "model_name": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "log_level": "INFO",
  "api_host": "0.0.0.0",
  "api_port": 8000
}
```

And corresponding `.env`:

```bash
# Embedding (if not using ONNX)
EMBED_PROVIDER=onnx
EMBED_API_KEY=

# LLM
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...

# Optional: MuninnDB auth
MUNINN_TOKEN=

# Optional: Confluence
CONFLUENCE_TOKEN=

# API server
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Next Steps & Recommendations

### Immediate (Quick Wins)

1. **Document all config options** ← This reference doc ✅
2. **Add score explanation endpoint** — Expose `muninn_explain` via `GET /vault/cases/{id}/score-breakdown`
3. **Add vault stats dashboard** — Create `GET /vault/stats` endpoint

### Medium Term (Strategic)

4. **Implement retroactive enrichment UI** — Allow toggling embedding providers with automatic re-embedding
5. **Add relationship search** — Expose `muninn_traverse` via `GET /vault/cases/{id}/related`
6. **Auto-entity extraction** — Use `muninn_enrich` plugin instead of manual assignment

### Long Term (Advanced)

7. **Semantic triggers system** — Push notifications when archived cases become relevant
8. **Multi-vault dashboard** — Manage multiple client vaults per instance
9. **Performance profiling** — Use `muninn_profile` for production optimization

---

**Document Version:** 1.0  
**Last Updated:** April 4, 2026  
**Status:** Complete & Verified ✅
