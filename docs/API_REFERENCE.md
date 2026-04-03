# API Reference

Base URL: `http://localhost:8475/api` (or `http://dalil:8475/api` from Docker Compose)

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
  "status": "healthy",
  "muninndb": "healthy",
  "uptime_seconds": 1234.5
}
```

### Consultation

Retrieve relevant cases from a vault and optionally synthesize an LLM response.

```http
POST /consult
```

**Request Body:**
```json
{
  "vault": "myproject",
  "query": "What's the best approach to handling API rate limiting?",
  "max_results": 5,
  "synthesize": true
}
```

**Response (200 OK):**
```json
{
  "query_id": "uuid-here",
  "query": "...",
  "vault": "myproject",
  "retrieved_cases": [
    {
      "id": "case-1",
      "title": "Rate Limiting Strategy",
      "type": "playbook",
      "content": "...",
      "confidence": 0.92,
      "relevance_score": 0.87
    }
  ],
  "synthesis": "Based on the best practices in your knowledge base, here's the recommended approach: ...",
  "synthesis_model": "gpt-4o",
  "total_cases": 5,
  "search_time_ms": 45,
  "synthesis_time_ms": 320
}
```

### Feedback (Learning)

Log positive/negative feedback on a consultation result to improve future retrievals.

```http
POST /feedback
```

**Request Body:**
```json
{
  "vault": "myproject",
  "query_id": "uuid-here",
  "case_ids": ["case-1", "case-3"],
  "relevance": 0.95,
  "notes": "Excellent, these were the exact cases I was looking for"
}
```

**Response (200 OK):**
```json
{
  "query_id": "uuid-here",
  "cases_updated": 2,
  "confidence_boost": "+0.08",
  "status": "recorded"
}
```

---

## Ingestion Endpoints

### Ingest CSV

```http
POST /ingest/csv
```

**Form Data:**
- `vault` (string): Target vault
- `file` (file): CSV file

**CSV Schema** (columns):
- `title` (required)
- `content` (required)
- `type` (optional, default: "consultation")
- `tags` (optional, comma-separated)
- `confidence` (optional, 0–1)

**Response (200 OK):**
```json
{
  "vault": "myproject",
  "ingested_rows": 42,
  "ingestion_id": "uuid-here",
  "summary": {
    "extracted_entities": 156,
    "graph_edges": 89,
    "total_tokens": 12450
  }
}
```

### Ingest PDF

```http
POST /ingest/pdf
```

**Form Data:**
- `vault` (string): Target vault
- `file` (file): PDF file
- `chunk_size` (optional, default: 1024)
- `chunk_overlap` (optional, default: 128)

**Response (200 OK):** Same format as CSV

### Ingest Confluence

```http
POST /ingest/confluence
```

**Request Body:**
```json
{
  "vault": "myproject",
  "confluence_base_url": "https://yourcompany.atlassian.net/wiki",
  "space_key": "ENGINEERING",
  "page_ancestor_id": "123456",
  "auth_token": "..."
}
```

**Response (200 OK):** Same format as CSV

---

## Vault Management Endpoints

### Vault Statistics

```http
GET /vault/stats?vault=myproject
```

**Response (200 OK):**
```json
{
  "vault": "myproject",
  "total_cases": 342,
  "total_entities": 1250,
  "total_edges": 890,
  "ingestion_count": 12,
  "last_ingestion": "2025-01-15T14:23:00Z",
  "total_tokens": 456000,
  "storage_size_mb": 23.4
}
```

### Vault Health

```http
GET /vault/health?vault=myproject
```

**Response (200 OK):**
```json
{
  "vault": "myproject",
  "status": "healthy",
  "index_status": "ready",
  "contradictions": 2,
  "orphaned_entities": 0,
  "index_fragmentation_pct": 5.2
}
```

### Recent Cases

```http
GET /vault/recent?vault=myproject&limit=10
```

**Response (200 OK):**
```json
{
  "vault": "myproject",
  "recent_cases": [
    {
      "id": "case-1",
      "title": "...",
      "type": "engagement",
      "created_at": "2025-01-15T12:30:00Z",
      "updated_at": "2025-01-15T13:45:00Z"
    }
  ],
  "total": 10
}
```

---

## Entity Management Endpoints

### List Entities

```http
GET /entities?vault=myproject
```

**Response (200 OK):**
```json
{
  "vault": "myproject",
  "entities": [
    {
      "id": "entity-1",
      "name": "Alice Johnson",
      "type": "person",
      "mention_count": 23,
      "first_seen": "2025-01-10T08:00:00Z",
      "last_seen": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 156
}
```

### Merge Entities

Merge duplicate entity records.

```http
POST /entities/merge
```

**Request Body:**
```json
{
  "vault": "myproject",
  "source_id": "entity-1",
  "target_id": "entity-2"
}
```

**Response (200 OK):**
```json
{
  "merged": true,
  "source_id": "entity-1",
  "target_id": "entity-2",
  "cases_updated": 12,
  "edges_consolidated": 8
}
```

### Delete Entity

```http
DELETE /entities/{entity_id}?vault=myproject
```

**Response (200 OK):**
```json
{
  "deleted": true,
  "entity_id": "entity-1",
  "cases_updated": 5
}
```

---

## Traversal Endpoints

### Graph Traversal

Explore relationships in the knowledge graph.

```http
POST /traverse
```

**Request Body:**
```json
{
  "vault": "myproject",
  "start_case_id": "case-1",
  "max_depth": 3,
  "relation_types": ["mentions", "contradicts", "related_to"],
  "limit": 50
}
```

**Response (200 OK):**
```json
{
  "start_case_id": "case-1",
  "traversal_id": "uuid-here",
  "paths": [
    {
      "path_length": 2,
      "cases": ["case-1", "case-5", "case-12"],
      "relations": ["mentions", "related_to"],
      "total_confidence": 0.87
    }
  ],
  "total_connected_cases": 23,
  "max_path_length": 3
}
```

---

## Error Responses

All endpoints return appropriate HTTP status codes:

| Status | Description |
|--------|-------------|
| **200 OK** | Request succeeded |
| **400 Bad Request** | Invalid input (missing required field, malformed JSON) |
| **404 Not Found** | Vault or resource not found |
| **409 Conflict** | Vault already exists or other conflict |
| **500 Internal Server Error** | Server error (check logs) |
| **503 Service Unavailable** | MuninnDB is unreachable |

**Error Response Format:**
```json
{
  "error": "Vault not found",
  "detail": "Vault 'nonexistent' does not exist",
  "status_code": 404,
  "timestamp": "2025-01-15T14:30:00Z"
}
```

---

## CLI Vault Management

Vault creation and management is CLI-only (not via HTTP):

```bash
# Create vault
dalil vault create --client myproject

# List vaults
dalil vault list

# Vault stats
dalil vault stats --vault myproject

# Generate API key
dalil vault key --vault myproject

# Clone vault
dalil vault clone --source production --destination staging

# Delete vault
dalil vault delete --vault old-project
```

See [SETUP.md](../SETUP.md) for full CLI reference.
