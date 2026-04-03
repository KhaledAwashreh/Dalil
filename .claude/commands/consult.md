---
name: dalil-consult
description: Query Dalil for grounded consulting context on any problem, feature, or bug
mode: agent
argument-hint: "<problem description> [--vault=default] [--tags=tag1,tag2] [--context=additional context]"
allowed-tools:
  - Bash
  - Agent
  - Read
  - Glob
  - Grep
---

# Dalil Consult

Query Dalil's knowledge base for relevant context, similar cases, and grounded recommendations.
Works as a standalone command or as a sub-agent called by other workflows.

## Variables

- `PROBLEM`: `$ARGUMENTS` with flags stripped — the question or problem description (required)
- `VAULT`: value of `--vault` flag, default `default`
- `TAGS`: value of `--tags` flag, comma-separated, default empty
- `CONTEXT`: value of `--context` flag, default empty
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO NOT fabricate cases or recommendations — only use what Dalil returns
- DO include the `request_id` in your output so feedback can be given later
- DO note confidence scores — these are MuninnDB Bayesian scores, not heuristics. Flag anything below 0.5 as low confidence
- DO present score breakdowns when available (`score_breakdowns` field) — shows how the score was composed
- If Dalil is unreachable, say so and stop — do not guess

---

## Workflow

### Step 1 — Parse Arguments

Extract `PROBLEM`, `VAULT`, `TAGS`, and `CONTEXT` from the arguments.

### Step 2 — Health Check

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf --max-time 3 "${dalil_url}/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"Dalil: {d.get('status', 'unknown')} | MuninnDB: {'connected' if d.get('muninn_connected') else 'disconnected'} | LLM: {d.get('llm_model', 'unknown')}\")
"
```

If Dalil is not reachable, output `DALIL_DOWN: true` and stop.

### Step 3 — Consult

Build and send the consultation request:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/consult" \
  -H "Content-Type: application/json" \
  -d "{
    \"problem\": \"${PROBLEM}\",
    \"context\": \"${CONTEXT}\",
    \"tags\": [${TAGS}],
    \"vault\": \"${VAULT}\"
  }"
```

### Step 4 — Parse and Present

Parse the response and present:

1. **Request ID** — for feedback later
2. **Recommendation** — the LLM-generated advice
3. **Similar Cases** — list with title, type, industry, score
4. **Score Breakdowns** — if `score_breakdowns` is present, show per-case scoring factors
5. **Sources** — where the knowledge came from
6. **Confidence** — MuninnDB Bayesian confidence score, flag if < 0.5
7. **Contradictions** — if any cases in the result contradict each other, note it
8. **Traversal Hint** — if results suggest deeper relationships, suggest using `/traverse` for graph exploration

### Step 5 — Output Format

```
## Dalil Consultation

**Request ID:** {request_id}
**Confidence:** {confidence}
**Tools Used:** {tools_used}

### Recommendation
{recommendation}

### Similar Cases
| Title | Type | Industry | Score |
|-------|------|----------|-------|
| ...   | ...  | ...      | ...   |

### Score Breakdowns
{If score_breakdowns present, show per-case breakdown of scoring factors}

### Sources
- {source_type}: {source_title}

---
To give feedback: `/dalil-feedback {request_id} [{case_id: "...", relevant: true/false}, ...]`
To explore related cases: `POST /traverse` with a case ID from above
```
