---
name: dalil-ingest
description: Ingest knowledge files (CSV, PDF) into Dalil's memory
mode: agent
argument-hint: "<file-path> [--vault=default] [--tags=tag1,tag2] [--type=csv|pdf]"
allowed-tools:
  - Bash
  - Glob
  - Read
---

# Dalil Ingest

Ingest knowledge files into Dalil's MuninnDB-backed memory. Supports CSV and PDF.
File type is auto-detected from extension unless `--type` is specified.

## Variables

- `FILE_PATH`: `$ARGUMENTS` with flags stripped — path to the file (required)
- `VAULT`: value of `--vault` flag, default `default`
- `TAGS`: value of `--tags` flag, comma-separated, default empty
- `FILE_TYPE`: value of `--type` flag, or auto-detected from extension
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO verify the file exists before attempting ingestion
- DO report the number of cases created
- DO NOT ingest files that look like credentials, secrets, or env files

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

### Step 3 — Report

Parse the response and output:

```
## Ingestion Complete

**Request ID:** {request_id}
**Source:** {file_path}
**Type:** {source_type}
**Cases Created:** {cases_created}
**Vault:** {vault}
```

If cases_created is 0, warn that the file may be empty or unparseable.
