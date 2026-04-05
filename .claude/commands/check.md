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
Uses muninn_status for vault metrics and muninn_contradictions for contradiction pairs.

Use this before starting work that depends on the vault's knowledge being reliable.

## Variables

- `VAULT`: value of `--vault` flag or first argument, default `default`
- `DALIL_URL`: env var `DALIL_URL`, default `http://localhost:8000`

## Rules

- DO flag vaults with 0 total_memories — the consumer should ingest knowledge first
- DO flag contradiction pairs with details
- DO flag if health is not "good"
- DO note enrichment_mode

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

**Total Memories:** {total_memories}
**Health:** {health}
**Enrichment Mode:** {enrichment_mode}

### Contradictions
{If contradiction_count > 0, list each contradiction pair}
{If contradiction_count == 0: "No contradictions detected."}

### Warnings
- [if total_memories == 0] Vault is empty — ingest knowledge before consulting
- [if health != "good"] Vault health is "{health}" — investigate
- [if contradictions found] {count} contradiction pairs found — review details above
```

### Step 3 — Recommendations

Based on the stats, suggest actions:

- Empty vault → suggest `/dalil-ingest`
- Contradictions → show specific pairs, suggest resolving conflicting cases
- Unhealthy vault → suggest checking MuninnDB logs
- Healthy vault → confirm it's ready for consultation
