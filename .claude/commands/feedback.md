---
name: dalil-feedback
description: Send feedback on a Dalil consultation to improve future results
mode: agent
argument-hint: "<request_id> [--results=[{case_id, relevant},...]] [--comment=reason]"
allowed-tools:
  - Bash
---

# Dalil Feedback

Send per-case relevance feedback on a previous consultation. This improves Dalil's knowledge over time:

- Uses **muninn_feedback** (SGD weight tuning) under the hood to adjust case scoring
- Cases marked relevant that co-occur get automatic "supports" links via muninn_link
- Cases marked not relevant are **not archived** — MuninnDB adjusts their scoring naturally

## Variables

- `REQUEST_ID`: first positional argument (required)
- `RESULTS`: value of `--results` flag — JSON array of `[{case_id, relevant}]` per-case signals (required)
- `COMMENT`: value of `--comment` flag, default empty
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO provide per-case relevance signals in the `results` array
- DO include a comment when marking cases as not relevant — it helps explain why
- Marking a case not relevant does NOT archive it — MuninnDB handles scoring adjustment

---

## Workflow

### Step 1 — Validate

If `REQUEST_ID` or `RESULTS` is missing, print usage and stop:

```
Usage: /dalil-feedback <request_id> --results='[{"case_id":"...", "relevant": true}, ...]' [--comment="reason"]
```

### Step 2 — Send Feedback

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/feedback" \
  -H "Content-Type: application/json" \
  -d "{
    \"request_id\": \"${REQUEST_ID}\",
    \"results\": ${RESULTS},
    \"comment\": \"${COMMENT}\"
  }"
```

### Step 3 — Report

```
## Feedback Recorded

**Request ID:** {request_id}
**Cases Updated:** {list of case_ids and their relevance signals}
**Weight Adjustments:** {SGD tuning applied}
**Links Created:** {any "supports" links created between co-relevant cases}
```
