# Documentation Validation Report

**Date:** 2026-04-04  
**Status:** ⚠️ Issues Found

---

## Issues Found (By Severity)

### 🔴 CRITICAL — Breaking Issues

#### 1. **Wrong MuninnDB REST Endpoint Port in Documentation**

**Severity:** CRITICAL  
**Location:** Multiple docs files  
**Issue:** Documentation and code disagree on the REST API port for MuninnDB.

**Evidence:**
- `docker-compose.yml` ports:
  - Port 8475: REST API
  - Port 8476: Web UI / Dashboard
- Code (`dalil/config/settings.py`):
  ```python
  base_url: str = "http://localhost:8476"  # WRONG - this is the dashboard!
  ```
- Code (`docker-compose.yml`): 
  ```yaml
  MUNINN_URL: "http://127.0.0.1:8476"  # WRONG
  ```

**Documentation says (CORRECT):**
- `docs/ARCHITECTURE.md`: "**REST (port 8475)** for retrieval"
- `docs/API_REFERENCE.md`: "Base URL: `http://localhost:8475/api`"

**Documentation says (WRONG):**
- `docs/CONFIGURATION.md` table: Default is `http://localhost:8475` ✓ but shows 8476 as Docker
- Example config in `docs/CONFIGURATION.md`: Uses 8475 ✓

**Impact:** API calls fail silently if using 8476 (hits dashboard, not REST API).

**Fix Required:**
- [ ] Change `dalil/config/settings.py` line 14: `base_url: str = "http://localhost:8475"`
- [ ] Change `docker-compose.yml` line 49: `MUNINN_URL: "http://127.0.0.1:8475"`
- [ ] Change `config.json/config.example.json` line 2: `"base_url": "http://localhost:8475"`

---

#### 2. **Missing `/vault/health` Endpoint**

**Severity:** CRITICAL  
**Location:** `docs/API_REFERENCE.md`  
**Issue:** Documentation references `/vault/health` endpoint that doesn't exist in code.

**Evidence:**
- `docs/API_REFERENCE.md` line 192: Lists "GET /vault/health?vault=myproject"
- `docs/API_REFERENCE.md` line 196-203: Shows response format for vault health
- Code grep: Only `/health` endpoint exists (line 145 of `dalil/api/main.py`)
- No `@app.get("/vault/health")` decorator in main.py

**Actual Endpoints:**
- `GET /health` — General system health (Dalil + MuninnDB)
- `GET /vault/stats` — Vault statistics (engram count, coherence, contradictions, etc.)

**Impact:** Users following documentation will get 404 errors when calling `/vault/health`.

**Fix Required:**
- [ ] Remove `/vault/health` section from `docs/API_REFERENCE.md` (lines 188-203)
- [ ] Update README endpoint summary to clarify available endpoints
- [ ] Consider if `/vault/health` should be implemented or if `/vault/stats` suffices

---

### 🟡 MEDIUM — Accuracy Issues

#### 3. **Python Version Mismatch**

**Severity:** MEDIUM  
**Location:** `README.md` badge + `pyproject.toml`  
**Issue:** README says 3.10+ but code requires 3.11+

**Evidence:**
- `README.md` line 14: `python-3.10%2B`
- `pyproject.toml` line 3: `requires-python = ">=3.11"`
- `SETUP.md` line 7: "Python 3.10+"

**Impact:** Users with Python 3.10 will fail during installation. Minor but confusing.

**Fix Required:**
- [ ] Update `README.md` badge to 3.11+
- [ ] Update `SETUP.md` to 3.11+

---

#### 4. **Incorrect Config Schema Field Names in CONFIGURATION.md**

**Severity:** MEDIUM  
**Location:** `docs/CONFIGURATION.md` line 14  
**Issue:** Documentation config example uses wrong field names.

**Evidence:**
- Docs show `"llm_provider"` but code uses `"provider"` in LLMSettings
- Docs show `"llm_model"` but code uses `"model"` in LLMSettings
- Docs show `"embedding_provider"` but code has `"provider"` in EmbeddingSettings

**Actual Config Structure (from `config.example.json`):**
```json
{
  "llm": {
    "type": "api",
    "provider": "ollama",       // NOT llm_provider
    "model": "mistral",         // NOT llm_model
    "temperature": 0.3
  },
  "embeddings": {
    "provider": "openai",       // NOT embedding_provider
    "api_key": ""
  }
}
```

**Documentation says (WRONG):**
```json
{
  "llm_provider": "anthropic",      // WRONG - should be nested in "llm" object
  "llm_model": "claude-3-5-sonnet",  // WRONG - should be nested in "llm" object
  "embedding_provider": "onnx"      // WRONG - should be nested in "embeddings" object
}
```

**Impact:** Users copying the config from docs will get invalid JSON, failed startup.

**Fix Required:**
- [ ] Update `docs/CONFIGURATION.md` lines 9-16 with correct nested structure
- [ ] Show actual top-level keys: `"llm"`, `"muninn"`, `"embeddings"`, `"ingestion"`

---

#### 5. **MCP Endpoint Inconsistency**

**Severity:** MEDIUM  
**Location:** `docs/ARCHITECTURE.md` vs code  
**Issue:** Documentation says "port 8750" but actual endpoint includes path `/mcp`

**Evidence:**
- `docs/ARCHITECTURE.md` line 17: "**MCP (port 8750)**"
- Code `dalil/config/settings.py` line 16: `mcp_url: str = "http://localhost:8750/mcp"`
- Code `config.example.json` line 3: `"mcp_url": "http://localhost:8750/mcp"`

**Impact:** Minor - port is correct but full endpoint path missing from docs.

**Fix Required:**
- [ ] Update `docs/ARCHITECTURE.md`: "**MCP (port 8750/mcp)**" or clarify full URL

---

### 🟠 LOW — Documentation Gaps/Clarifications

#### 6. **API_REFERENCE.md Base URL Seems Incorrect**

**Severity:** LOW  
**Location:** `docs/API_REFERENCE.md` line 3  
**Issue:** Shows `/api` prefix but endpoints don't have `/api`

**Evidence:**
- `docs/API_REFERENCE.md`: "Base URL: `http://localhost:8475/api`"
- Code `dalil/api/main.py`: All endpoints are defined without `/api` prefix
- Actual endpoints: `/health`, `/consult`, `/ingest/csv`, etc. (NOT `/api/health`)

**Impact:** Users would try `http://localhost:8475/api/health` when correct is `http://localhost:8475/health`

**Fix Required:**
- [ ] Change `docs/API_REFERENCE.md` line 3 to:
  ```
  Base URL: `http://localhost:8475` (Dalil API inside Docker shares network)
  ```

---

#### 7. **Endpoint Count Accuracy**

**Severity:** LOW  
**Location:** README.md  
**Issue:** Claims "18 REST API Endpoints" - verify this is accurate.

**Evidence:**  
- Grep found exactly 18 `@app.` decorators in `dalil/api/main.py`
- Endpoints verified:
  1. GET /health
  2. POST /consult
  3. POST /ingest/csv
  4. POST /ingest/pdf
  5. POST /ingest/csv/upload
  6. POST /ingest/pdf/upload
  7. POST /ingest/confluence
  8. POST /feedback
  9. PUT /cases/{id}
  10. POST /cases/consolidate
  11. PATCH /cases/{id}/state
  12. GET /vault/stats
  13. POST /traverse
  14. GET /session/recent
  15. GET /vault/entities
  16. GET /vault/entities/{name}
  17. GET /vault/entities/{name}/timeline
  18. GET /vault/entities/{name}/cases

**Status:** ✅ VERIFIED - 18 is correct

---

#### 8. **Old Config Schema in CONFIGURATION.md**

**Severity:** LOW  
**Location:** `docs/CONFIGURATION.md` lines 30-55  
**Issue:** Example config references old field names and uses deprecated structure.

**Evidence:**
- Docs example uses top-level fields: `llm_provider`, `llm_model`, `embedding_provider`
- Actual example uses nested structure: Top level `muninn`, `llm`, `ingestion`, `embeddings`
- Settings code in `settings.py` uses nested dataclass approach

**Example in docs (OUTDATED):**
```json
{
  "llm_provider": "anthropic",
  "llm_model": "claude-3-5-sonnet-20241022",
  "embedding_provider": "onnx"
}
```

**Actual structure (from code):**
```json
{
  "muninn": {
    "base_url": "http://localhost:8475",
    "mcp_url": "http://localhost:8750/mcp"
  },
  "llm": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  },
  "embeddings": {
    "provider": "onnx"
  }
}
```

**Fix Required:**
- [ ] Replace entire config.json example in `docs/CONFIGURATION.md` with current structure
- [ ] Add cross-reference to `config.json/config.example.json` for authoritative template

---

## Summary Table

| # | Issue | File(s) | Severity | Type |
|---|-------|---------|----------|------|
| 1 | Wrong MuninnDB port (8476 vs 8475) | settings.py, docker-compose.yml, config.example.json, docs | 🔴 CRITICAL | Config Bug |
| 2 | Missing /vault/health endpoint | API_REFERENCE.md | 🔴 CRITICAL | Outdated Docs |
| 3 | Python version mismatch | README.md, SETUP.md, pyproject.toml | 🟡 MEDIUM | Version Mismatch |
| 4 | Wrong config field names in docs | CONFIGURATION.md | 🟡 MEDIUM | Schema Error |
| 5 | MCP endpoint path missing | ARCHITECTURE.md | 🟡 MEDIUM | Incomplete Docs |
| 6 | API base URL has incorrect /api prefix | API_REFERENCE.md | 🟠 LOW | Path Error |
| 7 | Endpoint count verification | README.md | ✅ VERIFIED | - |
| 8 | Old config schema shown | CONFIGURATION.md | 🟠 LOW | Outdated Example |

---

## Validation Completeness

### Checked ✅

- API endpoint count (18/18 verified)
- Endpoint method/path correctness (18/18 verified)
- Python version requirements (mismatch found)
- Configuration schema (errors found)
- MuninnDB port references (errors found)
- Documentation cross-references (missing endpoint found)
- LLM/Embedding provider lists (spot-check: ONNX verified as default)
- Architecture diagrams (referenced correctly)

### Not Checked (Scope Limitation)

- Postman collection accuracy (18 requests)
- Actual runtime behavior with corrected configs
- All CLI commands `dalil vault *`
- All ingestion loader implementations
- Test file coverage (27 tests mentioned)
- Docker image build success
- Full API response schema completeness

---

## Recommended Fix Priority

1. **Fix endpoints & ports (ASAP)** — Issues #1, #2, #4, #6 break functionality
2. **Update Python version** — Issue #3 affects new users
3. **Clarify MCP path** — Issue #5 minor but important for integrations
4. **Replace config example** — Issue #8 prevents copy-paste usage

Total estimated effort: **30-45 minutes** to fix all issues.

---

## Notes

- Documentation is well-structured overall
- Most issues are detail-level not architectural
- Config schema refactoring in `CONFIGURATION.md` is most impactful fix
- Consider adding automated documentation validation to CI/CD
