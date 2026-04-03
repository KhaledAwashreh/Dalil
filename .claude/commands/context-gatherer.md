---
name: dalil-context-gatherer
description: Gathers and synthesizes context from Dalil for a task — feature, bug fix, or investigation
mode: agent
argument-hint: "<task description> [--vault=default] [--tags=tag1,tag2] [--depth=normal|deep]"
allowed-tools:
  - Bash
  - Agent
  - Read
  - Glob
  - Grep
---

# Dalil Context Gatherer

Sub-agent that gathers comprehensive context from Dalil for a given task.
Designed to be called by other agents (feature builders, bug fixers, investigators)
who need grounded domain context before proceeding.

Unlike a single `/dalil-consult`, this agent runs multiple queries, cross-references
results, checks for contradictions, and produces a structured context package.

Can also leverage graph traversal (`/traverse`) for relationship-based exploration,
session continuity (`/session/recent`) for ongoing context, and entity graph
(`/vault/entities/*`) for entity-centric exploration.

## Variables

- `TASK`: `$ARGUMENTS` with flags stripped — description of what the caller is working on (required)
- `VAULT`: value of `--vault` flag, default `default`
- `TAGS`: value of `--tags` flag, comma-separated, default empty
- `DEPTH`: value of `--depth` flag, `normal` or `deep`, default `normal`
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO NOT fabricate context — only use what Dalil returns
- DO cross-reference results from multiple queries for consistency
- DO flag contradictions between cases
- DO include provenance (case IDs, sources) for every fact
- DO include all request_ids so the caller can send feedback later
- Keep output under 500 lines unless `--depth=deep`

---

## Workflow

### Phase 1 — Vault Health Check

Run `/dalil-check` as a sub-agent for the target vault:

```
Prompt: /dalil-check --vault=${VAULT}
```

If the vault is empty, output `VAULT_EMPTY: true` and stop.
If there are contradictions, note them — they'll be relevant later.

### Phase 2 — Primary Consultation

Run `/dalil-consult` with the full task description:

```
Prompt: /dalil-consult "${TASK}" --vault=${VAULT} --tags=${TAGS}
```

Capture the `request_id` and all returned cases.

### Phase 3 — Session Continuity

Check for recent session context that may be relevant:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf "${dalil_url}/session/recent?vault=${VAULT}"
```

If recent consultations are related to the current task, incorporate their context to avoid redundant queries.

### Phase 4 — Decompose and Query

Break the task into 2-4 sub-questions based on what the primary consultation returned.
For each sub-question, run a focused consultation:

```
Prompt: /dalil-consult "${SUB_QUESTION}" --vault=${VAULT}
```

Examples of decomposition:
- Feature task → "what similar features were built before?", "what risks were encountered?", "what frameworks apply?"
- Bug fix → "what caused similar bugs?", "what systems are affected?", "what fixes were applied before?"

If `--depth=deep`, decompose into up to 6 sub-questions.

### Phase 5 — Graph Traversal

For high-relevance cases from previous phases, use `/traverse` to explore connected cases:

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf -X POST "${dalil_url}/traverse" \
  -H "Content-Type: application/json" \
  -d "{\"case_id\": \"${CASE_ID}\", \"vault\": \"${VAULT}\", \"depth\": 2}"
```

Also check the entity graph for entity-centric exploration:

```bash
curl -sf "${dalil_url}/vault/entities?vault=${VAULT}&entity=${ENTITY_NAME}"
```

This surfaces related cases that keyword search might miss.

### Phase 6 — Cross-Reference

Compare results across all consultations:
- Cases that appear in multiple queries → high relevance, note them
- Cases that contradict each other → flag as contradictions
- Cases with low confidence (< 0.5) → mark as uncertain

### Phase 7 — Output

Produce a structured context package:

```
## Context Package for: {TASK}

**Vault:** {vault}
**Queries Run:** {count}
**Unique Cases Found:** {count}
**Request IDs:** {list of all request_ids for feedback}

### Key Context
{Synthesized findings from all consultations — the most relevant facts, ordered by relevance}

### Related Cases
| Title | Type | Industry | Score | Appeared In |
|-------|------|----------|-------|-------------|
| ...   | ...  | ...      | ...   | query 1, 3  |

### Contradictions
{Any cases that contradict each other, with both sides presented}

### Gaps
{What the task needs that the vault doesn't cover — missing knowledge areas}

### Sources
- {source_type}: {title} (case_id: {id})

---
Feedback: `/dalil-feedback {request_id} useful` for each helpful consultation
```
