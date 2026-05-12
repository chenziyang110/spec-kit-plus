# Project Cognition Surface Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the in-flight `project-cognition` freshness / inventory / hook / CLI migration into its own clean implementation lane so it can ship independently from the `sp-implement` wave-budget contract.

**Architecture:** Treat this as a shared runtime migration, not a wording-only patch. The implementation should align the Python freshness/status APIs, the hook shim layer, the CLI command surface, inventory expectations, and generated guidance so every consumer either reads `project-cognition` as the primary runtime truth surface or intentionally remains a compatibility alias. The plan keeps this chain separate from the already-isolated wave-budget commit.

**Tech Stack:** Python, Typer CLI, hook adapters, Markdown workflow templates, pytest

---

## Scope Check

This work must stay in a separate implementation lane from the wave-budget
change because it touches:

- the shared `project-cognition` CLI and hook surface
- status-contract parsing and compatibility shims
- inventory baselines and generated asset expectations
- workflow guidance and template assertions

Bundling it with `sp-implement` wave-budget behavior would create a mixed
history that is harder to review and revert.

## File Structure

### Runtime and compatibility surfaces

- `src/specify_cli/__init__.py`
  - CLI command registration and preflight rendering for `project-cognition`
    versus `project-map`.
- `src/specify_cli/cognition/status.py`
  - Parsed status contract for `.specify/project-cognition/status.json`.
- `src/specify_cli/project_cognition_status.py`
  - Primary freshness and status helpers for the graph-native runtime.
- `src/specify_cli/project_map_status.py`
  - Compatibility shim or adapter surface; should no longer own the primary
    implementation when the new runtime helper exists.
- `src/specify_cli/hooks/project_cognition.py`
  - First-party hook entrypoint for cognition freshness validation.
- `src/specify_cli/hooks/project_map.py`
  - Compatibility shim that should route to `project_cognition` behavior.
- `src/specify_cli/hooks/preflight.py`
  - Shared brownfield workflow gate consuming the refreshed cognition hook.

### Template and guidance surfaces

- `templates/commands/tasks.md`
- `templates/commands/plan.md`
- `templates/commands/specify.md`
- `templates/commands/map-update.md`
- `tests/test_alignment_templates.py`
- `tests/test_map_runtime_template_guidance.py`
- `tests/test_project_map_hard_gate_guidance.py`

These files should consistently describe:

- `project-cognition` as the primary runtime truth surface
- `project-map` as compatibility/export or alias behavior where applicable
- class-aware freshness guidance instead of stale-only language

### Inventory and integration expectations

- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_claude.py`
- `tests/integrations/test_integration_codex.py`

These files should treat `.specify/project-cognition/status.json` as part of
the expected generated inventory only when the runtime actually installs it in
the tested lane.

### Freshness and status regression tests

- `tests/test_project_map_status.py`
- `tests/hooks/test_preflight_hooks.py`
- `tests/contract/test_hook_cli_surface.py`

These files should verify:

- the new primary helper behavior
- the compatibility alias behavior
- the hook-surface naming and routing

### Approved design and reference inputs

- `docs/superpowers/specs/2026-05-10-project-cognition-refresh-contract-design.md`
- `docs/superpowers/specs/2026-05-11-cross-project-project-cognition-reference-design.md`
- `docs/superpowers/plans/2026-05-10-project-cognition-refresh-contract-implementation.md`
- `docs/superpowers/plans/2026-05-11-cross-project-project-cognition-reference-implementation.md`

---

### Task 1: Lock the separation boundary with failing tests

**Files:**
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add a failing test that `project_cognition_status` is the primary helper surface**

Add a regression to `tests/test_project_map_status.py`:

```python
def test_project_map_status_module_is_compatibility_surface_only() -> None:
    from specify_cli import project_map_status as compat
    from specify_cli import project_cognition_status as primary

    assert hasattr(primary, "inspect_project_cognition_freshness")
    assert hasattr(primary, "inspect_project_cognition_freshness_for_command")
    assert hasattr(compat, "inspect_project_map_freshness")
```
```python
def test_project_map_status_alias_matches_primary_cognition_freshness(tmp_path: Path) -> None:
    from specify_cli.project_cognition_status import inspect_project_cognition_freshness
    from specify_cli.project_map_status import inspect_project_map_freshness

    _write_cognition_baseline(tmp_path)

    primary = inspect_project_cognition_freshness(tmp_path)
    alias = inspect_project_map_freshness(tmp_path)

    assert alias["freshness"] == primary["freshness"]
    assert alias["state"] == primary["state"]
```

- [ ] **Step 2: Add a failing hook-surface alias test**

Extend `tests/test_project_map_hard_gate_guidance.py` or
`tests/hooks/test_preflight_hooks.py` with:

```python
def test_project_map_hook_alias_uses_project_cognition_surface(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    def fake_result(project_root: Path, *, command_name: str):
        seen.append(command_name)
        return HookResult(event="project_cognition.refresh.validate", status="ok")

    monkeypatch.setattr("specify_cli.hooks.project_cognition.project_cognition_freshness_result", fake_result)
    from specify_cli.hooks.project_map import project_map_freshness_result

    result = project_map_freshness_result(tmp_path, command_name="implement")
    assert result.status == "ok"
    assert seen == ["implement"]
```

- [ ] **Step 3: Add failing inventory assertions for cognition status only where installed**

Update inventory tests so they fail unless the generated asset set and the
expected list agree on `.specify/project-cognition/status.json`.

Use assertions such as:

```python
assert ".specify/project-cognition/status.json" in expected
```

only after verifying the generated asset set includes the file in the tested
lane.

- [ ] **Step 4: Run the focused red suite**

Run:

```bash
pytest tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected: FAIL because the primary/alias boundary and inventory expectations are
not fully aligned yet.

- [ ] **Step 5: Commit the RED state test changes**

```bash
git add tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py
git commit -m "test: lock project cognition surface separation"
```

### Task 2: Move primary freshness ownership to `project_cognition_status`

**Files:**
- Modify: `src/specify_cli/project_cognition_status.py`
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/cognition/status.py`
- Test: `tests/test_project_map_status.py`

- [ ] **Step 1: Audit the primary helper API surface**

Run:

```bash
rg -n "inspect_project_cognition_freshness|inspect_project_map_freshness|ProjectMapStatus|TOPIC_FILES" src/specify_cli/project_cognition_status.py src/specify_cli/project_map_status.py
```

Expected:

```text
Identify which functions must live in `project_cognition_status.py` as the primary implementation and which names remain compatibility exports.
```

- [ ] **Step 2: Make `project_map_status.py` a true compatibility shim**

Refactor `src/specify_cli/project_map_status.py` to a small forwarding surface
such as:

```python
"""Compatibility shim for project cognition status helpers."""

from __future__ import annotations

from .project_cognition_status import *  # noqa: F401,F403
```

If wildcard export is too broad for lint or test expectations, use explicit
re-exports:

```python
from .project_cognition_status import (
    ProjectMapStatus,
    TOPIC_FILES,
    inspect_project_cognition_freshness as inspect_project_map_freshness,
    inspect_project_cognition_freshness_for_command as inspect_project_map_freshness_for_command,
    ...
)
```

- [ ] **Step 3: Ensure `CognitionStatus` can parse the runtime metadata fields used by the new helper**

In `src/specify_cli/cognition/status.py`, add or confirm fields and parsing for:

```python
freshness: str = ""
dirty: bool = False
dirty_reasons: list[str] = field(default_factory=list)
last_refresh_reason: str = ""
last_refresh_scope: str = ""
last_refresh_basis: str = ""
```

and any matching read logic needed by the primary helper.

- [ ] **Step 4: Run the status regression suite**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the primary/helper split**

```bash
git add src/specify_cli/project_cognition_status.py src/specify_cli/project_map_status.py src/specify_cli/cognition/status.py tests/test_project_map_status.py
git commit -m "refactor: separate project cognition status ownership"
```

### Task 3: Align hooks and CLI aliases to the new primary surface

**Files:**
- Modify: `src/specify_cli/hooks/project_cognition.py`
- Modify: `src/specify_cli/hooks/project_map.py`
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/hooks/test_preflight_hooks.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Make `project_map` hooks route through `project_cognition`**

In `src/specify_cli/hooks/project_map.py`, reduce the module to a compatibility
shim:

```python
"""Compatibility shim for project cognition hooks."""

from .project_cognition import *  # noqa: F401,F403
```

- [ ] **Step 2: Make preflight call the primary cognition hook**

In `src/specify_cli/hooks/preflight.py`, use:

```python
from .project_cognition import project_cognition_freshness_result
```

and replace:

```python
freshness = project_map_freshness_result(project_root, command_name=command_name)
```

with:

```python
freshness = project_cognition_freshness_result(project_root, command_name=command_name)
```

- [ ] **Step 3: Add explicit `project-cognition` CLI registration and keep `project-map` as compatibility alias**

In `src/specify_cli/__init__.py`, add a dedicated Typer group:

```python
project_cognition_app = typer.Typer(
    name="project-cognition",
    help="Inspect project cognition freshness and finalize or override refresh state",
    add_completion=False,
)
app.add_typer(project_cognition_app, name="project-cognition")
```

Then keep:

```python
project_map_app = typer.Typer(
    name="project-map",
    help="Compatibility alias for project-cognition commands",
    add_completion=False,
)
```

- [ ] **Step 4: Ensure both command groups call the primary freshness helpers**

Update the command handlers so they call:

```python
inspect_project_cognition_freshness(...)
inspect_project_cognition_freshness_for_command(...)
```

while preserving the `project-map` compatibility entrypoint names.

- [ ] **Step 5: Run hook and CLI contract tests**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the hook/CLI alias alignment**

```bash
git add src/specify_cli/hooks/project_cognition.py src/specify_cli/hooks/project_map.py src/specify_cli/hooks/preflight.py src/specify_cli/__init__.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: add project cognition alias surface"
```

### Task 4: Align template and inventory guidance to the primary runtime truth surface

**Files:**
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/map-update.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Replace stale `project-map freshness helper` wording with `project cognition freshness helper` where the new runtime truth surface is intended**

Use exact edits like:

```markdown
- If it exists, use the project cognition freshness helper for the active script variant to assess freshness before trusting the current project cognition baseline.
```

- [ ] **Step 2: Add inventory expectations for `.specify/project-cognition/status.json` only where the generated lane actually installs it**

In the integration inventory tests, add:

```python
".specify/project-cognition/status.json",
```

to the expected lists only after verifying the generated project under test now
contains that file in practice.

- [ ] **Step 3: Add or update template assertions for the new wording**

In `tests/test_alignment_templates.py`, use assertions like:

```python
assert "project cognition freshness helper" in lowered
assert "mark `.specify/project-map/index/status.json` dirty through the project cognition freshness helper" in lowered
```

- [ ] **Step 4: Run the template/inventory guidance suite**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the guidance and inventory alignment**

```bash
git add templates/commands/tasks.md templates/commands/plan.md templates/commands/specify.md templates/commands/map-update.md tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py
git commit -m "docs: align project cognition runtime guidance"
```

### Task 5: Record verification and produce the clean separation branch

**Files:**
- Modify: `docs/superpowers/plans/2026-05-11-project-cognition-surface-separation.md`

- [ ] **Step 1: Run the focused end-to-end suite**

Run:

```bash
pytest tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Record the exact verification notes**

```markdown
## Verification Notes

- `pytest tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q`
- Confirmed `project_cognition_status.py` is the primary freshness helper surface.
- Confirmed `project_map_status.py` and `hooks/project_map.py` act as compatibility shims.
- Confirmed CLI and generated guidance consistently describe `project-cognition` as the runtime truth surface.
- Confirmed generated inventory expectations match the installed `.specify/project-cognition/status.json` asset set.
```

- [ ] **Step 3: Commit the verification note update**

```bash
git add docs/superpowers/plans/2026-05-11-project-cognition-surface-separation.md
git commit -m "docs: record project cognition surface verification"
```

## Self-Review Notes

### Spec coverage

- Primary freshness ownership split: covered by Task 2.
- Hook and CLI aliasing: covered by Task 3.
- Inventory and guidance alignment: covered by Task 4.
- End-to-end regression verification: covered by Task 5.

### Placeholder scan

- No `TODO`, `TBD`, or deferred implementation placeholders remain.
- Every code-changing task points to exact files and concrete code or command targets.

### Type and naming consistency

- Primary surface name is `project-cognition`.
- Compatibility surface name is `project-map`.
- The plan consistently treats `project_map_status.py` and `hooks/project_map.py` as compatibility shims once the new surface is active.
