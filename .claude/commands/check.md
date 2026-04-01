---
name: dalil-check
description: Check vault knowledge health — contradictions, confidence distribution, coverage
mode: agent
argument-hint: "[--vault=default]"
allowed-tools:
  - Bash
---

# Dalil Check

Check the health and quality of knowledge in a Dalil vault.
Surfaces contradictions, confidence distribution, engram count, and storage usage.

Use this before starting work that depends on the vault's knowledge being reliable.

## Variables

- `VAULT`: value of `--vault` flag or first argument, default `default`
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO flag vaults with 0 engrams — the consumer should ingest knowledge first
- DO flag high contradiction counts as a warning
- DO flag if average confidence is below 0.5

---

## Workflow

### Step 1 — Fetch Stats

```bash
dalil_url="${DALIL_URL:-http://localhost:8000}"
curl -sf "${dalil_url}/vault/stats?vault=${VAULT}"
```

If Dalil is unreachable, output `DALIL_DOWN: true` and stop.

### Step 2 — Analyze and Report

Parse the response and present:

```
## Vault Health: {vault}

**Engrams:** {engram_count}
**Storage:** {storage_bytes} bytes
**Contradictions:** {contradiction_count}

### Confidence Distribution
{confidence_distribution as a simple breakdown}

### Coherence
{coherence_scores}

### Warnings
- [if engram_count == 0] Vault is empty — ingest knowledge before consulting
- [if contradiction_count > 0] {contradiction_count} contradictions found — review before relying on this vault
- [if low confidence engrams dominate] Most knowledge has low confidence — results may be unreliable
```

### Step 3 — Recommendations

Based on the stats, suggest actions:

- Empty vault → suggest `/dalil-ingest`
- Contradictions → suggest reviewing conflicting cases
- Low confidence → suggest re-ingesting with better source data
- Healthy vault → confirm it's ready for consultation
