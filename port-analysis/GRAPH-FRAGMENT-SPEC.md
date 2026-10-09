# Graph fragment spec — Understand-Anything KnowledgeGraph schema

Your fragment file: `.ua/intermediate/batch-<N>.json` (N is given in your brief).
Shape: `{"nodes": [ ... ], "edges": [ ... ]}` — valid JSON, UTF-8, no comments, no trailing commas.

## Node
Required fields: `id`, `type`, `name`, `summary`, `tags` (non-empty array), `complexity` (`"simple"` | `"moderate"` | `"complex"`).
Optional: `filePath` (repo-relative path), `lineRange` (`[start, end]`, 1-based, only when grounded in a real read/grep).
Extra keys are allowed and preserved.

Allowed `type` values: `file`, `function`, `class`, `module`, `concept`, `config`, `document`, `service`, `table`, `endpoint`, `pipeline`, `schema`, `resource`, `domain`, `flow`, `step`.

ID conventions (follow exactly):
- `file:<repo-relative-path>`
- `function:<repo-relative-path>:<name>`
- `class:<repo-relative-path>:<name>`
- `module:<name>` (logical module/package)
- `concept:<kebab-case-name>`
- `config:<path>`, `document:<path>`, `service:<name>`
- `endpoint:<path>:<method-or-route-name>`
- `table:<path>:<table-name>`, `schema:<path>`

Node-writing rules:
- `summary`: 1–2 sentences: WHAT it does and HOW (the mechanism), not a doc paraphrase. Name concrete types, functions, protocols, files.
- Every `function`/`class` node that represents a real symbol must have `filePath` and be findable in that file (grep-verified).
- Prefer real symbols you actually read over plausible-sounding names.
- `tags`: short kebab-case keywords (e.g. `sessions`, `ownership`, `presence`).

## Edge
Required fields: `source`, `target`, `type`, `direction` (`"forward"` | `"backward"` | `"bidirectional"`), `weight` (0–1 number).
Optional: `description`.

Allowed `type` values (38): `imports`, `exports`, `contains`, `inherits`, `implements`, `calls`, `subscribes`, `publishes`, `middleware`, `reads_from`, `writes_to`, `transforms`, `validates`, `depends_on`, `tested_by`, `configures`, `related`, `similar_to`, `deploys`, `serves`, `provisions`, `triggers`, `migrates`, `documents`, `routes`, `defines_schema`, `contains_flow`, `flow_step`, `cross_domain`, `cites`, `contradicts`, `builds_on`, `exemplifies`, `categorized_under`, `authored_by`, `instance_of`, `variant_of`, `uses_token`.

Weight conventions: `contains` 1.0; `inherits`/`implements` 0.9; `calls`/`exports`/`defines_schema` 0.8; `imports`/`deploys`/`migrates` 0.7; `depends_on`/`configures`/`triggers` 0.6; `tested_by`/`documents`/`provisions`/`serves`/`routes` 0.5; everything else 0.5.

Edge rules:
- Every endpoint must be a node id defined in YOUR fragment (define a tiny node for it rather than referencing ids you cannot guarantee). Dangling edges are dropped by the merge step.
- Every `file` node needs at least one edge.
- Model real topology: containment (`contains`), calls, publishes/subscribes (events/sockets), reads_from/writes_to (state, DB, files), routes/serves (HTTP/WS), configures, documents.

## Quality gates (checked by the orchestrator after the wave)
- Fragment parses as JSON; node ids unique; required node fields present; edge types/weights legal.
- 60–140 nodes and 100–250 edges per area (unless your brief says otherwise).
- Node `filePath` must exist in the repo; symbol nodes must grep-resolve.