#!/usr/bin/env node
// Strict validation of the final knowledge graph against the Understand-Anything core schema.
import { readFileSync } from 'node:fs';

const coreUrl = new URL('file:///Users/t/.agents/skills/understand/plugin/packages/core/dist/index.js');
const core = await import(coreUrl.href);
const candidates = ['KnowledgeGraphSchema', 'GraphNodeSchema', 'GraphEdgeSchema'];
console.log('core exports present:', candidates.filter(k => k in core).join(', '));

const graph = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const res = core.KnowledgeGraphSchema.safeParse(graph);
if (res.success) {
  console.log('ZOD OK — graph valid:', graph.nodes.length, 'nodes,', graph.edges.length, 'edges,', graph.layers.length, 'layers,', graph.tour.length, 'tour steps');
} else {
  console.log('ZOD FAIL —', res.error.issues.length, 'issues');
  for (const i of res.error.issues.slice(0, 25)) {
    console.log(` - ${i.path.join('.')}: ${i.message}`);
  }
  process.exitCode = 1;
}