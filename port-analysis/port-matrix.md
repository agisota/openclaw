# OpenClaw → ROX port matrix

Adopt/port plan for `github.com/rox-one/rox-one` (local clone `/Users/t/Projects/rox-one`,
Bun 1.3.14 + Electron 39 + React 18 + Tailwind v4) derived from the 12 area deep-dives in
`port-analysis/areas/`. All OpenClaw citations are against fork @ `b0c330d2`; all ROX
citations are real paths verified in the clone on 2026-10-09 (line numbers are the anchor
read during the study).

**Verdict legend:** `reuse-as-is` (ROX already has an equivalent — wire it, don't rebuild) ·
`adapt` (port the mechanism/shape onto ROX's existing seams) · `reimplement` (ROX has no
analogue; build against ROX conventions) · `skip` (deliberately out of scope).
**Effort:** S ≤1 wk · M = 1–4 wk · L = 1–3 mo · XL = multi-quarter.

---

## a1 — Multi-user / shared-team core  (`areas/a1-multi-user-core.md`)

The authored doc is explicit that multiplayer is **not a security boundary**
(`docs/concepts/multi-user.md:15`); port the usability plane, not implied tenant isolation.

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Identity model — three actor kinds `profile\|channel\|agent` | `areas/a1-multi-user-core.md`; `docs/concepts/multi-user.md:43`; `src/config/sessions/session-entry-provenance.ts:19` | `packages/core/src/platform/identity/store.ts:1`; `packages/server-core/src/authority/native-authority.ts:104` | adapt | M | flattening actor kinds loses creator/participant attribution |
| Named operator roles + scope ceiling at admission | `areas/a1-multi-user-core.md`; `src/config/zod-schema.gateway.ts:82`; `src/gateway/operator-role-policy.ts:95` | `packages/server-core/src/authority/native-authority.ts:449`; `packages/shared/src/orgs/types.ts:1` | adapt | L | ceiling must be intersected at WS admission, not just UI |
| Ownership layers (creator/owner/participants) + `sessions.assignOwner` | `areas/a1-multi-user-core.md`; `src/gateway/server-methods/sessions-mutations.ts:344` | `packages/server-core/src/sessions/SessionManager.ts:10788`; `packages/shared/src/protocol/channels.ts:6` | adapt | L | creator is write-once; must persist or share authority changes |
| Presence map (connect snapshot + beacon, TTL 5 min) | `areas/a1-multi-user-core.md`; `src/gateway/server/client-presence.ts:27` | `packages/shared/src/collaboration/presence.ts:14`; `packages/server-core/src/collaboration/sync-service.ts:17` | adapt | M | ephemeral-by-design; do not surface as authorization |
| Public session links (AES-256-GCM sealed locator) | `areas/a1-multi-user-core.md`; `src/gateway/control-ui-public-session-token.ts:15` | `packages/shared/src/collaboration/session-publication.ts:1`; `apps/electron/src/main/openclaw-host-control.ts:346` | reimplement | L | token bound to installation device identity; revocation can't recall copies |
| Visitor-access plugin (Cloudflare Access policy, TTL, sweep) | `areas/a1-multi-user-core.md`; `extensions/visitor-access/index.ts:54` | `packages/server-core/src/openclaw/runtime-manager.ts:1`; `packages/shared/src/openclaw/types.ts:73` | adapt | M | Cloudflare policy coupling; serialized mutation queue required |
| `trustedProxy` / `cloudflareAccessOidc` ingress identity | `areas/a1-multi-user-core.md`; `src/config/zod-schema.gateway.ts:331` | `packages/server-core/src/authority/native-authority.ts:567`; `packages/server-core/src/transport/server.ts:197` | skip | S | only needed if a hosted ingress is added later |

## a2 — Multi-user UI surfaces  (`areas/a2-multi-user-ui.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Sidebar filter/sort popover (Owners/Status/Group by) | `areas/a2-multi-user-ui.md`; `ui/src/components/app-sidebar-session-menu-renderers.ts:423` | `apps/electron/src/renderer/app.tsx:1`; `packages/shared/src/protocol/channels.ts:6` | reimplement | M | "Involving me" is Gateway-evaluated over full participant history |
| Owner chip + pair-stack + assign submenu | `areas/a2-multi-user-ui.md`; `ui/src/components/session-owner-chip.ts:31` | `packages/shared/src/protocol/channels.ts:6`; `apps/electron/src/transport/channel-map.ts:19` | adapt | M | attribution must follow created/owned/archived selection |
| Participant history rendering (creator vs owner vs participants) | `areas/a2-multi-user-ui.md`; `ui/src/pages/chat/components/chat-transcript-identity.ts:31` | `packages/server-core/src/sessions/SessionManager.ts:10788` | adapt | S | renaming a person must not rewrite participant history |
| Presence avatars + typing indicator | `areas/a2-multi-user-ui.md`; `ui/src/pages/chat/components/chat-typing-indicator.ts:45` | `packages/shared/src/collaboration/presence.ts:14`; `packages/shared/src/protocol/events.ts:56` | adapt | M | drafts must stay ephemeral, never in transcript/model context |
| Sharing menu: visibility + public link + members | `areas/a2-multi-user-ui.md`; `ui/src/pages/chat/components/chat-session-sharing.ts:149` | `apps/electron/src/renderer/app.tsx:1`; `packages/shared/src/protocol/channels.ts:6` | reimplement | M | `read-only`/`suggest`/`draft` must be enforced server-side |
| Settings → Profile → Connected accounts (per-person model) | `areas/a2-multi-user-ui.md`; `ui/src/pages/profile/model-accounts.ts:41` | `packages/core/src/platform/identity/index.ts:24`; `packages/shared/src/credentials/manager.ts:35` | adapt | M | reuse ROX secret store, not a second credential path |
| macOS WebChat surfaces (webview-hosted) | `areas/a2-multi-user-ui.md`; `apps/macos/Sources/OpenClaw/WebChatSwiftUI.swift:1142` | `apps/electron/src/main/window-manager.ts:58` | adapt | S | web + native experience share state, not drafts |

## b1 — Control UI (interactive web dashboard)  (`areas/b1-control-ui.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Serve dashboard static assets from same HTTP host | `areas/b1-control-ui.md`; `src/gateway/control-ui-index.ts:45`; `src/gateway/control-ui-static.ts:189` | `packages/server-core/src/webui/http-server.ts:379`; `packages/server-core/src/webui/index.ts:1` | reuse-as-is | S | base-path/route-preload parity with ROX WebUI |
| Build pipeline: stable chunking + boot manifest + locale virtual modules | `areas/b1-control-ui.md`; `ui/config/control-ui-chunking.ts:55`; `ui/scripts/control-ui-boot-manifest.mts:213` | `apps/webui/src/browser-main.tsx:1` | adapt | M | Vite vs Bun bundler; keep boot-manifest *concept* |
| WS transport: hello/snapshot + method+event catalog | `areas/b1-control-ui.md`; `packages/gateway-protocol/src/schema/frames.ts:31` | `packages/shared/src/protocol/channels.ts:6`; `packages/server-core/src/transport/types.ts:66` | adapt | L | map Control-UI method inventory onto OMP RPC, not a new socket |
| Auth / pairing handoff (single-use bootstrap token) | `areas/b1-control-ui.md`; `src/commands/control-ui-handoff.ts:141`; `src/gateway/server/ws-connection/connect-admission.ts:161` | `packages/core/src/platform/identity/index.ts:24`; `packages/server-core/src/webui/auth.ts:1` | adapt | M | keep credential out of URL; origin allow-list |
| CSP / security headers + media ticket | `areas/b1-control-ui.md`; `src/gateway/control-ui-csp.ts:34` | `packages/server-core/src/webui/http-server.ts:268` | adapt | S | hash inline scripts; `connect-src` limited to self+ws |
| Offline/reconnect backoff + warm reload + outbox | `areas/b1-control-ui.md`; `ui/src/api/gateway.ts:262` | `packages/server-core/src/transport/client.ts:124` | adapt | M | Electron history/`will-navigate` replaces web-chrome hooks |
| Operator panels (40+ pages: chat, sessions, cron, logs, usage…) | `areas/b1-control-ui.md`; `ui/src/app-routes.ts:86` | `apps/electron/src/renderer/app.tsx:1` | reimplement | XL | port panel-by-panel; not a single cutover |
| Sandboxed plugin/agent widgets | `areas/b1-control-ui.md`; `ui/src/lib/widget-sandbox-host.ts:28` | `apps/electron/src/main/openclaw-host-control.ts:346` | reimplement | M | isolated iframe/webview with strict CSP; load/hard timeouts |

## b2 — Canvas, Workboard, embedded browser, WebChat  (`areas/b2-canvas-workboard.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Workboard server: `workboard.*` RPC + SQLite store + CAS | `areas/b2-canvas-workboard.md`; `extensions/workboard/index.ts:28`; `extensions/workboard/src/gateway.ts:161` | `packages/shared/src/kanban/types.ts:8`; `packages/shared/src/kanban/storage.ts:1` | adapt | L | card↔session linkage must use ROX session model, not a new registry |
| Workboard browser plugin → React route + IPC bridge | `areas/b2-canvas-workboard.md`; `extensions/workboard/browser/index.ts:19` | `apps/electron/src/renderer/mindmap/MindMapHost.tsx:1`; `apps/electron/src/transport/channel-map.ts:19` | reimplement | L | keep "one capability object + subscribe/invalidate" pattern |
| Canvas `show_widget` → `board.widget.put` (script CSP sandbox) | `areas/b2-canvas-workboard.md`; `src/canvas/widget-tool.ts:315`; `src/gateway/server-methods/board.ts:242` | `packages/server-core/src/workgraph/index.ts:1`; `packages/shared/src/workflows/types.ts:44` | adapt | L | postMessage bridge is the real trust boundary; ticket-binding required |
| A2UI widget validation (v0.8 strict / v0.9 schema) | `areas/b2-canvas-workboard.md`; `extensions/canvas/src/a2ui-jsonl.ts:16` | `packages/shared/src/workflows/validate.ts:1` | adapt | M | mixed versions must be rejected, not silently rendered |
| Canvas document host + `buildWidgetDocument` wrap | `areas/b2-canvas-workboard.md`; `src/canvas/documents.ts:71`; `src/canvas/wrap.ts:66` | `packages/server-core/src/webui/http-server.ts:379`; `apps/electron/src/main/openclaw-host-control.ts:346` | adapt | M | bridge bytes must precede widget code; `default-src 'none'` |
| macOS embedded browser → Electron WebContentsView tabs | `areas/b2-canvas-workboard.md`; `apps/macos/Sources/OpenClaw/DashboardNativeBrowserHost.swift:26` | `apps/electron/src/main/window-manager.ts:58` | reimplement | L | per-profile `session.fromPartition`; staged-then-commit downloads |
| WebChat window fleet + route encoding | `areas/b2-canvas-workboard.md`; `apps/macos/Sources/OpenClaw/WebChatManager.swift:37` | `apps/electron/src/main/window-manager.ts:58` | adapt | M | keep "direct WS, no local static server" invariant |

## c1 — Memory stack  (`areas/c1-memory.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| SQLite index schema + per-agent DB + migrations | `areas/c1-memory.md`; `packages/memory-host-sdk/src/host/memory-schema.ts:322` | `packages/server-core/src/memory/fts-index.ts:1`; `packages/server-core/src/memory/MemoryService.ts:247` | adapt | L | FTS5 + optional sqlite-vec must exist in ROX's SQLite build |
| Provenance gates (`origin_class ∈ owner\|agent`) — the security property | `areas/c1-memory.md`; `packages/memory-host-sdk/src/host/session-provenance.ts:4`; `packages/memory-host-sdk/src/host/types.ts:40` | `packages/server-core/src/memory/provenance.ts:1`; `packages/server-core/src/memory/episodic-memory.ts:1` | reimplement | L | skipping the gate = memory poisoning from untrusted tool/web output |
| Hybrid search: BM25 + vector → decay → importance → MMR | `areas/c1-memory.md`; `extensions/memory-core/src/memory/hybrid.ts:56`; `.../temporal-decay.ts:25`; `.../mmr.ts:28` | `packages/server-core/src/memory/MemoryService.ts:247`; `packages/server-core/src/memory/decay.ts:1` | adapt | L | chunking version + provider model form an index identity; rebuild state machine needed |
| Context injection via prompt snapshot → per-turn boundary | `areas/c1-memory.md`; `src/plugins/memory-state.ts:331` | `packages/shared/src/agent/omp-agent.ts:167`; `packages/shared/src/memory/context-select.ts:1` | reimplement | L | ROX has no context-engine equivalent; pass rendered addition over OMP RPC |
| Recall lanes: deterministic trigger + escalation sub-agent | `areas/c1-memory.md`; `extensions/active-memory/trigger-recall.ts:26`; `extensions/active-memory/escalation.ts:82` | `packages/shared/src/memory/context-select.ts:1`; `packages/server-core/src/memory/MemoryService.ts:247` | adapt | M | lane 1 must stay lexical-only and deterministic (≥0.65, top 3) |
| Standing intents (prospective memory) | `areas/c1-memory.md`; `extensions/memory-core/src/standing-intents-kernel.ts:26` | `packages/server-core/src/memory/lesson-graph.ts:1` | adapt | M | matched on `before_prompt_build`; time reminders belong to cron |
| Memory wiki (claims/evidence/contradictions) | `areas/c1-memory.md`; `extensions/memory-wiki/index.ts:178` | `packages/server-core/src/memory/lesson-graph.ts:1`; `packages/server-core/src/memory/LessonStore.ts:1` | adapt | M | separable from capture — port after core memory works |
| Flush turn + forget/lineage retention | `areas/c1-memory.md`; `extensions/memory-core/src/flush-plan.ts:63`; `.../memory-entry-origins.ts:120` | `packages/server-core/src/memory/MemoryProposalStore.ts:1`; `packages/server-core/src/memory/MemoryFileStore.ts:1` | adapt | M | forget must remove corpus lines + chunks + embeddings, not just prose |

## c2 — Skills & plugin system  (`areas/c2-skills-plugins.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| `SKILL.md` parse/materialize (frontmatter + body refs) | `areas/c2-skills-plugins.md`; `src/skills/loading/frontmatter.ts:27`; `src/skills/loading/skill-materializer.ts:29` | `packages/shared/src/skills/storage.ts:302`; `packages/shared/src/skills/omp-discovery.ts:125` | reuse-as-is | S | ROX already ships a 330-skill catalog (`SKILLS.lock`) |
| Discovery roots + name-keyed precedence/collision report | `areas/c2-skills-plugins.md`; `src/skills/loading/workspace-skill-sources.ts:81`; `src/skills/loading/skill-precedence.ts:105` | `packages/shared/src/skills/omp-discovery.ts:23`; `packages/shared/src/skills/bundled.ts:118` | adapt | M | keep ordered root plan; do not collapse tiers silently |
| Gating/eligibility (agent allowlist, `requires.bins/env/config`) | `areas/c2-skills-plugins.md`; `src/skills/loading/config.ts:112`; `src/skills/discovery/agent-filter.ts:13` | `packages/shared/src/skills/storage.ts:42`; `packages/core/src/platform/identity/store.ts:1` | adapt | M | key allowlists on ROX operator identity; map `env` to credential fabric |
| Prompt surface (`<available_skills>`) + `skills_search`/`skills_read` | `areas/c2-skills-plugins.md`; `src/agents/system-prompt-skills.ts:3`; `src/agents/tools/installed-skill-tools.ts:20` | `packages/shared/src/agent/session-tool-defs.ts:61`; `packages/session-tools-core/src/tool-defs.ts:878` | adapt | M | inject into OMP session prompt; reuse tool-call path |
| Plugin manifest + registration-mode boundary | `areas/c2-skills-plugins.md`; `src/plugins/manifest-types.ts:416`; `docs/plugins/sdk-entrypoints/registration-mode.md:18` | `packages/server-core/src/openclaw/runtime-manager.ts:1` | reimplement | L | ROX must NOT copy "in-process, unsandboxed" — worker boundary |
| Plugin lifecycle / hot reload (`plugins.reload` drain+swap) | `areas/c2-skills-plugins.md`; `src/plugins/lifecycle.ts:48` | `packages/server-core/src/openclaw/runtime-manager.ts:1` | adapt | L | `restartRequired` when process-shared code can't swap |
| Registry trust gate (verdict → clean/blocked, fail-closed) | `areas/c2-skills-plugins.md`; `src/infra/clawhub-install-trust.ts:479` | `packages/shared/src/skills/bundled-core.ts:63` | reimplement | M | external registry shape; re-specify against ROX's registry |
| Custodian skills → system agent playbooks | `areas/c2-skills-plugins.md`; `custodian-skills/configure-channel/SKILL.md:1` | `apps/electron/resources/skills/REQUESTED-SKILLS.json:1` | adapt | S | ship as gated bundled skills, not privileged tools |

## d1 — Voice + realtime  (`areas/d1-voice-realtime.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Talk event vocabulary (`TALK_EVENT_TYPES`) + sequencer | `areas/d1-voice-realtime.md`; `src/talk/talk-events.ts:7` | `packages/shared/src/voice/contracts.ts:1`; `packages/shared/src/voice/index.ts:1` | adapt | M | one event model shared by renderer/server/future mobile |
| Provider registry (realtime voice + speech) | `areas/d1-voice-realtime.md`; `src/talk/provider-registry.ts:16`; `src/tts/provider-registry.ts` | `packages/shared/src/voice/runtime.ts:1`; `packages/core/src/platform/identity/provider-contract.ts:1` | adapt | M | add capability keys to ROX sources/MCP registry |
| Realtime bridge state machine (connect/retry/pending audio) | `areas/d1-voice-realtime.md`; `src/talk/realtime-session-lifecycle.ts:70` | `packages/shared/src/voice/job-machine.ts:1` | adapt | L | credentials stay in main; renderer gets ephemeral tokens only |
| TTS pipeline (buffered + streaming + precedence) | `areas/d1-voice-realtime.md`; `src/tts/tts-synthesis.ts:201`; `src/tts/tts-streaming.ts:12` | `packages/shared/src/voice/runtime.ts:1` | adapt | M | device playback stays renderer/native |
| STT relay (WS reconnect + bounded queues) | `areas/d1-voice-realtime.md`; `src/realtime-transcription/websocket-session.ts:20` | `packages/shared/src/voice/transcribe.ts:1`; `apps/electron/src/main/voice/overlay-owner.ts:1` | adapt | M | browser codec g711_ulaw@8k / pcm16@24k |
| Voice wake list + broadcast; on-device recognition only | `areas/d1-voice-realtime.md`; `src/gateway/server-methods/voicewake.ts:7` | `packages/shared/src/voice/hotkey-types.ts:1`; `apps/electron/src/renderer/voice/hotkey-dictation-host.tsx:1` | adapt | M | foreground-gated; route triggers to sessions |
| Telephony voice-call (Twilio/Telnyx/Plivo) | `areas/d1-voice-realtime.md`; `extensions/voice-call/src/runtime.ts:87` | `packages/shared/src/voice/meeting-stream.ts:1` | skip | L | needs public webhook + tunnel infra; desktop model must host or delegate |
| Meeting realtime engine seam | `areas/d1-voice-realtime.md`; `src/meeting-bot/realtime-engine.ts:99` | `packages/shared/src/voice/meeting-capture.ts:1`; `packages/shared/src/voice/meeting-stream.ts:1` | adapt | M | verify ROX meeting stack can host realtime engines |

## d2 — Meetings  (`areas/d2-meetings.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Session runtime (keyed transport:url lock, tab ownership, retry) | `areas/d2-meetings.md`; `src/meeting-bot/session-runtime.ts:51` | `packages/server-core/src/meetings/index.ts:24`; `packages/server-core/src/meetings/repository.ts:4` | adapt | L | transport-agnostic orchestrator over ROX meeting package |
| Transport selection (chrome / chrome-node / twilio dial-in) | `areas/d2-meetings.md`; `src/meeting-bot/platform-adapter.ts:384` | `packages/server-core/src/meetings/conation/native-shells.ts:1`; `apps/electron/src/main/meetings/capture.ts:1` | reimplement | XL | Chrome DOM automation fragility; no vendor SDK claimed |
| Caption transcription + per-line provenance/ownEcho | `areas/d2-meetings.md`; `src/meeting-bot/session-transcript-store.ts:72`; `src/meeting-bot/session-types.ts:16` | `apps/electron/src/main/meetings/local-asr.ts:1`; `apps/electron/src/shared/meetings-local.ts:159` | adapt | L | without provenance+ownEcho you echo the agent's own TTS into notes |
| Notes/summary pipeline (5-min cadence + heuristic fallback) | `areas/d2-meetings.md`; `src/transcripts/capture-summary.ts:218`; `src/transcripts/summary-model.ts:17` | `packages/shared/src/meeting-agents/planning.ts:116`; `packages/shared/src/meeting-agents/router.ts:178` | adapt | L | strict JSON schema + 20s budget; deterministic fallback |
| Participation idempotency (fingerprint dedupe, one correction) | `areas/d2-meetings.md`; `src/meeting-bot/participation.ts:44` | `packages/shared/src/meeting-agents/recipes.ts:1` | reuse-as-is | M | observations never grant action authority |
| Google Meet OAuth + artifacts (PKCE, scopes, Drive) | `areas/d2-meetings.md`; `extensions/google-meet/src/oauth.ts:21` | `packages/core/src/platform/identity/index.ts:24` | adapt | M | Media API is Developer Preview; Workspace enrolment may block |
| Feishu VC invite trigger (synthetic p2p message) | `areas/d2-meetings.md`; `extensions/feishu/src/monitor.vc-meeting-invited-handler.ts:108` | `packages/server-core/src/meetings/proposals.ts:1` | adapt | M | handler must not call a join API directly; default-off |
| Retention: no recording; bounded in-memory caps | `areas/d2-meetings.md`; `src/meeting-bot/participation.ts:13` | `apps/electron/src/main/meetings/local-store.ts:111` | adapt | S | keep `transcripts.enabled` kill switch + explicit observe tail |

## e1 — macOS/Linux install, onboarding, daemon lifecycle  (`areas/e1-macos-lifecycle.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| `curl\|bash` installer + Node provisioning + PATH rc rewrite | `areas/e1-macos-lifecycle.md`; `scripts/install.sh:1557`; `scripts/install.sh:1616` | `apps/electron/electron-builder.yml:91`; `packages/server/src/index.ts:1` | skip | S | Electron packaging replaces the npm-global flow |
| Runtime capability probe (SQLite WAL-safe + version floor) | `areas/e1-macos-lifecycle.md`; `scripts/install.sh:1557` | `packages/server/src/index.ts:50` | adapt | S | keep the user-space runtime fallback under `<state>/tools/` |
| Onboard `--install-daemon` tri-state decision | `areas/e1-macos-lifecycle.md`; `src/wizard/setup.finalize.ts:252` | `apps/electron/src/main/index.ts:1100` | adapt | M | quickstart=install default; skip when externally supervised |
| LaunchAgent plist/env wrapper → OS service abstraction | `areas/e1-macos-lifecycle.md`; `src/daemon/launchd-service-files.ts:42`; `src/daemon/launchd-plist.ts:20` | `apps/electron/src/main/index.ts:1100`; `packages/pi-agent-server/src/index.ts:1` | reimplement | L | transactional publish+rollback; 0600 env file else bricked service |
| Service authority/status fences | `areas/e1-macos-lifecycle.md`; `src/daemon/launchd-install.ts:87` | `packages/server-core/src/bootstrap/headless-start.ts:502` | adapt | M | refuse mutation from inside the service; system-daemon ownership |
| Doctor diagnostics (foreign jobs, port, runtime mismatch) | `areas/e1-macos-lifecycle.md`; `src/daemon/launchd-foreign-jobs.ts:15` | `packages/server-core/src/openclaw/runtime-manager.ts:1` | adapt | M | port-conflict/runtime-mismatch only; skip launchd reaping |
| Update channels + `checkOnStart` + detached handoff | `areas/e1-macos-lifecycle.md`; `src/infra/update-channels.ts:7` | `apps/electron/src/main/auto-update.ts:17` | reuse-as-is | S | wait-for-old-PID helper replaces `kickstart` |
| State dir / logs / uninstall scopes | `areas/e1-macos-lifecycle.md`; `src/daemon/paths.ts:37` | `apps/electron/src/main/native-replica.ts:63` | adapt | S | map `~/.openclaw` → `~/.rox`; stop service before deleting state |

## e2 — macOS companion app  (`areas/e2-macos-app.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Menu-bar/tray shell + navigation dispatch | `areas/e2-macos-app.md`; `apps/macos/Sources/OpenClaw/MenuBar.swift:44` | `apps/electron/src/main/menu.ts:31`; `apps/electron/src/shared/menu-schema.ts:1` | adapt | M | main-process router: Dashboard(web) vs native chat |
| Operator/node WS client + lease fencing + node.invoke bridge | `areas/e2-macos-app.md`; `apps/shared/OpenClawKit/Sources/OpenClawKit/GatewayChannel.swift:10` | `packages/server-core/src/transport/client.ts:124`; `packages/shared/src/agent/omp-agent.ts:386` | adapt | L | per-connection lease/generation fencing on ROX transport |
| Embedded-surface IPC (webview message handlers) | `areas/e2-macos-app.md`; `apps/macos/Sources/OpenClaw/DashboardWindowController.swift:151` | `apps/electron/src/preload/bootstrap.ts:241`; `apps/electron/src/main/openclaw-host-control.ts:255` | adapt | L | definition of `window.roxDesktop`; version every handler |
| Node capability model + TCC prompts | `areas/e2-macos-app.md`; `apps/macos/Sources/OpenClawIPC/IPC.swift:6`; `apps/macos/Sources/OpenClaw/NodeMode/MacNodeModeCoordinator.swift:1219` | `apps/electron/src/main/index.ts:1100`; `packages/server-core/src/authority/native-authority.ts:104` | reimplement | L | TCC/signature+path coupling: bundle-ID/path change resets grants |
| LaunchAgent management from app (install/start/stop, runtime pin, resume) | `areas/e2-macos-app.md`; `apps/macos/Sources/OpenClaw/GatewayLaunchAgentManager.swift:192` | `apps/electron/src/main/index.ts:1100`; `packages/pi-agent-server/src/index.ts:1` | reimplement | L | preserve "who owns the Gateway" or get duplicate gateways |
| Auto-update: Sparkle → electron-updater + channel gating | `areas/e2-macos-app.md`; `apps/macos/Sources/OpenClaw/AppLifecycleSupport.swift:74` | `apps/electron/src/main/auto-update.ts:17` | reuse-as-is | S | keep app and gateway/OMP on compatible release trains |
| Helper processes: stdio framing + app-control/exec UDS | `areas/e2-macos-app.md`; `apps/macos-mlx-tts/Package.swift:13`; `apps/macos/Sources/OpenClaw/MacControlServer.swift:34` | `apps/electron/src/main/deep-link.ts:1`; `apps/electron/src/main/notifications.ts:1` | reimplement | M | 0600 token + HMAC + peer-UID; separate exec-approvals socket |
| Signing / notarization / entitlements | `areas/e2-macos-app.md`; `docs/platforms/mac/signing.md:14` | `apps/electron/electron-builder.yml:91` | adapt | M | JIT entitlements only to runtime binaries; Team-ID audit fails closed |

## f — Gateway substrate (runtime, protocol, agent loop)  (`areas/f-substrate-gateway.md`)

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Process model: single owner + state lock + loopback bind | `areas/f-substrate-gateway.md`; `src/gateway/server.ts:24`; `src/gateway/net.ts:247` | `apps/electron/src/main/index.ts:1100`; `packages/server-core/src/bootstrap/headless-start.ts:502` | adapt | L | one in-process gateway module; refuse non-loopback without auth |
| Transport: req/res/event frames + `connect`-first handshake | `areas/f-substrate-gateway.md`; `packages/gateway-protocol/src/schema/frames.ts:31` | `packages/shared/src/protocol/channels.ts:6`; `packages/server-core/src/transport/types.ts:66` | adapt | L | one generated contract packet + N-1 window; no Swift codegen |
| Method registry + namespace/scope policy | `areas/f-substrate-gateway.md`; `src/gateway/methods/registry.ts:67` | `packages/server-core/src/transport/types.ts:47`; `packages/shared/src/protocol/routing.ts:17` | adapt | M | plugin methods must not weaken reserved core prefixes |
| Sessions/routing/queue steering (`steer\|followup\|collect\|interrupt`) | `areas/f-substrate-gateway.md`; `src/routing/session-key.ts:46` | `packages/server-core/src/sessions/SessionManager.ts:10788`; `packages/shared/src/agent/omp-agent.ts:2285` | adapt | L | per-session + global lane serialization as OMP queue policy |
| Agent loop: streaming + `activeWriterRunId` transcript fence | `areas/f-substrate-gateway.md`; `src/agents/embedded-agent-runner/run-orchestrator.ts:106` | `packages/shared/src/agent/omp-agent.ts:386`; `packages/server-core/src/sessions/SessionEventBus.ts:159` | adapt | L | `agent` returns runId immediately; `agent.wait` waits terminal |
| Config JSON5 + `SecretRef` (`env\|file\|exec`) + hot reload | `areas/f-substrate-gateway.md`; `src/config/io.load.ts:110`; `src/config/zod-schema.secret-input.ts:22` | `packages/core/src/platform/identity/index.ts:24`; `packages/shared/src/credentials/manager.ts:35` | adapt | L | map SecretRef onto ROX credential sources; skip invalid reloads |
| Plugin activation planner + gateway-startup loading | `areas/f-substrate-gateway.md`; `src/plugins/activation-planner.ts:76` | `packages/server-core/src/openclaw/runtime-manager.ts:1` | reimplement | L | keep descriptors in the same registry as core |
| Cron / hooks / single host-timer scheduler | `areas/f-substrate-gateway.md`; `src/infra/gateway-scheduler.ts:67` | `packages/pi-agent-server/src/index.ts:1` | adapt | M | `beginClose`/`stop` semantics; coalesce missed ticks |
| Node/device model + presence + pending invokes | `areas/f-substrate-gateway.md`; `src/gateway/node-registry.ts:175` | `packages/shared/src/protocol/routing.ts:498`; `packages/server-core/src/transport/server.ts:197` | adapt | M | caps/commands are claims; enforce server-side allowlists |
| State persistence: shared SQLite + per-agent DBs + writer lock | `areas/f-substrate-gateway.md`; `src/state/openclaw-state-db.paths.ts:34` | `packages/server-core/src/memory/fts-index.ts:1`; `packages/server-core/src/meetings/repository.ts:4` | adapt | M | single-writer lock; sessions JSON index + SQLite transcripts |

## g — ROX target surface (destination rules)  (`areas/g-rox-target-surface.md`)

These rows are the *destination* contract every ported feature must obey (source doc `g`).

| capability | OpenClaw reference (doc + key files) | ROX destination (verified) | verdict | effort | top risk |
|---|---|---|---|---|---|
| Typed method→channel map + no raw `webContents.send` | `areas/g-rox-target-surface.md` (§3.1) | `apps/electron/src/transport/channel-map.ts:19`; `apps/electron/src/transport/build-api.ts:26` | reuse-as-is | S | route every new call through `CHANNEL_MAP` + `RPC_CHANNELS` |
| Local-vs-remote channel classification (CI-enforced exhaustiveness) | `areas/g-rox-target-surface.md` (§3.1) | `packages/shared/src/protocol/routing.ts:17`; `packages/shared/src/protocol/routing.ts:498` | reuse-as-is | S | an unclassified new channel fails CI |
| WS RPC server/client transport with access modes | `areas/g-rox-target-surface.md` (§3.2) | `packages/server-core/src/transport/server.ts:197`; `packages/server-core/src/transport/client.ts:124` | reuse-as-is | S | re-subscribe listeners across workspace switches |
| Per-session event stream attach point | `areas/g-rox-target-surface.md` (§3.3) | `packages/server-core/src/sessions/SessionEventBus.ts:159`; `packages/server-core/src/sessions/SessionManager.ts:10788` | reuse-as-is | S | subscribe to the bus, never open a second socket |
| OMP RPC runtime + `extension_ui_response` obligation | `areas/g-rox-target-surface.md` (§3.3) | `packages/shared/src/agent/omp-agent.ts:386`; `packages/shared/src/agent/session-tool-defs.ts:61` | reuse-as-is | M | unanswered `extension_ui_request` stalls the whole turn |
| Identity + credential fabric | `areas/g-rox-target-surface.md` (§3.6) | `packages/core/src/platform/identity/index.ts:24`; `packages/shared/src/credentials/fabric/broker.ts:73` | reuse-as-is | S | use ROX fabric, not a parallel secret store |
| WebUI host (browser dashboard) | `areas/g-rox-target-surface.md` (§3.2) | `packages/server-core/src/webui/http-server.ts:379`; `packages/server-core/src/webui/index.ts:1` | reuse-as-is | S | tokenized auth host for the web surface |
| Russian-first i18n gate (12 locales, `t()`, parity) | `areas/g-rox-target-surface.md` (§3.8) | `packages/shared/src/i18n/languages.ts:6`; `packages/shared/src/i18n/setupI18n.ts:30` | reuse-as-is | S | every new key in all 12 files, ASCII-sorted, `_one/_few/_many` |
| Updater + packaging (electron-updater, dmg/nsis/AppImage) | `areas/g-rox-target-surface.md` (§3.7) | `apps/electron/src/main/auto-update.ts:17`; `apps/electron/electron-builder.yml:91` | reuse-as-is | S | respect ad-hoc-signing detection and update-feed suppression |

---

## Recommended sequencing (4 phases)

Dependencies flow one direction: **P1 substrate → P2 dashboards+skills → P3 memory+multi-user → P4 meetings+voice**.
P2/P3/P4 all depend on P1's transport/identity; P4 additionally depends on P3 (notes reuse memory/context).

**Phase 1 — Substrate, identity, ownership core (4–8 wk).**
Port the *invariants* from `f` (single-owner state lock, loopback default, method registry with
scope gating, per-session lane, transcript fence) and the `a1` identity/roles/ownership layers
(`profile|channel|agent`, creator/owner/participants, `sessions.assignOwner`). Everything else
registers through this. Reuse `g`'s typed channel map + `RpcChannels` and classify any new channel.
*First slice (MVP):* a new `sessions.assignOwner` RPC over the existing `WsRpcServer`, persisted
`creator`/`owner{assignedBy,assignedAt}`/`participants` on the session record, scope-checked at
admission, surfaced only in the renderer's session context menu.

**Phase 2 — Interactive dashboards + skills surface (8–12 wk).**
`b1` WebUI-hosted dashboard (chat streaming + tool cards + sessions sidebar + settings/config form),
`b2` Workboard→Kanban and Canvas→sandboxed widget path, `c2` skills loader/gating/prompt, `a2`
sidebar filter/sort + owner chip + presence/typing.
*First slice:* chat page with streamed deltas reconstructed client-side over OMP RPC (reuse
`gateway-chat-stream-projection` *pattern*), owner chip, and `<available_skills>` injected into the
OMP session prompt from the 330-skill catalog.

**Phase 3 — Memory + multi-user polish (10–14 wk).**
`c1` SQLite index + provenance gates + hybrid search + per-turn injection via OMP RPC; `a2`
public-link sharing menu; `a1` presence roll-out and (optional) visitor/trusted-proxy ingress.
*First slice:* `memory_search`/`memory_get` with a provenance-gated (`owner|agent`) bootstrap of
`MEMORY.md`, verified FTS5+sqlite-vec availability under Bun.

**Phase 4 — Meetings + voice (12–20 wk).**
`d2` transport-agnostic meeting session runtime + caption provenance/ownEcho + notes pipeline;
`d1` Talk event vocabulary + one bridge state machine + TTS/STT relay + voice wake.
*First slice:* an observe-only (`transcribe`) meeting capture with per-line provenance and a
5-minute-cadence summary, persisting to ROX's meeting store and a Meetings reader.

---

## Cross-cutting concerns

1. **Protocol / IPC boundary.** Everything crosses one versioned contract: renderer→preload→main
   via `CHANNEL_MAP` + `RPC_CHANNELS` (`apps/electron/src/transport/channel-map.ts:19`,
   `packages/shared/src/protocol/channels.ts:6`) and main↔backend via
   `WsRpcServer`/`WsRpcClient` (`packages/server-core/src/transport/server.ts:197`). New channels
   MUST be classified `LOCAL_ONLY` vs `REMOTE_ELIGIBLE` (`packages/shared/src/protocol/routing.ts:17`)
   or CI fails. Adopt OpenClaw's frames *shape* (`req`/`res`/`event`, `connect.challenge`,
   `hello-ok` with `features`/`snapshot`/`auth`/`policy`) but do **not** reuse the bespoke WS
   protocol or `protocol:gen:swift`.
2. **Identity fabric.** ROX already owns identity
   (`packages/core/src/platform/identity/index.ts:24`) and a credential/connection fabric
   (`packages/shared/src/credentials/fabric/broker.ts:73`, `packages/shared/src/credentials/manager.ts:35`).
   Port OpenClaw roles/scopes, ownership layers, per-person model accounts, Google Meet OAuth,
   skill allowlists and SecretRefs *onto this fabric* — never a second store. Multi-user is a
   usability plane, explicitly **not** a security boundary (`docs/concepts/multi-user.md:15`).
3. **i18n Russian-first.** Default language is `ru` (`packages/shared/src/i18n/languages.ts:6`);
   every user-facing string goes through `t()` and every new key lands in all 12 locale files,
   ASCII-sorted, with `_one/_few/_many` plural forms (`packages/shared/src/i18n/setupI18n.ts:30`,
   `packages/shared/src/i18n/locales/ru.json:1`). OpenClaw keys (flush prompts, role/denial,
   visitor, typing, model-account wizard, meeting captions) have no translations upstream — they
   must be authored in Russian as part of each port.
4. **Bun/Electron vs Node daemon.** OpenClaw is a standalone Node daemon with ~4.3k gateway
   files and codegen (`areas/f-substrate-gateway.md` §Risks). ROX runs Bun 1.3.14 + Electron 39
   with **OMP RPC in-process**. A literal port is wrong: keep the invariants, host the gateway as
   one in-process module, and use `electron-updater` instead of `curl install.sh`/npm-global/PATH
   rewrites (`apps/electron/src/main/auto-update.ts:17`).
5. **Storage: SQLite/FTS under Bun.** Confirmed by the study as the top unknown — the memory
   design depends on **FTS5 BM25** and optional **sqlite-vec**, plus f64-BLOB cosine fallback
   (`areas/c1-memory.md` §Risks). Verify ROX's SQLite build ships FTS5 (and sqlite-vec if used)
   under `bun:sqlite` before Phase 3; keep the in-process cosine fallback and an index-identity
   rebuild state machine so chunking/provider changes never mix incompatible embeddings.

---

## Non-goals

- **Not a tenant-isolation/security boundary.** Multi-user mode does not separate mutually
  untrusted users; those need separate hosts/OS users (`docs/concepts/multi-user.md:15`).
- **No vendor meeting SDKs / recording.** Do not claim Zoom/Teams meeting creation, dial-in, SDK,
  or recording; only Google Meet has create/dial-in, and no audio/video is ever recorded.
- **No in-process unsandboxed third-party plugins.** Reject OpenClaw's model; third-party plugin
  code runs in a Bun worker/child with a capability IPC surface.
- **No ClawHub publish** from the app (CLI/registry-side only).
- **No OpenClaw WS protocol wholesale** or Swift/JSON-Schema codegen; map the method inventory
  onto OMP RPC.
- **No `curl | bash` / npm-global installer** — Electron packaging + auto-update instead.
- **No Web Awesome / Lit port** — re-express visuals in React/Tailwind v4.
- **No telephony voice-call hosting** in v1 unless a public webhook/tunnel is provisioned.
- **No diarisation** beyond the platform caption speaker label; **no XPC** (sockets + stdio only).
- **No launchd foreign-job reaping** unless ROX later manages launchd jobs itself.

---

*Provenance: synthesized from the 12 area docs in `port-analysis/areas/` (commit `b0c330d2`)
and `g-rox-target-surface.md` §6; every ROX path above was verified to exist in
`/Users/t/Projects/rox-one` on 2026-10-09.*