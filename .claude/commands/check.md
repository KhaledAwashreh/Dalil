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
Uses muninn_contradictions for actual contradiction pairs and muninn_status for coherence metrics.
Surfaces contradiction details, coherence score, orphan ratio, duplication pressure, and confidence distribution.

Use this before starting work that depends on the vault's knowledge being reliable.

## Variables

- `VAULT`: value of `--vault` flag or first argument, default `default`
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO flag vaults with 0 engrams — the consumer should ingest knowledge first
- DO flag contradiction pairs with details (concept_a vs concept_b, contradiction type)
- DO flag if coherence_score is below 0.7
- DO flag if orphan_ratio is above 0.3
- DO flag if duplication_pressure is high
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
**Coherence Score:** {coherence_score} (0.0-1.0)
**Orphan Ratio:** {orphan_ratio}
**Duplication Pressure:** {duplication_pressure}

### Confidence Distribution
{confidence_distribution as a simple breakdown}

### Contradictions
{For each contradiction pair from muninn_contradictions:}
- **{concept_a}** vs **{concept_b}** — type: {contradiction_type}

### Warnings
- [if engram_count == 0] Vault is empty — ingest knowledge before consulting
- [if coherence_score < 0.7] Low coherence ({coherence_score}) — vault knowledge may be fragmented
- [if orphan_ratio > 0.3] High orphan ratio ({orphan_ratio}) — many unlinked engrams
- [if duplication_pressure is high] Duplication pressure detected — consider consolidation
- [if contradictions found] {count} contradiction pairs found — review details above
- [if low confidence engrams dominate] Most knowledge has low confidence — results may be unreliable
```

### Step 3 — Recommendations

Based on the stats, suggest actions:

- Empty vault → suggest `/dalil-ingest`
- Contradictions → show specific pairs, suggest resolving conflicting cases
- High duplication → suggest `POST /cases/consolidate` to merge duplicates
- High orphan ratio → suggest adding relationships or re-ingesting with richer context
- Low coherence → suggest reviewing and linking related cases
- Low confidence → suggest re-ingesting with better source data
- Healthy vault → confirm it's ready for consultation
