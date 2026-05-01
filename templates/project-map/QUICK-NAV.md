# Quick Navigation

> Layer 1 routing table and dictionary-style atlas entry surface. Start here.
> This document answers: "I need to do X — which document should I open?" and
> "Which module most likely owns the touched area?"

## By Task Type

- See overall architecture:
  Open first: `root/ARCHITECTURE.md`
- Change CLI internals:
  Open first: `modules/specify-cli-core/OVERVIEW.md`
  Then: `modules/specify-cli-core/ARCHITECTURE.md`
- Change workflow templates or passive skills:
  Open first: `root/WORKFLOWS.md`
  Then: `modules/templates-generated-surfaces/WORKFLOWS.md`
- Change an agent integration:
  Open first: `root/INTEGRATIONS.md`
  Then: `modules/specify-cli-core/ARCHITECTURE.md`
- Change Codex team runtime or engine:
  Open first: `modules/agent-teams-engine/OVERVIEW.md`
  Then: `root/OPERATIONS.md`
- Change hooks, packets, or orchestration:
  Open first: `root/ARCHITECTURE.md`
  Then: `modules/specify-cli-core/ARCHITECTURE.md`
- Change packaging, CI, or devcontainer:
  Open first: `root/STRUCTURE.md`
  Then: `root/OPERATIONS.md`
- Diagnose test failures:
  Open first: `root/TESTING.md`
  Then: module `TESTING.md` for the affected area
- Fix a bug (location known):
  Open first: module `OVERVIEW.md` for the affected area
  Then: `root/TESTING.md`
- Fix a bug (root cause unknown):
  Open first: `root/WORKFLOWS.md`
  Then: module `OVERVIEW.md` for the affected area

## By Symptom

- Workflows are no longer reading project-map:
  Read `PROJECT-HANDBOOK.md`, `root/WORKFLOWS.md`,
  `modules/templates-generated-surfaces/OVERVIEW.md`, and
  `src/specify_cli/integrations/base.py`
- Generated template behavior does not match runtime guidance:
  Read `root/WORKFLOWS.md`, `root/CONVENTIONS.md`,
  `modules/templates-generated-surfaces/OVERVIEW.md`, and
  `templates/command-partials/common/*.md`
- Freshness or dirty-state routing looks wrong:
  Read `root/OPERATIONS.md`, `root/WORKFLOWS.md`,
  `index/status.json`, and `src/specify_cli/project_map_status.py`
- Subagent dispatch guidance is inconsistent across workflows:
  Read `root/WORKFLOWS.md`,
  `modules/templates-generated-surfaces/WORKFLOWS.md`, and
  `templates/commands/*.md`

## Shared-Surface Hotspots

- `templates/command-partials/common/context-loading-gradient.md`
  Why it matters: shared atlas-gate wording for multiple `sp-*` commands
- `templates/commands/**`
  Why it matters: workflow contracts and user-visible execution rules
- `src/specify_cli/integrations/base.py`
  Why it matters: injected runtime guidance and logical atlas-contract wording
- `src/specify_cli/project_map_status.py`
  Why it matters: freshness, topic routing, and blocking vs review behavior

## Verification Routes

- Atlas template guidance:
  Run `pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q`
- Project-map layered contract:
  Run `pytest tests/test_project_map_layered_contract.py tests/test_project_handbook_templates.py -q`
- Freshness helper behavior:
  Run `pytest tests/test_project_map_status.py -q`

## Propagation-Risk Routes

- Shared partial changed:
  Review every command that includes it plus template-guidance tests
- Handbook or root topic changed:
  Review `Topic Map`, `atlas-index.json`, and freshness/topic-routing tests
- Integration guidance changed:
  Review `tests/test_extension_skills.py` and alignment/template guidance tests

## Module Lookup

- `specify-cli-core`
  Layer 2 summary: `root/ARCHITECTURE.md`
  Layer 3 detail: `modules/specify-cli-core/OVERVIEW.md`
- `templates-generated-surfaces`
  Layer 2 summary: `root/ARCHITECTURE.md`
  Layer 3 detail: `modules/templates-generated-surfaces/OVERVIEW.md`
- `agent-teams-engine`
  Layer 2 summary: `root/ARCHITECTURE.md`
  Layer 3 detail: `modules/agent-teams-engine/OVERVIEW.md`

## Root Topic Lookup

- Architecture boundaries:
  `root/ARCHITECTURE.md`
- Workflow and lifecycle behavior:
  `root/WORKFLOWS.md`
- Testing and verification entrypoints:
  `root/TESTING.md`
- Runtime recovery and freshness operations:
  `root/OPERATIONS.md`

## By Index File

- `index/atlas-index.json`
  Purpose: machine-readable atlas summary, entrypoints, and next-read routes
- `index/modules.json`
  Purpose: module registry, owned roots, doc paths, and doc status
- `index/relations.json`
  Purpose: cross-module dependency graph and propagation expansion routes
- `index/status.json`
  Purpose: freshness, commit binding, and topic-routing status

## How To Use This Document

1. Identify the current task type or symptom.
2. Open the listed root topic or module overview first.
3. Expand into relations and neighboring surfaces only when the entry route says
   the problem crosses shared surfaces or propagation risks.
4. Only read source code when atlas coverage is missing, stale, or too broad
   for the touched area.

**Staleness**: Check `index/status.json`. If the current HEAD differs from the
last refresh commit, review topic-routing guidance before trusting Layer 2 or
Layer 3. Layer 1 is the most stable surface, but it still routes through
freshness state rather than bypassing it.
