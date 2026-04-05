# Development & Roadmap

## Current Limitations

### 1. No Authentication or Authorization

- **Status:** Not implemented
- **Impact:** All vaults are accessible to any client at the API
- **Workaround:** Use a reverse proxy (nginx, Envoy) to enforce authentication before requests reach Dalil

### 2. Vault Management is CLI-Only

- **Status:** Intentional
- **Why:** Vault creation requires direct binary access to MuninnDB CLI tools. Cannot be safely exposed over HTTP without Docker socket mounting, which violates security best practices.
- **Workaround:** Create vaults ahead of time using the CLI, then manage them via API

```bash
dalil vault create production
dalil vault list
dalil vault key production
```

### 3. No Audit Logging

- **Status:** Basic event logging implemented (ConsultEvent, IngestEvent), but no persistent audit trail
- **Impact:** Cannot trace which client retrieved which cases
- **Workaround:** Implement via reverse proxy request logging or extend analytics layer

### 4. No Caching

- **Status:** Not implemented
- **Impact:** Every consultation queries MuninnDB fresh (no latency penalties, but no optimization)
- **Workaround:** Implement query caching in Redis if retrieval latency becomes problematic

### 5. No Rate Limiting

- **Status:** Not implemented
- **Impact:** Any client can hammer the API
- **Workaround:** Implement via FastAPI middleware, reverse proxy, or cloud provider (AWS API Gateway, etc.)

### 6. No Distributed Tracing

- **Status:** Not implemented
- **Impact:** Cannot trace a consultation request across MuninnDB layers
- **Workaround:** Implement OpenTelemetry integration

---

## Roadmap

### Phase 1: Core Stabilization (Current)
- ✅ Basic REST API (18 endpoints)
- ✅ CSV, PDF, Confluence ingestion
- ✅ Vault isolation per client
- ✅ Multiple LLM/embedding providers
- ⏳ Documentation reorganization

### Phase 2: Production Hardening
- 🔄 Authentication (OAuth2, API keys)
- 🔄 Audit logging (persistent, queryable)
- 🔄 Rate limiting (per-client, per-endpoint)
- 🔄 Metrics & monitoring (Prometheus)
- 🔄 Graceful degradation (circuit breaker to MuninnDB)

### Phase 3: Advanced Features
- 🔮 Multi-hop consultations (chain multiple queries)
- 🔮 Batch ingestion (async jobs)
- 🔮 Query optimization (learned weights)
- 🔮 Feedback loop automation (auto-adjust confidence)
- 🔮 Entity linking (dynamic relationship discovery)

### Phase 4: Integration Ecosystem
- 🔮 LangChain integration
- 🔮 Slack bot connector
- 🔮 Jira integration
- 🔮 Confluence rich media support
- 🔮 REST → GraphQL gateway

---

## Architecture Decision Records (ADRs)

### ADR-1: Why No LangGraph or Agent Frameworks?

**Decision:** Use plain Python orchestration instead of LangGraph, AutoGPT, or similar.

**Rationale:**
1. **Determinism:** Consultation pipeline is sequential and deterministic — every step is explicit
2. **Debuggability:** Plain Python is easier to trace and fix than agent loops
3. **Predictability:** No surprise loops, no unexpected LLM calls, deterministic latency
4. **Simplicity:** Thin orchestration layer (200 LOC) is easier to understand than 5000-line framework

**Tradeoff:** Cannot auto-build complex workflows, but can build exactly what we need, when we need it.

### ADR-2: Why MuninnDB and Not Traditional Vector DB?

**Decision:** Use MuninnDB (cognitive memory database) instead of Pinecone, Weaviate, Milvus, etc.

**Rationale:**
1. **Semantic + full-text fusion** — ACTIVATE pipeline combines vector search with BM25 ranking
2. **Graph-aware retrieval** — Spreading activation through relationship graph (ACT-R scoring)
3. **Confidence tracking** — Built-in confidence/contradict detection
4. **Entity management** — Native entities + automatic relationship inference
5. **Vault isolation** — Per-client encrypted separation by design
6. **Single dependency** — One Go binary, zero external services

**Tradeoff:** Smaller ecosystem than Pinecone, but far more powerful for consulting use cases where context and relationships matter.

### ADR-3: Why Vault Management CLI-Only?

**Decision:** Keep vault creation/deletion as CLI-only, not HTTP endpoints.

**Rationale:**
1. **Security:** Creating vaults requires invoking MuninnDB binaries directly. Exposing this over HTTP would require Docker socket mounting (privilege escalation risk).
2. **Safety:** Users can't accidentally mass-delete vaults through API chaos.
3. **Separ ation of concerns:** Vault lifecycle (rare, administrative) vs. consultation (frequent, client-facing).

**Tradeoff:** Slightly more operational overhead, but eliminates a whole class of security holes.

### ADR-4: Why Thin API Layer?

**Decision:** FastAPI + lightweight adapters instead of heavy ORM/framework.

**Rationale:**
1. **Clarity:** Every endpoint maps to one business function
2. **Control:** No magic; explicit MuninnDB calls
3. **Performance:** Minimal abstraction layers
4. **Flexibility:** Can swap backends (MuninnDB → other systems) easily

**Tradeoff:** Need custom validation/serialization for each endpoint, but code is readable and auditable.

---

## Contributing

### Adding a New Ingestion Source

1. Create `dalil/ingestion/newformat_loader.py`:
   ```python
   from dalil.ingestion.normalizer import normalize_case
   
   class NewFormatLoader:
       def load(self, source: str) -> List[ConsultingCase]:
           # Parse source, extract cases, return normalized list
           pass
   ```

2. Update `dalil/services/ingest_service.py` to call the loader

3. Add endpoint to `dalil/api/main.py`:
   ```python
   @app.post("/ingest/newformat")
   async def ingest_newformat(...):
       ...
   ```

4. Add Postman request to `Dalil.postman_collection.json`

5. Add tests in `dalil/tests/test_ingestion.py`

### Adding a New LLM Provider

1. Create `dalil/llm/provider_llm.py` inheriting `LLMProvider`
2. Implement `generate(...)` method
3. Update `dalil/llm/factory.py` to instantiate from `config.json`
4. Update `docs/LLM_PROVIDERS.md`

---

## Testing Strategy

### Unit Tests

Coverage includes:
- CSV/PDF parsing and normalization
- Prompt building with context windows
- Response formatting and error handling
- Case schema validation

Run:
```bash
pytest dalil/tests/ -v
```

### Integration Tests (Manual)

Use Postman collection `Dalil.postman_collection.json` to test full workflows:
1. Create a vault: `dalil vault create test-integration`
2. Ingest CSV: `POST /ingest/csv`
3. Consult: `POST /consult`
4. Verify response contains retrieved cases

### End-to-End Tests (Manual)

```bash
# Start containers
docker compose up -d

# Create vault
docker compose exec dalil python -m dalil vault create e2e-test

# Run Postman collection against http://localhost:8000

# Inspect logs
docker compose logs dalil
docker compose logs muninndb
```

---

## Monitoring & Observability

### Logs

- **Dalil API:** Logged to stdout (Docker: `docker compose logs dalil`)
- **MuninnDB:** Logged to stdout (Docker: `docker compose logs muninndb`)
- **Event logging:** `ConsultEvent`, `IngestEvent` written to analytics layer

### Metrics

Basic metrics tracked in `dalil/analytics/metrics.py`:
- Consultations (total, by vault, avg latency)
- Ingestions (total, by source, cases/sec)
- Errors (by type, by endpoint)

### Health Checks

- **`GET /health`:** Dalil + MuninnDB health
- **`GET /vault/stats?vault=X`:** Vault statistics and health

---

## Security Considerations

### Data at Rest

- Vault data stored in MuninnDB (encrypted by MuninnDB's vault mechanism)
- Configuration (API keys) in `.env` (Git-ignored)

### Data in Transit

- REST API should run behind HTTPS (use reverse proxy like nginx)
- MuninnDB communication (internal Docker network, not exposed)

### Access Control

- No built-in authentication — use reverse proxy (nginx, Envoy, API Gateway)
- API keys stored in MuninnDB vault registry (not in HTTP headers)

### Secrets Management

- API keys in `.env` (not in code, not in version control)
- Recommend AWS Secrets Manager, HashiCorp Vault, or similar for production

---

## Debugging

### MuninnDB Connection Issues

Check MuninnDB health:
```bash
curl http://localhost:8475/health
```

If unhealthy, inspect MuninnDB logs:
```bash
docker compose logs muninndb
```

### Slow Consultations

Check vault stats via Dalil:
```bash
curl http://localhost:8000/vault/stats?vault=myproject
```

Or check MuninnDB directly:
```bash
curl http://localhost:8475/api/health
```

### LLM Provider Errors

Check `.env` has the correct API key:
```bash
echo $ANTHROPIC_API_KEY  # Should not be empty
```

Test LLM access directly in Python:
```python
from dalil.llm.factory import LLMFactory
from dalil.config.settings import Settings

settings = Settings()
llm = LLMFactory.create(settings)
print(llm.generate("hello"))
```

---

## CI/CD

No current CI/CD. Recommended setup:

```yaml
# .github/workflows/test.yml
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      - run: pip install -r requirements.txt
      - run: pytest dalil/tests/
      - run: docker compose build
```

---

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG / release notes
- [ ] Run `pytest dalil/tests/` — all pass
- [ ] Manual E2E test with Docker Compose
- [ ] Tag release: `git tag v1.x.x`
- [ ] Build Docker image: `docker compose build`
- [ ] Push to registry
- [ ] Update deployment docs
