#!/usr/bin/env python3
"""Adversarial verifier v2: check every port-analysis doc citation and symbol node.

Fixes over v1:
 - extension alternation ordered longest-first + trailing boundary (no more `package.js`)
 - resolves refs against BOTH roots: openclaw and the ROX clone (rox/ prefix aware)
 - basename fallback for shortened citations (records as 'shortened')

Usage: python3 .ua/tmp/verify-citations.py
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path("/Users/t/Projects/openclaw")
ROX = Path("/Users/t/Projects/rox-one")
UA = ROOT / ".ua" / "intermediate"

EXT = r"(?:json5|jsonc|json|mjs|mts|tsx|ts|jsx|js|swift|kts|kt|rs|md|ya?ml|sh|css|html|toml|plist|sql|mdc)"
REF_RE = re.compile(
    r"`?(?:rox/)?((?:src|apps|packages|ui|extensions|docs|skills|custodian-skills|deploy|scripts|config|test|qa|workers|tools|native|registry|\.agents)/[\w./@%+-]+?\." + EXT + r"(?![A-Za-z0-9])(?::\d+(?:-\d+)?)?)"
)
SYMBOL_TYPES = {"function", "class"}

# basename index for shortened-citation fallback
def build_basename_index(root: Path):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True).stdout
    except Exception:
        return {}
    idx = {}
    for p in out.splitlines():
        idx.setdefault(p.rsplit("/", 1)[-1], []).append(p)
    return idx

IDX = {"openclaw": build_basename_index(ROOT), "rox": build_basename_index(ROX)}

def resolve(ref: str, doc: Path):
    """Return ('ok'|'rox'|'shortened ok'|'BAD', note)."""
    path_part, _, line_part = ref.partition(":")
    candidates = []
    if path_part.startswith("rox/"):
        candidates.append((ROX, path_part[4:]))
    candidates.append((ROOT, path_part))
    candidates.append((ROX, path_part))
    for base, rel in candidates:
        f = base / rel
        if f.exists() and f.is_file():
            if line_part:
                try:
                    ln = int(line_part.split("-")[0])
                    n = len(f.read_text(errors="replace").splitlines())
                    if ln < 1 or ln > n:
                        return "BAD", f"{ref} (line {ln} > {n} lines)"
                except Exception:
                    pass
            return ("rox" if base is ROX else "ok"), None
    base_name = path_part.rsplit("/", 1)[-1]
    hits = [p for p in IDX["openclaw"].get(base_name, []) + IDX["rox"].get(base_name, [])]
    if hits:
        return "shortened ok", f"{ref} → {hits[0]}"
    return "BAD", ref

report = {"docs": {}, "symbols": {}, "totals": {}}
ok = rox_ok = short = bad = 0
for md in sorted((ROOT / "port-analysis" / "areas").glob("*.md")):
    text = md.read_text(errors="replace")
    uniq = sorted(set(m.group(1) for m in REF_RE.finditer(text)))
    s = {"ok": 0, "rox_ok": 0, "shortened": [], "bad": [], "total": len(uniq)}
    for r in uniq:
        status, note = resolve(r, md)
        if status == "ok": s["ok"] += 1
        elif status == "rox": s["rox_ok"] += 1
        elif status == "shortened ok": s["shortened"].append(note)
        else: s["bad"].append(note)
    ok += s["ok"]; rox_ok += s["rox_ok"]; short += len(s["shortened"]); bad += len(s["bad"])
    report["docs"][md.name] = s

sym_ok = sym_bad = 0
for frag in sorted(UA.glob("batch-*.json")):
    if "existing" in frag.name:
        continue
    try:
        data = json.loads(frag.read_text())
    except Exception as e:
        report["symbols"][frag.name] = {"error": str(e)}
        continue
    st = {"checked": 0, "ok": 0, "miss": []}
    for n in data.get("nodes", []):
        if n.get("type") not in SYMBOL_TYPES:
            continue
        fp, name = n.get("filePath"), (n.get("name") or "").split("(")[0].strip()
        if not fp or not name:
            continue
        rel = fp[4:] if fp.startswith("rox/") else fp
        base = ROX if fp.startswith("rox/") else ROOT
        path = base / rel
        if not path.exists():
            st["miss"].append(f"{n['id']} (missing file {fp})")
            continue
        st["checked"] += 1
        if re.search(r"\b" + re.escape(name.split(".")[-1]) + r"\b", path.read_text(errors="replace")):
            st["ok"] += 1; sym_ok += 1
        else:
            st["miss"].append(f"{n['id']} (symbol '{name}' not in {fp})")
    sym_bad += len(st["miss"])
    report["symbols"][frag.name] = st

report["totals"] = {"doc_ok": ok, "doc_rox_ok": rox_ok, "doc_shortened": short, "doc_bad": bad,
                    "symbols_ok": sym_ok, "symbols_bad": sym_bad}
(UA / "verification-report.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report["totals"], indent=1))
print("=== bad refs ===")
for doc, s in report["docs"].items():
    for b in s["bad"]:
        print(f"{doc}: {b}")
print("=== shortened ===")
for doc, s in report["docs"].items():
    for b in s["shortened"][:8]:
        print(f"{doc}: {b}")
print("=== symbol misses ===")
for f, s in report["symbols"].items():
    if isinstance(s, dict):
        for m in s.get("miss", [])[:15]:
            print(f"{f}: {m}")