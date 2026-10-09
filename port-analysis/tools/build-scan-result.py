#!/usr/bin/env python3
"""Compose .ua/intermediate/scan-result.json so merge-batch-graphs.py can recover
`imports` edges from a real, tree-sitter-derived importMap.

Steps:
 1. read .ua/tmp/scan-partial.json (deterministic inventory from scan-project.mjs)
 2. collect filePaths referenced by the graph fragments (batch-*.json)
 3. run extract-import-map.mjs with analysisPaths = those files (fast)
 4. write .ua/intermediate/scan-result.json = scan partial + importMap + project narrative
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path("/Users/t/Projects/openclaw")
UA = ROOT / ".ua"
INTER = UA / "intermediate"
SKILL = Path("/Users/t/.agents/skills/understand/plugin/skills/understand")

partial = json.loads((UA / "tmp" / "scan-partial.json").read_text())

paths = set()
for frag in sorted(INTER.glob("batch-*.json")):
    if "existing" in frag.name:
        continue
    try:
        data = json.loads(frag.read_text())
    except Exception:
        continue
    for n in data.get("nodes", []):
        fp = n.get("filePath")
        if fp and (ROOT / fp).exists():
            paths.add(fp)
analysis = sorted(paths)

input_path = UA / "tmp" / "import-input.json"
out_path = UA / "tmp" / "import-map.json"
input_path.write_text(json.dumps({
    "projectRoot": str(ROOT),
    "files": [{"path": f["path"], "language": f.get("language", "unknown"),
               "fileCategory": f.get("fileCategory", "code")} for f in partial.get("files", [])],
    "analysisPaths": analysis,
}))
print(f"analysisPaths: {len(analysis)}")

r = subprocess.run(["node", str(SKILL / "extract-import-map.mjs"), str(input_path), str(out_path)],
                   capture_output=True, text=True, cwd=str(SKILL))
print("extract-import-map exit", r.returncode)
if r.stderr:
    tail = [l for l in r.stderr.splitlines() if not l.startswith("Warning:")]
    print("\n".join(tail[-5:]))

import_map = {}
if out_path.exists():
    im = json.loads(out_path.read_text())
    import_map = im.get("importMap", {})
    print("importMap entries:", len(import_map), "stats:", json.dumps(im.get("stats", {}))[:200])

scan_result = dict(partial)
scan_result["projectName"] = "openclaw"
scan_result["name"] = "openclaw"
scan_result["description"] = ("Multi-channel AI gateway with extensible messaging integrations — "
                              "personal assistant across chat channels plus native macOS/iOS/Android apps.")
scan_result["languages"] = ["typescript", "swift", "kotlin", "javascript", "shell", "css", "markdown"]
scan_result["frameworks"] = ["node", "lit", "swiftui", "vite", "vitest"]
scan_result["entryPoint"] = "src/index.ts"
scan_result["importMap"] = import_map
(INTER / "scan-result.json").write_text(json.dumps(scan_result))
print("wrote", INTER / "scan-result.json")