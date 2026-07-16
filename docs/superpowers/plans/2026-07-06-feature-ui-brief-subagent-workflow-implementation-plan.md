# Feature UI Brief Subagent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship feature-scoped UI reference intake so `sp-specify` can turn screenshots, HTML, UI code, and visual references into worker-ready UI contracts with verification gates.

**Architecture:** Add a narrow writable UI reference lane to the orchestration policy, then add generated artifact templates and workflow guidance that carry `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html` through `sp-specify -> sp-plan -> sp-tasks -> sp-implement`. Extend worker packet/result contracts so UI implementation packets and closeout evidence can be structured instead of prose-only.

**Tech Stack:** Python 3.11+, dataclasses, Literal types, Markdown templates, JSON task packet schemas, pytest, existing Specify integration renderers.

---

## Source Spec

Implement the approved design spec:

`docs/superpowers/specs/2026-07-06-feature-ui-brief-subagent-workflow-design.md`

Preserve these locks:

- `DESIGN.md` remains the project-wide design-system contract.
- `ui-brief.md` is the feature-scoped UI implementation contract.
- UI reference input is handled by a subagent lane during `sp-specify`.
- The UI reference lane is writable but may write only `FEATURE_DIR/ui-reference-notes.md`, `FEATURE_DIR/ui-brief.md`, and optional `FEATURE_DIR/ui-target.html`.
- The UI reference lane is not the existing read-only evidence lane.
- `approximate` is the default fidelity mode.
- `approximate` and `high` UI reference inputs activate the existing `Reference-Implementation` profile.
- `inspiration` does not activate `Reference-Implementation` by default.
- `ui-target.html` is a disposable visual target, not production source.
- Agent verification is preferred; human review is required only when agent visual comparison is unavailable, inconclusive, failed, or explicitly requested.

## Scope Check

This is one implementation slice. It touches several surfaces, but they belong to one workflow chain:

1. Orchestration capability decision.
2. Generated workflow artifact contracts.
3. Worker packet propagation.
4. Verification closeout guidance.

Do not split into separate feature branches unless review finds a hard sequencing blocker.

## File Structure

Create:

```text
templates/ui-reference-notes-template.md
templates/ui-brief-template.md
templates/ui-target-template.html
```

Modify:

```text
pyproject.toml
src/specify_cli/orchestration/models.py
src/specify_cli/orchestration/policy.py
src/specify_cli/orchestration/__init__.py
src/specify_cli/integrations/base.py
src/specify_cli/execution/packet_schema.py
src/specify_cli/execution/packet_compiler.py
src/specify_cli/execution/result_schema.py
src/specify_cli/execution/result_validator.py
templates/command-partials/specify/shell.md
templates/commands/specify.md
templates/spec-template.md
templates/alignment-template.md
templates/context-template.md
templates/workflow-state-template.md
templates/plan-template.md
templates/commands/plan.md
templates/tasks-template.md
templates/commands/tasks.md
templates/task-packet-template.json
templates/commands/implement.md
templates/worker-prompts/implementer.md
templates/passive-skills/spec-kit-ui-design/SKILL.md
templates/passive-skills/spec-kit-workflow-routing/SKILL.md
README.md
PROJECT-HANDBOOK.md
templates/project-handbook-template.md
tests/orchestration/test_models.py
tests/orchestration/test_policy.py
tests/execution/test_packet_schema.py
tests/execution/test_packet_compiler.py
tests/execution/test_result_validator.py
tests/test_packaging_assets.py
tests/test_alignment_templates.py
tests/test_command_surface_semantics.py
tests/test_passive_skill_guidance.py
tests/test_specify_guidance_docs.py
tests/test_project_handbook_templates.py
tests/integrations/test_base.py
tests/integrations/test_integration_base_markdown.py
tests/integrations/test_integration_base_toml.py
tests/integrations/test_integration_base_skills.py
tests/integrations/test_integration_codex.py
```

If implementation reveals an explicit generated-file inventory test for Copilot, Generic, Claude, or other integrations failing because the new templates are copied into `.specify/templates`, update that inventory test in the same task that makes the generated asset surface change.

## Working Tree Discipline

- Use worktree `F:\github\spec-kit-plus\.worktrees\ui-design-workflow-implementation`.
- Run `git status --short` before each task.
- Stage only files for the active task.
- Do not edit unrelated dirty files in the main worktree.
- Commit after each task.

---

### Task 1: Add Failing Orchestration Tests For Writable UI Reference Lane

**Files:**
- Modify: `tests/orchestration/test_models.py`
- Modify: `tests/orchestration/test_policy.py`

- [ ] **Step 1: Establish baseline**

Run:

```powershell
git status --short
python -m pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py -q
```

Expected: existing tests pass before adding new assertions.

- [ ] **Step 2: Add model tests for the UI reference lane contract**

In `tests/orchestration/test_models.py`, extend the imports:

```python
from typing import get_args

from specify_cli.orchestration.models import EvidenceLaneMode
```

If the file already imports from `specify_cli.orchestration.models`, add `EvidenceLaneMode` to that import instead of creating a duplicate import block.

Add these tests near `test_evidence_lane_decision_has_read_only_contract_defaults`:

```python
def test_evidence_lane_mode_includes_writable_ui_reference_artifact_contract():
    assert "read-only-evidence" in get_args(EvidenceLaneMode)
    assert "ui-reference-artifact" in get_args(EvidenceLaneMode)


def test_ui_reference_lane_decision_defaults_to_narrow_artifact_write_contract():
    decision = EvidenceLaneDecision(
        command_name="specify",
        dispatch_shape="one-subagent",
        reason="ui-reference-artifact-one-subagent",
        execution_surface="native-subagents",
        lane_mode="ui-reference-artifact",
    )

    assert decision.lane_mode == "ui-reference-artifact"
    assert decision.structured_result == "ui_reference_artifacts"
    assert "file-read" in decision.allowed_operations
    assert "ui-reference-notes-write" in decision.allowed_operations
    assert "ui-brief-write" in decision.allowed_operations
    assert "ui-target-html-write" in decision.allowed_operations
    assert "source-code-write" in decision.forbidden_operations
    assert "test-write" in decision.forbidden_operations
    assert "app-server" in decision.forbidden_operations
    assert "package-managers" in decision.forbidden_operations
    assert "file-write" not in decision.allowed_operations
```

- [ ] **Step 3: Add policy tests for UI reference dispatch**

In `tests/orchestration/test_policy.py`, extend the import from `specify_cli.orchestration.policy` to include `choose_ui_reference_lane_dispatch`.

Add these tests after the existing read-only evidence lane tests:

```python
def test_ui_reference_lane_routes_to_one_subagent_when_contract_ready() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "approximate",
        },
    )

    assert decision.command_name == "specify"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "ui-reference-artifact-one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.workflow_status == "ready"
    assert decision.lane_mode == "ui-reference-artifact"
    assert decision.structured_result == "ui_reference_artifacts"


def test_ui_reference_lane_blocks_approximate_when_native_subagents_unavailable() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "approximate",
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "ui-reference-artifact-subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "UI reference artifact lane requires native subagents for approximate fidelity"


def test_ui_reference_lane_allows_inspiration_inline_soft_risk_without_native_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "inspiration",
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "ui-reference-artifact-inspiration-inline-soft-risk"
    assert decision.execution_surface == "leader-inline"
    assert decision.workflow_status == "ready"
    assert decision.capability_degraded is True
    assert decision.lane_mode == "ui-reference-artifact"


def test_ui_reference_lane_uses_parallel_subagents_for_multiple_safe_lanes() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 3,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "high",
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "ui-reference-artifact-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
```

- [ ] **Step 4: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/orchestration/test_models.py::test_evidence_lane_mode_includes_writable_ui_reference_artifact_contract tests/orchestration/test_models.py::test_ui_reference_lane_decision_defaults_to_narrow_artifact_write_contract tests/orchestration/test_policy.py::test_ui_reference_lane_routes_to_one_subagent_when_contract_ready tests/orchestration/test_policy.py::test_ui_reference_lane_blocks_approximate_when_native_subagents_unavailable tests/orchestration/test_policy.py::test_ui_reference_lane_allows_inspiration_inline_soft_risk_without_native_subagents tests/orchestration/test_policy.py::test_ui_reference_lane_uses_parallel_subagents_for_multiple_safe_lanes -q
```

Expected: failures for missing `ui-reference-artifact` mode and missing `choose_ui_reference_lane_dispatch`.

- [ ] **Step 5: Commit failing tests**

Run:

```powershell
git add tests/orchestration/test_models.py tests/orchestration/test_policy.py
git commit -m "test: cover writable ui reference lane"
```

---

### Task 2: Implement Writable UI Reference Lane Policy

**Files:**
- Modify: `src/specify_cli/orchestration/models.py`
- Modify: `src/specify_cli/orchestration/policy.py`
- Modify: `src/specify_cli/orchestration/__init__.py`
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/orchestration/test_models.py`
- Test: `tests/orchestration/test_policy.py`
- Test: `tests/integrations/test_base.py`

- [ ] **Step 1: Add lane mode and operation defaults**

In `src/specify_cli/orchestration/models.py`, change:

```python
EvidenceLaneMode = Literal["read-only-evidence"]
```

to:

```python
EvidenceLaneMode = Literal["read-only-evidence", "ui-reference-artifact"]

READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS: tuple[str, ...] = (
    "file-read",
    "rg",
    "project-cognition",
    "memory-read",
    "state-read",
    "docs-read",
    "template-read",
)
READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS: tuple[str, ...] = (
    "file-write",
    "state-write",
    "handoff-write",
    "tests",
    "builds",
    "package-managers",
    "project-cli",
    "app-server",
)
UI_REFERENCE_ALLOWED_OPERATIONS: tuple[str, ...] = (
    "file-read",
    "rg",
    "project-cognition",
    "memory-read",
    "state-read",
    "docs-read",
    "template-read",
    "reference-input-read",
    "ui-reference-notes-write",
    "ui-brief-write",
    "ui-target-html-write",
)
UI_REFERENCE_FORBIDDEN_OPERATIONS: tuple[str, ...] = (
    "source-code-write",
    "test-write",
    "app-style-write",
    "component-implementation-write",
    "broad-state-write",
    "handoff-readiness-write",
    "tests",
    "builds",
    "package-managers",
    "project-cli",
    "app-server",
)
```

Change `EvidenceLaneDecision.allowed_operations` and `forbidden_operations` defaults to use the read-only constants:

```python
    allowed_operations: tuple[str, ...] = READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS
    forbidden_operations: tuple[str, ...] = READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS
```

At the top of `EvidenceLaneDecision.__post_init__`, before dispatch normalization, add:

```python
        if self.lane_mode == "ui-reference-artifact":
            if self.structured_result == "evidence_packet":
                object.__setattr__(self, "structured_result", "ui_reference_artifacts")
            if self.allowed_operations == READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS:
                object.__setattr__(self, "allowed_operations", UI_REFERENCE_ALLOWED_OPERATIONS)
            if self.forbidden_operations == READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS:
                object.__setattr__(self, "forbidden_operations", UI_REFERENCE_FORBIDDEN_OPERATIONS)
```

- [ ] **Step 2: Add policy function**

In `src/specify_cli/orchestration/policy.py`, near the evidence lane constants, add:

```python
_SAFE_UI_REFERENCE_LANE_COUNT_KEYS = (
    "safe_ui_reference_lanes",
    "ui_reference_lanes",
    "ui_reference_lane_count",
)
_UI_REFERENCE_CONTRACT_READY_KEYS = (
    "ui_reference_contract_ready",
    "ui_reference_artifact_contract_ready",
)
_UI_REFERENCE_REQUIRED_KEYS = (
    "ui_reference_required",
    "ui_reference_input_present",
)
```

After `choose_evidence_lane_dispatch`, add:

```python
def choose_ui_reference_lane_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> EvidenceLaneDecision:
    """Choose the writable UI-reference artifact lane for sp-specify UI reference intake."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_UI_REFERENCE_LANE_COUNT_KEYS) or 0
    contract_ready = _get_shape_flag(shape, _UI_REFERENCE_CONTRACT_READY_KEYS, default=False)
    required = _any_shape_flag(shape, _UI_REFERENCE_REQUIRED_KEYS)
    fidelity_mode = str(shape.get("fidelity_mode", "approximate")).strip().lower() or "approximate"
    inline_fallback_approved = _get_shape_flag(
        shape,
        ("inline_fallback_approved", "user_approved_inline_fallback"),
        default=False,
    )
    native_available = _native_subagents_available(snapshot, shape)
    strict_fidelity = fidelity_mode in {"approximate", "high"}

    def _leader_inline(reason: str, *, capability_degraded: bool = False) -> EvidenceLaneDecision:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="leader-inline",
            reason=reason,
            execution_surface="leader-inline",
            capability_degraded=capability_degraded,
            lane_mode="ui-reference-artifact",
        )

    def _blocked(reason: str) -> EvidenceLaneDecision:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="subagent-blocked",
            reason="ui-reference-artifact-subagent-blocked",
            execution_surface="none",
            workflow_status="blocked",
            blocked_reason=reason,
            lane_mode="ui-reference-artifact",
        )

    if fidelity_mode == "inspiration" and not native_available:
        return _leader_inline("ui-reference-artifact-inspiration-inline-soft-risk", capability_degraded=True)

    if safe_lanes < 1:
        if required and (strict_fidelity and not inline_fallback_approved):
            return _blocked(f"UI reference artifact lane requires a safe lane for {fidelity_mode} fidelity")
        return _leader_inline("ui-reference-artifact-leader-inline-no-safe-lane")

    if not contract_ready:
        if required and (strict_fidelity and not inline_fallback_approved):
            return _blocked("UI reference artifact lane contract is not ready")
        return _leader_inline("ui-reference-artifact-leader-inline-contract-missing")

    if not native_available:
        if strict_fidelity and not inline_fallback_approved:
            return _blocked(f"UI reference artifact lane requires native subagents for {fidelity_mode} fidelity")
        return _leader_inline("ui-reference-artifact-native-unavailable-inline-approved", capability_degraded=True)

    if safe_lanes > 1:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="parallel-subagents",
            reason="ui-reference-artifact-parallel-subagents",
            execution_surface="native-subagents",
            lane_mode="ui-reference-artifact",
        )

    return EvidenceLaneDecision(
        command_name=command_name,
        dispatch_shape="one-subagent",
        reason="ui-reference-artifact-one-subagent",
        execution_surface="native-subagents",
        lane_mode="ui-reference-artifact",
    )
```

- [ ] **Step 3: Export the policy API**

In `src/specify_cli/orchestration/__init__.py`, import and export `choose_ui_reference_lane_dispatch`.

Change:

```python
from .policy import choose_evidence_lane_dispatch, choose_subagent_dispatch
```

to:

```python
from .policy import choose_evidence_lane_dispatch, choose_subagent_dispatch, choose_ui_reference_lane_dispatch
```

Add `"choose_ui_reference_lane_dispatch"` to `__all__`.

- [ ] **Step 4: Update integration subagent discovery trigger**

In `src/specify_cli/integrations/base.py`, add `"choose_ui_reference_lane_dispatch"` to `SUBAGENT_DISCOVERY_TRIGGERS`.

- [ ] **Step 5: Add export test**

In `tests/orchestration/test_models.py`, extend `test_orchestration_exports_evidence_lane_policy_api`:

```python
    assert callable(orchestration.choose_ui_reference_lane_dispatch)
```

In `tests/integrations/test_base.py`, update the public orchestration helper allowlist if it asserts exact helper names. Add:

```python
"choose_ui_reference_lane_dispatch",
```

next to `"choose_evidence_lane_dispatch"`.

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/integrations/test_base.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/specify_cli/orchestration/models.py src/specify_cli/orchestration/policy.py src/specify_cli/orchestration/__init__.py src/specify_cli/integrations/base.py tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/integrations/test_base.py
git commit -m "feat: add writable ui reference lane policy"
```

---

### Task 3: Add UI Artifact Format Templates And Packaging

**Files:**
- Create: `templates/ui-reference-notes-template.md`
- Create: `templates/ui-brief-template.md`
- Create: `templates/ui-target-template.html`
- Modify: `pyproject.toml`
- Modify: `tests/test_packaging_assets.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing packaging assertions**

In `tests/test_packaging_assets.py`, add:

```python
def test_ui_reference_artifact_templates_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    assert '"templates/ui-reference-notes-template.md" = "specify_cli/core_pack/templates/ui-reference-notes-template.md"' in pyproject
    assert '"templates/ui-brief-template.md" = "specify_cli/core_pack/templates/ui-brief-template.md"' in pyproject
    assert '"templates/ui-target-template.html" = "specify_cli/core_pack/templates/ui-target-template.html"' in pyproject
```

In `test_install_shared_infra_copies_split_core_pack_template_dirs`, add these fixture files before calling `_install_shared_infra(...)`:

```python
    (core_pack / "templates" / "ui-reference-notes-template.md").write_text("# UI Reference Notes\n", encoding="utf-8")
    (core_pack / "templates" / "ui-brief-template.md").write_text("# UI Brief\n", encoding="utf-8")
    (core_pack / "templates" / "ui-target-template.html").write_text("<!doctype html>\n", encoding="utf-8")
```

Add assertions near the other `.specify/templates` assertions:

```python
    assert (project_root / ".specify" / "templates" / "ui-reference-notes-template.md").exists()
    assert (project_root / ".specify" / "templates" / "ui-brief-template.md").exists()
    assert (project_root / ".specify" / "templates" / "ui-target-template.html").exists()
```

- [ ] **Step 2: Add failing semantic assertions**

In `tests/test_alignment_templates.py`, add:

```python
def test_ui_reference_artifact_templates_define_strict_formats() -> None:
    notes = _read("templates/ui-reference-notes-template.md")
    brief = _read("templates/ui-brief-template.md")
    target = _read("templates/ui-target-template.html")

    for heading in (
        "## Reference Inputs",
        "## Fidelity Mode",
        "## Ownership And Reuse Constraints",
        "## Visual Facts",
        "## Layout Facts",
        "## Density And Visible Data",
        "## Component Facts",
        "## State Facts",
        "## Interaction Facts",
        "## Responsive Facts",
        "## Must Preserve Candidates",
        "## Adaptation Candidates",
        "## Risks And Gaps",
    ):
        assert heading in notes

    for heading in (
        "## Source Design System",
        "## Reference Inputs",
        "## Fidelity Contract",
        "## Screen Structure",
        "## Information Hierarchy",
        "## Components And States",
        "## Interactions",
        "## Responsive Behavior",
        "## Accessibility And Keyboard Requirements",
        "## Must Preserve",
        "## May Adapt",
        "## Must Not",
        "## Required Evidence",
        "## Worker Contract",
    ):
        assert heading in brief

    assert "<!doctype html>" in target.lower()
    assert 'data-ui-target="' in target
    assert 'data-fidelity="approximate"' in target
    assert 'data-viewport="desktop-1440"' in target
    assert 'data-viewport="mobile-390"' in target
    assert 'data-state="empty"' in target
    assert 'data-state="error"' in target
    assert "No external dependencies" in target
    assert "not production code" in target
    assert "https://" not in target
    assert "cdn" not in target.lower()
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/test_packaging_assets.py::test_ui_reference_artifact_templates_are_packaged tests/test_alignment_templates.py::test_ui_reference_artifact_templates_define_strict_formats -q
```

Expected: failures for missing package entries and missing template files.

- [ ] **Step 4: Add package entries**

In `pyproject.toml`, add these force-includes after `templates/tasks-template.md` and before `templates/task-index-template.json`:

```toml
"templates/ui-reference-notes-template.md" = "specify_cli/core_pack/templates/ui-reference-notes-template.md"
"templates/ui-brief-template.md" = "specify_cli/core_pack/templates/ui-brief-template.md"
"templates/ui-target-template.html" = "specify_cli/core_pack/templates/ui-target-template.html"
```

- [ ] **Step 5: Create `ui-reference-notes-template.md`**

Create `templates/ui-reference-notes-template.md` with:

```markdown
# UI Reference Notes

## Reference Inputs

- Source:
- Type: screenshot | html | code | url | notes
- Ownership: user-owned | project-owned | third-party | unknown

## Fidelity Mode

- Mode: approximate | high | inspiration
- User confirmation:
- Inline fallback status: subagent-owned | user-approved-inline-fallback | blocked

## Ownership And Reuse Constraints

- May reuse source code: no
- May copy brand expression: no
- May preserve layout and density:
- Must avoid:

## Visual Facts

- Color and contrast:
- Typography and scale:
- Visual rhythm:

## Layout Facts

- Regions:
- Region proportions:
- Navigation and containment:

## Density And Visible Data

- Visible item count:
- Visible column or field count:
- Control density:
- Information priority:

## Component Facts

- Components:
- Component variants:
- Component reuse candidates:

## State Facts

- Loading:
- Empty:
- Error:
- Selected:
- Disabled:
- Permission-limited:

## Interaction Facts

- Primary interactions:
- Secondary interactions:
- Feedback behavior:

## Responsive Facts

- Desktop behavior:
- Narrow/mobile behavior:
- Resize risks:

## Must Preserve Candidates

- Layout:
- Information hierarchy:
- Density:
- Interaction:

## Adaptation Candidates

- Icons:
- Copy:
- Framework-specific markup:
- Minor spacing:

## Risks And Gaps

- Missing reference states:
- Ambiguous visual decisions:
- Human review needs:
```

- [ ] **Step 6: Create `ui-brief-template.md`**

Create `templates/ui-brief-template.md` with:

```markdown
# UI Brief

## Source Design System

- Root design system: DESIGN.md
- Relevant rules:
- Token and component constraints:

## Reference Inputs

- UI reference notes: ui-reference-notes.md
- Visual target: ui-target.html when present
- Ownership:

## Fidelity Contract

- Mode: approximate | high | inspiration
- Must match:
- May adapt:
- Must not copy:
- Human review condition:

## Screen Structure

- Layout:
- Regions:
- Navigation:
- Primary surface:

## Information Hierarchy

- First priority:
- Second priority:
- Supporting details:
- De-emphasized details:

## Components And States

- Components:
- Loading:
- Empty:
- Error:
- Selected:
- Disabled:
- Permission-limited:
- Success or failure feedback:

## Interactions

- Primary flow:
- Secondary flow:
- Keyboard and focus path:
- Feedback timing:

## Responsive Behavior

- Desktop or primary viewport:
- Mobile or narrow viewport:
- Overflow behavior:

## Accessibility And Keyboard Requirements

- Semantic structure:
- Focus visibility:
- Keyboard operation:
- Contrast intent:

## Must Preserve

- Layout structure:
- Information hierarchy:
- Component density:
- Visible data volume:
- Primary interactions:

## May Adapt

- Exact icons:
- Minor spacing:
- Copy:
- Framework-specific markup:

## Must Not

- Reinterpret the layout into a different pattern.
- Replace dense tables or workbench views with cards unless explicitly allowed.
- Add decorative gradients, hero sections, or unrelated visual treatment.
- Copy third-party source code or protected brand expression.
- Treat ui-target.html as production source.

## Required Evidence

- Desktop or primary-width screenshot:
- Mobile or narrow-width screenshot:
- Key state screenshots or captures:
- Keyboard and focus check:
- Browser console check for web UI:
- Accessibility check when interactive:
- Human review requirement:

## Worker Contract

- Required references:
- Required packet fields:
- Done condition:
- Stop and reopen condition:
```

- [ ] **Step 7: Create `ui-target-template.html`**

Create `templates/ui-target-template.html` with:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>UI Target - Feature</title>
  <style>
    /* Local CSS only. No external dependencies. This file is a disposable visual target, not production code. */
    :root {
      color-scheme: light;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #ffffff;
      color: #111827;
    }
    body {
      margin: 0;
      padding: 24px;
      background: #f6f7f9;
    }
    main {
      display: grid;
      gap: 24px;
    }
    section {
      border: 1px solid #d8dee8;
      background: #ffffff;
      padding: 16px;
    }
  </style>
</head>
<body>
  <main data-ui-target="feature-name" data-fidelity="approximate">
    <section data-viewport="desktop-1440">
      <h1>Desktop target composition</h1>
      <p>Preserve layout, density, information hierarchy, and visible data volume.</p>
    </section>

    <section data-viewport="mobile-390">
      <h1>Mobile target composition</h1>
      <p>Preserve priority and interaction intent in the narrow layout.</p>
    </section>

    <section data-state="empty">
      <h1>Empty state</h1>
      <p>Show the empty condition without changing the overall layout pattern.</p>
    </section>

    <section data-state="error">
      <h1>Error state</h1>
      <p>Show the error condition with a clear recovery action.</p>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 8: Run tests**

Run:

```powershell
python -m pytest tests/test_packaging_assets.py::test_ui_reference_artifact_templates_are_packaged tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs tests/test_alignment_templates.py::test_ui_reference_artifact_templates_define_strict_formats -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

Run:

```powershell
git add pyproject.toml templates/ui-reference-notes-template.md templates/ui-brief-template.md templates/ui-target-template.html tests/test_packaging_assets.py tests/test_alignment_templates.py
git commit -m "feat: add ui reference artifact templates"
```

---

### Task 4: Add `sp-specify` UI Reference Intake And Profile Mapping

**Files:**
- Modify: `templates/command-partials/specify/shell.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Add failing template tests**

In `tests/test_alignment_templates.py`, add:

```python
def test_specify_ui_reference_input_uses_writable_subagent_lane() -> None:
    command = _read("templates/commands/specify.md")
    shell = _read("templates/command-partials/specify/shell.md")
    combined = f"{command}\n{shell}"

    assert "UI Reference Input" in combined
    assert "choose_ui_reference_lane_dispatch" in combined
    assert "lane_mode: ui-reference-artifact" in combined
    assert "ui-reference-notes.md" in combined
    assert "ui-brief.md" in combined
    assert "ui-target.html" in combined
    assert "approximate" in combined
    assert "Reference-Implementation" in combined
    assert "Fidelity Requirements" in combined
    assert "read-only evidence lane" in combined
    assert "must not directly parse" in combined.lower()


def test_feature_ui_brief_artifacts_are_carried_by_spec_package_templates() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    state = _read("templates/workflow-state-template.md")

    assert "UI Reference Processing" in spec
    assert "ui-reference-notes.md" in spec
    assert "ui-brief.md" in spec
    assert "Fidelity Requirements" in spec
    assert "Reference Object" in spec
    assert "Required Fidelity" in spec
    assert "Reference Behavior Inventory" in spec
    assert "UI Brief Carry-Forward" in alignment
    assert "ui_reference_processing_status" in alignment
    assert "UI Reference Inputs" in context
    assert "ui_reference_lane_mode" in state
    assert "ui_fidelity_mode" in state
    assert "visual_comparison_or_human_review" in state
```

In `tests/test_command_surface_semantics.py`, extend `test_templates_include_design_quality_sections`:

```python
    assert "UI Reference Processing" in read_template("templates/spec-template.md")
    assert "ui-reference-notes.md" in read_template("templates/spec-template.md")
    assert "ui-brief.md" in read_template("templates/spec-template.md")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_specify_ui_reference_input_uses_writable_subagent_lane tests/test_alignment_templates.py::test_feature_ui_brief_artifacts_are_carried_by_spec_package_templates tests/test_command_surface_semantics.py::test_templates_include_design_quality_sections -q
```

Expected: failures because the UI reference lane and artifacts are not yet in templates.

- [ ] **Step 3: Update `sp-specify` summary shell**

In `templates/command-partials/specify/shell.md`, add this section after the existing context/process bullets about project context and before approach comparison:

```markdown
## UI Reference Input

- Detect screenshots, HTML/CSS mockups, Tailwind/shadcn/React/Vue/Svelte snippets, Figma exports, reference URLs, existing product pages, or wording such as "make it like this", "basically the same", "copy this layout", or "use this as the design".
- When UI reference input exists, ask for the fidelity mode unless the user already stated it:
  - `approximate` by default: preserve layout, density, hierarchy, visual rhythm, component structure, and primary interactions.
  - `high`: require visual comparison and deviation notes.
  - `inspiration`: extract principles only and avoid similar-looking output.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` before dispatching UI reference work.
- Record `lane_mode: ui-reference-artifact`, `dispatch_shape`, `execution_surface`, `workflow_status`, `blocked_reason`, and whether inline fallback was user approved.
- The `sp-specify` leader must not directly parse UI references and write the UI contract when UI reference input is present. The leader dispatches and validates the lane.
- The writable UI reference lane may write only `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html` inside the active `FEATURE_DIR`.
- Do not treat this as a read-only evidence lane; source code, tests, app styling, component implementation, package managers, builds, and app servers remain forbidden.
```

In the Output Contract section of the same file, add:

```markdown
- When UI reference input exists, require `ui-reference-notes.md`; when the feature has a concrete UI surface, require `ui-brief.md`; create `ui-target.html` only when a disposable visual target materially reduces ambiguity.
- For `approximate` and `high` UI reference fidelity, activate `Reference-Implementation`, populate `Fidelity Requirements`, and record UI-specific `required_evidence`.
```

- [ ] **Step 4: Update detailed `sp-specify` template**

In `templates/commands/specify.md`, add a subsection titled `**UI reference input handling**` before artifact writing guidance. Include this exact guidance:

```markdown
**UI reference input handling**:
- Detect screenshots, HTML/CSS mockups, UI framework snippets, design exports, URLs, existing pages, and "make it like this" language as UI reference input.
- Ask the user which fidelity mode applies when not already explicit: `approximate` (default), `high`, or `inspiration`.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: ui-reference-artifact`.
- For `approximate` and `high`, native subagents are required unless the user explicitly approves inline fallback; if unavailable, block with the missing capability instead of guessing.
- For `inspiration`, inline fallback may proceed with a recorded soft risk when subagents are unavailable.
- Dispatch the UI reference lane to write only `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`.
- Validate that `ui-target.html`, when present, is single-file, low-dependency, no external runtime, no CDN, no production-source claim, and preserves information density over decorative polish.
- For `approximate` and `high`, set `active_profile: Reference-Implementation`, require `Fidelity Requirements`, and add `required_evidence` terms: `reference_source_evidence`, `ui_fidelity_criteria`, `real_entrypoint_ui_evidence`, `visual_comparison_or_human_review`; add `deviation_log` when fidelity is `high`.
```

Update the existing read-only evidence lane sentence in Quick Guidelines so it still applies to ordinary evidence work, but explicitly excludes UI reference artifact work:

```markdown
- Before dispatching independent review or evidence work, use `choose_evidence_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: read-only-evidence`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents` when a validated isolated read-only lane exists. Use delegated read-only lanes only for isolated review/evidence packets, never for source edits or artifact writes. UI reference artifact work uses `choose_ui_reference_lane_dispatch` and the `ui-reference-artifact` lane instead.
```

- [ ] **Step 5: Update spec package templates**

In `templates/spec-template.md`, add `## UI Reference Processing` after `## Experience Requirements`:

```markdown
## UI Reference Processing

Use this section when the feature request includes screenshots, HTML/CSS mockups, UI framework code, design exports, reference URLs, existing UI pages, or language asking to match a specific UI.

- ui_reference_processing_status: [not-applicable | subagent-dispatched | completed | blocked | inline-fallback-approved]
- ui_reference_lane_mode: [none | ui-reference-artifact]
- ui_fidelity_mode: [none | approximate | high | inspiration]
- ui_reference_notes: [FEATURE_DIR/ui-reference-notes.md | none]
- ui_brief: [FEATURE_DIR/ui-brief.md | none]
- ui_target: [FEATURE_DIR/ui-target.html | none]
- visual_review_requirement: [not-needed | agent-visual-comparison | pending-human-review]
- ownership_classification: [user-owned | project-owned | third-party | unknown | mixed]
- inline_fallback_reason: [none | user-approved-inline-fallback | inspiration-soft-risk]
```

In the existing `## Fidelity Requirements` comment, add:

```markdown
  UI reference inputs with `approximate` or `high` fidelity activate this section.
  Map `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`
  into Reference Object, Required Fidelity, and Reference Behavior Inventory.
```

In `templates/alignment-template.md`, add `## UI Brief Carry-Forward` near the design-system carry-forward section:

```markdown
## UI Brief Carry-Forward

- ui_reference_processing_status:
- ui_reference_lane_mode:
- ui_fidelity_mode:
- ui_reference_notes:
- ui_brief:
- ui_target:
- ownership_classification:
- Reference-Implementation activated:
- required_evidence:
```

In `templates/context-template.md`, add `## UI Reference Inputs`:

```markdown
## UI Reference Inputs

- UI reference notes:
- UI brief:
- Visual target:
- Reference ownership:
- Fidelity mode:
- Must preserve:
- May adapt:
- Must not:
- Human review condition:
```

In `templates/workflow-state-template.md`, add a `## UI Reference Processing` section after `## Unknown Handling`:

```markdown
## UI Reference Processing

- ui_reference_processing_status: [not-applicable | subagent-dispatched | completed | blocked | inline-fallback-approved]
- ui_reference_lane_mode: [none | ui-reference-artifact]
- ui_fidelity_mode: [none | approximate | high | inspiration]
- ui_reference_notes: [path or none]
- ui_brief: [path or none]
- ui_target: [path or none]
- ui_reference_ownership: [user-owned | project-owned | third-party | unknown | mixed | none]
- visual_verification_requirement: [none | agent-visual-comparison | visual-comparison-or-human-review | pending-human-review]
- required_evidence: [none | reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review, deviation_log]
```

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_specify_ui_reference_input_uses_writable_subagent_lane tests/test_alignment_templates.py::test_feature_ui_brief_artifacts_are_carried_by_spec_package_templates tests/test_command_surface_semantics.py::test_templates_include_design_quality_sections -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add templates/command-partials/specify/shell.md templates/commands/specify.md templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/workflow-state-template.md tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "feat: add specify ui reference brief intake"
```

---

### Task 5: Carry UI Brief Through Plan, Tasks, Implement, And Passive Guidance

**Files:**
- Modify: `templates/plan-template.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/worker-prompts/implementer.md`
- Modify: `templates/passive-skills/spec-kit-ui-design/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`

- [ ] **Step 1: Add failing carry-forward tests**

In `tests/test_alignment_templates.py`, add:

```python
def test_plan_tasks_implement_carry_feature_ui_brief_contract() -> None:
    plan_template = _read("templates/plan-template.md")
    plan_command = _read("templates/commands/plan.md")
    tasks_template = _read("templates/tasks-template.md")
    tasks_command = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")
    worker_prompt = _read("templates/worker-prompts/implementer.md")

    assert "Feature UI Brief Adoption" in plan_template
    assert "ui-brief.md" in plan_command
    assert "Reference-Implementation" in plan_command
    assert "visual_comparison_or_human_review" in plan_command
    assert "UI Implementation Contract" in tasks_template
    assert "ui_contract" in tasks_template
    assert "ui_fidelity_mode" in tasks_command
    assert "required_evidence" in tasks_command
    assert "ui_verification" in implement
    assert "pending-human-review" in implement
    assert "ui_contract" in worker_prompt
    assert "ui_evidence" in worker_prompt
```

In `tests/test_passive_skill_guidance.py`, add:

```python
def test_ui_design_passive_skill_requires_subagent_for_ui_reference_input() -> None:
    content = _read("templates/passive-skills/spec-kit-ui-design/SKILL.md")
    lowered = content.lower()

    assert "ui reference input" in lowered
    assert "ui-reference-artifact" in content
    assert "choose_ui_reference_lane_dispatch" in content
    assert "ui-reference-notes.md" in content
    assert "ui-brief.md" in content
    assert "ui-target.html" in content
    assert "pending-human-review" in content
    assert "must not claim" in lowered
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_plan_tasks_implement_carry_feature_ui_brief_contract tests/test_passive_skill_guidance.py::test_ui_design_passive_skill_requires_subagent_for_ui_reference_input -q
```

Expected: failures because downstream workflow guidance does not yet carry feature UI brief.

- [ ] **Step 3: Update planning templates**

In `templates/plan-template.md`, add `## Feature UI Brief Adoption` after `## Design System Adoption`:

```markdown
## Feature UI Brief Adoption

- UI brief source:
- UI reference notes:
- Visual target:
- Fidelity mode:
- Reference-Implementation profile:
- Required evidence:
- Must preserve:
- May adapt:
- Must not:
- Visual verification strategy:
```

In `templates/commands/plan.md`, extend the Design System Adoption guidance with:

```markdown
## Feature UI Brief Adoption

When `FEATURE_DIR/ui-brief.md` exists, read it before planning implementation details. Treat it as a planning input alongside `DESIGN.md`, not as optional background.

For `approximate` and `high` fidelity, preserve the existing `Reference-Implementation` profile and promote these UI-specific evidence terms into `Implementation Constitution`:

- `reference_source_evidence`
- `ui_fidelity_criteria`
- `real_entrypoint_ui_evidence`
- `visual_comparison_or_human_review`
- `deviation_log` when fidelity is `high`

The plan must state what implementers must preserve, what they may adapt, what they must not copy, and whether visual comparison can be agent-verified or needs human review.
```

- [ ] **Step 4: Update task-generation templates**

In `templates/tasks-template.md`, add this section after `## Design Quality Coverage`:

```markdown
## UI Implementation Contract Coverage

| Surface | UI Brief | Fidelity | Must Preserve | May Adapt | Must Not | Required Evidence | Task IDs |
|---------|----------|----------|---------------|-----------|----------|-------------------|----------|

- Every UI-bearing task derived from `ui-brief.md` must include `ui_contract` packet fields.
- If fidelity is `approximate` or `high`, include `required_evidence` with `reference_source_evidence`, `ui_fidelity_criteria`, `real_entrypoint_ui_evidence`, and `visual_comparison_or_human_review`.
- If fidelity is `high`, include `deviation_log`.
- Do not pass raw "make it like this" wording to a worker without the compiled UI contract.
```

In `templates/commands/tasks.md`, add guidance near task packet generation:

```markdown
**Feature UI brief packet compilation**:
- When `ui-brief.md` exists, compile its contract into `ui_contract`.
- Set `ui_fidelity_mode` to `approximate`, `high`, or `inspiration`.
- Add `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html` to required references.
- Add required states and evidence to task packet fields.
- For `approximate` and `high`, include `required_evidence: [reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review]`.
- For `high`, also include `deviation_log`.
```

- [ ] **Step 5: Update implementation guidance and worker prompt**

In `templates/commands/implement.md`, add this gate before final validation guidance:

```markdown
**UI verification gate**:
- Before closing a UI-bearing task with `ui_contract`, confirm the worker returned `ui_evidence` and `ui_verification`.
- Do not mark UI fidelity as passed from tests alone.
- If `visual_comparison_or_human_review` is required and no vision-capable comparison is available, record `fidelity_status: pending-human-review`.
- If `high` fidelity is required, require visual comparison or human review plus deviation notes before claiming fidelity pass.
- Functional completion may be recorded separately from visual fidelity approval.
```

In `templates/worker-prompts/implementer.md`, add to the worker contract:

```markdown
- If the packet includes `ui_contract`, follow it as binding UI implementation scope. Do not reinterpret the original screenshot, HTML, or UI code reference into a different layout pattern.
- If the packet includes `ui_contract.visual_target`, treat `ui-target.html` as a disposable visual target, not production source.
- If the packet requires UI evidence, return `ui_evidence` with screenshots or captures, state coverage, console or terminal checks, accessibility or keyboard checks when relevant, and notes for any allowed deviation.
- If the packet requires `visual_comparison_or_human_review` and you cannot perform visual comparison, return `ui_verification.fidelity_status: pending-human-review` instead of claiming visual match.
```

- [ ] **Step 6: Update passive skills**

In `templates/passive-skills/spec-kit-ui-design/SKILL.md`, add a section after `## Design System Gate`:

```markdown
## UI Reference Input Gate

- Treat screenshots, HTML/CSS mockups, UI framework snippets, Figma exports, reference URLs, existing pages, and "make it like this" language as UI reference input.
- In `sp-specify`, UI reference input requires `choose_ui_reference_lane_dispatch` and `lane_mode: ui-reference-artifact`.
- The UI reference lane writes `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`.
- `approximate` is the default fidelity mode. `high` requires visual comparison; `inspiration` extracts principles only.
- If the environment cannot prove visual similarity, the workflow must record `pending-human-review`.
- The agent must not claim a UI visually matches a reference without agent visual comparison or human approval.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, extend the `sp-design`/UI routing guidance with:

```markdown
- Use `sp-specify` with the UI reference artifact lane when a feature request includes concrete UI reference input for that feature. Use `sp-design` only when the project-wide design system itself is missing, contradictory, or being changed.
```

- [ ] **Step 7: Run tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_plan_tasks_implement_carry_feature_ui_brief_contract tests/test_passive_skill_guidance.py::test_ui_design_passive_skill_requires_subagent_for_ui_reference_input -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add templates/plan-template.md templates/commands/plan.md templates/tasks-template.md templates/commands/tasks.md templates/commands/implement.md templates/worker-prompts/implementer.md templates/passive-skills/spec-kit-ui-design/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_alignment_templates.py tests/test_passive_skill_guidance.py
git commit -m "feat: carry ui brief through implementation workflows"
```

---

### Task 6: Add Structured UI Contract And Verification To Worker Packets

**Files:**
- Modify: `src/specify_cli/execution/packet_schema.py`
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Modify: `templates/task-packet-template.json`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_packet_compiler.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Add failing packet schema tests**

In `tests/execution/test_packet_schema.py`, import the new types that will be added:

```python
    UIContract,
    UIVerification,
```

Add this test near `test_worker_task_packet_captures_required_execution_contract`:

```python
def test_worker_task_packet_captures_ui_contract_and_result_verification() -> None:
    packet = WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T021",
        story_id="US1",
        objective="Implement exception panel UI",
        intent=ExecutionIntent(outcome="Implement UI from ui-brief.md"),
        scope=PacketScope(write_scope=["src/app/exceptions/page.tsx"]),
        context_bundle=[],
        required_references=[
            PacketReference(path="DESIGN.md", reason="root design contract"),
            PacketReference(path="specs/001-feature/ui-brief.md", reason="feature UI contract"),
        ],
        hard_rules=["Follow ui_contract"],
        forbidden_drift=["Do not replace dense table with cards"],
        validation_gates=["npm test -- exceptions"],
        done_criteria=["UI evidence returned"],
        handoff_requirements=["return ui_evidence and ui_verification"],
        ui_contract=UIContract(
            design_sources=["DESIGN.md", "specs/001-feature/ui-brief.md"],
            reference_notes="specs/001-feature/ui-reference-notes.md",
            visual_target="specs/001-feature/ui-target.html",
            fidelity_level="approximate",
            must_preserve=["three-column layout", "compact table density"],
            may_adapt=["icons", "minor spacing"],
            must_not=["copy third-party source", "turn table into cards"],
            required_states=["loading", "empty", "error"],
            required_evidence=["desktop screenshot", "mobile screenshot"],
        ),
    )

    payload = worker_task_packet_payload(packet)
    round_tripped = worker_task_packet_from_json(json.dumps(payload))

    assert round_tripped.ui_contract.fidelity_level == "approximate"
    assert "compact table density" in round_tripped.ui_contract.must_preserve
    assert "desktop screenshot" in round_tripped.ui_contract.required_evidence

    result = WorkerTaskResult(
        task_id="T021",
        status="success",
        ui_evidence=[
            {"kind": "screenshot", "path": "artifacts/ui/desktop-1440.png", "viewport": "1440"}
        ],
        ui_verification=UIVerification(
            contract_check="pass",
            runtime_evidence="pass",
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
            reviewer="agent",
        ),
    )
    result_payload = worker_task_result_payload(result)
    parsed_result = worker_task_result_from_json(json.dumps(result_payload))

    assert parsed_result.ui_evidence[0]["kind"] == "screenshot"
    assert parsed_result.ui_verification.fidelity_status == "pending-human-review"
```

- [ ] **Step 2: Add failing packet compiler test**

In `tests/execution/test_packet_compiler.py`, add:

```python
def test_compile_worker_task_packet_extracts_ui_contract(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-ui-feature"
    feature_dir.mkdir(parents=True)
    (project_root / "DESIGN.md").write_text("# Design\n", encoding="utf-8")
    (feature_dir / "ui-reference-notes.md").write_text("# UI Reference Notes\n", encoding="utf-8")
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    (feature_dir / "ui-target.html").write_text("<!doctype html>\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("## Required Implementation References\n\n- DESIGN.md\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## T021: Implement exception panel UI",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/app/exceptions/page.tsx] |",
                "| read_scope | [DESIGN.md, specs/001-ui-feature/ui-brief.md] |",
                "| required_evidence | [reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review] |",
                "",
                "### UI Implementation Contract",
                "| Field | Value |",
                "|-------|-------|",
                "| design_sources | [DESIGN.md, specs/001-ui-feature/ui-brief.md] |",
                "| reference_notes | specs/001-ui-feature/ui-reference-notes.md |",
                "| visual_target | specs/001-ui-feature/ui-target.html |",
                "| fidelity_level | approximate |",
                "| must_preserve | [three-column layout, compact table density] |",
                "| may_adapt | [icons, minor spacing] |",
                "| must_not | [copy third-party source, turn table into cards] |",
                "| required_states | [loading, empty, error] |",
                "| required_evidence | [desktop screenshot, mobile screenshot] |",
                "",
                "- [ ] T021 [US1] Implement exception panel UI",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    assert packet.ui_contract.fidelity_level == "approximate"
    assert packet.ui_contract.reference_notes == "specs/001-ui-feature/ui-reference-notes.md"
    assert packet.ui_contract.visual_target == "specs/001-ui-feature/ui-target.html"
    assert "three-column layout" in packet.ui_contract.must_preserve
    assert "turn table into cards" in packet.ui_contract.must_not
    assert "visual_comparison_or_human_review" in packet.required_evidence
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/execution/test_packet_schema.py::test_worker_task_packet_captures_ui_contract_and_result_verification tests/execution/test_packet_compiler.py::test_compile_worker_task_packet_extracts_ui_contract -q
```

Expected: failures because `UIContract`, `UIVerification`, `ui_contract`, `ui_evidence`, and `ui_verification` are missing.

- [ ] **Step 4: Add packet schema types**

In `src/specify_cli/execution/packet_schema.py`, add after `ExecutionIntent`:

```python
UIFidelityLevel = Literal["none", "approximate", "high", "inspiration"]


@dataclass(slots=True)
class UIContract:
    design_sources: list[str] = field(default_factory=list)
    reference_notes: str = ""
    visual_target: str = ""
    fidelity_level: UIFidelityLevel = "none"
    must_preserve: list[str] = field(default_factory=list)
    may_adapt: list[str] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    required_states: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
```

Add to `WorkerTaskPacket`:

```python
    ui_contract: UIContract = field(default_factory=UIContract)
```

Update `worker_task_packet_from_json` before `packet_payload = _filter_dataclass_payload(...)`:

```python
    ui_contract = UIContract(
        **_filter_dataclass_payload(UIContract, payload.get("ui_contract", {}))
    )
```

Then set:

```python
    packet_payload["ui_contract"] = ui_contract
```

- [ ] **Step 5: Add result schema UI verification**

In `src/specify_cli/execution/result_schema.py`, add after `RuleAcknowledgement`:

```python
@dataclass(slots=True)
class UIVerification:
    contract_check: str = "not-run"
    runtime_evidence: str = "not-run"
    visual_comparison: str = "unavailable"
    fidelity_status: str = "not-applicable"
    reviewer: str = "agent"
```

Add to `WorkerTaskResult`:

```python
    ui_evidence: list[dict[str, str]] = field(default_factory=list)
    ui_verification: UIVerification = field(default_factory=UIVerification)
```

In `worker_task_result_from_json`, normalize `ui_evidence` like the other evidence lists:

```python
    result_payload["ui_evidence"] = _normalize_evidence_items(
        result_payload.get("ui_evidence", [])
    )
    result_payload["ui_verification"] = UIVerification(
        **_filter_dataclass_payload(UIVerification, result_payload.get("ui_verification", {}))
    )
```

- [ ] **Step 6: Parse UI contract from tasks**

In `src/specify_cli/execution/packet_compiler.py`, import `UIContract`.

Add helper:

```python
def _ui_contract_for_task(task_detail: str) -> UIContract:
    section = _section_body(task_detail, "UI Implementation Contract")
    if not section:
        return UIContract()
    return UIContract(
        design_sources=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "design_sources"),
        reference_notes=next(iter(_task_detail_table_field_values(task_detail, "UI Implementation Contract", "reference_notes")), ""),
        visual_target=next(iter(_task_detail_table_field_values(task_detail, "UI Implementation Contract", "visual_target")), ""),
        fidelity_level=next(iter(_task_detail_table_field_values(task_detail, "UI Implementation Contract", "fidelity_level")), "none"),
        must_preserve=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "must_preserve"),
        may_adapt=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "may_adapt"),
        must_not=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "must_not"),
        required_states=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "required_states"),
        required_evidence=_task_detail_table_field_values(task_detail, "UI Implementation Contract", "required_evidence"),
    )
```

When constructing `WorkerTaskPacket`, pass:

```python
        ui_contract=_ui_contract_for_task(task_detail),
```

Add the UI contract references into `required_references` only if they are not empty. If an existing helper already deduplicates references, reuse it; otherwise append `PacketReference` entries for each path in `ui_contract.design_sources`, `ui_contract.reference_notes`, and `ui_contract.visual_target` with reason `"UI implementation contract reference"`.

- [ ] **Step 7: Update task packet template**

In `templates/task-packet-template.json`, add:

```json
  "ui_contract": {
    "design_sources": [],
    "reference_notes": "",
    "visual_target": "",
    "fidelity_level": "none",
    "must_preserve": [],
    "may_adapt": [],
    "must_not": [],
    "required_states": [],
    "required_evidence": []
  },
```

Place it after `"required_evidence": []`.

- [ ] **Step 8: Add result validator coverage**

Inspect `tests/execution/test_result_validator.py` for how `required_evidence` is validated. Add a test that creates a packet with:

```python
sample_packet.required_evidence = ["visual_comparison_or_human_review"]
sample_packet.ui_contract.fidelity_level = "approximate"
```

and a result with:

```python
result.ui_verification.fidelity_status = "pending-human-review"
```

Expected assertion: validation accepts `pending-human-review` as a valid status for visual comparison evidence when visual comparison is unavailable. If the validator has no hook for this yet, add a small validator rule that fails only when `visual_comparison_or_human_review` is required and `ui_verification.fidelity_status` is empty, `not-applicable`, or absent.

Use this expected error text for missing verification:

```text
visual_comparison_or_human_review requires ui_verification fidelity_status
```

- [ ] **Step 9: Run tests**

Run:

```powershell
python -m pytest tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: all pass.

- [ ] **Step 10: Commit**

Run:

```powershell
git add src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_compiler.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py templates/task-packet-template.json tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py
git commit -m "feat: add ui contract worker packet fields"
```

---

### Task 7: Update Integration Rendering And Generated Asset Tests

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: integration inventory tests if they fail after new template files are copied

- [ ] **Step 1: Add generated command assertions**

In each base integration test file, add or extend the test that checks generated `sp.specify` or `sp-specify` content. Assert:

```python
assert "choose_ui_reference_lane_dispatch" in content
assert "ui-reference-artifact" in content
assert "ui-reference-notes.md" in content
assert "ui-brief.md" in content
assert "Reference-Implementation" in content
```

Use each file's existing helper for generated command content:

- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`

- [ ] **Step 2: Run integration tests and inspect inventory failures**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: content assertions pass after previous tasks. If inventory tests fail with extra `.specify/templates/ui-reference-notes-template.md`, `.specify/templates/ui-brief-template.md`, or `.specify/templates/ui-target-template.html`, update the expected inventory builders in the failing tests.

- [ ] **Step 3: Update Codex subagent discovery assertion if needed**

If a Codex generated skill test checks subagent-triggering text, add:

```python
assert "choose_ui_reference_lane_dispatch" in skill_content
```

to the same test that already checks `choose_evidence_lane_dispatch`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py
git commit -m "test: cover generated ui reference workflow guidance"
```

If additional inventory tests changed, include those files in the same commit.

---

### Task 8: Update Documentation And Handbook Surfaces

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_project_handbook_templates.py`

- [ ] **Step 1: Add documentation tests**

In `tests/test_specify_guidance_docs.py`, extend the design workflow documentation test with:

```python
assert "ui-brief.md" in content
assert "ui-reference-notes.md" in content
assert "ui-reference-artifact" in content
assert "approximate" in content
assert "pending-human-review" in content
```

In `tests/test_project_handbook_templates.py`, add equivalent assertions for `templates/project-handbook-template.md` and `PROJECT-HANDBOOK.md` using the file-reading helper already present in that test file:

```python
assert "ui-brief.md" in content
assert "ui-reference-notes.md" in content
assert "UI reference" in content
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py -q
```

Expected: failures because docs do not yet describe the feature UI brief lane.

- [ ] **Step 3: Update README**

In `README.md`, near the existing `design` / `sp-design` and Design System Helpers guidance, add:

```markdown
Feature UI references are handled during `sp-specify`. When a feature request includes screenshots, HTML/CSS mockups, UI framework snippets, design exports, URLs, existing pages, or "make it like this" language, `sp-specify` asks for a fidelity mode and defaults to `approximate`. It uses the writable `ui-reference-artifact` lane to produce `ui-reference-notes.md` and `ui-brief.md`, plus optional `ui-target.html`. Approximate and high-fidelity references activate the existing `Reference-Implementation` profile and carry UI-specific evidence requirements through plan, tasks, and implementation. If agent visual comparison is unavailable, visual fidelity remains `pending-human-review` instead of being claimed as complete.
```

- [ ] **Step 4: Update handbooks**

In `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`, extend the `UI design system` bullet with:

```markdown
Feature-specific UI references are owned by `sp-specify`, not `sp-design`: screenshots, HTML/CSS mockups, UI framework snippets, design exports, URLs, existing pages, or "make it like this" language route through the writable `ui-reference-artifact` lane. That lane writes `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`; downstream plan/tasks/implement stages treat `ui-brief.md` as the worker-facing UI contract and record `pending-human-review` when visual fidelity cannot be proven by agent verification.
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py
git commit -m "docs: document feature ui brief workflow"
```

---

### Task 9: Final Verification

**Files:**
- No source edits expected unless tests reveal an integration drift.

- [ ] **Step 1: Run focused regression suite**

Run:

```powershell
python -m pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py tests/test_packaging_assets.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py -q
```

Expected: all pass.

- [ ] **Step 2: Run integration regression suite**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_copilot.py tests/integrations/test_integration_generic.py -q
```

Expected: all pass. If a file inventory test fails because the new UI template files are copied into `.specify/templates`, update only that inventory expectation and rerun the failing test.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all pass with the repository's normal skipped tests.

- [ ] **Step 4: Run static checks**

Run:

```powershell
git diff --check
$terms = @('T'+'BD','TO'+'DO','PLACE'+'HOLDER','FIX'+'ME','?'+'??','to be '+'decided','to be '+'defined')
Select-String -Path docs/superpowers/plans/2026-07-06-feature-ui-brief-subagent-workflow-implementation-plan.md -Pattern $terms -SimpleMatch
```

Expected: `git diff --check` has no output. `Select-String` has no matches.

- [ ] **Step 5: Review changed files**

Run:

```powershell
git status --short
git diff --stat main..HEAD
```

Expected: only files related to the UI brief workflow, tests, docs, and the plan are changed relative to `main`.

- [ ] **Step 6: Commit final verification notes only if a test-driven fix was needed**

If Task 9 required source or test edits, return to the task that owns that surface, add the missing focused test or implementation step there, and commit with that task's file list. If Task 9 required no edits, do not create an empty commit.

## Execution Notes

- This plan intentionally changes orchestration model/policy because `ui-reference-artifact` is a writable lane. Do not implement it as a read-only evidence lane.
- This plan intentionally maps approximate and high UI references to `Reference-Implementation` because the repository already has fidelity and required-evidence contracts.
- This plan intentionally treats `ui-target.html` as an artifact format with low dependency rules, not as an app implementation scaffold.
- This plan intentionally separates functional completion from visual fidelity approval through `ui_verification.fidelity_status`.
