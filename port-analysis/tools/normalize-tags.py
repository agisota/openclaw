#!/usr/bin/env python3
"""One-shot normalizer: coerce fragment node `tags` from comma strings to arrays.
Rewrites only the `tags` field; everything else preserved byte-for-byte at the JSON level.
"""
import json, re, glob

def norm(v):
    if isinstance(v, list):
        out = [str(t).strip() for t in v if str(t).strip()]
    elif isinstance(v, str):
        out = [t.strip() for t in re.split(r"[,;]", v) if t.strip()]
    else:
        out = []
    return out or ["untagged"]

total = 0
for f in sorted(glob.glob("/Users/t/Projects/openclaw/.ua/intermediate/batch-*.json")):
    if "existing" in f:
        continue
    d = json.load(open(f))
    changed = 0
    for n in d.get("nodes", []):
        if not isinstance(n.get("tags"), list):
            n["tags"] = norm(n.get("tags"))
            changed += 1
    if changed:
        json.dump(d, open(f, "w"), indent=1)
        print(f"{f.split('/')[-1]}: normalized {changed} nodes")
        total += changed
print("total:", total)