# Compatibility / Export Navigation

> Compatibility/export Layer 1 routing table for handbook and atlas outputs.
> Ordinary brownfield workflows should start from the project cognition runtime,
> then use this document only when compatibility/export navigation is explicitly needed.
> Start here only when compatibility/export navigation is explicitly needed.
> This document answers: "I need to inspect exported atlas docs — which file should I open?"
> and "Which compatibility/export module most likely owns the touched area?"

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

## By Capability

- Investigate a known capability:
  Open first: `index/capabilities.json`
  Then: `modules/<module-id>/deep/workflows/<capability-id>.md`
- Extend an existing capability:
  Open first: `modules/<module-id>/deep/workflows/<capability-id>.md`
  Then: `modules/<module-id>/WORKFLOWS.md`
- Review change impact for an existing capability:
  Open first: `modules/<module-id>/deep/workflows/<capability-id>.md`
  Then: `index/relations.json`

## By Symptom

- Debug a reported symptom:
  Open first: `index/symptoms.json`
  Then: the recommended deep workflow page for the mapped capability
- Compatibility/export consumers are no longer reading project-map outputs:
  Read `PROJECT-HANDBOOK.md`, `root/WORKFLOWS.md`,
  `modules/templates-generated-surfaces/OVERVIEW.md`, and
  `src/specify_cli/integrations/base.py`
- Generated template behavior does not match runtime guidance:
  Read `root/WORKFLOWS.md`, `root/CONVENTIONS.md`,
  `modules/templates-generated-surfaces/OVERVIEW.md`, and
  `templates/command-partials/common/*.md`
- Compatibility/export freshness or dirty-state routing looks wrong:
  Read `root/OPERATIONS.md`, `root/WORKFLOWS.md`,
  `index/status.json`, `.specify/project-cognition/status.json`, and
  `tools/specify-runtime/`
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
- `tools/specify-runtime/`
  Why it matters: freshness, topic routing, validation, query, and blocking vs review behavior

## Verification Routes

- Compatibility/export template guidance:
  Run `pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q`
- Compatibility/export layered contract:
  Run `pytest tests/test_project_map_layered_contract.py tests/test_project_handbook_templates.py -q`
- Compatibility/export freshness helper behavior:
  Run `pytest tests/test_project_map_freshness_scripts.py -q` and
  `cd tools/specify-runtime && go test ./...`

## Propagation-Risk Routes

- Shared partial changed:
  Review every command that includes it plus template-guidance tests
- Handbook or compatibility root topic changed:
  Review `Topic Map`, `atlas-index.json`, and freshness/topic-routing tests
- Capability deep workflow changed:
  Review `index/capabilities.json`, `index/symptoms.json`, `modules/<module-id>/WORKFLOWS.md`, and adjacent capability routes in `index/relations.json`
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
- `index/capabilities.json`
  Purpose: capability registry, owning modules, and deep workflow routes
- `index/symptoms.json`
  Purpose: symptom registry, likely capability routes, and read-first pages
- `index/status.json`
  Purpose: freshness, commit binding, and topic-routing status

## How To Use This Document

1. Start with the project cognition runtime for ordinary brownfield work.
2. Use this document only when you need compatibility/export navigation or need to inspect exported atlas outputs.
3. Open the listed root topic or module overview first.
4. Expand into relations and neighboring surfaces only when the entry route says
   the problem crosses shared surfaces or propagation risks.
5. Only read source code when exported compatibility coverage is missing, stale, or too broad
   for the touched area.

**Staleness**: Check `index/status.json`. If the current HEAD differs from the
last refresh commit, review topic-routing guidance before trusting these
compatibility/export outputs. Layer 1 remains the most stable exported surface,
but it still routes through freshness state rather than bypassing it.
