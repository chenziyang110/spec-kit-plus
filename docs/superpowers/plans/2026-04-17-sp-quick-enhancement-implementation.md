# sp-quick Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-quick` from slug-only lightweight tracking into an id-based, resumable quick-task workflow with `specify quick` lifecycle management and a derived quick index.

**Architecture:** Keep the shared quick workflow template as the behavior contract, then add a thin `specify quick` CLI surface and shell helpers that read `STATUS.md` as the source of truth and maintain `.planning/quick/index.json` as a rebuildable projection. Preserve the current lightweight quick positioning by avoiding branch/worktree defaults and by keeping recovery centered on empty `sp-quick` invocation rather than a heavy runtime.

**Tech Stack:** Python 3.11+, Typer CLI, Markdown command templates, Bash/PowerShell helper scripts, pytest

---

### Task 1: Lock the New quick Contract in Shared Templates

**Files:**
- Modify: `templates/commands/quick.md`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_quick_skill_mirror.py`
- Test: `tests/test_quick_template_guidance.py`
- Test: `tests/test_quick_skill_mirror.py`

- [ ] **Step 1: Write the failing template assertions for id-based quick workspaces and empty-invocation recovery**

Add or update assertions in `tests/test_quick_template_guidance.py` and `tests/test_quick_skill_mirror.py` so the suite expects:

```python
assert ".planning/quick/<id>-<slug>/" in content
assert ".planning/quick/index.json" in content
assert "if exactly one unfinished quick task exists" in content
assert "if multiple unfinished quick tasks exist" in content
assert "ask the user which quick task to continue" in content
assert "blocked" in content
assert "close" in content
assert "archive" in content
```

Also change any existing slug-only expectations such as:

```python
assert ".planning/quick/<slug>/" in content
```

to the new `<id>-<slug>` shape.

- [ ] **Step 2: Run the focused template tests to verify they fail against the current template**

Run:

```bash
pytest tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py -q
```

Expected: FAIL because `templates/commands/quick.md` still documents `.planning/quick/<slug>/` and does not yet mention `index.json`, close/archive, or empty-call unfinished-task routing.

- [ ] **Step 3: Update `templates/commands/quick.md` to reflect the new quick-task model**

Revise the template so it explicitly documents:

```markdown
- Create or resume `.planning/quick/<id>-<slug>/STATUS.md` before substantial analysis.
- Maintain `.planning/quick/index.json` as a derived quick-task index.
- `sp-quick <description>` creates a new quick task.
- Empty `sp-quick` resumes unfinished quick work when possible.
- If exactly one unfinished quick task exists, resume it automatically.
- If multiple unfinished quick tasks exist, ask the user which one to continue and show `id`, title, current status, and `next_action`.
- Treat `blocked` as resumable unfinished work for recovery routing.
- Use `close` for terminal lifecycle state and `archive` for storage movement.
```

Update the status template frontmatter and summary guidance so the directory and summary pointer examples use:

```markdown
summary_path: [.planning/quick/<id>-<slug>/SUMMARY.md]
```

and add explicit index guidance such as:

```markdown
- `STATUS.md` is the source of truth.
- `.planning/quick/index.json` is a derived index used for list, status, resume, close, and archive operations.
```

- [ ] **Step 4: Run the focused template tests again**

Run:

```bash
pytest tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the template-contract update**

Run:

```bash
git add templates/commands/quick.md tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py
git commit -m "feat: update sp-quick template contract"
```


### Task 2: Add a Quick Index and Discovery Helpers

**Files:**
- Create: `scripts/bash/quick-state.sh`
- Create: `scripts/powershell/quick-state.ps1`
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
- Test: `tests/test_quick_cli.py`

- [ ] **Step 1: Write failing CLI-facing tests for quick discovery and index behavior**

Create `tests/test_quick_cli.py` with tests that exercise helper-backed quick discovery through the Python CLI layer. Cover:

```python
def test_quick_list_defaults_to_unfinished_items(...)
def test_quick_status_reads_status_md_as_source_of_truth(...)
def test_quick_archive_rejects_active_task(...)
def test_quick_index_can_be_rebuilt_when_missing(...)
```

Model the fixture state with directories like:

```text
.planning/quick/260417-001-fix-quick-index-sync/STATUS.md
.planning/quick/260417-002-align-cursor-quick-docs/STATUS.md
.planning/quick/index.json
```

and frontmatter values like:

```markdown
---
status: blocked
trigger: "fix quick indexing"
updated: 2026-04-17T10:00:00Z
---
```

- [ ] **Step 2: Run the new CLI-facing tests to confirm the helpers do not exist yet**

Run:

```bash
pytest tests/test_quick_cli.py -q
```

Expected: FAIL because there is no quick helper surface or index implementation yet.

- [ ] **Step 3: Add Bash helper support for quick listing, status loading, and index rebuild**

Create `scripts/bash/quick-state.sh` with small, single-purpose entrypoints such as:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
MODE="${2:-list}"

case "$MODE" in
  list) ;;
  status) ;;
  rebuild-index) ;;
  close) ;;
  archive) ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 1
    ;;
esac
```

Implement logic to:

- scan `.planning/quick/` for `<id>-<slug>` directories
- ignore archive folders when listing active tasks
- read `STATUS.md` frontmatter fields needed for CLI display
- rebuild `.planning/quick/index.json` from `STATUS.md` when missing or stale

Update `scripts/bash/common.sh` only if a shared helper function is needed for frontmatter-safe path calculations or `.planning/quick/` path derivation.

- [ ] **Step 4: Add PowerShell helper support with the same behavior**

Create `scripts/powershell/quick-state.ps1` with matching operations:

```powershell
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("list","status","rebuild-index","close","archive")]
    [string]$Mode = "list",
    [string]$QuickId = ""
)
```

Implement the same rules as the Bash version:

- `<id>-<slug>` is the only supported workspace shape
- `STATUS.md` is the source of truth
- `index.json` is derived and rebuildable
- active-task listing defaults to unfinished tasks only
- archive rejects non-terminal states

Update `scripts/powershell/common.ps1` only if a shared helper is required for quick directory or frontmatter utilities.

- [ ] **Step 5: Run the helper-facing tests**

Run:

```bash
pytest tests/test_quick_cli.py -q
```

Expected: PASS for helper-backed status discovery and index rebuild behavior.

- [ ] **Step 6: Commit the quick helper layer**

Run:

```bash
git add scripts/bash/quick-state.sh scripts/powershell/quick-state.ps1 scripts/bash/common.sh scripts/powershell/common.ps1 tests/test_quick_cli.py
git commit -m "feat: add quick state helper scripts"
```


### Task 3: Add `specify quick` CLI Commands

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/test_quick_cli.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Extend the failing CLI tests to cover the new Typer command surface**

Add cases in `tests/test_quick_cli.py` for:

```python
def test_quick_list_command_prints_unfinished_tasks(...)
def test_quick_status_command_prints_current_focus_and_next_action(...)
def test_quick_close_command_requires_resolved_or_blocked(...)
def test_quick_archive_command_rejects_active_tasks(...)
```

and add an integration-level assertion in `tests/integrations/test_cli.py` to verify the CLI help exposes the new `quick` management group or subcommands.

- [ ] **Step 2: Run the CLI tests to verify the command surface is missing**

Run:

```bash
pytest tests/test_quick_cli.py tests/integrations/test_cli.py -q
```

Expected: FAIL because `src/specify_cli/__init__.py` has no `quick` command group yet.

- [ ] **Step 3: Add the Typer subcommand group and command implementations**

In `src/specify_cli/__init__.py`, add a dedicated Typer app:

```python
quick_app = typer.Typer(
    name="quick",
    help="Inspect and manage tracked quick tasks",
    add_completion=False,
)
app.add_typer(quick_app, name="quick")
```

Implement the first slice commands:

```python
@quick_app.command("list")
def quick_list(...): ...

@quick_app.command("status")
def quick_status(quick_id: str, ...): ...

@quick_app.command("resume")
def quick_resume(quick_id: str, ...): ...

@quick_app.command("close")
def quick_close(
    quick_id: str,
    status: str = typer.Option(..., "--status"),
): ...

@quick_app.command("archive")
def quick_archive(quick_id: str, ...): ...
```

Wire these commands to the helper layer so they:

- default `list` to unfinished tasks
- render `id`, title, status, and `next_action`
- read `STATUS.md` as the source of truth
- allow `close` only for `resolved` and `blocked`
- reject `archive` for active tasks

- [ ] **Step 4: Run the CLI command tests again**

Run:

```bash
pytest tests/test_quick_cli.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the CLI management surface**

Run:

```bash
git add src/specify_cli/__init__.py tests/test_quick_cli.py tests/integrations/test_cli.py
git commit -m "feat: add specify quick management commands"
```


### Task 4: Align Generated Skills and Integration Mirrors

**Files:**
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `.agents/skills/sp-quick/SKILL.md`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/test_quick_skill_mirror.py`

- [ ] **Step 1: Add failing Codex-specific assertions for the updated quick contract**

Update `tests/integrations/test_integration_codex.py` and, if needed, `tests/test_quick_skill_mirror.py` so generated Codex quick skills are expected to contain:

```python
assert ".planning/quick/<id>-<slug>/" in content
assert ".planning/quick/index.json" in content
assert "if exactly one unfinished quick task exists" in content
assert "if multiple unfinished quick tasks exist" in content
```

- [ ] **Step 2: Run the Codex generation tests to confirm the mirror is stale**

Run:

```bash
pytest tests/integrations/test_integration_codex.py tests/test_quick_skill_mirror.py -q
```

Expected: FAIL because the generated or mirrored Codex skill still reflects the old slug-only contract.

- [ ] **Step 3: Update the Codex quick augmentation and repo mirror**

Adjust `src/specify_cli/integrations/codex/__init__.py` so the Codex addendum preserves the shared quick semantics instead of reintroducing the old path shape. Regenerate or manually update `.agents/skills/sp-quick/SKILL.md` so it mirrors the new contract.

Key phrases to preserve in the mirror:

```markdown
- `.planning/quick/<id>-<slug>/STATUS.md`
- `.planning/quick/index.json`
- empty `sp-quick` recovery
- ask the user which quick task to continue
- `blocked` quick tasks remain resumable
```

- [ ] **Step 4: Re-run the Codex mirror tests**

Run:

```bash
pytest tests/integrations/test_integration_codex.py tests/test_quick_skill_mirror.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the integration alignment**

Run:

```bash
git add src/specify_cli/integrations/codex/__init__.py .agents/skills/sp-quick/SKILL.md tests/integrations/test_integration_codex.py tests/test_quick_skill_mirror.py
git commit -m "feat: align codex quick skill with new quick state model"
```


### Task 5: Update User-Facing Docs for the New quick Model

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/superpowers/specs/2026-04-17-sp-quick-enhancement-design.md`
- Test: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add failing doc assertions for quick recovery and management commands**

Extend or add doc tests so the repo expects the guidance docs to mention:

```python
assert "empty `sp-quick`" in content or "invoke `sp-quick` with no arguments" in content
assert "specify quick list" in content
assert "specify quick status" in content
assert "specify quick close" in content
assert "specify quick archive" in content
```

Keep the existing fast/quick/specify routing assertions intact.

- [ ] **Step 2: Run the doc tests to verify the guidance is behind**

Run:

```bash
pytest tests/test_specify_guidance_docs.py -q
```

Expected: FAIL because the docs currently describe `sp-quick` only as a bounded workspace without the new recovery and management model.

- [ ] **Step 3: Update the user-facing docs**

Revise `README.md` and `docs/quickstart.md` to explain:

- quick tasks now use `.planning/quick/<id>-<slug>/`
- empty `sp-quick` resumes unfinished work when possible
- `blocked` quick tasks can be resumed
- `specify quick list|status|resume|close|archive` are available
- `list` defaults to unfinished tasks

Update the approved design document only if the implementation wording or command names drift from the spec during execution. Do not rewrite the design itself unless the code meaning changes.

- [ ] **Step 4: Run the guidance doc tests again**

Run:

```bash
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the documentation update**

Run:

```bash
git add README.md docs/quickstart.md docs/superpowers/specs/2026-04-17-sp-quick-enhancement-design.md tests/test_specify_guidance_docs.py
git commit -m "docs: explain resumable quick task workflow"
```


### Task 6: Run the Full Targeted Regression Sweep

**Files:**
- Modify: `docs/superpowers/plans/2026-04-17-sp-quick-enhancement-implementation.md`

- [ ] **Step 1: Run the targeted regression suite for all changed surfaces**

Run:

```bash
pytest \
  tests/test_quick_template_guidance.py \
  tests/test_quick_skill_mirror.py \
  tests/test_quick_cli.py \
  tests/test_specify_guidance_docs.py \
  tests/integrations/test_cli.py \
  tests/integrations/test_integration_codex.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Perform a manual CLI sanity pass**

Run:

```bash
python -m specify_cli --help
python -m specify_cli quick --help
python -m specify_cli quick list --help
python -m specify_cli quick status demo-id --help
```

Expected:

- the root CLI still loads normally
- `quick` appears as a management surface
- command help text reflects the new quick-task vocabulary

- [ ] **Step 3: Record any final deviations directly in this plan before handoff**

If implementation required renaming helper files, moving command registration, or adjusting exact flag syntax, update this plan document so the final executed record matches the code.

- [ ] **Step 4: Commit the verification pass if this plan file changed during execution**

Run only if this file changed:

```bash
git add docs/superpowers/plans/2026-04-17-sp-quick-enhancement-implementation.md
git commit -m "docs: finalize sp-quick enhancement implementation plan"
```

## Spec Coverage Check

- Stable `<id>-<slug>` quick-task identity: covered by Tasks 1, 2, 3, and 5.
- `STATUS.md` as source of truth plus `.planning/quick/index.json` as derived projection: covered by Tasks 1, 2, and 3.
- Empty `sp-quick` recovery and multiple-task selection behavior: covered by Task 1 and mirrored in Task 4 docs/contracts.
- `blocked` remains resumable unfinished work: covered by Tasks 1, 2, 3, and 5.
- `specify quick list|status|resume|close|archive`: covered by Tasks 2, 3, and 5.
- `close` versus `archive` lifecycle separation: covered by Tasks 1, 2, and 3.
- No default branch/worktree behavior: preserved by omission from implementation tasks and by doc wording in Task 5.
- Shared-first behavior across integrations with minimal Codex-specific augmentation: covered by Tasks 1, 4, and 5.

## Placeholder Scan

Checked for:

- `TBD`
- `TODO`
- "implement later"
- vague steps without commands

No placeholders remain. Each task names files, concrete assertions, and verification commands.

## Type and Naming Consistency

The plan consistently uses:

- `.planning/quick/<id>-<slug>/`
- `STATUS.md`
- `SUMMARY.md`
- `.planning/quick/index.json`
- `specify quick list|status|resume|close|archive`
- terminal lifecycle values `resolved|blocked`

If implementation discovers a naming conflict with existing CLI command registration, update Task 3 and Task 5 together so CLI syntax and docs remain aligned.
