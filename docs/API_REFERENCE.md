# API Reference

Base URL: `http://localhost:8000`

All requests/responses use **JSON**.

---

## Core Endpoints

### Health Check

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "muninn_connected": true,
  "llm_provider": "APILLM",
  "llm_model": "deepseek-v3.1:671b-cloud"
}
```

`status` is `"ok"` when MuninnDB is connected, `"degraded"` otherwise.

### Consultation

Retrieve relevant cases from a vault and synthesize an LLM response.

```http
POST /consult
```

**Request Body:**
```json
{
  "problem": "What's the best approach to handling API rate limiting?",
  "context": "Mid-size SaaS company with 10k daily active users",
  "tags": ["architecture", "scaling"],
  "vault": "default"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `problem` | string | yes | The consulting problem or question |
| `context` | string | no | Additional context about the client/situation |
| `tags` | list[str] | no | Focus area tags for filtering |
| `vault` | string | no | Client vault for isolation (default: `"default"`) |

**Response (200 OK):**
```json
{
  "request_id": "uuid-here",
  "recommendation": "Based on the retrieved cases, here's the recommended approach...",
  "similar_cases": [
    {
      "id": "01KM3S...",
      "title": "Rate Limiting Strategy",
      "type": "playbook",
      "industry": "technology",
      "score": 0.87,
      "content": "...",
      "summary": "...",
      "tags": ["architecture"]
    }
  ],
  "sources": [
    {"type": "muninn", "uri": "engram://01KM3S...", "title": "Rate Limiting Strategy"}
  ],
  "tools_used": ["muninn_memory"],
  "confidence": 0.82,
  "reasoning_summary": "...",
  "score_breakdowns": null
}
```

### Feedback

Provide relevance feedback on consultation results to improve future retrievals.

```http
POST /feedback
```

**Request Body (preferred — per-case signals):**
```json
{
  "request_id": "uuid-from-consult",
  "results": [
    {"case_id": "case-1", "relevant": true},
    {"case_id": "case-2", "relevant": false}
  ],
  "comment": "First case was exactly what I needed"
}
```

**Request Body (legacy — bulk signal):**
```json
{
  "request_id": "uuid-from-consult",
  "signal": "useful",
  "case_ids": ["case-1", "case-2"]
}
```

**Response (200 OK):**
```json
{
  "request_id": "uuid-here",
  "cases_affected": 2,
  "actions_taken": [
    "sent relevance feedback for 2 cases",
    "linked 1 pairs of co-relevant cases"
  ]
}
```

Under the hood, this calls `muninn_feedback` for SGD weight tuning and `muninn_link` to connect co-relevant cases.

---

## Ingestion Endpoints

### Ingest CSV (server path)

```http
POST /ingest/csv
```

**Request Body:**
```json
{
  "file_path": "/path/to/cases.csv",
  "vault": "default",
  "tags": ["imported"]
}
```

### Ingest CSV (file upload)

```http
POST /ingest/csv/upload
```

**Form Data:**
- `file` (file): CSV file
- `vault` (string): Target vault (default: `"default"`)
- `tags` (string): Comma-separated tags

### Ingest PDF (server path)

```http
POST /ingest/pdf
```

**Request Body:**
```json
{
  "file_path": "/path/to/document.pdf",
  "vault": "default",
  "tags": ["imported"]
}
```

### Ingest PDF (file upload)

```http
POST /ingest/pdf/upload
```

**Form Data:**
- `file` (file): PDF file
- `vault` (string): Target vault
- `tags` (string): Comma-separated tags

### Ingest Confluence

```http
POST /ingest/confluence
```

**Request Body (by URL):**
```json
{
  "url": "https://yourorg.atlassian.net/wiki/spaces/TEAM/pages/123456/Page+Title",
  "vault": "default",
  "tags": ["confluence"]
}
```

**Request Body (by page ID):**
```json
{
  "page_id": "123456",
  "vault": "default"
}
```

**Request Body (entire space):**
```json
{
  "space_key": "TEAM",
  "vault": "default",
  "limit": 25,
  "tags": ["confluence", "bulk"]
}
```

**Ingestion Response (all formats):**
```json
{
  "request_id": "uuid-here",
  "source_type": "csv",
  "cases_created": 42,
  "vault": "default"
}
```

---

## Case Management Endpoints

### Evolve Case

Update a case in place, archiving the previous version.

```http
PUT /cases/{case_id}
```

**Request Body:**
```json
{
  "case_id": "01KM3S...",
  "content": "Updated content with new insights",
  "concept": "Reason for the update",
  "vault": "default"
}
```

Calls `muninn_evolve` with `new_content` and `reason` parameters.

**Response (200 OK):**
```json
{
  "case_id": "01KM3S...",
  "vault": "default",
  "result": {"id": "01KNE6...", "concept": ""}
}
```

### Set Case State

Change the lifecycle state of a case.

```http
PATCH /cases/{case_id}/state
```

**Request Body:**
```json
{
  "case_id": "01KM3S...",
  "state": "archived",
  "vault": "default"
}
```

Valid states: `planning`, `active`, `paused`, `blocked`, `completed`, `cancelled`, `archived`, `soft_deleted`.

**Response (200 OK):**
```json
{
  "case_id": "01KM3S...",
  "state": "archived",
  "success": true
}
```

### Consolidate Cases

Merge multiple cases into one.

```http
POST /cases/consolidate
```

**Request Body:**
```json
{
  "case_ids": ["case-1", "case-2", "case-3"],
  "concept": "Merged: Common pattern",
  "vault": "default"
}
```

Requires at least 2 `case_ids`. Calls `muninn_consolidate`.

**Response (200 OK):**
```json
{
  "vault": "default",
  "merged_id": "01KNE7...",
  "result": {"id": "01KNE7..."}
}
```

---

## Vault Statistics

```http
GET /vault/stats?vault=default
```

**Response (200 OK):**
```json
{
  "vault": "default",
  "total_memories": 34830,
  "health": "good",
  "enrichment_mode": "inline",
  "contradiction_count": 0,
  "contradictions": []
}
```

Fields come from MuninnDB's `muninn_status` and `muninn_contradictions` tools.

---

## Session Continuity

```http
GET /session/recent?vault=default&limit=5
```

Returns recent memory activity via `muninn_session`. Defaults to last 24 hours.

**Response (200 OK):**
```json
{
  "vault": "default",
  "memories": [
    {
      "writes": [
        {"id": "01KNE6...", "concept": "...", "created_at": "2026-04-05T..."}
      ],
      "activations": 0,
      "since": "2026-04-04T..."
    }
  ]
}
```

---

## Entity Graph Endpoints

### List Entities

```http
GET /vault/entities?vault=default
```

**Response (200 OK):**
```json
{
  "vault": "default",
  "entities": []
}
```

### Entity Detail

```http
GET /vault/entities/{entity_name}?vault=default
```

Returns 200 with entity details or 404 if not found.

### Entity Timeline

```http
GET /vault/entities/{entity_name}/timeline?vault=default
```

### Entity Cases

```http
GET /vault/entities/{entity_name}/cases?vault=default
```

---

## Graph Traversal

BFS traversal from a starting engram.

```http
POST /traverse
```

**Request Body:**
```json
{
  "start_id": "01KM3S...",
  "max_depth": 3,
  "relation_filter": ["supports", "contradicts"],
  "vault": "default"
}
```

**Response (200 OK):**
```json
{
  "start_id": "01KM3S...",
  "vault": "default",
  "result": {
    "nodes": [
      {"id": "01KM3S...", "concept": "...", "hop_dist": 0}
    ],
    "edges": null,
    "total_reachable": 1,
    "query_ms": 0
  }
}
```

---

## Error Responses

| Status | Description |
|--------|-------------|
| **200 OK** | Request succeeded |
| **400 Bad Request** | Invalid input (e.g., consolidate with < 2 case_ids) |
| **404 Not Found** | Entity not found, or request_id expired |
| **405 Method Not Allowed** | Wrong HTTP method |
| **422 Unprocessable Entity** | Missing required fields or invalid JSON |
| **500 Internal Server Error** | Server error (check logs) |

**Error Response Format:**
```json
{
  "detail": "At least 2 case_ids required"
}
```
