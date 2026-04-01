---
name: dalil-feedback
description: Send feedback on a Dalil consultation to improve future results
mode: agent
argument-hint: "<request_id> <useful|not_useful> [--comment=reason]"
allowed-tools:
  - Bash
---

# Dalil Feedback

Send feedback on a previous consultation. This improves Dalil's knowledge over time:

- **useful** — re-activates returned cases (boosts temporal priority) and links them with "supports" relations
- **not_useful** — archives the returned cases with a reason

## Variables

- `REQUEST_ID`: first positional argument (required)
- `SIGNAL`: second positional argument, `useful` or `not_useful` (required)
- `COMMENT`: value of `--comment` flag, default empty
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO validate that signal is either `useful` or `not_useful`
- DO include a comment when marking `not_useful` — it helps explain why

---

## Workflow

### Step 1 — Validate

If `REQUEST_ID` or `SIGNAL` is missing, print usage and stop:

```
Usage: /dalil-feedback <request_id> <useful|not_useful> [--comment="reason"]
```

### Step 2 — Send Feedback

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/feedback" \
  -H "Content-Type: application/json" \
  -d "{
    \"request_id\": \"${REQUEST_ID}\",
    \"signal\": \"${SIGNAL}\",
    \"comment\": \"${COMMENT}\"
  }"
```

### Step 3 — Report

```
## Feedback Recorded

**Request ID:** {request_id}
**Signal:** {signal}
**Cases Affected:** {cases_affected}
**Actions:** {actions_taken}
```
