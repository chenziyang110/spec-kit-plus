# Project Cognition Refresh Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the contradiction where `sp-map-update` reports refresh success but the next workflow immediately blocks as stale and recommends `sp-map-update` again.

**Architecture:** Introduce a shared freshness outcome model in `project_map_status.py` that separates factual state from next-action guidance and distinguishes runtime-truth drift from support drift and partial refresh. Update CLI, hooks, shell-parity helpers, and shared workflow guidance to consume that model consistently so refresh producers and refresh consumers use the same definition of readiness.

**Tech Stack:** Python status and hook helpers in `src/specify_cli`, Typer CLI surfaces, bash and PowerShell freshness helpers, Markdown workflow templates and passive skills, pytest unit/contract/integration/template guidance tests.

---

## File Structure

```text
MODIFY
  src/specify_cli/project_map_status.py
    Purpose: define the shared freshness state model, classify changed paths into runtime/support/reference layers, and return next-action guidance used by all call sites.
  src/specify_cli/hooks/project_map.py
    Purpose: convert shared freshness results into hook-level blocked/warn/ok outcomes without flattening every failure into the same message.
  src/specify_cli/hooks/preflight.py
    Purpose: preserve implement-specific dirty-scope exceptions while consuming the richer shared freshness payload.
  src/specify_cli/__init__.py
    Purpose: align `project-map check`, `record-refresh`, `complete-refresh`, and workflow preflight copy with the new shared readiness contract.
  src/specify_cli/debug/cli.py
    Purpose: stop debug preflight from using stale-only wording when support drift or partial refresh is the real state.
  scripts/bash/project-map-freshness.sh
    Purpose: keep bash helper classification and output schema aligned with Python freshness semantics.
  scripts/powershell/project-map-freshness.ps1
    Purpose: keep PowerShell helper classification and output schema aligned with Python freshness semantics.
  templates/commands/map-update.md
    Purpose: document that `sp-map-update` can end in ready or partial outcomes and must verify readiness after recording updates.
  templates/commands/specify.md
    Purpose: teach `sp-specify` to route based on freshness class rather than blindly repeating `sp-map-update`.
  templates/commands/plan.md
  templates/commands/tasks.md
  templates/commands/debug.md
  templates/commands/test-scan.md
  templates/commands/test-build.md
  templates/commands/checklist.md
  templates/commands/quick.md
  templates/command-partials/common/context-loading-gradient.md
  templates/passive-skills/spec-kit-project-map-gate/SKILL.md
    Purpose: align all shared brownfield gate wording with state + next-action semantics.
  src/specify_cli/integrations/base.py
    Purpose: keep generated integration guidance consistent with the new gate contract.
  README.md
  PROJECT-HANDBOOK.md
  templates/project-handbook-template.md
    Purpose: document the difference between recorded refresh and ready refresh and explain how support drift is handled.

TESTS TO MODIFY
  tests/test_project_map_status.py
  tests/test_project_map_freshness_scripts.py
  tests/hooks/test_preflight_hooks.py
  tests/test_project_map_hard_gate_guidance.py
  tests/integrations/test_cli.py
  tests/contract/test_hook_cli_surface.py
  tests/test_alignment_templates.py
  tests/test_debug_template_guidance.py
  tests/test_testing_workflow_guidance.py
  tests/test_hook_template_guidance.py
  tests/test_command_surface_semantics.py
  tests/test_map_runtime_template_guidance.py
  tests/test_specify_guidance_docs.py
    Purpose: lock in shared classification, shell parity, CLI copy, hook behavior, and generated guidance consistency.
```

---

## Task 1: Lock the new shared state model with failing tests

**Files:**
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/test_project_map_freshness_scripts.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add Python freshness classification tests for support drift**

Add a failing test to `tests/test_project_map_status.py` that seeds a fresh baseline, then evaluates changed paths including:

```python
changed_files = [".specify/templates/runtime-config.template.json"]
```

and expects the result payload to include:

```python
assert result["freshness"] == "support_drift"
assert result["recommended_next_action"] in {
    "commit_or_ignore_support_files",
    "review_policy_configuration",
}
assert any("support" in reason.lower() for reason in result["reasons"])
```

- [ ] **Step 2: Add Python freshness classification tests for partial refresh**

In `tests/test_project_map_status.py`, add a second failing test that simulates:

- a valid baseline
- changed files that still classify as runtime-truth drift
- a refresh result that has recorded update metadata but still evaluates as blocked

and expects:

```python
assert result["freshness"] == "partial_refresh"
assert result["recommended_next_action"] != "retry_current_workflow"
```

- [ ] **Step 3: Add shell parity tests for support drift**

Update `tests/test_project_map_freshness_scripts.py` with bash and PowerShell checks that introduce a support-only changed path and assert both helpers return the same class and next action:

```python
assert bash_result["freshness"] == "support_drift"
assert pwsh_result["freshness"] == "support_drift"
assert bash_result["recommended_next_action"] == pwsh_result["recommended_next_action"]
```

- [ ] **Step 4: Add preflight guidance tests for class-aware recommendations**

Update `tests/test_project_map_hard_gate_guidance.py` so:

- runtime-truth stale still recommends `/sp-map-update`
- missing still recommends `/sp-map-scan` then `/sp-map-build`
- support drift does not recommend `/sp-map-update`

Use assertions like:

```python
assert "/sp-map-update" not in blocked.errors[0]
assert "support" in blocked.errors[0].lower()
```

- [ ] **Step 5: Add CLI outcome tests for record-refresh vs ready**

Update `tests/integrations/test_cli.py` to cover:

- `project-map record-refresh --format json` on a truly freshable baseline returning `fresh`
- `project-map record-refresh --format json` on a support-drift scenario returning a non-ready class and a non-retry recommendation

Use assertions like:

```python
assert payload["freshness"] in {"fresh", "partial_refresh", "support_drift"}
assert "recommended_next_action" in payload
```

- [ ] **Step 6: Run the focused red suite**

Run:

```bash
pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_cli.py -q
```

Expected: FAIL because the shared state model and new fields do not exist yet.

## Task 2: Introduce the shared freshness state and next-action model

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `tests/test_project_map_status.py`

- [ ] **Step 1: Add explicit state and recommendation constants**

In `src/specify_cli/project_map_status.py`, introduce explicit constant sets near the existing guidance strings:

```python
FRESHNESS_READY_STATE = "fresh"
FRESHNESS_RUNTIME_STALE_STATE = "stale"
FRESHNESS_SUPPORT_DRIFT_STATE = "support_drift"
FRESHNESS_MISSING_STATE = "missing"
FRESHNESS_PARTIAL_REFRESH_STATE = "partial_refresh"

NEXT_ACTION_RETRY = "retry_current_workflow"
NEXT_ACTION_MAP_UPDATE = "run_map_update"
NEXT_ACTION_MAP_SCAN_BUILD = "run_map_scan_build"
NEXT_ACTION_SUPPORT = "commit_or_ignore_support_files"
NEXT_ACTION_POLICY = "review_policy_configuration"
```

- [ ] **Step 2: Split path classification into layer + severity**

Replace the single-string `classify_changed_path()` contract with a richer result object such as:

```python
def classify_changed_path(path: str) -> dict[str, str]:
    return {
        "layer": "runtime_truth",
        "severity": "stale",
    }
```

Use these rules:

- runtime-truth surfaces: `stale`
- support/tool-managed surfaces: `support_drift`
- reference/export surfaces: `ignore`
- broader code surfaces: `possibly_stale`

- [ ] **Step 3: Add shared recommendation builder**

Create a helper in `src/specify_cli/project_map_status.py`:

```python
def recommended_next_action_for_freshness(*, freshness: str, reasons: list[str]) -> str:
    if freshness == FRESHNESS_MISSING_STATE:
        return NEXT_ACTION_MAP_SCAN_BUILD
    if freshness == FRESHNESS_RUNTIME_STALE_STATE:
        return NEXT_ACTION_MAP_UPDATE
    if freshness == FRESHNESS_SUPPORT_DRIFT_STATE:
        return NEXT_ACTION_SUPPORT
    if freshness == FRESHNESS_PARTIAL_REFRESH_STATE:
        return NEXT_ACTION_MAP_UPDATE
    return NEXT_ACTION_RETRY
```

- [ ] **Step 4: Return the new fields from `assess_project_map_freshness()`**

Update every return payload in `assess_project_map_freshness()` to include:

```python
"recommended_next_action": NEXT_ACTION_RETRY,
"readiness": "ready",
```

For blocked or partial states, set `readiness` to `"blocked"` and choose the correct next action.

- [ ] **Step 5: Reclassify support drift without hard-mapping it to runtime stale**

In the changed-files loop, when classification returns support drift, keep `worst` from becoming runtime stale and instead produce:

```python
worst = "support_drift"
reasons.append(f"tool-managed support surface changed: {changed}")
```

unless a true runtime-stale path is also present.

- [ ] **Step 6: Run the status tests**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: PASS.

## Task 3: Align `sp-map-update` and CLI refresh commands with readiness semantics

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add a renderer for class-aware freshness guidance**

In `src/specify_cli/__init__.py`, add a helper that renders guidance from:

```python
freshness = result["freshness"]
next_action = result["recommended_next_action"]
```

and emits copy based on the combination rather than just `missing` vs `stale`.

- [ ] **Step 2: Update `_project_map_preflight()` messaging**

Refactor `_project_map_preflight()` so:

- `missing` says `sp-map-scan` then `sp-map-build`
- `stale` says `sp-map-update`
- `support_drift` does not say `sp-map-update`
- `partial_refresh` says the refresh was recorded but readiness is still blocked

Use logic shaped like:

```python
if freshness == "support_drift":
    console.print("Resolve the support-surface drift before retrying.")
elif freshness == "partial_refresh":
    console.print("Refresh data was recorded, but the runtime is still not ready.")
```

- [ ] **Step 3: Update `project-map record-refresh` and `complete-refresh` expectations**

After `mark_project_map_refreshed()` or `complete_project_map_refresh()`, keep calling `inspect_project_map_freshness(project_root)` and rely on its result instead of implying readiness from the write itself.

The command should not be changed to suppress non-ready outcomes.

- [ ] **Step 4: Add CLI assertions for class-aware copy**

In `tests/integrations/test_cli.py` and `tests/contract/test_hook_cli_surface.py`, add assertions for output or JSON payload fields such as:

```python
assert payload["recommended_next_action"] == "commit_or_ignore_support_files"
assert "sp-map-update" not in result.output.lower()
```

- [ ] **Step 5: Run the CLI and contract tests**

Run:

```bash
pytest tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

## Task 4: Update hook and debug consumers to use the richer freshness payload

**Files:**
- Modify: `src/specify_cli/hooks/project_map.py`
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`

- [ ] **Step 1: Make hook blocking class-aware**

In `src/specify_cli/hooks/project_map.py`, replace stale-only fallback strings with logic based on:

```python
state = str(freshness.get("freshness", "")).strip().lower()
next_action = str(freshness.get("recommended_next_action", "")).strip().lower()
```

and ensure support drift produces support-specific guidance.

- [ ] **Step 2: Preserve implement special-case behavior on top of the new state**

Keep the existing `implement` dirty-origin overlap logic in `src/specify_cli/hooks/preflight.py`, but ensure it only applies to true dirty runtime-stale outcomes rather than every blocked state.

Use a guard shaped like:

```python
and str(freshness_payload.get("freshness", "")).strip().lower() == "stale"
and str(freshness_payload.get("recommended_next_action", "")).strip().lower() == "run_map_update"
```

- [ ] **Step 3: Update debug preflight wording**

In `src/specify_cli/debug/cli.py`, replace stale-only language with class-aware handling:

```python
if freshness == "support_drift":
    console.print("[red]Error:[/red] Project cognition runtime has support-surface drift ...")
```

- [ ] **Step 4: Add focused hook/debug tests**

Update tests so:

- runtime stale still blocks
- support drift blocks or warns with support-specific language
- implement dirty-scope exception still works

- [ ] **Step 5: Run the hook/debug tests**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/test_project_map_hard_gate_guidance.py -q
```

Expected: PASS.

## Task 5: Keep bash and PowerShell helper parity with Python freshness semantics

**Files:**
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Add support-drift classification to bash helper**

Update `classify_path()` in `scripts/bash/project-map-freshness.sh` so support/tool-managed paths can emit:

```bash
echo "support_drift"
```

instead of unconditionally returning `stale`.

- [ ] **Step 2: Add support-drift classification to PowerShell helper**

Update `Classify-Path` in `scripts/powershell/project-map-freshness.ps1` so support/tool-managed paths return:

```powershell
return "support_drift"
```

- [ ] **Step 3: Add next-action emission to both helpers**

Extend the emitted JSON from both helpers so it includes:

```json
{
  "recommended_next_action": "commit_or_ignore_support_files"
}
```

when appropriate.

- [ ] **Step 4: Verify shell parity**

Update `tests/test_project_map_freshness_scripts.py` to compare Python-equivalent states for:

- missing
- stale
- support drift
- possibly stale

- [ ] **Step 5: Run the helper parity tests**

Run:

```bash
pytest tests/test_project_map_freshness_scripts.py -q
```

Expected: PASS.

## Task 6: Align shared workflow guidance and generated integration wording

**Files:**
- Modify: `templates/commands/map-update.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_testing_workflow_guidance.py`
- Modify: `tests/test_hook_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`

- [ ] **Step 1: Update `map-update` contract wording**

In `templates/commands/map-update.md`, add explicit language that `sp-map-update` must verify readiness after recording changes and may end in a partial outcome rather than unconditional success.

Include wording like:

```md
- After recording updates, re-evaluate runtime readiness through the shared freshness contract.
- Do not report refresh completion when the runtime remains blocked.
```

- [ ] **Step 2: Update brownfield gate wording across shared templates**

In the shared gate partial and passive skill, replace stale-only rules with state-aware rules, for example:

```md
- `support_drift` -> stop and tell the user to resolve support-surface drift; do not reflexively route to `sp-map-update`
- `partial_refresh` -> tell the user the refresh was recorded but readiness did not pass
```

- [ ] **Step 3: Update generated integration guidance**

In `src/specify_cli/integrations/base.py`, replace generic "missing, stale, or too weak" phrasing with wording that allows support drift and partial refresh to be surfaced distinctly.

- [ ] **Step 4: Update wording tests**

Adjust test expectations to assert:

```python
assert "support_drift" in content.lower()
assert "do not report refresh completion" in content.lower()
```

where appropriate.

- [ ] **Step 5: Run the guidance suite**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_hook_template_guidance.py tests/test_map_runtime_template_guidance.py -q
```

Expected: PASS.

## Task 7: Align top-level docs with the new contract

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Update README contract wording**

Document that:

- `map-update` is the primary localized refresh path
- refresh recording and refresh readiness are different outcomes
- support drift is not the same as runtime-truth staleness

- [ ] **Step 2: Update handbook guidance**

In `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`, explain the new state vocabulary and what downstream workflows should do with it.

- [ ] **Step 3: Update doc tests**

Adjust tests so they assert the new contract, for example:

```python
assert "recorded refresh and ready refresh" in readme.lower()
assert "support drift" in handbook.lower()
```

- [ ] **Step 4: Run the doc suite**

Run:

```bash
pytest tests/test_specify_guidance_docs.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

## Task 8: Run the full targeted verification pass

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-project-cognition-refresh-contract-implementation.md`

- [ ] **Step 1: Run the full targeted test batch**

Run:

```bash
pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/hooks/test_preflight_hooks.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_hook_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_specify_guidance_docs.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

- [ ] **Step 2: Run one source-aware smoke command**

Run:

```bash
$env:PYTHONPATH='src'; python -m specify_cli project-map check --format json
```

Expected: JSON output including `freshness` and `recommended_next_action`.

- [ ] **Step 3: Review the diff before committing**

Run:

```bash
git diff -- src/specify_cli/project_map_status.py src/specify_cli/hooks/project_map.py src/specify_cli/hooks/preflight.py src/specify_cli/__init__.py src/specify_cli/debug/cli.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/commands/map-update.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/debug.md templates/commands/test-scan.md templates/commands/test-build.md templates/commands/checklist.md templates/commands/quick.md templates/command-partials/common/context-loading-gradient.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md src/specify_cli/integrations/base.py README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md
```

Expected: Only the planned contract, guidance, and parity changes appear.

- [ ] **Step 4: Commit**

```bash
git add src/specify_cli/project_map_status.py src/specify_cli/hooks/project_map.py src/specify_cli/hooks/preflight.py src/specify_cli/__init__.py src/specify_cli/debug/cli.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/commands/map-update.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/debug.md templates/commands/test-scan.md templates/commands/test-build.md templates/commands/checklist.md templates/commands/quick.md templates/command-partials/common/context-loading-gradient.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md src/specify_cli/integrations/base.py README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/hooks/test_preflight_hooks.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_hook_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_specify_guidance_docs.py tests/test_command_surface_semantics.py docs/superpowers/plans/2026-05-10-project-cognition-refresh-contract-implementation.md
git commit -m "fix: align project cognition refresh readiness contract"
```

---

## Self-Review

- Spec coverage:
  - shared completion contract -> Tasks 2 and 3
  - freshness input model -> Tasks 1, 2, and 5
  - state + next-action separation -> Tasks 2, 3, and 4
  - shared guidance consistency -> Tasks 6 and 7
  - regression protection -> Tasks 1 and 8
- Placeholder scan:
  - No `TBD`, `TODO`, or "implement later" placeholders remain.
  - Every task names exact files and exact commands.
- Type consistency:
  - Plan consistently uses `freshness` for the factual state field and `recommended_next_action` for the action field.
  - Plan consistently uses `support_drift` and `partial_refresh` as new state names.
