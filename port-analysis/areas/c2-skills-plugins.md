---
area: "Skills & plugin system"
slug: c2-skills-plugins
date: 2026-10-09
commit: b0c330d2
coverage:
  - src/skills (loading, discovery, lifecycle, runtime, security, library, workshop)
  - skills/ bundled tree
  - custodian-skills/ release-versioned operational playbooks
  - src/plugins + src/plugin-sdk + packages/plugin-sdk
  - docs/tools/{skills,creating-skills,skills-config,custodian-skills}.md
  - docs/plugins/{architecture,manifest,architecture-internals} + reference
  - ClawHub client/install/trust/publish (src/infra/clawhub-*, src/skills/lifecycle/clawhub*)
date: 2026-10-09
commit: b0c330d2
---

# Skills & plugin system (OpenClaw → ROX port study)

## What it is / user-visible behavior

Two distinct layers that are frequently confused but share one trust-relevant
story:

- **Skills** are `SKILL.md` markdown instruction packs. They add **no tools** —
  they teach the agent how to use tools it already has (`docs/tools/index.md:53`).
  A skill is a directory containing `SKILL.md` (YAML frontmatter + markdown
  body); the directory path is organisational only, the skill's identity and
  slash command come from the `name` frontmatter field or the directory name
  (`docs/tools/skills.md:91`). Eligible skills are compiled into an
  `<available_skills>` XML block injected into the system prompt, plus optional
  `skills_search` / `skills_read` tools for catalogs too large for the prompt
  (`docs/tools/skills.md:873`, `docs/tools/skills.md:945`).
- **Plugins** are code. A native plugin ships `openclaw.plugin.json` and a
  `register(api)` entry that registers tools, channels, providers, hooks,
  services, HTTP routes, CLI commands, or skills
  (`docs/plugins/architecture.md:107`, `docs/tools/index.md:66`). Native plugins
  run **in-process** with the Gateway and are explicitly **not sandboxed**
  (`docs/plugins/architecture.md:908`) — a malicious native plugin is arbitrary
  code execution inside the process.
- **Extensions** are simply bundled plugins: `extensions/*/openclaw.plugin.json`
  is the bundled channel/provider plugin tree, e.g. Discord and Telegram ship
  `skills` directories and channel manifests alongside their entry code
  (`extensions/discord/openclaw.plugin.json:1`, `extensions/telegram/openclaw.plugin.json:1`).
- **Custodian skills** (`custodian-skills/`) are release-versioned operational
  playbooks that load at the bundled tier but are **absent for every agent
  except the configured system/Custodian agent** (`docs/tools/custodian-skills.md:11`).
- **ClawHub** is the public registry: a plugin catalog plus a skill registry
  with a packaged trust/scan envelope consumed before install
  (`docs/tools/skills.md:334`, `docs/tools/skills.md:377`).

## End-to-end flow

```mermaid
flowchart TD
  subgraph Skill discovery
    SR[Skill roots: workspace, .agents/skills, personal, managed, workshop, bundled, custodian, extraDirs]
    MPS[Plugin manifest skills dirs → generated symlinks]
  end
  subgraph Plugin discovery
    PR[Plugin roots: plugins.load.paths, workspace .openclaw/extensions, source-checkout bundled, global]
    MF[openclaw.plugin.json / bundle manifest.json]
  end

  SR --> DISC[discoverSkillCandidates]
  MPS --> DISC
  DISC --> LOAD[loadSingleSkillDirectory → parseSkillFrontmatter → materializeSkill]
  LOAD --> PREC[mergeSkillRecords: name-keyed highest-precedence wins]
  PREC --> GATE[filterSkillEntries: agent allowlist, skills.entries.enabled, allowBundled, requires.bins/env/config, os, secret owners]
  GATE --> SNAP[Session snapshot + system prompt available_skills XML]
  GATE --> CMD[User-invocable slash commands / $refs]
  GATE --> TOOLS[skills_search / skills_read tools if catalog omitted]

  PR --> RD[read manifest + package.json#openclaw]
  MF --> RD
  RD --> SAFE[Safety gates: entry containment, world-writable, uid ownership]
  SAFE --> ENABLE{plugins.enabled + allow/deny + entries/<id>.enabled}
  ENABLE -- blocked --> DIAG[Diagnostic: disabled/blocked/failed, no execution]
  ENABLE -- enabled --> REG[execute register(api) in registrationMode]
  REG --> REGISTRY[PluginRegistry: tools, channels, providers, hooks, services, routes, CLI]
  REGISTRY --> SURFACE[Agent tool surface + channel/message tool + HTTP routes]
  MPS -. generated symlinks .-> DISC

  TOOLS --> EXEC[Tool call execution]
  SNAP --> MODEL[Model selects skill and reads SKILL.md]
  CMD --> EXEC
  SURFACE --> EXEC
  MODEL --> EXEC
```

## Mechanisms

### 1. SKILL.md format, frontmatter and helper files
- Parsing: `parseSkillFrontmatter` calls `parseFrontmatterBlockResult` from
  `packages/markdown-core/src/frontmatter.ts` (YAML first, single-line fallback)
  and `structuredClone`s the result so cached metadata does not retain the
  source `SKILL.md` (`src/skills/loading/frontmatter.ts:27`,
  `packages/markdown-core/src/frontmatter.ts:282`).
- The `metadata` field is a JSON5 blob; `resolveOpenClawManifestBlock` reads it
  as a string and parses via JSON5 fallback (`src/shared/frontmatter.ts:29`).
- `resolveSkillManifestMetadata` yields `always`, `emoji`, `homepage`,
  `skillKey`, `primaryEnv`, `os`, `requires`, `install`
  (`src/skills/loading/frontmatter.ts:146`); `resolveOpenClawManifestInstall`
  parses `brew|node|go|uv|download` installer specs
  (`src/shared/frontmatter.ts:67`, `src/skills/loading/frontmatter.ts:76`).
- Invocation policy: `user-invocable` (default true) and
  `disable-model-invocation` (default false)
  (`src/skills/loading/frontmatter.ts:168`); `command-dispatch: tool` +
  `command-tool` route a slash command straight to a tool, bypassing the model
  (`docs/tools/skills.md:477`).
- `resolveSkillKey` = `metadata.skillKey ?? skill.name`, the key used for
  `skills.entries` config and allowlists (`src/skills/loading/frontmatter.ts:180`).
- Helper scripts/references: the **body** references `{baseDir}` (resolved by
  the agent against the skill directory); supporting scripts/references/assets
  live beside `SKILL.md` and are read at their `filePath`/`baseDir`
  (`src/skills/loading/skill-contract.ts:6`, `docs/tools/skills.md:456`).
  `materializeSkill` derives `displayName` from the first H1
  (`src/skills/loading/skill-materializer.ts:29`).

### 2. Discovery + precedence
- Root plan is assembled low-to-high by `resolveWorkspaceSkillSourcePlan`:
  `extraDirs` + plugin skill roots (tier `extra`) → bundled → custodian
  (bundled tier, only for the Custodian agent) → workshop → managed
  (`<state-dir>/skills`) → personal (`~/.agents/skills`, default state only) →
  workspace roots (`src/skills/loading/workspace-skill-sources.ts:81`).
  Custodian inclusion is gated by `resolveCustodianSkillAgentId`
  (`src/skills/loading/workspace-skill-sources.ts:69`).
- Workspace-local roots are `<workspace>/skills` and
  `<workspace>/.agents/skills`, with `skills/` winning
  (`src/skills/loading/workspace-skill-roots.ts:39`).
- Discovery walks up to 6 levels for `SKILL.md` under a configured root,
  bounding recursive scans with a directory/entry budget
  (`src/skills/loading/skill-root-discovery.ts:26`,
  `src/skills/loading/skill-root-discovery.ts:414`). Plugin skills are
  discovered only as **validated generated symlinks** whose realpath stays
  inside a declared plugin skill root, with a hardlink policy per root
  (`src/skills/loading/skill-root-discovery.ts:639`).
- Precedence is a name-keyed merge where the last/highest source wins;
  `mergeSkillRecords` records collisions when two entries share a name but
  have different canonical paths (`src/skills/loading/skill-precedence.ts:105`);
  execution-workspace entries are appended with lower precedence
  (`src/skills/loading/skill-precedence.ts:129`). Collision reporting warns when
  a workspace/project skill shadows bundled/custodian
  (`src/skills/loading/skill-precedence.ts:13`).
- Plugin-declared skill dirs are materialised as generated symlinks under
  `~/.openclaw/plugin-skills/` so the SDK can find them at the conventional
  extra-dir path, which is why plugin skills lose to bundled/managed/workspace
  (`src/skills/loading/plugin-skills.ts:280`, `docs/tools/skills.md:265`).

### 3. Gating: which skills reach which agent/session
- `shouldIncludeSkill` is the load-time gate: `skills.entries.<key>.enabled === false`
  disables; a degraded secret owner disables; the bundled allowlist
  (`skills.allowBundled`, bundled/custodian sources only) filters; then runtime
  eligibility checks `os`, `always`, `requires.bins|anyBins|env|config`
  (`src/skills/loading/config.ts:112`, `src/skills/loading/config.ts:84`).
- Agent visibility is separate from location: `resolveEffectiveAgentSkillFilter`
  reads `agents.entries.<id>.skills` and falls back to `agents.defaults.skills`
  (`src/skills/discovery/agent-filter.ts:13`). A non-empty per-agent list is
  final (does not merge defaults); `[]` exposes nothing
  (`docs/tools/skills.md:251`).
- Session overlay: `isSessionSkillEnabled` applies sparse
  `skillOverrides` after the base filter; Workshop skills bypass allowlists and
  session toggles entirely (`src/skills/discovery/agent-filter.ts:43`,
  `src/skills/loading/config.ts:101`).
- `filterSkillEntries` composes selection + `shouldIncludeSkill` and is the
  single filter used across prompt building, slash-command discovery, sandbox
  sync and snapshots (`src/skills/loading/workspace-skill-filter.ts:11`).
- The whole pipeline is async and retries when binary probing is not yet
  current, then emits `eligible` entries (`src/skills/loading/workspace-skill-loader.ts:551`).

### 4. How the skill surface becomes callable
Three surfaces, all gated by the same eligible list:
- **Prompt**: `formatSkillsForPromptCore` renders `<available_skills><skill><name>/<location>`
  (`src/skills/loading/skill-contract.ts:131`); `buildSkillsSection` injects it
  with instructions to read the exact location (`src/agents/system-prompt-skills.ts:3`).
  `compactSkillsPromptForContext` bounds descriptions against a token budget
  while keeping every name/location (`src/skills/loading/skill-contract.ts:56`).
- **Tools**: `createInstalledSkillTools` builds `skills_search` (metadata +
  bounded body lexical search) and `skills_read` (whole `SKILL.md`, 256 KiB cap)
  over the eligible catalog (`src/agents/tools/installed-skill-tools.ts:20`,
  `src/agents/installed-skill-catalog.ts:147`, `:248`,
  `src/agents/installed-skill-catalog.ts:20`). Read authority is bound so a
  `skills_read` denial also disables body indexing.
- **Slash commands / $refs**: `buildWorkspaceSkillCommandSpecs` filters
  user-invocable skills and assigns unique command names
  (`src/skills/discovery/command-specs.ts:89`); workspace/agent command lists
  come from `chat-commands.ts` (`src/skills/discovery/chat-commands.ts:77`).
  `command-dispatch: tool` invocations go through `resolveSkillDispatchTools`,
  which applies the **same** tool-policy pipeline (profile/provider/global/
  agent/group/sender/sandbox/subagent/owner-only) as normal agent turns
  (`src/skills/runtime/tool-dispatch.ts:58`).
- Snapshots are captured at session start and refreshed on watcher/Gateway/
  node-connect triggers (`docs/tools/skills.md:754`).

### 5. Plugin lifecycle: manifest, activation boundary, hot reload, sandboxing, packaging
- **Manifest** (`openclaw.plugin.json`) is the control-plane source of truth and
  must be readable **without executing plugin code**; the TypeScript shape is
  `PluginManifest` (`src/plugins/manifest-types.ts:416`,
  `docs/plugins/manifest.md:20`). It declares identity, `configSchema`,
  capabilities/contracts, `activation` hints, `skills` dirs, `mcpServers`,
  `cliCommands`, doctor/backup/QA metadata (`docs/plugins/manifest.md:24`).
- **Authoring contract**: `definePluginEntry({id,name,description,register})`
  for non-channel plugins and `defineBundledChannelEntry` for channels
  (`src/plugin-sdk/plugin-entry.ts:240`,
  `src/plugin-sdk/channel-entry-contract.ts:491`). The published package is
  `@openclaw/plugin-sdk` with a large subpath export map
  (`packages/plugin-sdk/package.json:2`); each subpath re-exports the real
  implementation from `src/plugin-sdk/*` (e.g.
  `packages/plugin-sdk/src/plugin-entry.ts:1`).
- **Activation boundary**: `api.registrationMode` is `full|discovery|tool-discovery|setup-only|setup-runtime|cli-metadata`;
  the live runtime applies to `full`, `discovery`, `tool-discovery` and `setup-runtime`, while
  `setup-only`/`cli-metadata` are unavailable and throw on runtime access
  (`docs/plugins/sdk-entrypoints/registration-mode.md:18-27`).
  Manifest `activation`/`setup` blocks narrow loading (e.g. `onStartup`,
  `onConfigPaths`, `onAgentHarnesses`) and are metadata, not lifecycle hooks
  (`docs/plugins/architecture-internals/load-pipeline.md:70`).
- **Load pipeline**: discover roots → read manifests/package metadata → reject
  unsafe candidates (entry escapes root, world-writable, non-bundled uid
  mismatch) → normalize `plugins.enabled|allow|deny|entries|slots|load.paths`
  → decide enablement → load modules → call `register(api)` → publish to
  `PluginRegistry` (`docs/plugins/architecture-internals/load-pipeline.md:17`,
  `docs/plugins/architecture-internals/load-pipeline.md:39`). Registration
  lands in `PluginRegistry` (`src/plugins/registry-types.ts:383`), and core
  reads the registry rather than plugin modules
  (`docs/plugins/architecture-internals/load-pipeline.md:280`).
- **Hot reload**: `plugins.reload` / `plugins.refresh` prepare a new plugin-cache
  generation, drain admitted work under a 60 s budget, stop the previous
  registration, register the replacement, then publish runtime methods and
  metadata together; `restartRequired: true` is set when process-shared code
  cannot be swapped (`src/plugins/lifecycle.ts:48`,
  `docs/plugins/architecture.md:177`). Failed installs still persist and tell
  the operator to run `openclaw plugins reload <id>`
  (`src/plugins/lifecycle.ts:12`).
- **Sandboxing**: none. Native plugins are in-process; only *bundles* are the
  safer metadata/content path, and even those are normalised into registry
  records without importing runtime code
  (`docs/plugins/architecture.md:908`,
  `docs/plugins/architecture-internals/load-pipeline.md:116`). `plugins.allow`
  is an id-level load permit, **not** source-provenance verification
  (`docs/plugins/architecture.md:921`).
- **Package/bundle contract**: `package.json#openclaw` carries
  `extensions`/`runtimeExtensions`/`setupEntry`/`channel`/`install.*` including
  `clawhubSpec`, `npmSpec`, `minHostVersion`, `compat.pluginApi`,
  `expectedIntegrity` (`docs/plugins/manifest/package-json.md:33`). Compatible
  bundle formats are detected by file name — `.codex-plugin/plugin.json`,
  `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, and the Agent
  Plugins `plugin.json` (`src/plugins/bundle-manifest.ts:27`,
  `src/plugins/bundle-manifest.ts:222`).
- Duplicate plugin ids resolve by precedence: config-selected > source-checkout
  bundled > tracked global install > bundled > workspace > untracked global
  (`docs/plugins/manifest/package-json.md:129`).
- Enable is a config mutation guarded by `plugins.enabled`, `plugins.deny` and
  `plugins.allow` (`src/plugins/enable.ts:44`); install/update/uninstall/config
  cleanup and inspection are surfaced by the management service
  (`src/plugins/management-service.ts:1`). Install sources are planned from
  source specs (`src/plugins/install-source-plan.ts:1`) and every install path
  runs the install security scan + operator install policy before activation
  (`src/plugins/install-security-scan.ts:24`, `docs/tools/skills.md:421`).

### 6. ClawHub publish/install + trust
- Client: one bounded HTTP client with base URL `https://clawhub.ai`, token
  resolution, retries and a 256 MiB archive cap
  (`src/infra/clawhub-client.ts:17`, `src/infra/clawhub-client.ts:24`).
- Trust gate (shared by plugin and skill installs): `checkClawHubPackageTrust`
  fetches the exact-release security verdict and maps it through
  `assessClawHubTrust` to `clean|review-recommended|review-required|blocked`
  (`src/infra/clawhub-install-trust.ts:479`,
  `src/infra/clawhub-install-trust.ts:113`); the failure codes are
  `clawhub_security_unavailable` / `clawhub_download_blocked`
  (`src/infra/clawhub-install-trust.ts:17`). Publisher handle is verified against
  the expected owner and mismatches fail closed (`src/infra/clawhub-install-trust.ts:337`).
- Skill install: `performClawHubSkillInstall` resolves the version, checks the
  mutable-GitHub-ref hazard (requires a full 40-char commit),
  `checkClawHubSkillTrust`, then downloads/verifies the archive before install
  (`src/skills/lifecycle/clawhub-install-core.ts:248`,
  `src/skills/lifecycle/clawhub-install-core.ts:217`). Tracking lives in
  `.clawhub/lock.json` and per-skill `.clawhub/origin.json`
  (`docs/tools/skills.md:370`).
- Skill verify/install/update entry points: `verifySkillWithClawHub`,
  `installSkillFromClawHub`, `updateSkillsFromClawHub`
  (`src/skills/lifecycle/clawhub.ts:48`, `:191`, `:206`).
- Plugin catalog: `joinClawHubPluginCatalog` / `browseClawHubCatalog` /
  `searchClawHubCatalogKeywords` map ClawHub packages into the plugin catalog
  and detail/inspection views; `searchInstallablePluginPackages` is the search
  seam (`src/plugins/catalog-discovery.ts:129`, `:588`, `:619`,
  `src/plugins/catalog-search.ts:14`). Plugin skill *previews* read a ClawHub
  release inventory (paths/sizes/SHA-256) without downloading or installing
  (`src/infra/clawhub-plugin-skills.ts:21`).
- Publish is **not** an OpenClaw code path: the bundled `clawhub` skill directs
  publishing/syncing to the standalone `clawhub` CLI (`skills/clawhub/SKILL.md:1`,
  `docs/tools/skills.md:352`). `openclaw skills`/`openclaw plugins` cover
  discovery/install/update/verify.
- Archive safety: skill bundles are scanned by `scanSkillBundle` (literal-secret
  assertion + per-file findings) and the general scanner
  (`src/skills/security/skill-bundle-scan.ts:21`, `:38`,
  `src/skills/security/scanner.ts:498`).

### 7. Custodian-skills purpose
Release-versioned operational playbooks under `custodian-skills/`, loaded at the
bundled tier but restricted to `agents.defaults.systemAgent.agentId`
(`docs/tools/custodian-skills.md:11`). Each follows a fixed
Gather → Mutate → Repair → Prove → Report contract, mutating only through
validated non-interactive writes (`docs/tools/custodian-skills.md:19`). Shipped
first wave: `configure-channel`, `add-model-provider`, `diagnose-gateway`,
`cloud-image-bake` (`docs/tools/custodian-skills.md:33`,
`custodian-skills/configure-channel/SKILL.md:1`). The trick is that they are
implemented as *skills*, not privileged code — they get no new tools or
credentials (`docs/tools/skills.md:171`).

### 8. Plugins vs skills vs extensions
- Tool = typed callable function; Skill = markdown instructions in the prompt;
  Plugin = code that adds capabilities (`docs/tools/index.md:40`, `:53`, `:66`).
- A plugin can ship **skills** by listing `skills` dirs in
  `openclaw.plugin.json`; they load when the plugin is enabled and merge at the
  low `extraDirs` precedence tier (`docs/tools/skills.md:265`,
  `src/skills/loading/plugin-skills.ts:41`).
- Extensions = the bundled plugin tree compiled with the host checkout; bundled
  plugin trust is resolved from the on-disk source snapshot, not install metadata
  (`docs/plugins/architecture.md:929`). A plugin can also contribute MCP servers,
  themes, Control UI, dashboard widgets, and CLI commands
  (`docs/plugins/manifest.md:33`).

## Key contracts & data shapes

- `Skill` interface: `name, displayName?, description, locationNote?, readContent?, contentHash?, filePath, baseDir, discoveryRoot?, fileHost?, sourceInfo, disableModelInvocation, source`
  (`src/skills/loading/skill-contract.ts:6`).
- Skill frontmatter keys: `name`, `description`, `homepage`, `user-invocable`,
  `disable-model-invocation`, `command-dispatch`, `command-tool`,
  `command-arg-mode`; nested `metadata.openclaw.{always,emoji,homepage,skillKey,primaryEnv,os,requires.{bins,anyBins,env,config},install[]}`
  (`docs/tools/skills.md:460`, `docs/tools/skills.md:515`).
- `PluginManifest` (native `openclaw.plugin.json`): `id`, `configSchema` required;
  `kind`, `channels`, `providers`, `skills`, `contracts`, `activation`, `setup`,
  `mcpServers`, `cliCommands`, `commandAliases`, `uiCapabilities`, `themes`,
  `dashboard`, `backupResources`, `qaRunners`, `requiresPlugins`,
  `autoEnableWhenConfiguredProviders`, `legacyPluginIds`
  (`src/plugins/manifest-types.ts:416`).
- `packages/plugin-sdk/package.json#exports` subpath map — the plugin import
  contract (`packages/plugin-sdk/package.json:6`).
- `definePluginEntry` returns `DefinedPluginEntry` = `{id,name,description,kind?,reload?,nodeHostCommands?,securityAuditCollectors?,configSchema,register}`
  (`src/plugin-sdk/plugin-entry.ts:227`).
- Plugin lifecycle types: `PluginRuntimeApplication` (`operationId, generation,
  pluginIds, sourceDigests?, selectedEntries?, restartRequired?, warnings?`) and
  `PluginLifecycleReason` = `install|enable|disable|uninstall|reload|metadata`
  (`src/plugins/lifecycle.ts:48`, `:59`).
- `registrationMode` values + per-mode required registrations
  (`docs/plugins/sdk-entrypoints/registration-mode.md:18`).
- Trust envelope: `clawhub.skill.verify.v1` and ClawHub security verdict items
  (`docs/tools/skills.md:378`, `src/infra/clawhub-skill-security.ts:115`).
- `PluginRegistry` (`src/plugins/registry-types.ts:383`).

## Tests & QA

- Skill loading/filtering/precedence: `src/skills/loading/*.test.ts`
  (`frontmatter.test.ts`, `workspace-precedence.test.ts`,
  `workspace-bundled-allowlist.test.ts`, `plugin-skills.test.ts`,
  `skill-root-discovery.test.ts`, `skill-path-containment.test.ts`).
- Skill tools: `src/agents/tools/installed-skill-tools.test.ts`; scanner
  `src/skills/security/*.test.ts`.
- ClawHub: `src/infra/clawhub-client.test.ts`, `clawhub-install-trust` paths
  exercised by `clawhub-skill-security.test.ts`, `clawhub-packages.test.ts`,
  `clawhub-spec.test.ts`; skill lifecycle e2e
  `src/cli/skills-cli.clawhub-install.e2e.test.ts`,
  `src/cli/plugins-search-command.clawhub.e2e.test.ts`.
- Plugins: `src/plugins/*.test.ts` (manifest-registry, install-*, loader.*,
  lifecycle) and `bundled-manifest-contract-plugins.test.ts` contract tests
  (`docs/plugins/architecture.md:856`).
- Docs to use as acceptance references: `docs/tools/skills.md`,
  `docs/tools/creating-skills.md`, `docs/tools/custodian-skills.md`,
  `docs/plugins/architecture.md`, `docs/plugins/architecture-internals/load-pipeline.md`.

## Port notes to ROX

ROX already has a 330-skill catalog (`apps/electron/resources/skills/SKILLS.lock`),
`sources`/MCP, identity/credential fabric, and `~/.rox` config dir. Mapping:

1. **Skill format/loader → `packages/server-core` (Bun).** Port
   `parseSkillFrontmatter` + `materializeSkill` + `Skill` shape almost verbatim;
   keep the JSON5 `metadata.openclaw` block (rename to a `rox`-keyed block only if
   you also migrate bundled skills). This is pure, dependency-light code.
2. **Discovery/precedence → server-core `skills/loading`.** Model the root plan
   as an explicit, ordered array (`extra → bundled → custodian → workshop →
   managed → personal → workspace`) with a name-keyed merge and a collision
   report, exactly like `resolveWorkspaceSkillSourcePlan` + `mergeSkillRecords`.
   ROX's existing `SKILLS.lock` maps to the bundled tier; add a managed tier
   under `~/.rox/skills`.
3. **Gating → server-core, keyed on ROX identity.** ROX's identity fabric gives a
   stable per-operator id — use it for an agent/operator allowlist analogous to
   `agents.entries.<id>.skills` plus `skills.allowBundled`. Keep `requires.bins/env/config`
   eligibility; map "env" to ROX credential fabric rather than raw `process.env`.
4. **Prompt surface → Electron renderer session bootstrap.** Inject the
   `<available_skills>` XML block into the OMP RPC session prompt from
   server-core; expose `skills_search`/`skills_read` as session tools through the
   same RPC tool registry. Do **not** invent a new IPC channel: reuse the existing
   server→renderer tool-call path (`packages/server`, `apps/electron/src/main`).
   Surface `/skill <name>` and `$skill` references in the renderer composer.
5. **Plugins → server-core plugin registry + Bun worker boundary.** ROX should
   keep OpenClaw's manifest-first split (`openclaw.plugin.json`-equivalent
   `rox.plugin.json`, readable without executing code) and the registration-mode
   boundary. Critically, ROX **should not** copy "in-process, unsandboxed":
   run third-party plugin code in a Bun worker / child process with an explicit
   capability IPC surface, keeping only bundled skills/plugins in-process.
6. **ClawHub → a ROX registry service behind `packages/server`.** Port the trust
   gate (exact-release verdict → `clean|review-recommended|review-required|blocked`,
   fail-closed publisher mismatch) and the `.clawhub/origin.json`-style tracking
   records; keep install policy execution operator-side. Publish is out of scope
   for the app — keep it a CLI/registry-side workflow.
7. **Custodian → ROX system agent.** Adopt the Gather→Mutate→Repair→Prove→Report
   playbook contract and the "skill, not privileged tool" design: ship them as
   bundled skills gated to one system operator id instead of new tools.
8. **i18n:** skill/plugin descriptions and UI strings are Russian-first in ROX;
   keep `description` in SKILL.md frontmatter as authored (English built-ins) and
   localize only the surfaced catalog labels in the renderer.

## Risks & unknowns

- **No plugin sandboxing upstream.** Porting native-plugin semantics as-is would
  silently make ROX plugins arbitrary in-process code. This is the top port risk
  and must be re-architected (worker boundary), not copied.
- **Identity-keyed allowlists.** OpenClaw keys allowlists on agent id; ROX's
  equivalent (operator identity vs session) must be chosen deliberately or
  visibility will diverge from ROX's existing meeting/skill scoping.
- **Manifest surface is huge.** `PluginManifest` has dozens of optional fields;
  porting a subset while plugins declare the rest must degrade gracefully (ignore
  unknown fields, never fail closed on them).
- **ClawHub endpoint shape is external.** The client assumes `clawhub.ai` API v1
  paths (`/api/v1/packages/...`) and a security-verdict schema; ROX's registry
  may differ, so the trust gate must be re-specified against ROX's registry.
- **UNVERIFIED:** exact `openclaw plugins publish` existence (publish appears to
  be delegated to the standalone `clawhub` CLI; no in-repo publish command was
  read). Treat "publishing is external" as evidence-based for the CLI but not for
  every release/CI path.
- **UNVERIFIED:** the precise contents of `src/plugins/loader-runtime-core.ts`
  (large; not read) — the load-pipeline ordering above is cited from
  `docs/plugins/architecture-internals/load-pipeline.md`, not the implementation.
- **UNVERIFIED:** whether ROX's `SKILLS.lock` format is compatible with
  OpenClaw's revision/hash model without a migration.