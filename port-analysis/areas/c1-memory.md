---
area: memory stack (capture, storage, indexing, retrieval, injection)
slug: c1-memory
coverage: "Memory Core plugin (turn capture, curated annotations, provenance, SQLite index schema, hybrid search ranking, dreaming promotion/consolidation, flush, forget/lineage, standing intents), Memory Wiki knowledge layer, active-memory recall lanes, memory-host-sdk, context-engine + legacy engine + memory prompt assembly, session-search vs memory-search, honcho/external provider path, multi-user scoping, memory tools"
date: 2026-10-09
commit: b0c330d2
---

# Memory stack (Memory Core, Wiki, active-memory, context engine)

## What it is / user-visible behavior

OpenClaw memory is **plain Markdown + one SQLite index**, organized into trust tiers with different write rules and injection behavior (`docs/concepts/memory-architecture.md:11`). Five design rules: no hidden state, writing is the hard part, the write path is the security boundary, deterministic gates with model judgment inside them, and failures never block replies (`docs/concepts/memory-architecture.md:30`).

Tiers (`docs/concepts/memory-architecture.md:55`):

| Tier | Surface | Written by | Injected |
| --- | --- | --- | --- |
| Instructions | `AGENTS.md`, workspace files | human | always |
| Curated core | `MEMORY.md`, `USER.md` | dreaming consolidation / direct user ask | session start, provenance-gated, budgeted |
| Episodic | `memory/YYYY-MM-DD.md`, transcripts | agent / flush / transcript ingestion | on recall only |
| Prospective | standing intents (SQLite) + cron | `intent` tool | only on trigger fire |
| Review | `DREAMS.md` | dreaming phases | never (human reading) |

User-visible surfaces:
- The agent has three memory tools: `memory_search` (semantic+keyword), `memory_get` (exact excerpt read), `intent` (event-conditioned standing intents) (`docs/concepts/memory.md:149`); all three are provided by the active memory plugin (default `memory-core`) (`docs/concepts/memory.md:157`).
- `MEMORY.md`/`USER.md` load at session start (budgeted) when eligible; daily notes load only via recall (`docs/concepts/memory.md:17`).
- Before compaction a silent **memory-flush turn** saves unwritten context to a daily note (`docs/concepts/memory.md:229`).
- Dreaming is on by default, schedules a cron sweep, and promotes only gated candidates into `MEMORY.md` (`docs/concepts/memory.md:285`).
- Active Memory is the deep "lane 2" recall that escalates to a blocking sub-agent only when deterministic recall found no strong hit (`docs/concepts/active-memory.md:10`).
- `memory-wiki` compiles durable knowledge into a claims/evidence wiki vault with its own tools `wiki_status/wiki_search/wiki_get/wiki_apply/wiki_lint` (`docs/concepts/memory.md:213`).
- `memory forget --dry-run` previews and then deletes session-derived artifacts and records forgotten sessions (`docs/concepts/memory-provenance.md:33`).

## End-to-end flow

```mermaid
flowchart LR
  A["Conversation turn"] -->|capture/mark provenance| B["Session transcript / daily note / flush"]
  B -->|session ingestion + curated annotations| C["Episodic writes: memory/*.md, session-corpus"]
  C -->|chunk 400/80 + embed + FTS| D["SQLite index: chunks + vec + FTS + provenance + recall metadata"]
  D -->|memory_search hybrid| E["BM25 + vector merge -> decay -> importance -> MMR"]
  E -->|memory_get / citations| F["Model context (tool results)"]
  D -->|dreaming gate + consolidation| G["Promotion into MEMORY.md / USER.md"]
  G -->|bootstrap, provenance-eligible| F
  B -->|trigger prefilter (Lane 1)| F
  A -->|recall intent + no strong hit| H["Active Memory escalation sub-agent"]
  H --> F
```

(Flow direction: conversation → extraction → store → retrieval → prompt injection; with the dreaming promotion feedback loop from store back into bootstrap injection.)

## Mechanisms

### 1. Turn capture & extraction (what gets written)
- During work the agent appends observations to daily notes; before compaction a flush turn saves unwritten context; at session end transcripts become ingestible evidence (`docs/concepts/memory-architecture.md:136`).
- The flush plan builder produces the flush prompt, target path `memory/YYYY-MM-DD.md`, soft threshold, and force-flush bytes (`extensions/memory-core/src/flush-plan.ts:63`); the prompt forbids overwriting `MEMORY.md`/`DREAMS.md` (`extensions/memory-core/src/flush-plan.ts:19`).
- Session ingestion scans transcript sources, drops non-interactive sessions (`sessionKind !== "interactive"` → null, `extensions/memory-core/src/session-ingestion.ts:132`), builds bounded snippets (`extensions/memory-core/src/session-ingestion.ts:34`), and stamps provenance per line (`extensions/memory-core/src/session-ingestion.ts:406`). It writes to `memory/.dreams/session-corpus/<day>.txt` via `appendSessionCorpusLines` (`extensions/memory-core/src/session-ingestion.ts:472`).
- Admission policy (`memoryPolicy.excludeSessions`) and forgotten-session tombstones exclude sources before transcript reads (`extensions/memory-core/src/session-ingestion.ts:187`).
- Curated annotations (trailing HTML comments) are parsed into `importance` (1–10), `triggers`, and `projectKey` by `extractCuratedEntryRecallMetadata` (`packages/memory-host-sdk/src/host/curated-annotations.ts:114`, importance clamped 1–10 at `:140`; project keys normalized at `:67`).

### 2. Provenance (unforgeable origin classes)
- Each indexed chunk carries `origin_class ∈ {owner,agent,untrusted,system}`, `session_kind ∈ {interactive,cron,heartbeat,subagent,unknown}`, `observed_at`, `supersedes_key` in a dedicated table the model cannot write through prose (`packages/memory-host-sdk/src/host/memory-schema-provenance.ts:7`).
- Transcript provenance is derived by `classifySessionMessageOrigin`: assistant → `agent` if turn origin is `owner` else turn origin, forced `untrusted` when `__openclaw.turnTainted` is set; user → `system` for `internal_system`, else `owner` when `senderIsOwner`, else `untrusted` (`packages/memory-host-sdk/src/host/session-provenance.ts:4`; caller defaults the turn origin to `untrusted` at `packages/memory-host-sdk/src/host/session-files.ts:711`).
- Every exported transcript line gets a `MemoryEntryProvenance` (`packages/memory-host-sdk/src/host/session-files.ts:810`).
- The chunk writer writes provenance with an `untrusted`/`unknown` fallback when none is supplied (`extensions/memory-core/src/memory/manager-chunk-writer.ts:127`).
- Automatic injection is gated by `isMemoryOriginEligibleForAutomaticInjection` (only `owner`/`agent`) (`packages/memory-host-sdk/src/host/types.ts:40`).

### 3. Where it lives / schema
- Canonical memory is files: `MEMORY.md`, optional `USER.md`, `memory/*.md`, plus `memory.search.extraPaths` (`docs/concepts/memory-builtin.md:259`); the index is per-agent SQLite at `~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite` (`docs/concepts/memory-builtin.md:150`).
- Canonical/derived schema is built by `ensureMemoryIndexSchema` (`packages/memory-host-sdk/src/host/memory-schema.ts:322`): `memory_index_chunks` and `memory_index_sources` (STRICT) (`packages/memory-host-sdk/src/host/memory-schema-base.ts:21`, `:79`), `memory_embedding_cache` (`:37`), `memory_index_state` revision counter (`:91`), and a rebuild-safe derived-table list (`:54`).
- Recall metadata is an additive owner table `memory_index_chunk_recall_metadata` (importance/triggers/project_key, `packages/memory-host-sdk/src/host/memory-schema-recall.ts:7`); legacy columns are migrated out of the chunk table (`:61`).
- Chunk embeddings are little-endian f64 BLOBs; sqlite-vec keeps a separate 32-bit index (`docs/concepts/memory-builtin.md:210`). Chunks are 400 tokens with 80-token overlap by default (`docs/concepts/memory-builtin.md:133`, configured via `manager-sync-ops.ts` chunking settings).

### 4. Indexing & search (ranking, embeddings, hybrid)
- `MemorySearchOrchestration.search()` runs keyword (FTS5) and vector legs and merges them (`extensions/memory-core/src/memory/manager-search-orchestration.ts:62`).
- FTS5 tables are created as `USING fts5(...)` with unicode61/trigram tokenizers (`packages/memory-host-sdk/src/host/memory-schema-fts.ts:225`, `:314`); keyword ranking uses `bm25()` (`extensions/memory-core/src/memory/manager-search.ts:344`) converted by `bm25RankToScore` (`extensions/memory-core/src/memory/keyword-query.ts:14`).
- `mergeHybridResults` fuses vector+keyword by weight, keeps exact-path tiers, then applies temporal decay, importance, project ranking, and MMR (`extensions/memory-core/src/memory/hybrid.ts:56`, `:184`, `:193`, `:247`).
- Recency decay: exponential `exp(-(ln2/halfLifeDays)*ageDays)` with 30-day default half-life; `MEMORY.md`/`USER.md`/undated `memory/` files are evergreen (`extensions/memory-core/src/memory/temporal-decay.ts:25`, `extensions/memory-core/src/memory/temporal-decay.ts:57`).
- Importance multiplier: `0.75 + clamp(1..10)*0.05`, neutral when null (`extensions/memory-core/src/memory/importance.ts:1`).
- MMR: relevance-biased lambda 0.7, Jaccard token overlap, `λ*relevance − (1−λ)*maxSimilarity` (`extensions/memory-core/src/memory/mmr.ts:28`; docs `docs/concepts/memory-search.md:163`).
- Project ranking multiplies 1.15 when all stored project keys are active, else 0.9 (`extensions/memory-core/src/memory/project-ranking.ts:14`).
- The final selection preserves strict ≥ `minScore` results and may fill spare slots with keyword-only matches (`extensions/memory-core/src/memory/hybrid.ts:270`).
- Embedding providers: OpenAI default; explicit `auto`/`none`/named; `provider: "none"` is deliberate FTS-only, a named-but-unavailable provider reports memory unavailable rather than silently degrading (`docs/concepts/memory-search.md:129`, `extensions/memory-core/src/memory/embeddings.ts:138`).
- Search manager acquisition: `getMemorySearchManager` resolves config, workspace access, and `MemoryIndexManager.get` (`extensions/memory-core/src/memory/search-manager.ts:35`).

### 5. Injection & context engine
- Memory plugins register capabilities (prompt builder, flush resolver, runtime, public artifacts, recall tool names) via `api.registerMemoryCapability`; memory-core registers `recallToolNames: ["memory_search","memory_get"]` and `supportsPrivateTranscriptRecall` (`extensions/memory-core/index.ts:219`).
- The prompt builder returns the "Memory Recall" guidance section only when `memory_search`/`memory_get` are available (`extensions/memory-core/index.ts:223`, `extensions/memory-core/src/memory-tool-contract.ts:131`).
- `src/plugins/memory-state.ts` prepares an immutable, run-scoped prompt snapshot (`prepareMemoryPromptSection`, `src/plugins/memory-state.ts:331`) and renders it (`buildMemoryPromptSection`, `src/plugins/memory-state.ts:375`); it also exposes the selected runtime (`getMemoryRuntime`, `:436`).
- The **context engine** controls assembly/compaction. The built-in `legacy` engine "ingest: no-op, assemble: pass-through, compact: delegate" (`src/context-engine/legacy.ts:7`); engines with full transcript-semantics declarations implement `commitTurn`/`maintain` (`docs/concepts/context-engine.md:256`). Plugins can opt into the memory prompt via `buildMemorySystemPromptAddition(...)` (`src/context-engine/delegate.ts:158`), and non-owning engines delegate compaction via `delegateCompactionToRuntime` (`src/context-engine/delegate.ts:66`).
- Bootstrap injection of `MEMORY.md`/`USER.md` is budget-limited per file with a fixed `USER.md` cap (`src/agents/embedded-agent-helpers/bootstrap.ts:102`, `src/agents/bootstrap-budget.ts:44`).
- Project-scoped curated files are filtered to the active repository keys (`filterProjectScopedCuratedContextFiles`, `src/agents/project-memory-bootstrap.ts:35`) and a separately budgeted "## Project Memory" block is built from eligible curated entries (`buildProjectMemoryBootstrap`, `:74`).

### 6. Recall lanes, triggers, and escalation
- Provider-native results expose `automaticRecall.{eligible,projectKeys,triggers,importance}`; eligibility requires `source==="memory"` + trusted provenance, and rejects only an **empty** project-key list — a missing project key still qualifies (`projectKeys?.length !== 0`, `src/plugins/memory-provider-adapter.ts:225`, `:244-249`).
- **Lane 1 (deterministic trigger recall)**: `active-memory` runs on `before_prompt_build` (`extensions/active-memory/index.ts:209`), resolves candidates lexically (`lexicalOnly: true`), and selects strong matches at score ≥ 0.65, top 3 (`extensions/active-memory/trigger-recall.ts:26`, `:84`), then injects a compact prefixed block (`:106`, `:382`).
- **Lane 2 (escalation)**: `resolveRecallEscalationDecision` runs only when the message shows recall intent AND lane 1 had no strong hit (default `escalate` mode) (`extensions/active-memory/escalation.ts:82`, `extensions/active-memory/index.ts:495`).
- Memory wiki registers prompt supplement, async prompt preparation, and corpus supplement (`extensions/memory-wiki/index.ts:178`), exposing cross-corpus results via `searchMemoryCorpusSupplements` (`extensions/memory-core/src/memory-corpus.ts:260`).

### 7. Session-search vs memory-search
- `memory_search` can return **session transcript hits** when session indexing is enabled (`experimental.sessionMemory` + `"sessions"` in sources), but those `sessions/...jsonl`-style paths are search references, not readable by `memory_get` (`docs/concepts/memory.md:159`, `docs/concepts/memory-search.md:193`).
- Exact transcript recall uses the separate Gateway tools `sessions_search` → `sessions_history` (`src/agents/tools/sessions-search-tool.ts:297`).
- Session hits obey `tools.sessions.visibility` (default `all`); cross-agent access governed by `tools.agentToAgent` (`docs/concepts/memory-search.md:200`); memory-core enforces it via `filterMemorySearchHitsBySessionVisibility` (`extensions/memory-core/src/session-search-visibility.ts:165`).

### 8. Dedup, decay, forget
- Per-session message dedup hashes (`scope+basis+snippet`) and tracked-hash caps prevent duplicate ingestion (`extensions/memory-core/src/session-ingestion.ts:427`, `:460`).
- Recall-loop prevention marks injected content so it is never re-extracted; dedup is enforced during dreaming (`docs/concepts/memory-architecture.md:104`).
- Dreaming promotion ranks by weighted signals frequency/relevance/diversity/recency/consolidation/conceptual (`extensions/memory-core/src/short-term-promotion.ts:32`, `:88`); the deterministic gate structurally blocks `untrusted`/`system` candidates before any prompt (`extensions/memory-core/src/dreaming-consolidation-candidates.ts:11`, `:18`).
- `memory forget` deletes tracked entry origins, session-corpus lines, index chunks/embeddings, rewrite preimages, and records forgotten sessions; promotion markers `<!-- openclaw-memory-promotion:KEY -->` connect entries to origin rows (`extensions/memory-core/src/memory-entry-origins.ts:120`, `:183`; docs `docs/concepts/memory-provenance.md:70`).
- Consolidation transfers parent origins to the surviving entry via `reserveMemoryEntryOrigins` (`extensions/memory-core/src/memory-entry-origins.ts:168`).

### 9. Standing intents (prospective memory)
- `intent` tool creates/lists/cancels event-conditioned intents (`extensions/memory-core/index.ts:101`); time-based reminders use cron instead. Intents are stored in a per-agent `standing_intents` SQLite table with an FTS shadow (`extensions/memory-core/src/standing-intents-kernel.ts:26`, `:30`), and matched on `before_prompt_build` (`extensions/memory-core/index.ts:276`).

### 10. External provider path (Honcho) & multi-user scoping
- Honcho is an **external plugin** (`@honcho-ai/openclaw-honcho`) that persists conversations after every turn, builds user/agent models, and injects context on `before_prompt_build` (`docs/concepts/memory-honcho.md:9`, `:103`); it can coexist with builtin search (`docs/concepts/memory-honcho.md:122`).
- Per-agent isolation: each agent has its own SQLite store and index identity; selection is scoped to the agent (`docs/concepts/memory-builtin.md:150`). Session visibility defaults to `all` and is the multi-user guard for transcript hits (`docs/concepts/memory-search.md:201`); personal `USER.md` is per-person (`src/agents/tools/personal-instructions-tool.ts:34`).

## Key contracts & data shapes

- **Tables**: `memory_index_chunks`, `memory_index_sources`, `memory_index_chunks_fts`, `memory_index_paths_fts`, `memory_embedding_cache`, `memory_index_state`, `memory_index_chunk_provenance`, `memory_index_chunk_recall_metadata`; intents in `standing_intents` (+ `standing_intents_fts`).
- **Types**: `MemorySource = "memory" | "sessions"`; `MemoryOriginClass = owner|agent|untrusted|system`; `MemorySessionKind`; `MemoryEntryProvenance {originClass, sessionKind, observedAt, supersedesKey?}`; `MemorySearchResult {path,startLine,endLine,score,vectorScore?,textScore?,snippet,source,importance?,triggers?,projectKey?,provenance?}` (`packages/memory-host-sdk/src/host/types.ts:4`, `:13`, `:20`).
- **Plugin capability**: `MemoryPluginCapability { recallToolNames, deterministicRecallToolName, supportsPrivateTranscriptRecall, promptBuilder, flushPlanResolver, runtime, publicArtifacts }` (`extensions/memory-core/index.ts:219`; types in `src/plugins/registry-contribution-types.ts`).
- **Context engine interface**: `ContextEngine { info, ingest, assemble, compact, commitTurn?, maintain?, bootstrap?, ingestBatch?, afterTurn?, prepareSubagentSpawn?, onSubagentEnded?, dispose? }` (`docs/concepts/context-engine.md:230`); `AssembleResult { messages, estimatedTokens, systemPromptAddition?, promptAuthority?, contextProjection? }` (`docs/concepts/context-engine.md:303`).
- **Tool names**: `memory_search`, `memory_get`, `intent`, `sessions_search`, `sessions_history`, `wiki_status`, `wiki_search`, `wiki_get`, `wiki_apply`, `wiki_lint`.
- **Memory flush plan**: `MemoryFlushPlan { softThresholdTokens, forceFlushTranscriptBytes, reserveTokensFloor, model?, prompt, systemPrompt, relativePath }` (`extensions/memory-core/src/flush-plan.ts:99`).
- **Wiki schema elements**: `WikiClaimSchema` (with `WikiClaimEvidenceSchema`), `contradictions` (`extensions/memory-wiki/src/tool.ts:84`, `:101`); compile dashboard sections incl. contradictions/low-confidence/claim-health (`extensions/memory-wiki/src/compile.ts:128`, `:177`).
- **CLI**: `openclaw memory status|index|reset|search|forget|promote|promote-explain|rem-backfill|rem-harness|session-backfill` (`docs/cli/memory.md`).

## Tests & QA

Representative suites (read by filename/import; not executed): `extensions/memory-core/src/memory/hybrid.test.ts`, `.../hybrid.project-ranking.test.ts`, `.../temporal-decay.test.ts`, `.../mmr.test.ts`, `.../manager-search*.test.ts` (vector/knn/provenance/retrieval-offthread), `.../manager-schema-admission.test.ts`, `.../manager-chunk-writer.test.ts`; `extensions/memory-core/src/session-ingestion.test.ts`, `.../memory-entry-origins.test.ts`, `.../short-term-promotion*.test.ts`, `.../dreaming*.test.ts`, `.../memory-forget*.test.ts`, `.../session-search-visibility.test.ts`, `.../standing-intents.test.ts`; SDK: `packages/memory-host-sdk/src/host/memory-schema.test.ts`, `.../memory-schema-provenance.test.ts`, `.../session-files.provenance.test.ts`, `.../curated-annotations.test.ts`; `src/context-engine/*.test.ts`; `extensions/active-memory/*` tests; `extensions/memory-wiki/src/*.test.ts`.

## Port notes to ROX

ROX target: Electron main `apps/electron/src/main` + preload + renderer, backend `packages/server` + `packages/server-core`, workspaces `packages/{core,shared,session-tools-core,pi-agent-server}`, sessions via OMP RPC, Bun 1.3.14 + Electron 39, config dir `~/.rox`, Russian-first i18n.

1. **Storage layer → `packages/server-core` + `packages/core`.** Port the SQLite schema as a versioned migration set owned by server-core: canonical tables `memory_index_chunks`, `memory_index_sources`, `memory_index_chunks_fts` (FTS5), `memory_embedding_cache`, `memory_index_state`, plus the additive provenance/recall-metadata tables. Keep provenance in SQLite columns (never parsed from Markdown) — this is the whole security property. ROX already uses SQLite; reuse the existing migration runner rather than a second convention.
2. **Embeddings + hybrid search → `packages/core` (Bun).** Implement `mergeHybridResults` (weighted vector+BM25, exact-path tiers), `applyImportanceMultiplier`, `applyTemporalDecayToHybridResults`, `applyMMRToHybridResults`, `projectScoreMultiplier` as pure functions — they are dependency-free and directly portable. Provider adapter interface should match ROX's identity/credential fabric (`packages/core/src/platform/identity`) so OpenAI/Ollama/local providers reuse ROX credentials rather than OpenClaw's `models.providers`.
3. **Context injection → OMP RPC boundary.** ROX has no OpenClaw context-engine interface; the natural mapping is: run the memory prompt snapshot build in server-core and pass the rendered `systemPromptAddition` string (or `prependContext`) through OMP RPC per turn. Port the trigger-recall lane (0.65 threshold, top 3) as a pre-turn hook; port active-memory escalation as an OMP sub-agent call gated on recall-intent + no strong hit. Keep lane 1 lexical-only and deterministic.
4. **Tools → session-tools-core / OMP tool registry.** Map `memory_search`/`memory_get`/`intent`/`wiki_*` to ROX's tool registration; `sessions_search`/`sessions_history` belong to the existing session tooling. Enforce session-visibility scoping at the server-core boundary (multi-user and multi-agent), equivalent to `filterMemorySearchHitsBySessionVisibility`.
5. **Wiki layer.** ROX meetings already model structured, provenance-rich records; `memory-wiki`'s claims/evidence/contradiction model (`WikiClaimSchema`, compile dashboards) is a good fit for a ROX knowledge view, but is separable from capture — port after core memory works.
6. **UI.** Bootstrap/curated files and the Dreams/DREAMS review trail map to ROX's Electron renderer; i18n is Russian-first — the guidance strings ("## Memory Recall", trigger block headers, flush prompts) need localization, which OpenClaw does not do.
7. **Config.** Map `plugins.entries.memory-core.config.*`, `memory.search.*`, `plugins.slots.memory`, `plugins.slots.contextEngine` onto ROX's `~/.rox` config; ROX should collapse the plugin-slot indirection since it has one memory stack.

## Risks & unknowns

- **Reimplementing provenance gates is the top risk.** If ROX injection does not gate on `originClass ∈ {owner,agent}` and project keys, untrusted tool/web output can be auto-injected (memory poisoning). The gate is currently split between the index (`memory_index_chunk_provenance`) and the provider adapter (`automaticRecall.eligible`) — ROX must reproduce both.
- **FTS5 + sqlite-vec availability under Bun/Electron.** OpenClaw relies on FTS5 BM25 and optional sqlite-vec; verify the ROX SQLite build ships both, and keep the in-process cosine fallback (f64 BLOB vectors) for when sqlite-vec is unavailable.
- **Embedding-model/index-identity coupling.** Chunking version + provider model form an index identity; changing either must pause/repair search. ROX needs an equivalent identity/rebuild state machine or it will silently mix incompatible embeddings.
- **Turn capture fidelity.** OpenClaw derives provenance from transcript metadata (`__openclaw.senderIsOwner`, `turnTainted`, `provenance.kind=internal_system`) and heartbeat/recalled-memory turn state. ROX's OMP transcripts must carry equivalent per-message provenance or classification degrades to `untrusted` (fail-safe, but loses recall quality).
- **UNVERIFIED:** exact `MemoryIndexManager` class surface and `manager.ts` internals beyond the readonly slice read; `manager-source-index-kernel.ts` chunk/embedding orchestration details; the full `standing-intents-model.ts` trigger schema fields; memory-wiki vault/OKF on-disk format; whether `memory_get` supports `corpus=wiki` reading beyond the schema enum; precise docs for `rem-backfill`/`session-backfill` internals. No builds/tests/formatters were run.