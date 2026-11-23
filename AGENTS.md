# AGENTS.md

## Read the map first

This repo has a pre-built knowledge graph. Do not re-read the whole codebase at
the start of a session.

- `graphify-out/GRAPH_REPORT.md` — plain-language architecture summary. Read this first.
- `graphify-out/graph.json` — the full graph (~4,100 nodes, ~11,600 edges, ~150 clusters).
- `graphify-out/graph.html` — visual map. Open in a browser.

Answer questions from the graph before opening source files:

```
graphify query "how does memory evolution work"    # small focused subgraph
graphify explain "Harness"                         # one node and its neighbors
graphify path "Harness" "DeepSeekProvider"         # how two things connect
```

Open source files only when you need to edit them, or when the graph is not
enough. Quote `source_file` / `source_location` from the graph when you cite code.

## After code changes

```
graphify update .
```

Re-reads only changed code files. No LLM tokens. Run it after edits.

## If the graph is stale or missing

```
graphify update .  # code-only refresh, free
/graphify .        # full rebuild, costs tokens on docs
```

## Scope

`src/back/opik/` is a vendored third-party clone (~12.5k files). It is excluded
in `.graphifyignore`. Do not index it, and do not confuse it with Irina's own
code under `src/back/harness/`.
