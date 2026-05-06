---
name: dalil-ingest
description: Ingest knowledge files (CSV, PDF) or Confluence pages/spaces into Dalil's memory
mode: agent
argument-hint: "<file-path-or-url> [--vault=default] [--tags=tag1,tag2] [--type=csv|pdf|confluence] [--space=KEY] [--limit=25] [--evolve=case_id] [--consolidate]"
allowed-tools:
  - Bash
  - Glob
  - Read
---

# Dalil Ingest

Ingest knowledge into Dalil's MuninnDB-backed memory. Supports CSV, PDF, and Confluence (pages or entire spaces).

Enrichment (entity extraction, summarization, relationship detection) is handled by MuninnDB's
background pipeline.

## Variables

- `INPUT`: `$ARGUMENTS` with flags stripped — file path or Confluence URL (required)
- `VAULT`: value of `--vault` flag, default `default`
- `TAGS`: value of `--tags` flag, comma-separated, default empty
- `FILE_TYPE`: value of `--type` flag, or auto-detected from extension/URL
- `SPACE_KEY`: value of `--space` flag — if set, ingest an entire Confluence space
- `LIMIT`: value of `--limit` flag, default `25` — max pages when ingesting a space
- `EVOLVE_CASE_ID`: value of `--evolve` flag — if set, update an existing case
- `CONSOLIDATE`: presence of `--consolidate` flag — if set, run deduplication after ingestion
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO verify file exists before attempting file ingestion
- DO check OAuth auth status before Confluence ingestion
- DO report the number of cases created
- DO NOT ingest files that look like credentials, secrets, or env files

---

## Workflow

### Step 1 — Detect Input Type

Determine the ingestion type from the input:

- If `--space` is set → Confluence space ingestion
- If input starts with `http` and contains `atlassian.net/wiki` → Confluence page URL
- If input ends with `.csv` → CSV file
- If input ends with `.pdf` → PDF file
- If `--type` is set, use that override

### Step 2a — File Ingestion (CSV/PDF)

Check the file exists, then upload:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"

if [[ "$FILE_TYPE" == "pdf" ]] || [[ "$ext" == "pdf" ]]; then
  endpoint="/ingest/pdf/upload"
elif [[ "$FILE_TYPE" == "csv" ]] || [[ "$ext" == "csv" ]]; then
  endpoint="/ingest/csv/upload"
fi

curl -sf -X POST "${dalil_url}${endpoint}" \
  -F "file=@${file_path}" \
  -F "vault=${VAULT}" \
  -F "tags=${TAGS}"
```

### Step 2b — Confluence Page Ingestion

First check OAuth status:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf "${dalil_url}/auth/status?provider=atlassian"
```

If not authenticated, tell the user to visit `http://localhost:8000/auth/login/atlassian` first.

Then ingest the page:

```bash
curl -sf -X POST "${dalil_url}/ingest/confluence" \
  -H "Content-Type: application/json" \
  -d '{"url": "${URL}", "vault": "${VAULT}", "tags": [${TAGS}]}'
```

### Step 2c — Confluence Space Ingestion

Same auth check as above, then:

```bash
curl -sf -X POST "${dalil_url}/ingest/confluence" \
  -H "Content-Type: application/json" \
  -d '{"space_key": "${SPACE_KEY}", "vault": "${VAULT}", "tags": [${TAGS}], "limit": ${LIMIT}}'
```

Note: `limit` defaults to 25 pages. Increase with `--limit` for larger spaces.

### Step 3 — Evolve Existing Case (if --evolve)

If `EVOLVE_CASE_ID` is set, update the existing case:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X PUT "${dalil_url}/cases/${EVOLVE_CASE_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"case_id\": \"${EVOLVE_CASE_ID}\", \"vault\": \"${VAULT}\", \"content\": \"...\", \"concept\": \"Updated via ingestion\"}"
```

### Step 4 — Consolidate Duplicates (if --consolidate)

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/cases/consolidate" \
  -H "Content-Type: application/json" \
  -d '{"case_ids": ["id-1", "id-2"], "vault": "${VAULT}"}'
```

### Step 5 — Report

```
## Ingestion Complete

**Request ID:** {request_id}
**Source:** {input}
**Type:** {source_type}
**Cases Created:** {cases_created}
**Vault:** {vault}
**Enrichment:** handled by MuninnDB background pipeline
```

If cases_created is 0, warn that the source may be empty or inaccessible.
For Confluence: if 401/403, suggest re-authenticating via `http://localhost:8000/auth/login/atlassian`.
