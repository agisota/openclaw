#!/bin/bash
# Final graph pipeline for /Users/t/Projects/openclaw (run with bash, from repo root).
set -euo pipefail
cd /Users/t/Projects/openclaw
PY=/Users/t/.local/bin/python3.12
SKILL=/Users/t/.agents/skills/understand/plugin/skills/understand

echo "== 1. scan-result.json (inventory + importMap for edge recovery) =="
$PY .ua/tmp/build-scan-result.py

echo "== 2. merge fragments (with importMap recovery) =="
$PY "$SKILL/merge-batch-graphs.py" /Users/t/Projects/openclaw 2>&1 | tail -8

echo "== 3. layers + tour + project meta =="
$PY .ua/tmp/build-graph.py

echo "== 4. deterministic validation =="
node .ua/tmp/ua-inline-validate.cjs .ua/knowledge-graph.json .ua/intermediate/review.json
$PY - <<'EOF'
import json
r = json.load(open('.ua/intermediate/review.json'))
print('issues:', len(r['issues']), 'warnings:', len(r['warnings']))
for i in r['issues'][:12]: print('ISSUE:', i)
print('stats:', json.dumps(r['stats'])[:500])
EOF

echo "== 5. copy deliverables into port-analysis/ =="
mkdir -p port-analysis/graph-fragments
cp .ua/knowledge-graph.json port-analysis/knowledge-graph.json
for f in .ua/intermediate/batch-*.json; do
  case "$f" in *existing*) continue;; esac
  cp "$f" port-analysis/graph-fragments/
done
cp .ua/intermediate/stats.json port-analysis/graph-fragments/stats.json 2>/dev/null || true
cp .ua/intermediate/review.json port-analysis/graph-fragments/review.json 2>/dev/null || true
echo "done: port-analysis/knowledge-graph.json + graph-fragments/"