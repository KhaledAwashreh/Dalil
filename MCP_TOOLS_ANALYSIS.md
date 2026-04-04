# MuninnDB MCP Tools - Complete Analysis

## Summary

**Repository**: [scrypster/muninndb](https://github.com/scrypster/muninndb)  
**Documentation**: Feature Reference lists **35 tools**, but code tests expect **36** (discrepancy identified)

---

## ⚠️ Critical Finding: Tool Count Discrepancy

- **README claims**: 35 MCP tools
- **Code test expects**: 36 tools ([internal/mcp/tools_test.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools_test.go#L7))
- **Missing from docs**: `muninn_entity_state_batch` (exists in code but not documented in feature-reference.md summary)

---

## Complete MCP Tools Reference

| # | Tool Name | Purpose/Description | Code Reference | Dalil Uses | Notes |
|---|-----------|-------------------|-----------------|-----------|-------|
| 1 | `muninn_remember` | Store a new memory (engram) with atomic concept-one-fact design | [tools.go#L3-L15](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L3-L15) | ✅ YES | Core write operation |
| 2 | `muninn_remember_batch` | Store multiple memories at once (max 50 per batch) | [tools.go#L82-L93](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L82-L93) | ✅ YES | Used for bulk ingestion |
| 3 | `muninn_recall` | Semantic search with context, modes (semantic/recent/balanced/deep), profiles (default/causal/confirmatory/adversarial/structural) | [tools.go#L161-L173](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L161-L173) | ❌ NO | *Dalil references `muninn_activate` (doesn't exist)* |
| 4 | `muninn_read` | Fetch a single memory by ULID with full content plus caller-provided entities | [tools.go#L187-L214](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L187-L214) | ❌ NO | Read-only indexed lookup |
| 5 | `muninn_forget` | Soft-delete a memory (7-day recovery window) | [tools.go#L187-L214](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L187-L214) | ❌ NO | Recoverable deletion |
| 6 | `muninn_link` | Create or strengthen association between two memories with typed relations (16 types) | [tools.go#L219-L220](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L219-L220) | ✅ YES | Manual knowledge-graph links |
| 7 | `muninn_contradictions` | Check for semantic contradictions between memories | [handlers.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/handlers.go) | ✅ YES | Bayesian confidence updates |
| 8 | `muninn_status` | Health and stats: coherence, orphan ratio, vault metrics | [handlers.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/handlers.go) | ✅ YES | Vault diagnostics |
| 9 | `muninn_guide` | Get vault-aware usage instructions (call on first connect) | [tools.go#L387-L410](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L387-L410) | ❌ NO | AI onboarding tool |
| 10 | `muninn_evolve` | Update memory and archive old version (lifecycle progression) | [tools.go#L302-L322](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L302-L322) | ✅ YES | Memory versioning |
| 11 | `muninn_consolidate` | Merge N memories into 1 (deduplication, coherence management) | [handlers.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/handlers.go) | ✅ YES | Semantic dedup |
| 12 | `muninn_session` | Recent activity summary (activation/write events since timestamp) | [tools.go#L135-L157](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L135-L157) | ❌ NO | Session context replay |
| 13 | `muninn_decide` | Record a decision with rationale and link to supporting evidence | [tools.go#L287-L302](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L287-L302) | ❌ NO | Decision tracking |
| 14 | `muninn_restore` | Recover a soft-deleted memory within 7-day window | [tools.go#L302-L322](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L302-L322) | ❌ NO | Recovery tool |
| 15 | `muninn_traverse` | BFS graph exploration from a start memory, configurable depth/relation filters | [tools.go#L330-L342](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L330-L342) | ❌ NO | Knowledge graph navigation |
| 16 | `muninn_explain` | Score breakdown for debugging recall (why memory ranked high/low) | [tools.go#L342-L356](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L342-L356) | ✅ YES | Transparency/debugging |
| 17 | `muninn_state` | Change lifecycle state (planning→active→paused→completed→archived) | [tools.go#L356-L370](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L356-L370) | ❌ NO | Workflow management |
| 18 | `muninn_list_deleted` | List soft-deleted memories within 7-day recovery window | [tools.go#L370-L387](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L370-L387) | ❌ NO | Recovery discovery |
| 19 | `muninn_retry_enrich` | Re-queue memory for plugin enrichment (entity extraction, summarization) | [tools.go#L387-L410](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L387-L410) | ❌ NO | Enrichment management |
| 20 | `muninn_remember_tree` | Write nested hierarchy (outlines, task trees) as linked engrams; returns root_id + node_map | [tools.go#L463-L480](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L463-L480) | ❌ NO | Hierarchical memory (MCP-only) |
| 21 | `muninn_recall_tree` | Retrieve full ordered hierarchy from root_id; all nodes with metadata | [tools.go#L527-L553](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L527-L553) | ❌ NO | Hierarchical retrieval |
| 22 | `muninn_add_child` | Add single child node to existing parent tree without resending whole structure | [tools.go#L582-L597](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L582-L597) | ❌ NO | Incremental tree updates |
| 23 | `muninn_entities` | List all known entities in vault sorted by mention count; optional state filter | [tools.go#L707-L725](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L707-L725) | ❌ NO | Entity discovery |
| 24 | `muninn_entity` | Full aggregate view: entity metadata, engrams mentioning it, relationships | [tools.go#L707-L725](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L707-L725) | ❌ NO | Entity details |
| 25 | `muninn_entity_clusters` | Co-occurrence clustering; returns entity pairs frequently appearing together | [tools.go#L553-L568](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L553-L568) | ❌ NO | Entity relationship discovery |
| 26 | `muninn_entity_state` | Set entity lifecycle state (active/deprecated/merged/resolved) | [tools.go#L434-L463](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L434-L463) | ❌ NO | Entity state management |
| 27 | `muninn_entity_state_batch` | Batch version of muninn_entity_state (multiple entities at once) | [context.go#L150-L165](https://github.com/scrypster/muninndb/blob/main/internal/mcp/context.go#L150-L165) | ❌ NO | **Not in feature-reference docs** |
| 28 | `muninn_entity_timeline` | Chronological view of entity evolution (all engrams mentioning it, oldest-first) | [tools.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go) | ❌ NO | Entity history |
| 29 | `muninn_find_by_entity` | Fast reverse-index lookup: all memories mentioning a given entity | [tools.go#L410-L434](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L410-L434) | ❌ NO | Entity-to-engram discovery |
| 30 | `muninn_similar_entities` | Trigram duplicate detection; returns entity name pairs above similarity threshold | [tools.go#L612-L625](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L612-L625) | ❌ NO | Entity deduplication |
| 31 | `muninn_merge_entity` | Merge entity_a into canonical entity_b; relinks all engrams; supports dry_run | [tools.go#L612-L625](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L612-L625) | ❌ NO | Entity normalization |
| 32 | `muninn_export_graph` | Export entity relationship graph as JSON-LD (default) or GraphML for visualisation | [tools.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go) | ❌ NO | Knowledge graph export |
| 33 | `muninn_feedback` | SGD scoring weight update; pass `useful` (bool) to signal helpful retrieval | [handlers.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/handlers.go) | ✅ YES | Reinforcement learning |
| 34 | `muninn_provenance` | Full audit trail: who wrote, what changed, why (timestamps, session IDs) | [tools.go#L648-L669](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L648-L669) | ❌ NO | Compliance/audit |
| 35 | `muninn_replay_enrichment` | Re-run enrichment pipeline delta (missing entities/relationships/classification/summary) | [tools.go#L648-L669](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L648-L669) | ❌ NO | Plugin management |
| 36 | `muninn_where_left_off` | Most recently accessed memories for session context (O(limit) performance) | [tools.go#L387-L410](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go#L387-L410) | ❌ NO | **Undocumented in summary** |

---

## Dalil's Current Tool Usage

### ✅ Tools Actively Used (9 tools)
1. **`muninn_remember`** — Ingestion of cases as memories
2. **`muninn_remember_batch`** — Bulk case loading (chunked to 50-item batches)
3. **`muninn_feedback`** — User-guided SGD weight tuning for relevance
4. **`muninn_link`** — Manual cross-case association creation
5. **`muninn_explain`** — Query score breakdown for transparency
6. **`muninn_status`** — Vault health metrics and coherence monitoring
7. **`muninn_contradictions`** — Conflict detection between cases
8. **`muninn_evolve`** — Case updates with version archiving
9. **`muninn_consolidate`** — Semantic deduplication and merging

### ❌ Tools NOT Used (27 tools)
- `muninn_recall` (Dalil docs incorrectly reference `muninn_activate` which doesn't exist)
- `muninn_read`, `muninn_forget`, `muninn_session`, `muninn_decide`, `muninn_restore`
- `muninn_traverse`, `muninn_state`, `muninn_list_deleted`, `muninn_retry_enrich`, `muninn_guide`
- All hierarchical memory tools (`muninn_remember_tree`, `muninn_recall_tree`, `muninn_add_child`)
- All entity graph tools (`muninn_entities`, `muninn_entity`, `muninn_entity_clusters`, `muninn_entity_state`, `muninn_entity_state_batch`, `muninn_entity_timeline`, `muninn_find_by_entity`, `muninn_similar_entities`, `muninn_merge_entity`)
- Graph export: `muninn_export_graph`
- Audit & enrichment: `muninn_provenance`, `muninn_replay_enrichment`, `muninn_where_left_off`

---

## Critical Issues Found

### 1. **Tool Count Mismatch**
- README claims **35 tools**
- Code tests enforce **36 tools** (test file: [smoke_exhaustive_test.go](https://github.com/scrypster/muninndb/blob/main/cmd/muninn/smoke_exhaustive_test.go#L0-L37), [tools_test.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools_test.go#L7))
- Missing from feature-reference docs: `muninn_entity_state_batch` and `muninn_where_left_off`

### 2. **Dalil References Non-Existent Tool**
- Dalil documentation mentions `muninn_activate` 
- **This tool does not exist** in MuninnDB
- Should be: `muninn_recall` (activate means retrieve/search memories)
- **Verification**: No `muninn_activate` in tools.go, handlers.go, context.go, or test files

### 3. **Unused High-Value Tools**
Dalil is not leveraging powerful features:
- **`muninn_traverse`** — Would enable deep reasoning over case relationship chains
- **`muninn_entity_clusters`** — Would auto-discover related cases via entity co-occurrence
- **`muninn_session`** — Could restore prior case context automatically
- **`muninn_where_left_off`** — Could resume interrupted investigations

---

## MCP Tools by Category

### Core Write Operations (3)
`muninn_remember`, `muninn_remember_batch`, `muninn_link`

### Core Read Operations (1)
`muninn_recall`

### Memory Management (9)
`muninn_read`, `muninn_forget`, `muninn_restore`, `muninn_evolve`, `muninn_consolidate`, `muninn_decide`, `muninn_state`, `muninn_list_deleted`, `muninn_guide`

### Debugging & Analytics (4)
`muninn_explain`, `muninn_status`, `muninn_contradictions`, `muninn_traverse`

### Hierarchical Memory (3)
`muninn_remember_tree`, `muninn_recall_tree`, `muninn_add_child`

### Entity Graph (10)
`muninn_entities`, `muninn_entity`, `muninn_entity_clusters`, `muninn_entity_state`, `muninn_entity_state_batch`, `muninn_entity_timeline`, `muninn_find_by_entity`, `muninn_similar_entities`, `muninn_merge_entity`, `muninn_export_graph`

### Feedback & Learning (1)
`muninn_feedback`

### Enrichment & Plugins (2)
`muninn_retry_enrich`, `muninn_replay_enrichment`

### Provenance & Context (2)
`muninn_provenance`, `muninn_where_left_off`

### Session Management (1)
`muninn_session`

---

## Recommendations for Dalil

### High Priority
1. **Fix documentation** — Change `muninn_activate` to `muninn_recall` in all Dalil docs and code
2. **Implement `muninn_recall`** — Replace any placeholder activation logic with proper semantic search  
3. **Add `muninn_where_left_off`** — Resume prior case context on each new query

### Medium Priority
4. **Enable `muninn_traverse`** — Leverage relationship graphs for multi-hop reasoning
5. **Add `muninn_session`** — Group case retrievals into named investigation sessions (audit trails)
6. **Expose `muninn_entity_clusters`** — Auto-suggest related cases based on entity co-occurrence

### Low Priority (Advanced)
7. **Use hierarchical memory** — Structure case hierarchies (jurisdiction → district → case type)
8. **Implement `muninn_decide`** — Record legal decisions with rationale and linked precedent

---

## Source Code References

**Tool Definitions**: [internal/mcp/tools.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools.go)  
**Handler Implementations**: [internal/mcp/handlers.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/handlers.go)  
**Tool Classification**: [internal/mcp/context.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/context.go) (isMutatingTool, isReadOnlyTool)  
**Test Validation**: [internal/mcp/tools_test.go](https://github.com/scrypster/muninndb/blob/main/internal/mcp/tools_test.go) (TestAllToolDefinitionsCount = 36)  
**Integration Tests**: [cmd/muninn/smoke_exhaustive_test.go](https://github.com/scrypster/muninndb/blob/main/cmd/muninn/smoke_exhaustive_test.go) (TestSmoke_AllMCPTools)

---

## Verification Status

| Claim | Status | Evidence |
|-------|--------|----------|
| 35 tools claimed | ❌ INCORRECT | Code enforces 36 tools; feature-reference.md summarizes only 35 |
| `muninn_activate` exists | ❌ FALSE | Not in any MuninnDB file; Dalil documentation error |
| Dalil uses correct tool names | ⚠️ PARTIAL | 9 tools accurate, but references non-existent `muninn_activate` |
| All tools documented | ❌ INCOMPLETE | `muninn_entity_state_batch` and `muninn_where_left_off` missing from feature-reference summary |

