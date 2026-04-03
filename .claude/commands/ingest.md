---
name: dalil-ingest
description: Ingest knowledge files (CSV, PDF) into Dalil's memory
mode: agent
argument-hint: "<file-path> [--vault=default] [--tags=tag1,tag2] [--type=csv|pdf] [--evolve=case_id] [--consolidate]"
allowed-tools:
  - Bash
  - Glob
  - Read
---

# Dalil Ingest

Ingest knowledge files into Dalil's MuninnDB-backed memory. Supports CSV and PDF.
File type is auto-detected from extension unless `--type` is specified.

Enrichment (entity extraction, summarization, relationship detection) is handled by MuninnDB's
background pipeline. Source-provided entities, relationships, and summaries are passed through
as inline enrichment.

Additional capabilities: evolve existing cases (`PUT /cases/{id}`) and consolidate
duplicates (`POST /cases/consolidate`).

## Variables

- `FILE_PATH`: `$ARGUMENTS` with flags stripped — path to the file (required)
- `VAULT`: value of `--vault` flag, default `default`
- `TAGS`: value of `--tags` flag, comma-separated, default empty
- `FILE_TYPE`: value of `--type` flag, or auto-detected from extension
- `EVOLVE_CASE_ID`: value of `--evolve` flag — if set, update an existing case instead of creating new
- `CONSOLIDATE`: presence of `--consolidate` flag — if set, run deduplication after ingestion
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO verify the file exists before attempting ingestion
- DO report the number of cases created
- DO NOT ingest files that look like credentials, secrets, or env files
- Enrichment happens in MuninnDB's background pipeline — no need to wait for it
- If `--evolve` is used, update the existing case rather than creating a new one
- If `--consolidate` is used, run deduplication after ingestion completes

---

## Workflow

### Step 1 — Validate File

Check the file exists and determine type:

```bash
file_path="${FILE_PATH}"
if [[ ! -f "$file_path" ]]; then
  echo "FILE_NOT_FOUND: $file_path"
  exit 1
fi

ext="${file_path##*.}"
echo "File: $file_path | Extension: $ext"
```

If the file matches `*.env`, `*credentials*`, `*secret*`, `*token*` — refuse and stop.

### Step 2 — Ingest via Upload

Use multipart upload (works with any file path):

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"

# Determine endpoint from type
if [[ "$FILE_TYPE" == "pdf" ]] || [[ "$ext" == "pdf" ]]; then
  endpoint="/ingest/pdf/upload"
elif [[ "$FILE_TYPE" == "csv" ]] || [[ "$ext" == "csv" ]]; then
  endpoint="/ingest/csv/upload"
else
  echo "Unsupported file type: $ext (use --type=csv or --type=pdf)"
  exit 1
fi

curl -sf -X POST "${dalil_url}${endpoint}" \
  -F "file=@${file_path}" \
  -F "vault=${VAULT}" \
  -F "tags=${TAGS}"
```

### Step 3 — Evolve Existing Case (if --evolve)

If `EVOLVE_CASE_ID` is set, update the existing case instead of creating new ones:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X PUT "${dalil_url}/cases/${EVOLVE_CASE_ID}" \
  -H "Content-Type: application/json" \
  -d "{
    \"vault\": \"${VAULT}\",
    \"content\": \"$(cat ${FILE_PATH})\",
    \"tags\": [${TAGS}]
  }"
```

### Step 4 — Consolidate Duplicates (if --consolidate)

If `CONSOLIDATE` flag is present, run deduplication:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/cases/consolidate" \
  -H "Content-Type: application/json" \
  -d "{\"vault\": \"${VAULT}\"}"
```

Report any cases that were merged.

### Step 5 — Report

Parse the response and output:

```
## Ingestion Complete

**Request ID:** {request_id}
**Source:** {file_path}
**Type:** {source_type}
**Cases Created:** {cases_created}
**Vault:** {vault}
**Enrichment:** handled by MuninnDB background pipeline
**Consolidation:** {if --consolidate, report merged cases}
```

If cases_created is 0, warn that the file may be empty or unparseable.
