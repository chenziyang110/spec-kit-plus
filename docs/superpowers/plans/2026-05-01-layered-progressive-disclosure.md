# Layered Progressive Disclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "load everything" context model in sp-* workflows with a four-layer onion model (routing → summary → detail → source) that loads proportionally to command complexity.

**Architecture:** Four-layer information model with per-command loading gradient. Higher layers are indexes into lower layers. Each knowledge point has exactly one authoritative document; others reference by link. Freshness is layered (not binary), dispatch mode tracks complexity (not uniform), and gaps are explicit (not silent).

**Design Spec:** `docs/superpowers/specs/2026-05-01-layered-progressive-disclosure-design.md`

**Tech Stack:** Markdown templates, JSON index files, `{{spec-kit-include: ...}}` template partials, Python CLI helpers.

---

## File Structure

```
NEW:
  .specify/project-map/QUICK-NAV.md                          — Layer 1 task→document routing matrix
  templates/command-partials/common/context-loading-gradient.md  — Tier-aware loading rules (replaces flat navigation-check)
  templates/command-partials/common/dispatch-mode-gradient.md   — Dispatch mode per command tier
  templates/command-partials/common/pre-analysis-protocol.md    — Shared "understand before acting" framework
  templates/command-partials/common/gate-self-check.md          — Phase-boundary confirmation output

MODIFIED:
  .specify/project-map/index/status.json                     — Add commit_hash, doc_status fields
  .specify/project-map/index/modules.json                    — Add doc_status: documented|indexed-only|gap
  .specify/project-map/root/ARCHITECTURE.md                  — Slim capability cards to Layer 2 summary
  .specify/project-map/map-state.md                          — Propagate scan gaps to open gaps
  templates/command-partials/common/navigation-check.md      — Replace with layered loading logic
  templates/command-partials/common/learning-layer.md        — Make tier-aware (skip for trivial)
  templates/command-partials/common/subagent-execution.md    — Add dispatch mode gradient
  templates/commands/fast.md                                 — Layer 1 only, leader-direct, skip learning
  templates/commands/quick.md                                — Layer 1+2, subagent-preferred, light learning
  templates/commands/debug.md                                — Add fast-path, shared pre-analysis
  templates/commands/specify.md                              — Full layers, shared pre-analysis
  templates/commands/implement.md                            — Subagent-mandatory, gate self-check
  templates/commands/plan.md                                 — Full layers
  templates/commands/tasks.md                                — Per-plan loading
  PROJECT-HANDBOOK.md                                        — Add task-type routing matrix + gap markers
```

---

## Phase 1: Foundation — Layer 1 Routing Table & Index Changes

### Task 1: Create QUICK-NAV.md (Layer 1 routing table)

**Files:**
- Create: `.specify/project-map/QUICK-NAV.md`

- [ ] **Step 1: Write QUICK-NAV.md with task-type routing matrix and module→document mapping**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .specify/project-map/QUICK-NAV.md
git commit -m "feat: add QUICK-NAV.md as Layer 1 routing table"
```

### Task 2: Add doc_status and commit binding to index files

**Files:**
- Modify: `.specify/project-map/index/modules.json`
- Modify: `.specify/project-map/index/status.json`

- [ ] **Step 1: Add doc_status field to each module in modules.json**

Edit `.specify/project-map/index/modules.json` — add `"doc_status": "documented"` to each module entry that has all 5 docs (ARCHITECTURE.md, OVERVIEW.md, STRUCTURE.md, TESTING.md, WORKFLOWS.md). All three current modules are `documented`.

```json
{
  "id": "specify-cli-core",
  "doc_status": "documented",
  ...
}
```

- [ ] **Step 2: Add commit_hash and doc_status_summary to status.json**

Edit `.specify/project-map/index/status.json` — add under `global`:

```json
"commit_hash": "WORKTREE-subagents-first-refactor",
"doc_status_summary": {
  "documented": 3,
  "indexed_only": 0,
  "gap": 0
}
```

- [ ] **Step 3: Commit**

```bash
git add .specify/project-map/index/modules.json .specify/project-map/index/status.json
git commit -m "feat: add doc_status fields and commit binding to index files"
```

### Task 3: Add task-type routing matrix to PROJECT-HANDBOOK.md

**Files:**
- Modify: `PROJECT-HANDBOOK.md`

- [ ] **Step 1: Insert "Quick Navigation By Task" section before "Topic Map"**

Replace the "Where To Read Next" section with an expanded version that includes the routing matrix from QUICK-NAV.md and a pointer to it. Add a note in the "How To Read This Project" section directing readers to `QUICK-NAV.md` as the first stop.

In `PROJECT-HANDBOOK.md`, after the "How To Read This Project" section, insert:

```markdown
## Quick Navigation (Layer 1)

For task-based routing, open `.specify/project-map/QUICK-NAV.md` first — it is a ≤50-line decision matrix that answers "which document should I open?" for 12 common task types. The handbook and project-map together form a four-layer atlas:

- **Layer 1 (routing)**: `QUICK-NAV.md` — task→document mapping
- **Layer 2 (summary)**: `root/ARCHITECTURE.md` capability cards — module-at-a-glance
- **Layer 3 (detail)**: `modules/<name>/OVERVIEW.md` — full technical detail
- **Layer 4 (source)**: Live code — when docs are missing or stale
```

- [ ] **Step 2: Commit**

```bash
git add PROJECT-HANDBOOK.md
git commit -m "feat: add Layer 1 routing table pointer to handbook"
```

---

## Phase 2: Slim Capability Cards to Layer 2 Summary

### Task 4: Slim down ARCHITECTURE.md capability cards

**Files:**
- Modify: `.specify/project-map/root/ARCHITECTURE.md`

- [ ] **Step 1: Replace full capability cards with Layer 2 summary cards**

Each card reduced to ≤10 lines: entry interface, truth location, extension point, key constraint, test command, link to Layer 3 doc. Move enumerations (IPC channels, shell integration sequences, message type lists) to their module OVERVIEW.md files if not already there.

For the specify-cli-core card, replace the detailed section with:

```markdown
### specify-cli-core
- **Entry**: `src/specify_cli/__init__.py` — Typer app, command registration
- **Truth**: `src/specify_cli/integrations/base.py` — integration registry
- **Key deps**: templates, scripts, tests, pyproject.toml
- **Extension point**: `src/specify_cli/integrations/` — add adapter
- **Do not touch**: upstream agent CLI behavior, external MCP servers
- **Test**: `uv run --extra test pytest -q -n auto`
- **Full docs**: → `modules/specify-cli-core/OVERVIEW.md`

### templates-generated-surfaces
- **Entry**: `templates/commands/` — workflow command templates
- **Truth**: `templates/command-partials/` — shared partials
- **Key deps**: scripts, passive-skills, worker-prompts
- **Extension point**: add new command template + partials
- **Do not touch**: generated output in downstream projects directly
- **Test**: `pytest tests/integrations -q`
- **Full docs**: → `modules/templates-generated-surfaces/OVERVIEW.md`

### agent-teams-engine
- **Entry**: `extensions/agent-teams/engine/src/` — Node/TypeScript
- **Truth**: `extensions/agent-teams/engine/package.json`
- **Key deps**: Rust crates, tmux/psmux, native hooks
- **Extension point**: `extensions/agent-teams/engine/skills/worker/SKILL.md`
- **Do not touch**: Rust crates without running targeted scan packet
- **Test**: `npm --prefix extensions/agent-teams/engine run build`
- **Full docs**: → `modules/agent-teams-engine/OVERVIEW.md`
```

- [ ] **Step 2: Commit**

```bash
git add .specify/project-map/root/ARCHITECTURE.md
git commit -m "refactor: slim capability cards to Layer 2 summary format"
```

---

## Phase 3: Tier-Aware Common Partials

### Task 5: Create context-loading-gradient.md (replaces flat navigation-check)

**Files:**
- Create: `templates/command-partials/common/context-loading-gradient.md`

- [ ] **Step 1: Write the tier-aware loading rules**

```markdown
## Context Loading

This command is tier: `{TIER}`. Load only the layers this tier requires.

### Layer Access by Tier

| Tier | Commands | Layers | Freshness Check |
|------|----------|--------|-----------------|
| trivial | sp-fast | Layer 1 only + target source | Skip |
| light | sp-quick, sp-debug | Layer 1 + Layer 2 summary + target Layer 3 sections | Warn if stale, do not block |
| heavy | sp-specify, sp-plan, sp-tasks, sp-implement | Layer 1 + Layer 2 + Layer 3 full | Enforce; stale triggers scoped rescan |

### Loading Order (all tiers)

1. Read `.specify/project-map/QUICK-NAV.md` first — determine which document to open
2. Read the routed document's Layer 2 summary section
3. [light/heavy only] Read target module's Layer 3 OVERVIEW.md (target sections only for light)
4. [heavy only] Read `root/CONVENTIONS.md` relevant sections + `index/relations.json` for cross-module impact
5. [all tiers] Read source files on-demand when docs are insufficient or marked `gap`

### Freshness (layered, not binary)

- Layer 1 (QUICK-NAV.md): almost never stale — skip check
- Layer 2 (summary cards in ARCHITECTURE.md): changes slowly — warn only
- Layer 3 (module OVERVIEW.md): changes faster — enforce for heavy commands

Check: compare `index/status.json` → `global.commit_hash` with current HEAD.
- Same commit → fresh
- Different, but only Layer 3 files changed → Layer 1+2 still valid
- Different, structural files changed → all layers may be stale

When stale: heavy commands run scoped rescan of affected module only (not global rebuild).
Light commands proceed with a warning.
Trivial commands skip freshness entirely.
```

- [ ] **Step 2: Commit**

```bash
git add templates/command-partials/common/context-loading-gradient.md
git commit -m "feat: add tier-aware context loading gradient partial"
```

### Task 6: Create dispatch-mode-gradient.md

**Files:**
- Create: `templates/command-partials/common/dispatch-mode-gradient.md`

- [ ] **Step 1: Write dispatch gradient rules**

```markdown
## Dispatch Mode

Dispatch mode follows command tier, not a uniform rule.

| Tier | Dispatch Mode | Rule |
|------|---------------|------|
| trivial | leader-direct | No subagent dispatch. Leader performs and verifies the change directly. |
| light | subagent-preferred | Dispatch to one subagent; leader-inline fallback allowed if dispatch unavailable. |
| heavy | subagent-mandatory | Must dispatch. If dispatch unavailable, record reason and escalate. |

### Fallback (light tier only)

When subagent dispatch is unavailable for a light-tier command:
1. Record the reason in workflow state
2. Switch to `execution_surface: leader-inline`
3. Proceed with the same scope and verification gates

This is a designed fallback path, not an exception.
```

- [ ] **Step 2: Commit**

```bash
git add templates/command-partials/common/dispatch-mode-gradient.md
git commit -m "feat: add dispatch mode gradient partial"
```

### Task 7: Update learning-layer.md to be tier-aware

**Files:**
- Modify: `templates/command-partials/common/learning-layer.md`

- [ ] **Step 1: Add tier-based learning rules**

Prepend to learning-layer.md:

```markdown
## Passive Project Learning Layer

Learning capture is proportional to command complexity:

| Tier | Learning Behavior |
|------|-------------------|
| trivial | Skip all learning hooks. No capture. |
| light | Auto-capture on resolution only. No review, no signal. |
| heavy | Full learning: start → signal on friction → review → capture-auto |

### Tier: trivial
- Do not run `specify learning start`.
- Do not read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, or `.specify/memory/project-learnings.md`.
- Do not review `.planning/learnings/candidates.md`.
- Do not invoke any learning hooks.

### Tier: light
```

Then add the existing content under the light and heavy tier headers, with appropriate scoping.

- [ ] **Step 2: Commit**

```bash
git add templates/command-partials/common/learning-layer.md
git commit -m "feat: make learning layer tier-aware (skip for trivial)"
```

### Task 8: Create pre-analysis-protocol.md (shared between specify and debug)

**Files:**
- Create: `templates/command-partials/common/pre-analysis-protocol.md`

- [ ] **Step 1: Write shared pre-analysis output format**

```markdown
## Pre-Analysis Protocol

Shared "understand before acting" framework. Used by sp-specify and sp-debug.
Each command defines only its specialized phases; this format is the common output.

### Required Output Fields

- **Scope boundary**: What is in scope? What is explicitly out of scope?
- **Key constraints**: What must not change? What invariants must hold?
- **Affected surface area**: Which modules, files, APIs, or contracts are touched?
- **Known unknowns**: What is unclear? What needs verification before proceeding?
- **Recommended next step**: Based on the analysis, what is the safest next action?

### Inter-Command Recognition

If a pre-analysis output already exists from a prior command (e.g., sp-specify completed before sp-debug), read that output. Do not re-analyze the same surface. Add only the specialized analysis your command requires.

### Fast-Path (debug only)

When all three conditions are met, skip observer framing and proceed directly to reproduction gate:
1. Exact error location is known (file + line or function)
2. Clear reproduction steps are provided
3. Impact surface is bounded (single module, no cross-module coupling)

Record the fast-path decision with: "Fast-path: error location known, repro steps clear, impact bounded to [module]."
```

- [ ] **Step 2: Commit**

```bash
git add templates/command-partials/common/pre-analysis-protocol.md
git commit -m "feat: add shared pre-analysis protocol partial"
```

### Task 9: Create gate-self-check.md

**Files:**
- Create: `templates/command-partials/common/gate-self-check.md`

- [ ] **Step 1: Write gate self-check mechanism**

```markdown
## Gate Self-Check

At each phase boundary, output an explicit confirmation. This replaces pure declaration with verifiable checkpoints.

### Format

```
[GATE CHECK] Phase: <phase_name>
- Forbidden actions in this phase: <list>
- I confirm I have NOT performed any forbidden action since the last gate.
- Files modified in this phase: <list or "none">
```

### When to emit

- On phase transition (e.g., analysis → specification, specification → handoff)
- Before final reporting
- After any recovery from a false start or route change

### Enforcement

This is a Level 2 enforcement (gate self-check). It does not prevent tool use, but it creates an auditable record. If a gate check cannot be honestly emitted, the phase is not complete.
```

- [ ] **Step 2: Commit**

```bash
git add templates/command-partials/common/gate-self-check.md
git commit -m "feat: add gate self-check mechanism partial"
```

---

## Phase 4: Rewire Command Templates

### Task 10: Rewire sp-fast for trivial tier (Layer 1 only, leader-direct, no learning)

**Files:**
- Modify: `templates/commands/fast.md`

- [ ] **Step 1: Replace Mandatory Subagent Execution section**

Replace the current "Mandatory Subagent Execution" section with:

```markdown
{{spec-kit-include: ../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: trivial. Dispatch mode: leader-direct.**

The leader performs the change directly. No subagent dispatch. No task contract needed.
```

- [ ] **Step 2: Replace Passive Project Learning Layer section**

Replace with:

```markdown
{{spec-kit-include: ../command-partials/common/learning-layer.md}}

**This command tier: trivial.** Skip all learning hooks. Do not read constitution, project-rules, or project-learnings. Do not run learning start, signal, review, or capture.
```

- [ ] **Step 3: Replace freshness/navigation check**

Remove the inline freshness logic. Replace with:

```markdown
{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**This command tier: trivial.** Load only:
1. `.specify/project-map/QUICK-NAV.md` — confirm target document route
2. Target source file(s) — read the files to change
Skip freshness check entirely. Do not read root docs, module docs, or index files.
```

- [ ] **Step 4: Update Scope Gate to use objective criteria**

Replace subjective criteria with:

```markdown
## Scope Gate

Use `sp-fast` only when ALL of:
- ≤3 files touched
- No shared registration surface (router table, export barrel, template registry)
- No protocol/contract boundary crossed
- No dependency changes
- Task is clear in one sentence
- Root cause known (if bug fix)

If any check fails → upgrade to `/sp-quick`.
If scope >10 files or crosses module boundary → upgrade to `/sp-specify`.
```

- [ ] **Step 5: Commit**

```bash
git add templates/commands/fast.md
git commit -m "feat: rewire sp-fast for trivial tier (Layer 1 only, leader-direct)"
```

### Task 11: Rewire sp-quick for light tier (Layer 1+2, subagent-preferred)

**Files:**
- Modify: `templates/commands/quick.md`

- [ ] **Step 1: Replace Mandatory Subagent Execution section**

Replace with:

```markdown
{{spec-kit-include: ../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: light. Dispatch mode: subagent-preferred.**

Dispatch to one subagent with a task contract. If subagent dispatch is unavailable, record reason and fall back to leader-inline.
```

- [ ] **Step 2: Replace Required Context Inputs with layered loading**

Replace the "Required Context Inputs" section with layered loading referencing the context-loading-gradient partial. Keep STATUS.md management, but simplify freshness to warn-only.

```markdown
{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**This command tier: light.** Load:
1. `.specify/project-map/QUICK-NAV.md` — route to target module
2. `root/ARCHITECTURE.md` — read target module's Layer 2 summary card only
3. Target module `OVERVIEW.md` — read only sections relevant to the task
4. `root/CONVENTIONS.md` — read only the relevant pattern section (DI, IPC, or Error)
5. `index/relations.json` — check cross-module impact

**Freshness**: Check `index/status.json` commit_hash vs HEAD. If stale, warn but proceed. Do not trigger rescan.
```

- [ ] **Step 3: Simplify learning to auto-capture only**

Replace learning hooks with light-tier behavior (auto-capture on resolution, no review).

- [ ] **Step 4: Commit**

```bash
git add templates/commands/quick.md
git commit -m "feat: rewire sp-quick for light tier (Layer 1+2, subagent-preferred)"
```

### Task 12: Rewire sp-debug for light tier with fast-path

**Files:**
- Modify: `templates/commands/debug.md`

- [ ] **Step 1: Add fast-path gate before Observer Framing**

Insert after the command header, before Stage 1:

```markdown
{{spec-kit-include: ../command-partials/common/pre-analysis-protocol.md}}

## Fast-Path Gate (before Observer Framing)

Check these three conditions. If ALL are true, skip directly to Stage 3 (Reproduction Gate):

1. **Exact error location known**: File path + line number or function name
2. **Clear reproduction steps**: User provided or trivially inferable
3. **Impact surface bounded**: Single module, no cross-module IPC or shared state

If fast-path: record "Fast-path: error at [location], repro [steps], impact bounded to [module]." Then jump to Stage 3.
If not: proceed to Stage 1 (Observer Framing).
```

- [ ] **Step 2: Add dispatch mode and context loading sections**

Add context-loading-gradient.md include with light tier loading rules.

- [ ] **Step 3: Commit**

```bash
git add templates/commands/debug.md
git commit -m "feat: add fast-path gate and light-tier loading to sp-debug"
```

### Task 13: Rewire sp-specify for heavy tier with shared pre-analysis

**Files:**
- Modify: `templates/commands/specify.md`

- [ ] **Step 1: Add pre-analysis protocol reference**

Replace the inline clarification analysis with a reference to the shared pre-analysis protocol. The analysis output format (scope boundary, key constraints, affected surface, known unknowns, recommended next step) becomes the spec's analysis section.

In the outline section, add after parsing:

```markdown
{{spec-kit-include: ../command-partials/common/pre-analysis-protocol.md}}

Generate the pre-analysis output as the first section of `context.md`.
```

- [ ] **Step 2: Add context loading for heavy tier**

Replace inline navigation/freshness with:

```markdown
{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**This command tier: heavy.** Load:
1. `.specify/project-map/QUICK-NAV.md` — route to all affected modules
2. `root/ARCHITECTURE.md` — all Layer 2 summary cards
3. All affected module `OVERVIEW.md` files — full content
4. `root/CONVENTIONS.md` — full
5. `index/relations.json` — full dependency graph
6. `index/status.json` — freshness gate (enforce; stale → scoped rescan)

**Freshness enforcement**: Compare `status.json` commit_hash with HEAD. If stale on target module Layer 3, run scoped rescan of affected module only (not global rebuild).
```

- [ ] **Step 3: Add gate self-check before handoff**

Add gate self-check at phase boundaries.

- [ ] **Step 4: Commit**

```bash
git add templates/commands/specify.md
git commit -m "feat: add shared pre-analysis and heavy-tier loading to sp-specify"
```

### Task 14: Rewire sp-implement with gate self-check

**Files:**
- Modify: `templates/commands/implement.md`

- [ ] **Step 1: Add gate self-check after each task completion**

Insert after the task execution loop:

```markdown
{{spec-kit-include: ../command-partials/common/gate-self-check.md}}

After each task completion, emit a gate self-check. After all tasks, emit a final gate self-check confirming no forbidden actions were taken.
```

- [ ] **Step 2: Add heavy-tier loading reference**

```markdown
{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**This command tier: heavy.** Load task-scoped module docs. Freshness enforced on target Layer 3.
```

- [ ] **Step 3: Add blocker classification**

Add to the blocker handling section:

```markdown
### Blocker Classification

| Type | Examples | Route |
|------|----------|-------|
| environment | Missing toolchain, wrong Node version, pip/uv failure | Fix inline or ask user |
| test-failure | Test fails after implementation change | Analyze locally first |
| runtime-bug | Crash, unexpected behavior in implemented code | Route to `/sp-debug` |
| external | Upstream API change, network dependency | Record and escalate to user |
| scope-creep | Task expands beyond original contract | Upgrade to `/sp-plan` or `/sp-specify` |
```

- [ ] **Step 4: Commit**

```bash
git add templates/commands/implement.md
git commit -m "feat: add gate self-check and blocker classification to sp-implement"
```

### Task 15: Rewire sp-plan and sp-tasks for heavy tier

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`

- [ ] **Step 1: Add heavy-tier context loading to sp-plan**

Add `{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}` with heavy tier rules.

- [ ] **Step 2: Add per-plan loading to sp-tasks**

Tasks command loads Layer 1 + Layer 2 summary; reads only the plan artifacts for task breakdown. Does not need full Layer 3 module docs (those are for sp-implement).

- [ ] **Step 3: Commit**

```bash
git add templates/commands/plan.md templates/commands/tasks.md
git commit -m "feat: add tier-aware loading to sp-plan and sp-tasks"
```

---

## Phase 5: Gap Transparency & Reverse Coverage

### Task 16: Propagate scan gaps and validate coverage

**Files:**
- Modify: `.specify/project-map/map-state.md`

- [ ] **Step 1: Fill Open Gaps from scan packets**

If scan packets recorded known gaps (e.g., "Rust CLI build details — Low", "ESRP signing details — Low"), propagate them to the `## Open Gaps` section of `map-state.md` rather than leaving it as `- gap: []`.

```markdown
## Open Gaps

| Gap | Severity | Source Packet | Status |
|-----|----------|---------------|--------|
| ... | ... | ... | acknowledged |
```

- [ ] **Step 2: Add important-row coverage validation section**

Add after the critical rows section:

```markdown
### Important Rows → Atlas Targets (reverse validation)

[Same table format as Critical Rows section, applied to all important rows]
```

- [ ] **Step 3: Commit**

```bash
git add .specify/project-map/map-state.md
git commit -m "feat: propagate scan gaps and validate important-row coverage"
```

---

## Phase 6: Integration Verification

### Task 17: Verify template include chain works end-to-end

**Files:**
- Modify: `templates/command-partials/common/navigation-check.md` (update to reference new partials)

- [ ] **Step 1: Update navigation-check.md**

Add a note at top that this file is superseded by `context-loading-gradient.md` for commands that have adopted the layered model. Keep for backward compatibility with commands not yet migrated.

```markdown
> **Note:** Commands that include `context-loading-gradient.md` use layered loading and should NOT also include this file. This file is retained for commands not yet migrated to the layered model.
```

- [ ] **Step 2: Run template rendering tests**

```bash
uv run --extra test pytest tests/test_project_map_layered_contract.py -v
uv run --extra test pytest tests/integrations -q
```

Expected: Tests should pass. If any test asserts on the old navigation/freshness wording, update the test.

- [ ] **Step 3: Commit**

```bash
git add templates/command-partials/common/navigation-check.md tests/
git commit -m "chore: add migration note to navigation-check, update tests"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All 10 design principles have corresponding tasks
- [ ] Placeholder sanity: No TBD, TODO, or "implement later" in any step
- [ ] Type consistency: Layer names (Layer 1/2/3/4) match across all files
- [ ] Template includes: All `{{spec-kit-include: ...}}` paths reference files that exist or will be created in earlier tasks
- [ ] Freshness: `commit_hash` field name consistent across status.json and all references
- [ ] Doc status values: `documented | indexed_only | gap` consistent across modules.json and QUICK-NAV.md
- [ ] Dispatch tier names: `trivial | light | heavy` consistent across all partials and command templates
