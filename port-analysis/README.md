# OpenClaw → ROX port study — index & executive summary

Adopt/port study answering: **what in `openclaw/openclaw` (fork `agisota/openclaw` @
`b0c330d2`) is worth bringing into `github.com/rox-one/rox-one`, and where does it land?**
Read-only analysis; the plan is [`port-matrix.md`](port-matrix.md).

## What was studied

Two codebases, read without modification:

- **OpenClaw** — `/Users/t/Projects/openclaw` @ `b0c330d2`: a Node/Bun multi-channel AI
  gateway (WebSocket daemon + Control UI + macOS/iOS/Android apps), TypeScript/Swift/Kotlin.
- **ROX** — `/Users/t/Projects/rox-one` (fork of `craft-ai-agents/craft-agents-oss`):
  Bun 1.3.14 + Electron 39 + React 18 + Tailwind v4 desktop app, OMP (oh-my-pi) RPC runtime,
  Russian-first i18n, existing meetings/skills/identity subsystems.

Twelve feature areas were deep-dived, each with verified `path:line` evidence on both sides,
plus a dedicated destination survey:

| area | doc | focus |
|---|---|---|
| a1 | [areas/a1-multi-user-core.md](areas/a1-multi-user-core.md) | multi-user mode: identity, roles/scopes, ownership, presence, public links, visitor access |
| a2 | [areas/a2-multi-user-ui.md](areas/a2-multi-user-ui.md) | sidebar filter/sort, owner chips, presence/typing, sharing menu, per-person model accounts |
| b1 | [areas/b1-control-ui.md](areas/b1-control-ui.md) | Control UI: build/serving, WS protocol, auth/pairing, CSP, offline/reconnect, panels |
| b2 | [areas/b2-canvas-workboard.md](areas/b2-canvas-workboard.md) | Workboard, Canvas/A2UI widgets, embedded macOS browser, WebChat windows |
| c1 | [areas/c1-memory.md](areas/c1-memory.md) | memory tiers, SQLite index, provenance, hybrid search, injection, dream/forget |
| c2 | [areas/c2-skills-plugins.md](areas/c2-skills-plugins.md) | SKILL.md, discovery/precedence, gating, plugins, ClawHub trust, custodian skills |
| d1 | [areas/d1-voice-realtime.md](areas/d1-voice-realtime.md) | Talk realtime, TTS, STT, voice wake, voice-call |
| d2 | [areas/d2-meetings.md](areas/d2-meetings.md) | meeting bot: transports, transcription, notes/summary, retention |
| e1 | [areas/e1-macos-lifecycle.md](areas/e1-macos-lifecycle.md) | install, onboarding, LaunchAgent lifecycle, doctor, update, uninstall |
| e2 | [areas/e2-macos-app.md](areas/e2-macos-app.md) | macOS companion app: shell/menus, WS client, TCC capabilities, helpers, updater |
| f | [areas/f-substrate-gateway.md](areas/f-substrate-gateway.md) | the substrate: process model, protocol, sessions/queues, agent loop, config, state |
| g | [areas/g-rox-target-surface.md](areas/g-rox-target-surface.md) | **destination** inventory — where each area lands in ROX |

## Method

**Understand-Anything (UA) pipeline.** A scan of OpenClaw was split into 12 graph-fragment
batches (`graph-fragments/batch-101.json` … `batch-112.json`, schema in
[GRAPH-FRAGMENT-SPEC.md](GRAPH-FRAGMENT-SPEC.md)), each emitting knowledge-graph nodes/edges
(`file`, `function`, `class`, `concept`, `schema`, `endpoint`, `service`, `flow`, …). The
batches were merged into [`knowledge-graph.json`](knowledge-graph.json) and enriched with
`layers.json`, `tour.json`, `stats.json`, `review.json` under `.ua/intermediate/`.

**12 parallel research agents.** One agent per area (a1…g) produced the deep-dives above from
real file reads/greps, with every claim carrying a `path:line` citation and uncertainty marked
`UNVERIFIED:`.

**Validators (all green at study close).** Evidence lives in
`.ua/intermediate/verification-report.json`, `review.json` and `verification/`:

1. **Doc-citation validator** — every cited source checked against disk:
   `doc_ok = 1006` (OpenClaw), `doc_rox_ok = 71` (ROX), `doc_shortened = 0`, `doc_bad = 0`.
2. **Symbol-existence validator** — greps for named symbols: `symbols_ok = 433`,
   `symbols_bad = 0`.
3. **Graph review validator** — `review.json`: `issues = []`, 3 orphan-node warnings.
4. **Strict schema validation** — the final graph parses against the understand-anything
   core zod schema (`KnowledgeGraphSchema`); plus a per-fragment id-convention audit.
5. **Adversarial claim verification** — three independent agents re-checked sampled
   mechanism/contract claims per area doc against source; reports in `verification/`.

**Defects found and fixed during verification** (kept for traceability):

- `batch-108.json` (meetings) used bare node ids (`f1`…`f78`) that the merge step would have
  mis-prefixed — remapped to canonical ids (`file:…`, `function:…`, …), edges rewritten.
- `batch-112.json` (ROX) used double-prefixed ids (`function:file:rox/…`) and unprefixed
  `filePath`s — rewritten into the `rox/<path>` namespace.
- Comma-string `tags` in six fragments normalized to arrays (core schema requires arrays).

**Adversarial verification results** — three independent agents sampled 299 claims across the
12 docs: **290 SUPPORTED, 6 REFUTED, 2 UNCLEAR** (a1–b2: 100/103; c1–d2: 83/88; e1–g: 105/108).
All nine issues were corrected in the docs from the verifiers' code evidence — b1 CSP scope,
b2 widget-bridge surface, a2 visibility gating, c1 project-key eligibility, c2 runtime modes,
d1 relay TTL (20→30 min), e2 node launchd label, f SecretRef `store` source, g meetings export
range. Remaining line-drift notes are recorded verbatim in `verification/*.json`.

## Graph stats

From `.ua/intermediate/stats.json` (identical in `review.json.stats`):

- **1,412 nodes, 2,920 edges, 13 layers, 13 tour steps.**
- Nodes by type: `file` 570, `function` 309, `concept` 202, `class` 120, `document` 51,
  `endpoint` 46, `step` 27, `module` 26, `service` 13, `schema` 11, `table` 10, `config` 8,
  `flow` 8, `pipeline` 5, `resource` 4, `domain` 2.
- Top edge types: `imports` 863, `contains` 626, `calls` 285, `related` 239, `depends_on` 165,
  `documents` 148, `implements` 143, `routes` 53, `defines_schema` 45, `exports` 42,
  `configures` 40, `reads_from` 34, `flow_step` 33, `contains_flow` 29.
- Layers: `gateway` 254, `dashboards` 240, `macos` 142, `skills` 122, `lifecycle` 117,
  `memory` 114, `voice` 104, `meetings` 101, `rox` 90, `multi-user` 86, `docs` 19, `mobile` 17,
  `channels` 6.
- Project meta: `{name: openclaw, gitCommitHash:
  b0c330d27df4a528f65185cc3e509284d1b218d9}`.

## How to view the graph

```bash
cd ~/.agents/skills/understand/plugin/packages/dashboard && \
  GRAPH_DIR=/Users/t/Projects/openclaw npx vite --host 127.0.0.1
```

Then open the **tokenized URL printed by Vite** (the dev server prints an auth token; use the
exact URL it emits rather than `http://127.0.0.1:5173/`).

## File map

| path | contents |
|---|---|
| [`port-matrix.md`](port-matrix.md) | the adopt/port plan — per-area capability tables, verdicts, effort, sequencing, MVP slices, cross-cutting concerns, non-goals |
| `areas/` | 12 area deep-dives (`a1…g`) — verified evidence on both codebases |
| `areas/g-rox-target-surface.md` | ROX destination inventory + file-level integration table |
| [`knowledge-graph.json`](knowledge-graph.json) | merged UA graph: 1,412 nodes / 2,920 edges / 13 layers / 13 tour steps |
| `graph-fragments/` | raw UA research: `batch-101.json`…`batch-112.json` (`{nodes, edges}`), plus copies of `stats.json` / `review.json` |
| `verification/` | adversarial claim-verification reports from three independent agents |
| `tools/` | the reproducible pipeline: scan→importMap, fragment merge, layer/tour build, validators |
| [`GRAPH-FRAGMENT-SPEC.md`](GRAPH-FRAGMENT-SPEC.md) | node/edge schema + id conventions the fragments conform to |
| `.ua/intermediate/` | local pipeline internals: `scan-result.json`, `assembled-graph.json`, `layers.json`, `tour.json`, `stats.json`, `review.json`, `verification-report.json`, raw batches |

## Five user-facing feature areas (the payoff)

The 12 technical areas roll up into five product-facing capabilities for ROX:

1. **Multiplayer → multi-user mode.** Several trusted people operate one agent: creator/owner/
   participants per session, named roles + scope ceilings, presence/typing, public read-only
   session links, per-person model accounts. (areas **a1, a2**.) Explicitly a usability plane,
   **not** an isolation boundary.
2. **Interactive dashboards.** A dashboard surface hosted by ROX's embedded server: streaming
   chat with tool cards, sessions sidebar, settings/config, cron/logs/usage panels, plus Kanban
   Workboard and sandboxed agent/Canvas widgets. (areas **b1, b2**.)
3. **Memory + skills.** Plain-Markdown memory with a SQLite/FTS index, provenance-gated
   injection, hybrid retrieval and dream/forget lifecycle; plus the `SKILL.md` catalog,
   discovery/precedence, prompt injection and a sandboxed plugin boundary. (areas **c1, c2**.)
4. **Meetings + voice.** Join/transcribe external calls with per-line provenance and a notes/
   summary pipeline, and full-duplex Talk (realtime bridge, TTS, STT relay, wake words).
   (areas **d1, d2**.)
5. **macOS setup.** Onboarding + daemon/service lifecycle (LaunchAgent/OS-service abstraction),
   menu-bar shell, TCC capability model, helper processes and auto-update.
   (areas **e1, e2**, substrate **f**, destination **g**.)

---

*Study date 2026-10-09. All OpenClaw citations are against fork @ `b0c330d2`; all ROX paths in
`port-matrix.md` were verified to exist in `/Users/t/Projects/rox-one` at study time.*