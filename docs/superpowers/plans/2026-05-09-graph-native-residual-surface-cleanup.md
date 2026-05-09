# Graph-Native Residual Surface Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining handbook-first and project-map-first brownfield runtime semantics from upstream workflow, scaffolding, and test surfaces while preserving explicit compatibility/export behavior.

**Architecture:** Execute this as three contract-aligned slices. First, migrate the upstream workflow templates and partials so `sp-specify`, `sp-plan`, `sp-tasks`, `sp-clarify`, `sp-deep-research`, and `sp-constitution` become graph-native cognition-first. Second, normalize compatibility infrastructure and team scaffolding so `PROJECT-HANDBOOK.md` and `.specify/project-map/**` remain supported outputs but no longer masquerade as ordinary runtime truth. Third, realign tests, fixtures, and convergence locks so only intentional compatibility/export residue survives.

**Tech Stack:** Python 3.13, Typer CLI surfaces, Markdown workflow templates, Bash/PowerShell helper scripts, Codex/Claude integration scaffolding, pytest

---

## Scope Check

The approved spec touches many files, but they are one tightly coupled cleanup
program rather than separate subsystems:

- upstream workflow contract wording
- compatibility-layer helper semantics
- team and packet context bundles
- template, CLI, and script regression locks

Splitting these into separate plans would leave the repository in a
half-migrated state where workflow entrypoints, helper surfaces, and tests
contradict each other.
This plan keeps the work in one lane and sequences it as small, reviewable
tasks.

## File Structure

```text
MODIFY: upstream workflow contracts
  templates/commands/specify.md
    Purpose: remove BUILD-HANDBOOK heavy gate and make graph-native cognition the default spec-entry runtime truth path.
  templates/commands/plan.md
    Purpose: remove BUILD-HANDBOOK heavy gate and make cognition-first planning gating explicit.
  templates/commands/tasks.md
    Purpose: remove BUILD-HANDBOOK heavy gate and make cognition-first task-generation gating explicit.
  templates/commands/clarify.md
    Purpose: replace runtime-handbook repair language with cognition-first touched-area repair language.
  templates/commands/deep-research.md
    Purpose: stop treating BUILD-HANDBOOK as the default implementation-pattern proof surface.
  templates/commands/constitution.md
    Purpose: treat handbook/project-map artifacts as compatibility/export surfaces rather than default repo-derived truth.
  templates/command-partials/specify/shell.md
    Purpose: replace handbook/project-map navigation wording with graph-native cognition wording.
  templates/command-partials/plan/shell.md
    Purpose: replace handbook/project-map primary-input wording with cognition/runtime-slice wording.
  templates/command-partials/tasks/shell.md
    Purpose: replace handbook/project-map primary-input wording with cognition/runtime-slice wording.

MODIFY: compatibility infrastructure and team scaffolding
  scripts/bash/project-map-freshness.sh
    Purpose: keep compatibility-layer lifecycle logic, but adjust outward wording so it no longer implies project-map is default runtime truth.
  scripts/powershell/project-map-freshness.ps1
    Purpose: keep shell parity for compatibility-layer lifecycle messaging.
  templates/project-map/QUICK-NAV.md
    Purpose: describe itself as compatibility/export navigation rather than ordinary workflow first-read guidance.
  templates/project-map/map-state-template.md
    Purpose: mark handbook/project-map outputs as compatibility/export outputs maintained by the compatibility layer.
  templates/project-map/index/atlas-index.json
    Purpose: keep machine-readable export metadata while clarifying entrypoint semantics.
  src/specify_cli/integrations/claude/templates/implement-teams.md
    Purpose: stop defaulting worker context bundles to PROJECT-HANDBOOK/project-map surfaces.
  src/specify_cli/integrations/codex/__init__.py
    Purpose: align Codex subagent join-point wording with compatibility-layer production instead of runtime truth.
  src/specify_cli/__init__.py
    Purpose: align generated guidance and CLI descriptions with the new compatibility/export framing where needed.

MODIFY: tests and fixtures
  tests/test_project_map_hard_gate_guidance.py
    Purpose: remove the current exception that still requires BUILD-HANDBOOK gates in specify/plan/tasks.
  tests/test_runtime_handbook_contract.py
    Purpose: keep runtime contract coverage graph-native and reject renewed handbook-first language.
  tests/execution/test_packet_validator.py
    Purpose: replace handbook-first default context bundles with cognition-first bundles.
  tests/codex_team/test_worker_bootstrap.py
    Purpose: replace handbook-first worker bootstrap metadata with cognition-first execution context bundles.
  tests/test_project_map_freshness_scripts.py
    Purpose: preserve compatibility-layer helper behavior while realigning message and status expectations.
  tests/integrations/test_cli.py
    Purpose: align map command descriptions, mark-dirty payload expectations, and compatibility messaging.

CREATE: new lock coverage
  tests/test_graph_native_residual_cleanup.py
    Purpose: enforce a strict allowlist so migrate-now residue cannot return outside intentional compatibility/export and infrastructure-itself surfaces.
  docs/project-cognition-compatibility-inventory.md
    Purpose: document the explicit compatibility/export allowlist for remaining handbook/project-map surfaces.
```

---

## Task 1: Lock the upstream workflow migration in failing tests

**Files:**
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Replace the current `specify/plan/tasks` exception in `tests/test_project_map_hard_gate_guidance.py`**

Change the `for rel_path in ...` assertions so `templates/commands/specify.md`,
`templates/commands/plan.md`, and `templates/commands/tasks.md` are no longer
allowed to keep `build-handbook.md` or `build-workflow-contract`.

Use assertions like:

```python
for rel_path in TARGETS:
    content = _read(rel_path).lower()
    assert ".specify/project-cognition/status.json" in content, f"{rel_path} missing cognition status gate"
    if rel_path == "templates/commands/debug.md":
        assert ".specify/project-cognition/slices/debug.json" in content, f"{rel_path} missing debug slice gate"
    else:
        assert ".specify/project-cognition/slices/change.json" in content, f"{rel_path} missing change slice gate"
    assert "build-handbook.md" not in content, f"{rel_path} should not keep BUILD-HANDBOOK gate"
    assert "build-workflow-contract" not in content, f"{rel_path} should not keep BUILD-WORKFLOW-CONTRACT gate"
```

- [ ] **Step 2: Expand the same test file to cover the upstream partials**

Add explicit checks for:

- `templates/command-partials/specify/shell.md`
- `templates/command-partials/plan/shell.md`
- `templates/command-partials/tasks/shell.md`

Use assertions like:

```python
for rel_path in (
    "templates/command-partials/specify/shell.md",
    "templates/command-partials/plan/shell.md",
    "templates/command-partials/tasks/shell.md",
):
    content = _read(rel_path).lower()
    assert ".specify/project-cognition/status.json" in content
    assert "handbook/project-map" not in content
    assert "build-handbook.md" not in content
```

- [ ] **Step 3: Add runtime contract coverage for the upstream templates in `tests/test_runtime_handbook_contract.py`**

Add a new test that reads:

- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`

and asserts:

```python
for rel_path in (
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
):
    content = _read(rel_path)
    lowered = content.lower()
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "runtime handbook gate" not in lowered
```

- [ ] **Step 4: Run the focused red suite**

Run:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/test_runtime_handbook_contract.py -q
```

Expected: FAIL because the current upstream templates and partials still contain
`BUILD-HANDBOOK.md`, `build-workflow-contract`, and
`handbook/project-map` wording.

- [ ] **Step 5: Commit the failing-test lock**

Run:

```bash
git add tests/test_project_map_hard_gate_guidance.py tests/test_runtime_handbook_contract.py
git commit -m "test: lock graph-native upstream workflow contracts"
```

## Task 2: Migrate `sp-specify`, `sp-plan`, and `sp-tasks` to graph-native cognition

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/command-partials/specify/shell.md`
- Modify: `templates/command-partials/plan/shell.md`
- Modify: `templates/command-partials/tasks/shell.md`
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Replace `specify` pre-gate wording with graph-native cognition gate**

In `templates/commands/specify.md`, replace the sections that currently say:

- `Runtime handbook gate`
- `Pass the handbook gate by reading:`
- `BUILD-HANDBOOK.md`
- `BUILD-WORKFLOW-CONTRACT`

with cognition-first language shaped like:

```md
**Runtime cognition gate:** you must pass the project cognition gate before repository
analysis, planning-critical clarification, or implementation-shaping code reads begin.

**This command tier: heavy.** Pass the cognition gate by reading:
1. `.specify/project-cognition/status.json`
2. `.specify/project-cognition/slices/change.json`
3. `.specify/project-cognition/graph/nodes.json`
4. `.specify/project-cognition/graph/edges.json`
5. `.specify/project-cognition/graph/claims.json`
6. `.specify/project-cognition/graph/conflicts.json`
```

- [ ] **Step 2: Rewrite the `Ensure repository navigation system exists` block in `templates/commands/specify.md`**

Replace the `.specify/project-map/index/status.json` + `BUILD-HANDBOOK.md`
checks with guidance that:

- checks `.specify/project-cognition/status.json`
- uses `sp-map-update` for stale or too-weak baselines
- falls back to `sp-map-scan -> sp-map-build` only when no usable baseline
  exists
- treats `.specify/project-map/**` as support-only compatibility artifacts

Include wording like:

```md
- Check whether `.specify/project-cognition/status.json` exists.
- [AGENT] If cognition freshness is `missing`, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that baseline before continuing.
- [AGENT] If cognition freshness is `stale`, stop and tell the user to run `{{invoke:map-update}}`; if no usable baseline remains, rebuild through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- Do not treat support-only project-map exports as the primary runtime read path for this workflow.
```

- [ ] **Step 3: Replace `BUILD-HANDBOOK.md` reads inside `templates/commands/specify.md`**

Rewrite the `Load context`, `Run a codebase scout before clarification`,
`intent-analysis`, `Analyze the whole feature before decomposing it`,
`gray areas`, and `planning-critical question` sections so they reference
project cognition surfaces instead of `BUILD-HANDBOOK.md`.

Use replacements like:

```md
- [AGENT] Read `.specify/project-cognition/status.json`.
- [AGENT] Read `.specify/project-cognition/slices/change.json`.
- Read graph artifacts only when the touched area requires deeper ownership, propagation, or conflict context.
- Derive gray areas from the combination of user intent, project cognition slices, and targeted repository evidence.
```

- [ ] **Step 4: Apply the same migration pattern to `templates/commands/plan.md` and `templates/commands/tasks.md`**

For both files:

- replace the `Ensure repository navigation system exists` block
- replace the `Load context` block
- replace the heavy-gate list
- rewrite final refresh wording so it says
  `refresh cognition baseline and synchronize compatibility/export outputs`
  instead of `handbook/project-map truth`

Use exact artifact names:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/slices/change.json`
- `.specify/project-cognition/graph/nodes.json`
- `.specify/project-cognition/graph/edges.json`
- `.specify/project-cognition/graph/claims.json`
- `.specify/project-cognition/graph/conflicts.json`

- [ ] **Step 5: Update the three upstream partials**

Edit:

- `templates/command-partials/specify/shell.md`
- `templates/command-partials/plan/shell.md`
- `templates/command-partials/tasks/shell.md`

so `## Context` reads like:

```md
- Primary inputs: the user's request, the active workflow artifacts, passive learning files, and the graph-native project cognition runtime.
```

and remove lines that still say:

- `handbook/project-map navigation system`
- `project handbook/project-map set`
- `Do not trust stale navigation coverage when handbook/project-map context should be the source of truth.`

Replace the guardrail with:

```md
- Do not trust stale or insufficient cognition coverage; refresh the runtime baseline before relying on broad repository inference.
```

- [ ] **Step 6: Run the upstream workflow suite**

Run:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/test_runtime_handbook_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the upstream workflow migration**

Run:

```bash
git add templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/command-partials/specify/shell.md templates/command-partials/plan/shell.md templates/command-partials/tasks/shell.md tests/test_project_map_hard_gate_guidance.py tests/test_runtime_handbook_contract.py
git commit -m "refactor: migrate upstream workflows to cognition runtime"
```

## Task 3: Migrate `clarify`, `deep-research`, and `constitution`

**Files:**
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/constitution.md`

- [ ] **Step 1: Replace `BUILD-HANDBOOK.md` as the default touched-area proof surface in `clarify.md`**

Change the `Load context` section so:

- `BUILD-HANDBOOK.md if present`
- `targeted live repository files only when the runtime handbook cannot answer`

becomes:

```md
- `.specify/project-cognition/status.json`
- `.specify/project-cognition/slices/change.json`
- targeted graph artifacts when deeper ownership, propagation, or conflict proof is required
- targeted live repository files only when project cognition artifacts cannot safely answer the touched planning-critical gap
```

- [ ] **Step 2: Rewrite the refresh guidance in `clarify.md`**

Replace:

```md
if this repair pass proves the current handbook/project-map no longer captures ...
```

with:

```md
if this repair pass proves the current cognition baseline no longer captures the touched area's ownership, workflow, integration boundary, or verification surface accurately enough, treat `.specify/project-cognition/status.json` as the runtime truth source; if the baseline is stale, run `{{invoke:map-update}}`; if no usable baseline remains, run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`, and synchronize compatibility/export outputs after the refresh completes
```

- [ ] **Step 3: Apply the same pattern to `deep-research.md`**

Replace the default `BUILD-HANDBOOK.md` / `runtime handbook` proof language with
cognition-first proof language:

```md
- `.specify/project-cognition/status.json`
- `.specify/project-cognition/slices/change.json`
- targeted graph artifacts when current implementation patterns need deeper proof
- targeted live files only when the cognition runtime cannot prove the pattern safely
```

- [ ] **Step 4: Reframe `constitution.md` from handbook/project-map truth to cognition truth plus compatibility exports**

Replace wording like:

- `read BUILD-HANDBOOK.md as the runtime handbook entrypoint`
- `mark the related handbook/project-map surface for refresh`
- `handbook/project-map evidence`

with wording like:

```md
- read `.specify/project-cognition/status.json` plus the smallest relevant graph and slice artifacts as the runtime entrypoint
- treat `PROJECT-HANDBOOK.md` and `.specify/project-map/**` as compatibility/export references when the amendment explicitly affects those exports
- if the amendment changes structure, ownership, workflows, testing strategy, integrations, or operator expectations, mark the cognition baseline for refresh and note which compatibility/export outputs must be synchronized
```

- [ ] **Step 5: Run a focused wording search and spot-check**

Run:

```powershell
rg -n "BUILD-HANDBOOK|runtime handbook|handbook/project-map" templates/commands/clarify.md templates/commands/deep-research.md templates/commands/constitution.md
```

Expected: no results.

- [ ] **Step 6: Commit the secondary workflow migration**

Run:

```bash
git add templates/commands/clarify.md templates/commands/deep-research.md templates/commands/constitution.md
git commit -m "refactor: migrate residual analysis workflows to cognition runtime"
```

## Task 4: Lock packet and worker bootstrap context bundles in failing tests

**Files:**
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/codex_team/test_worker_bootstrap.py`

- [ ] **Step 1: Replace the packet fixture in `tests/execution/test_packet_validator.py`**

Swap the current handbook-first `context_bundle` item:

```python
ContextBundleItem(
    path="BUILD-HANDBOOK.md",
    kind="runtime_handbook",
    purpose="Workflow-specific runtime handbook for planning and implementation work",
    required_for=["workflow_boundary"],
    read_order=1,
    must_read=True,
    selection_reason="build runtime handbook is the primary atlas surface for non-debug work",
)
```

with cognition-first items shaped like:

```python
ContextBundleItem(
    path=".specify/project-cognition/status.json",
    kind="project_map",
    purpose="Project cognition runtime status baseline for graph readiness, stale paths, and refresh metadata",
    required_for=["workflow_boundary"],
    read_order=1,
    must_read=True,
    selection_reason="project cognition status is the primary brownfield baseline before delegated execution",
),
ContextBundleItem(
    path=".specify/project-cognition/slices/change.json",
    kind="task_reference",
    purpose="Workflow-specific cognition change slice carrying touched-scope context and conflict signals",
    required_for=["workflow_boundary", "forbidden_drift"],
    read_order=2,
    must_read=True,
    selection_reason="change slice is the default task-local runtime context for non-debug work",
),
```

- [ ] **Step 2: Replace the worker bootstrap metadata in `tests/codex_team/test_worker_bootstrap.py`**

Change:

```python
"context_bundle": "1. PROJECT-HANDBOOK.md [handbook] - root navigation artifact",
```

to:

```python
"context_bundle": "1. .specify/project-cognition/status.json [project_map] - project cognition runtime status baseline; 2. .specify/project-cognition/slices/change.json [task_reference] - touched-scope execution context",
```

and update the corresponding assertions to match exactly.

- [ ] **Step 3: Run the focused red suite**

Run:

```powershell
pytest tests/execution/test_packet_validator.py tests/codex_team/test_worker_bootstrap.py -q
```

Expected: FAIL if any runtime/helper code or text fixtures still encode the old
handbook-first bundle assumptions.

- [ ] **Step 4: Commit the failing bundle locks**

Run:

```bash
git add tests/execution/test_packet_validator.py tests/codex_team/test_worker_bootstrap.py
git commit -m "test: lock cognition-first execution bundles"
```

## Task 5: Normalize compatibility infrastructure and team scaffolding

**Files:**
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `templates/project-map/QUICK-NAV.md`
- Modify: `templates/project-map/map-state-template.md`
- Modify: `templates/project-map/index/atlas-index.json`
- Modify: `src/specify_cli/integrations/claude/templates/implement-teams.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_project_map_freshness_scripts.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Update compatibility-layer helper messages in both shell scripts**

Keep canonical compatibility outputs unchanged, but reframe outward messages.

For example, replace:

```text
Cannot record a fresh project-map baseline because canonical map files are missing:
Run /sp-map-scan, then /sp-map-build first so PROJECT-HANDBOOK.md, .specify/project-map/QUICK-NAV.md, and the layered atlas files exist.
```

with:

```text
Cannot record compatibility/export project-map freshness because canonical export files are missing:
Run /sp-map-scan, then /sp-map-build to rebuild the cognition baseline and regenerate PROJECT-HANDBOOK.md, .specify/project-map/QUICK-NAV.md, and the layered compatibility/export atlas files.
```

Do this in both:

- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/project-map-freshness.ps1`

- [ ] **Step 2: Update `tests/test_project_map_freshness_scripts.py` to lock the new helper wording**

Change assertions like:

```python
assert "canonical map files are missing" in result.stderr.lower()
```

to:

```python
assert "compatibility/export project-map freshness" in result.stderr.lower()
assert "regenerate" in result.stderr.lower()
```

Keep all status-path and helper-behavior assertions intact.

- [ ] **Step 3: Reframe `templates/project-map/QUICK-NAV.md` as compatibility/export navigation**

Replace the top note:

```md
> Layer 1 routing table and dictionary-style atlas entry surface. Start here.
```

with:

```md
> Compatibility/export navigation surface for readers, exports, and migration continuity.
> Ordinary brownfield workflows should start from the graph-native project cognition runtime, not from this document.
```

Also replace:

```md
- Workflows are no longer reading project-map:
  Read `PROJECT-HANDBOOK.md`, `root/WORKFLOWS.md`, ...
```

with:

```md
- Need the compatibility/export navigation view:
  Read `PROJECT-HANDBOOK.md`, `root/WORKFLOWS.md`, ...
```

- [ ] **Step 4: Reframe `templates/project-map/map-state-template.md` and `templates/project-map/index/atlas-index.json`**

In `map-state-template.md`, add compatibility/export labeling:

```md
## Atlas Outputs

- compatibility_handbook: PROJECT-HANDBOOK.md
- compatibility_quick_nav: .specify/project-map/QUICK-NAV.md
```

and update the section note so it says these outputs are synchronized exports,
not the default runtime truth path.

In `atlas-index.json`, keep the same paths but update values like:

- `"layer_1_purpose"`
- `"entry_contract"`
- `"recommended_minimum_read_set"`

so they describe a compatibility/export atlas instead of a first-read runtime
contract.

- [ ] **Step 5: Rework the Claude/Codex team scaffolding**

In `src/specify_cli/integrations/claude/templates/implement-teams.md`:

- remove the ban on reading only `PROJECT-HANDBOOK.md` / `.specify/project-map/*`
  as if those are the default recovered context
- rewrite the execution context bundle bullets so they include:

```md
- include `.specify/project-cognition/status.json`
- include the smallest relevant project cognition slice for the lane, usually `.specify/project-cognition/slices/change.json`
- include graph claims/conflicts only when the lane needs deeper ownership or propagation proof
- include `PROJECT-HANDBOOK.md` or `.specify/project-map/**` only when the lane explicitly needs compatibility/export context
```

In `src/specify_cli/integrations/codex/__init__.py`, replace:

```python
"before writing `PROJECT-HANDBOOK.md`, before updating `.specify/project-map/`, and before the final packet evidence and consistency pass."
```

with wording that makes those join points explicitly about compatibility/export
production, for example:

```python
"before writing compatibility/export outputs such as `PROJECT-HANDBOOK.md` and `.specify/project-map/`, and before the final packet evidence and consistency pass."
```

- [ ] **Step 6: Align any generated guidance text in `src/specify_cli/__init__.py` and CLI tests**

Update text that still implies `project-map` descriptions are
`handbook/project-map coverage` default entrypoints.

In `tests/integrations/test_cli.py`, replace:

```python
assert "handbook/project-map coverage" in map_scan_fm["description"].lower()
```

with a cognition-first expectation like:

```python
assert "graph-native cognition baseline" in map_scan_fm["description"].lower()
```

- [ ] **Step 7: Run the compatibility/scaffolding suite**

Run:

```powershell
pytest tests/test_project_map_freshness_scripts.py tests/integrations/test_cli.py -q
```

Expected: PASS for helper/CLI wording and behavior.

- [ ] **Step 8: Commit the compatibility infrastructure normalization**

Run:

```bash
git add scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/project-map/QUICK-NAV.md templates/project-map/map-state-template.md templates/project-map/index/atlas-index.json src/specify_cli/integrations/claude/templates/implement-teams.md src/specify_cli/integrations/codex/__init__.py src/specify_cli/__init__.py tests/test_project_map_freshness_scripts.py tests/integrations/test_cli.py
git commit -m "refactor: normalize compatibility export infrastructure"
```

## Task 6: Bring packet/runtime helpers and worker scaffolding to green

**Files:**
- Modify: `src/specify_cli/integrations/claude/templates/implement-teams.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/codex_team/test_worker_bootstrap.py`

- [ ] **Step 1: Ensure the worker-facing context bundle contract is cognition-first**

After Task 5 scaffolding changes are in place, verify that any worker-facing
examples or helper text that still say:

- `PROJECT-HANDBOOK.md [handbook] - root navigation artifact`
- `build runtime handbook`

are replaced with the cognition-first bundle language from Task 4.

- [ ] **Step 2: Run the packet/worker suite**

Run:

```powershell
pytest tests/execution/test_packet_validator.py tests/codex_team/test_worker_bootstrap.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit the green bundle alignment**

Run:

```bash
git add src/specify_cli/integrations/claude/templates/implement-teams.md src/specify_cli/integrations/codex/__init__.py tests/execution/test_packet_validator.py tests/codex_team/test_worker_bootstrap.py
git commit -m "refactor: align worker execution context bundles"
```

## Task 7: Add the residual cleanup allowlist and convergence lock

**Files:**
- Create: `docs/project-cognition-compatibility-inventory.md`
- Create: `tests/test_graph_native_residual_cleanup.py`

- [ ] **Step 1: Create the explicit compatibility inventory**

Create `docs/project-cognition-compatibility-inventory.md` with content like:

```md
# Project Cognition Compatibility Inventory

## Intentional Compatibility/Export Surfaces

- `PROJECT-HANDBOOK.md` remains a compatibility/export reader artifact.
- `DEBUG-HANDBOOK.md` remains a compatibility/export reader artifact when generated.
- `BUILD-HANDBOOK.md` remains a compatibility/export reader artifact when generated.
- `.specify/project-map/**` remains a compatibility/export and synchronization surface.
- `project-map-freshness` helpers remain compatibility/export lifecycle helpers.

## Not Default Runtime Truth

The surfaces above must not be treated as:

- the default brownfield gate
- the default scout artifact
- the default top-level worker context bundle
- the ordinary workflow first-read path
```

- [ ] **Step 2: Create `tests/test_graph_native_residual_cleanup.py`**

Use a strict allowlist-based scan like:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCANNED_FILES = [
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/clarify.md",
    "templates/commands/deep-research.md",
    "templates/commands/constitution.md",
    "templates/command-partials/specify/shell.md",
    "templates/command-partials/plan/shell.md",
    "templates/command-partials/tasks/shell.md",
    "src/specify_cli/integrations/claude/templates/implement-teams.md",
    "src/specify_cli/integrations/codex/__init__.py",
    "tests/execution/test_packet_validator.py",
    "tests/codex_team/test_worker_bootstrap.py",
]
LEGACY_TOKENS = (
    "BUILD-HANDBOOK.md",
    "PROJECT-HANDBOOK.md [handbook]",
    "runtime handbook",
    "handbook/project-map",
)


def test_migrate_now_surfaces_do_not_reintroduce_handbook_first_contracts() -> None:
    unexpected = []
    for rel_path in SCANNED_FILES:
        text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
        if any(token in text for token in LEGACY_TOKENS):
            unexpected.append(rel_path)
    assert unexpected == []
```

- [ ] **Step 3: Run the red convergence lock**

Run:

```powershell
pytest tests/test_graph_native_residual_cleanup.py -q
```

Expected: FAIL until all migrate-now surfaces are clean.

- [ ] **Step 4: Commit the new lock**

Run:

```bash
git add docs/project-cognition-compatibility-inventory.md tests/test_graph_native_residual_cleanup.py
git commit -m "test: add residual cleanup convergence lock"
```

## Task 8: Run the final residue scan and targeted convergence suite

**Files:**
- Modify: `docs/project-cognition-compatibility-inventory.md` if the final allowlist needs tightening
- Modify: `tests/test_graph_native_residual_cleanup.py` only if the scan proves a narrower allowlist is warranted

- [ ] **Step 1: Run the final repo-wide residue scan**

Run:

```powershell
rg -n "DEBUG-HANDBOOK|BUILD-HANDBOOK|project-map freshness|handbook/project-map|runtime handbook|\.specify/project-map/|PROJECT-HANDBOOK\.md" README.md PROJECT-HANDBOOK.md docs src templates tests scripts --glob '!docs/superpowers/**'
```

Expected classification:

- `migrate-now`: zero hits
- `compatibility/export`: only explicit inventory, export docs, and compatibility-layer templates/helpers
- `infrastructure-itself`: only scripts/templates whose job is maintaining compatibility outputs

- [ ] **Step 2: Tighten the inventory or lock if the scan exposes an over-broad allowlist**

If the scan returns a hit that is not clearly compatibility/export or
infrastructure-itself, fix the code instead of broadening the allowlist.

- [ ] **Step 3: Run the targeted convergence suite**

Run:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/test_runtime_handbook_contract.py tests/execution/test_packet_validator.py tests/codex_team/test_worker_bootstrap.py tests/test_project_map_freshness_scripts.py tests/integrations/test_cli.py tests/test_graph_native_residual_cleanup.py -q
```

Expected: PASS.

- [ ] **Step 4: Run the broader residual verification slice**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the completed residual cleanup**

Run:

```bash
git add docs/project-cognition-compatibility-inventory.md tests/test_graph_native_residual_cleanup.py README.md PROJECT-HANDBOOK.md templates src tests scripts
git commit -m "test: lock graph-native residual surface cleanup"
```

## Self-Review

- Spec coverage:
  - upstream workflow contracts are covered by Tasks 1-3
  - compatibility/export infrastructure is covered by Task 5
  - packet/worker scaffolding is covered by Tasks 4 and 6
  - allowlist and convergence lock are covered by Tasks 7-8
- Placeholder scan:
  - no unresolved placeholder markers or deferred-fill notes remain
  - each task names exact files, commands, and expected outcomes
- Type consistency:
  - the plan consistently uses `ContextBundleItem.kind` values that exist today:
    `project_map` and `task_reference`
  - the plan consistently uses the graph-native surfaces already present in the codebase:
    `.specify/project-cognition/status.json`
    `.specify/project-cognition/slices/change.json`
    `.specify/project-cognition/graph/{nodes,edges,claims,conflicts}.json`

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-graph-native-residual-surface-cleanup.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
