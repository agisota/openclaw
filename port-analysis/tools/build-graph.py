#!/usr/bin/env python3
"""Assemble the final Understand-Anything knowledge-graph.json for the OpenClaw fork.

Inputs:
  .ua/intermediate/assembled-graph.json   (produced by merge-batch-graphs.py)
  .ua/intermediate/batch-*.json           (raw fragments, for provenance)

Output:
  .ua/knowledge-graph.json                (+ .ua/intermediate/layers.json, tour.json, stats.json)

Layer assignment: special id namespaces first, then ordered path-prefix rules, then batch provenance.
File-level nodes MUST land in exactly one layer (validator requirement).
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/t/Projects/openclaw")
UA = ROOT / ".ua"
INTER = UA / "intermediate"

FILE_LEVEL = {"file", "config", "document", "service", "pipeline", "table", "schema", "resource", "endpoint"}

LAYERS = [
    ("multi-user", "Multi-user / team mode", "Session ownership, roles, presence, sharing and visitor access on a shared Gateway."),
    ("dashboards", "Interactive dashboards", "Control UI, workboard, canvas widgets and embedded browser surfaces."),
    ("memory", "Memory & context", "Memory capture, storage, retrieval and prompt injection."),
    ("skills", "Skills & plugins", "SKILL.md discovery/gating plus the plugin runtime and ClawHub distribution."),
    ("voice", "Voice & realtime", "Realtime talk, TTS/STT pipelines, voice wake and voice-call channel."),
    ("meetings", "Meetings", "Meeting bots that join calls, transcribe, and deliver recaps."),
    ("macos", "macOS app", "The native companion app, its embedded surfaces, permissions and helpers."),
    ("lifecycle", "Install / onboard / daemon", "Installer, onboarding, LaunchAgent daemon lifecycle, doctor and updates."),
    ("mobile", "Mobile & shared apps", "iOS, Android, Linux and shared Swift kits."),
    ("channels", "Channels", "Messaging channel integrations (Discord, Slack, Telegram, WhatsApp, ...)."),
    ("docs", "Docs & specs", "Documentation and upstream completeness specs."),
    ("rox", "ROX port targets", "ROX (rox-one) integration surfaces for the port."),
    ("platform", "Platform & tooling", "Agent runtime, tools, providers, infra and everything else."),
    ("gateway", "Gateway substrate", "Gateway process, protocol, sessions, config, state and plugin loading."),
]
LAYER_IDS = [l[0] for l in LAYERS]

BATCH_AREA = {
    101: "multi-user", 102: "multi-user",
    103: "dashboards", 104: "dashboards",
    105: "memory", 106: "skills",
    107: "voice", 108: "meetings",
    109: "lifecycle", 110: "macos",
    111: "gateway", 112: "rox",
}

# Ordered rules: (layer, compiled regex) applied to "filePath" or id payload.
RULES = [
    ("rox", re.compile(r"^(rox/|ROX:)")),
    ("multi-user", re.compile(r"^(docs/concepts/(multi-user|user-model|presence)|docs/start/teams|docs/gateway/team-server|docs/reference/user-model|extensions/visitor-access/|docs/web/control-ui/sessions-and-sidebar)")),
    ("dashboards", re.compile(r"^(ui/|extensions/workboard/|packages/workboard-contract/|extensions/canvas/|src/canvas-host/|src/boards/|docs/web/|docs/cli/workboard|docs/plugins/workboard|docs/plugins/reference/workboard)")),
    ("memory", re.compile(r"^(extensions/memory-|src/memory|src/context-engine/|packages/memory-host-sdk/|packages/.*/memory|docs/concepts/(memory|active-memory|context-engine)|docs/concepts/memory-|docs/cli/memory)")),
    ("skills", re.compile(r"^(src/skills/|src/plugin-sdk/|src/plugins/|packages/plugin-sdk/|packages/plugin-package-contract/|skills/|custodian-skills/|docs/tools/skills|docs/plugins/building|docs/reference/plugin)")),
    ("voice", re.compile(r"^(src/talk/|src/tts/|src/realtime-transcription/|extensions/voice-call/|extensions/openai/|extensions/google/|docs/(.*voice|.*talk)|docs/concepts/streaming)")),
    ("meetings", re.compile(r"^(src/meeting-bot/|extensions/(google-meet|teams-meetings|zoom-meetings)/|docs/plugins/(meeting|teams-meetings|zoom-meetings|google-meet))")),
    ("lifecycle", re.compile(r"^(src/cli/|src/daemon/|src/commands/|deploy/|docs/install/|docs/cli/|docs/start/|docs/help/|scripts/)")),
    ("macos", re.compile(r"^(apps/macos|apps/macos-mlx-tts|docs/platforms/mac)")),
    ("mobile", re.compile(r"^apps/(ios|android|linux|shared|swabble|\.i18n)")),
    ("channels", re.compile(r"^(src/channels/|src/auto-reply/|extensions/(discord|slack|telegram|whatsapp|signal|imessage|matrix|msteams|feishu|line|mattermost|googlechat|zalouser|tlon|clickclack|irc|nostr|twitch|nextcloud|synology|qq|wechat|yuanbao|zalo|whatsapp))")),
    ("gateway", re.compile(r"^(src/(gateway|sessions|routing|state|config|storage|secrets|security|pairing|node-host|infra|logging|utils|process|runtime|hooks|cron|flows|acp|tui|web|web-fetch|web-search|trajectory|snapshot|transcripts|status|model-catalog|model-picker|llm|mcp|media|image-generation|video-generation|music-generation|link-understanding|proxy-capture|provider-runtime|projects|plugin-state|polls|system-agent|claws|chat|broadcast|bootstrap|interactive|decisions|audit|classes)/|packages/gateway-protocol/|packages/gateway-client/|packages/acp-core/|packages/agent-core/|packages/llm-core/|packages/model-catalog-core/|packages/terminal-core/|packages/net-policy/|packages/retry/|packages/tool-call-repair/|packages/worker-runtime/|packages/normalization-core/|packages/ai/|packages/sdk/|packages/session-url-contract/|packages/markdown-core/|packages/mermaid-renderer/)")),
    ("docs", re.compile(r"^(docs/|\.agents/skills/)")),
]

DOC_AREA_BY_SLUG = {
    "a1": "multi-user", "a2": "multi-user", "b1": "dashboards", "b2": "dashboards",
    "c1": "memory", "c2": "skills", "d1": "voice", "d2": "meetings",
    "e1": "lifecycle", "e2": "macos", "f": "gateway", "g": "rox",
}


def payload(node):
    fp = node.get("filePath") or ""
    if fp:
        return fp.lstrip("./")
    nid = node.get("id", "")
    if ":" in nid:
        return nid.split(":", 1)[1]
    return nid


def assign_layer(node, provenance):
    nid = node.get("id", "")
    fp = (node.get("filePath") or "").lstrip("./")
    if nid.startswith("concept:rox-") or nid.startswith("file:rox/") or fp.startswith("rox/"):
        return "rox"
    if fp.startswith("port-analysis/"):
        m = re.match(r"port-analysis/(?:areas/)?([a-z])", fp)
        if m:
            return DOC_AREA_BY_SLUG.get(m.group(1), "docs")
        return "docs"
    target = payload(node)
    for layer, rx in RULES:
        if rx.search(target):
            return layer
    b = provenance.get(nid)
    if b in BATCH_AREA:
        return BATCH_AREA[b]
    return "platform"


def main():
    graph = json.loads((INTER / "assembled-graph.json").read_text())
    nodes = graph["nodes"] if isinstance(graph, dict) else graph
    edges = graph.get("edges", []) if isinstance(graph, dict) else []

    # Safety net: coerce string tags into arrays (schema requires arrays).
    for n in nodes:
        t = n.get("tags")
        if isinstance(t, str):
            n["tags"] = [x.strip() for x in re.split(r"[,;]", t) if x.strip()] or ["untagged"]
        elif not isinstance(t, list) or not t:
            n["tags"] = ["untagged"]
        else:
            n["tags"] = [str(x).strip() for x in t if str(x).strip()] or ["untagged"]

    provenance = {}
    for f in sorted(INTER.glob("batch-*.json")):
        n = int(re.search(r"batch-(\d+)", f.name).group(1))
        try:
            frag = json.loads(f.read_text())
        except Exception as e:
            print(f"WARN: unreadable {f.name}: {e}")
            continue
        for node in frag.get("nodes", []):
            provenance.setdefault(node.get("id"), n)

    by_id = {n["id"]: n for n in nodes}
    deg = defaultdict(int)
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1

    layer_nodes = defaultdict(list)
    for n in nodes:
        layer_nodes[assign_layer(n, provenance)].append(n)

    layers = []
    for lid, name, desc in LAYERS:
        ids = [n["id"] for n in layer_nodes.get(lid, [])]
        if not ids:
            continue
        layers.append({"id": lid, "name": name, "description": desc, "nodeIds": ids})

    # Tour: one step per non-empty layer, top nodes by degree (file-level/concept preferred).
    tour = []
    order = 1
    for lid, name, desc in LAYERS:
        if not layer_nodes.get(lid):
            continue
        ranked = sorted(layer_nodes[lid], key=lambda n: (-deg[n["id"]], n["id"]))
        pick, seen_names = [], set()
        for n in ranked:
            if n["name"] in seen_names:
                continue
            seen_names.add(n["name"])
            pick.append(n)
            if len(pick) == 4:
                break
        tour.append({
            "order": order,
            "title": f"{name} — key surfaces",
            "description": f"Start with these entry points for {desc[0].lower() + desc[1:]}",
            "nodeIds": [n["id"] for n in pick],
        })
        order += 1

    project = {
        "name": "openclaw",
        "languages": ["typescript", "swift", "kotlin", "rust", "javascript", "shell", "css", "markdown"],
        "frameworks": ["node", "lit", "swiftui", "electron", "vite", "vitest"],
        "description": "Multi-channel AI gateway with extensible messaging integrations — personal assistant across channels plus native apps (fork agisota/openclaw @ b0c330d2).",
        "analyzedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "gitCommitHash": "b0c330d27df4a528f65185cc3e509284d1b218d9",
    }
    final = {"version": "1.0.0", "kind": "codebase", "project": project,
             "nodes": nodes, "edges": edges, "layers": layers, "tour": tour}
    (UA / "knowledge-graph.json").write_text(json.dumps(final, indent=1))
    (INTER / "layers.json").write_text(json.dumps(layers, indent=1))
    (INTER / "tour.json").write_text(json.dumps(tour, indent=1))

    stats = {
        "nodes": len(nodes), "edges": len(edges), "layers": len(layers), "tour": len(tour),
        "by_type": {}, "by_layer": {l["id"]: len(l["nodeIds"]) for l in layers},
    }
    for n in nodes:
        stats["by_type"][n["type"]] = stats["by_type"].get(n["type"], 0) + 1
    (INTER / "stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()