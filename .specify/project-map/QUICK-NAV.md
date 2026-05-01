# Quick Navigation

> Layer 1 routing table. Start here. This document answers: "I need to do X — which document should I open?"

## By Task Type

| I need to | Open first | Then (if needed) |
|-----------|-----------|-------------------|
| See overall architecture | `root/ARCHITECTURE.md` | |
| Change CLI internals | `modules/specify-cli-core/OVERVIEW.md` | `modules/specify-cli-core/ARCHITECTURE.md` |
| Change workflow templates or passive skills | `root/WORKFLOWS.md` | `modules/templates-generated-surfaces/WORKFLOWS.md` |
| Change an agent integration | `root/INTEGRATIONS.md` | `modules/specify-cli-core/ARCHITECTURE.md` |
| Change Codex team runtime or engine | `modules/agent-teams-engine/OVERVIEW.md` | `root/OPERATIONS.md` |
| Change hooks, packets, or orchestration | `root/ARCHITECTURE.md` | `modules/specify-cli-core/ARCHITECTURE.md` |
| Change packaging, CI, or devcontainer | `root/STRUCTURE.md` | `root/OPERATIONS.md` |
| Diagnose test failures | `root/TESTING.md` | module `TESTING.md` for affected area |
| Fix a bug (location known) | module `OVERVIEW.md` for the affected area | `root/TESTING.md` for test commands |
| Fix a bug (root cause unknown) | `root/WORKFLOWS.md` (debug workflow) | module `OVERVIEW.md` for affected area |
| Understand IPC / RPC patterns | `root/ARCHITECTURE.md` § IPC Channels | `root/CONVENTIONS.md` § IPC Patterns |
| Add a new service or module | `root/CONVENTIONS.md` | `root/STRUCTURE.md` § Placement Rules |

## By Module

| Module | Layer 2 Summary | Layer 3 Detail | Doc Status |
|--------|----------------|----------------|------------|
| specify-cli-core | `root/ARCHITECTURE.md` § specify-cli-core | `modules/specify-cli-core/OVERVIEW.md` | documented |
| templates-generated-surfaces | `root/ARCHITECTURE.md` § templates-generated-surfaces | `modules/templates-generated-surfaces/OVERVIEW.md` | documented |
| agent-teams-engine | `root/ARCHITECTURE.md` § agent-teams-engine | `modules/agent-teams-engine/OVERVIEW.md` | documented |

## By Index File

| Index | Purpose | When to read |
|-------|---------|-------------|
| `index/atlas-index.json` | Machine-readable atlas summary and next-read routes | Before broad brownfield work |
| `index/modules.json` | Module registry, owned roots, doc paths, doc status | To check if a module has Layer 3 docs |
| `index/relations.json` | Cross-module dependency graph | To assess change impact across modules |
| `index/status.json` | Freshness, commit binding, module coverage status | Before trusting map for heavy commands |

## How To Use This Document

1. Find your task type in the first table → open the "Open first" document
2. Read its Layer 2 summary section (first 10-15 lines) → decide if you need Layer 3
3. If Layer 3 is needed → follow the link in the summary to the module OVERVIEW.md
4. Only read source code when documentation is marked `gap` or is stale

**Staleness**: Check `index/status.json` for the commit binding. If the current HEAD differs from `last_refresh_commit`, Layer 3 docs may be stale. Layer 1 (this file) is almost never stale.
