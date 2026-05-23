# Quick Debug Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-time `sp-quick` understanding checkpoint and make `sp-debug` choose leader-inline or subagent-assisted execution based on investigation complexity.

**Architecture:** This is primarily a generated workflow contract change. Update the command templates and generated integration addenda together so raw templates, rendered Markdown commands, rendered skills, Codex skills, and Cursor skills all describe the same behavior. Keep runtime orchestration `ExecutionModel` unchanged; debug's `leader-inline | subagent-assisted | blocked` vocabulary is debug session/template state, not the shared orchestration model.

**Tech Stack:** Python 3.13, pytest, Markdown workflow templates, generated integration renderers, Typer integration tests, PowerShell shell commands.

---

## Source Spec

Approved design:

`docs/superpowers/specs/2026-05-23-quick-debug-execution-design.md`

Implementation must preserve these decisions:

- `sp-quick` adds one default understanding checkpoint before substantive execution.
- `sp-quick` records `understanding_confirmed` in quick `STATUS.md` frontmatter.
- `sp-quick` resume blocks code edits, broad repository analysis, delegation, and validation commands while `understanding_confirmed: false`.
- `sp-debug` allows leader-inline execution for small focused investigations.
- `sp-debug` uses one or more subagents for broad, independent, or parallel evidence lanes.
- `sp-debug` preserves `subagent-blocked` and `execution_surface: none` for unsafe, unavailable, or unpacketizable execution.
- Debug's `execution_model: leader-inline | subagent-assisted | blocked` is debug session/template vocabulary only. Do not add those literals to `src/specify_cli/orchestration/models.py`.

## File Structure

Runtime model guard:

- `tests/orchestration/test_models.py`
  - Add a guard proving debug execution labels are not shared orchestration `ExecutionModel` literals.
  - Do not modify `src/specify_cli/orchestration/models.py` unless this guard exposes an existing contradiction.

Quick workflow templates:

- `templates/commands/quick.md`
  - Add the `Understanding Checkpoint` gate.
  - Add `understanding_confirmed` to `STATUS.md` frontmatter.
  - Add a body section that records the confirmed checkpoint summary.
  - Update resume and coordinator rules so false confirmation blocks substantive execution.
- `templates/command-partials/quick/shell.md`
  - Add concise generated-command wording for the checkpoint.

Debug workflow templates:

- `templates/commands/debug.md`
  - Replace mandatory debug subagent language with complexity-based execution.
  - Keep observer framing, evidence gates, root-cause discipline, and human verification unchanged.
  - Allow leader-inline fix application only after root cause and RED/proof gates.
  - Keep subagent evidence collection for broad or independent evidence lanes.
- `templates/command-partials/debug/shell.md`
  - Mirror the concise leader-inline versus subagent-assisted rule.
- `templates/debug.md`
  - Add debug session frontmatter fields for execution decision state.

Integration renderers:

- `src/specify_cli/integrations/base.py`
  - Update `_append_debug_leader_gate`, `_append_debug_routing_contract`, `_append_quick_leader_gate`, `_append_quick_routing_contract`, `_augment_debug_skill`, and `_augment_quick_skill`.
  - Remove stale quick/debug `subagents-first` wording where it contradicts the new contract.
  - For quick, only allow execution routing after `understanding_confirmed: true`.
  - For debug, make leader-inline a valid first path for focused investigations.
- `src/specify_cli/integrations/cursor_agent/__init__.py`
  - Update Cursor's quick-specific addenda, which override the shared quick augmentation.
  - Ensure Cursor generated quick skills include the checkpoint before subagent routing.

Docs and passive skills:

- `README.md`
  - Update quick/debug execution guidance.
- `PROJECT-HANDBOOK.md`
  - Update maintainer guidance for workflow contracts.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
  - Update quick/debug routing language.
- `templates/passive-skills/subagent-driven-development/SKILL.md`
  - Stop saying debug always uses subagents for substantive work.
- `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
  - Keep parallel dispatch guidance for multi-lane debug and quick after confirmation.

Tests:

- `tests/test_quick_template_guidance.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_subagent_mandatory_template_guidance.py`
- `tests/test_alignment_templates.py`
- `tests/test_quick_skill_mirror.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_cli.py`
- `tests/integrations/test_integration_codex.py`
- `tests/integrations/test_integration_cursor_agent.py`

## Task 1: Lock Runtime Schema Boundary And Debug Session Fields

**Files:**
- Modify: `tests/orchestration/test_models.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `templates/debug.md`

- [ ] **Step 1: Add the orchestration model guard test**

In `tests/orchestration/test_models.py`, add this test after `test_execution_decision_rejects_invalid_execution_model()`:

```python
def test_debug_execution_labels_stay_out_of_shared_orchestration_execution_model():
    assert get_args(ExecutionModel) == ("subagent-mandatory", "adaptive")

    for execution_model in ("leader-inline", "subagent-assisted", "blocked"):
        try:
            ExecutionDecision(
                command_name="debug",
                dispatch_shape="one-subagent",
                reason="debug-session-field-not-runtime-model",
                execution_model=execution_model,  # type: ignore[arg-type]
            )
        except ValueError as exc:
            assert "Unsupported execution model" in str(exc)
        else:
            raise AssertionError(f"{execution_model} must remain debug session state only")
```

- [ ] **Step 2: Add failing debug session template assertions**

In `tests/test_debug_template_guidance.py`, extend `test_debug_session_template_uses_canonical_intake_fields()` after `legacy_session_needs_reintake`:

```python
    assert "execution_model:" in content
    assert "leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape:" in content
    assert "leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface:" in content
    assert "leader-inline | native-subagents | none" in content
    assert "dispatch_reason:" in content
    assert "blocked_reason:" in content
```

- [ ] **Step 3: Run the focused tests and confirm the RED**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py::test_debug_execution_labels_stay_out_of_shared_orchestration_execution_model tests/test_debug_template_guidance.py::test_debug_session_template_uses_canonical_intake_fields
```

Expected: orchestration guard passes; debug session template assertion fails because `templates/debug.md` does not yet contain the execution decision fields.

- [ ] **Step 4: Add debug session execution fields**

In `templates/debug.md`, add these lines in the frontmatter block after `legacy_session_needs_reintake`:

```markdown
execution_model: leader-inline | subagent-assisted | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
dispatch_reason: [why leader-inline, subagent-assisted, or blocked was selected]
blocked_reason: [required when dispatch_shape is subagent-blocked or execution_surface is none]
```

- [ ] **Step 5: Run the focused tests and confirm GREEN**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py::test_debug_execution_labels_stay_out_of_shared_orchestration_execution_model tests/test_debug_template_guidance.py::test_debug_session_template_uses_canonical_intake_fields
```

Expected: both tests pass.

- [ ] **Step 6: Commit the schema boundary**

Run:

```powershell
git add tests/orchestration/test_models.py tests/test_debug_template_guidance.py templates/debug.md
git commit -m "test: lock debug execution state boundary"
```

## Task 2: Add `sp-quick` Understanding Checkpoint To Templates

**Files:**
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `templates/commands/quick.md`
- Modify: `templates/command-partials/quick/shell.md`

- [ ] **Step 1: Add failing quick checkpoint assertions**

In `tests/test_quick_template_guidance.py`, add this test after `test_quick_template_exists_and_defines_lightweight_tracked_flow()`:

```python
def test_quick_template_requires_one_time_understanding_checkpoint() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "## understanding checkpoint" in content
    assert "problem understood" in content
    assert "planned outcome" in content
    assert "scope boundary" in content
    assert "execution approach" in content
    assert "validation" in content
    assert "wait for user confirmation" in content
    assert "revise the checkpoint" in content
    assert "not a full spec" in content
    assert "not a `sp-plan` substitute" in content
```

Extend `test_quick_template_includes_concrete_status_template()` after `trigger: "[verbatim user input]"` expectations with:

```python
    assert "understanding_confirmed: false | true" in content
    assert "## understanding checkpoint" in content
    assert "confirmed_problem:" in content
    assert "confirmed_outcome:" in content
    assert "confirmed_scope_boundary:" in content
    assert "confirmed_execution_approach:" in content
    assert "confirmed_validation:" in content
```

Add this test near the empty-call recovery test:

```python
def test_quick_template_blocks_resume_until_understanding_is_confirmed() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "understanding_confirmed: false" in content
    assert "blocks substantive execution" in content
    assert "must not proceed to code edits" in content
    assert "broad repository analysis" in content
    assert "delegation" in content
    assert "validation commands" in content
    assert "until the checkpoint is confirmed" in content
```

- [ ] **Step 2: Run quick template tests and confirm RED**

Run:

```powershell
uv run pytest -q tests/test_quick_template_guidance.py
```

Expected: new checkpoint assertions fail because the template does not yet describe the confirmation gate or status fields.

- [ ] **Step 3: Add the quick checkpoint section**

In `templates/commands/quick.md`, insert this section after `## Required Context Inputs` and the project cognition readiness carry-forward block, before `## Workflow Quality Requirements`:

```markdown
## Understanding Checkpoint

`sp-quick` has one default understanding checkpoint before substantive execution. This is not a full spec, not a `sp-plan` substitute, and not a detailed task-plan approval. It exists so the user can confirm that the quick-task direction is correct before the workflow runs to completion.

After the constitution gate, quick workspace initialization, project cognition gate, and any required minimal reads, present one concise checkpoint:

- `Problem understood`: what you believe the user wants solved.
- `Planned outcome`: what result you intend to deliver.
- `Scope boundary`: what you will not do in this quick task.
- `Execution approach`: how you expect to proceed.
- `Validation`: what evidence will prove the quick task is complete.

Wait for user confirmation before code edits, broad repository analysis, delegation, implementation commands, or validation commands. If the user corrects the understanding, revise the checkpoint once with the corrected direction and ask for confirmation again.

Record the confirmed checkpoint in `STATUS.md`. `understanding_confirmed: false` blocks substantive execution on resume. While it is false, only read the minimal context needed to reconstruct or revise the checkpoint; do not proceed to code edits, broad repository analysis, delegation, or validation commands until the checkpoint is confirmed and `STATUS.md` is updated.
```

- [ ] **Step 4: Update quick coordinator sequencing**

In `templates/commands/quick.md`, in `## Coordinator Model`, replace the sentence:

```markdown
- Before implementation work starts, identify whether the quick task is best handled by one bounded subagent or by two or more independent subagents that can safely proceed in parallel.
```

with:

```markdown
- Before implementation work starts, confirm the Understanding Checkpoint and persist `understanding_confirmed: true` in `STATUS.md`; only then identify whether the quick task is best handled by one bounded subagent or by two or more independent subagents that can safely proceed in parallel.
```

Replace:

```markdown
- The first actionable execution step after scope lock is to dispatch the first subagent batch, not to continue local deep-dive analysis.
```

with:

```markdown
- The first actionable execution step after scope lock and understanding confirmation is to dispatch the first subagent batch, not to continue local deep-dive analysis.
```

- [ ] **Step 5: Update the quick `STATUS.md` template**

In the frontmatter block under `## STATUS.md Template`, add this line after `trigger: "[verbatim user input]"`:

```markdown
understanding_confirmed: false | true
```

Add this body section after `## Execution Intent` and before `## Execution`:

```markdown
## Understanding Checkpoint
<!-- OVERWRITE/REFINE before substantive execution starts -->

confirmed_problem: [what the user confirmed the quick task should solve]
confirmed_outcome: [the result the user confirmed]
confirmed_scope_boundary:
  - [explicit non-goals, excluded files, excluded workflows, or escalation boundaries]
confirmed_execution_approach:
  - [the confirmed execution path]
confirmed_validation:
  - [the confirmed evidence required before closeout]
```

- [ ] **Step 6: Update the quick command partial**

In `templates/command-partials/quick/shell.md`, add this bullet to the `## Context` list:

```markdown
- Before substantive execution, present one Understanding Checkpoint covering the understood problem, planned outcome, scope boundary, execution approach, and validation evidence; wait for user confirmation and record it in quick `STATUS.md`.
```

Add this bullet to `## Objective` after the current two sentences:

```markdown
Before the lightweight path starts substantive execution, make the agent's understanding visible once so the user can confirm or correct the direction.
```

- [ ] **Step 7: Run quick template tests and confirm GREEN**

Run:

```powershell
uv run pytest -q tests/test_quick_template_guidance.py
```

Expected: quick template tests pass.

- [ ] **Step 8: Commit the quick checkpoint template change**

Run:

```powershell
git add tests/test_quick_template_guidance.py templates/commands/quick.md templates/command-partials/quick/shell.md
git commit -m "feat: add quick understanding checkpoint"
```

## Task 3: Make `sp-debug` Complexity-Based In Templates

**Files:**
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_subagent_mandatory_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `templates/commands/debug.md`
- Modify: `templates/command-partials/debug/shell.md`

- [ ] **Step 1: Update debug template tests for complexity-based execution**

In `tests/test_debug_template_guidance.py`, update `test_debug_template_documents_map_backed_intake_contract()`:

Remove these assertions:

```python
    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
```

Add these assertions near the existing leader assertions:

```python
    assert "complexity-based debug execution" in content
    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "dispatch_reason" in content
    assert "blocked_reason" in content
    assert "use `leader-inline` when the investigation is small, focused, and has a short evidence chain" in content
    assert "use `subagent-assisted` when the investigation has multiple independent evidence lanes" in content
```

Later in the same test, replace the second group of mandatory assertions:

```python
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
```

with:

```python
    assert "subagent-assisted" in content
    assert "leader-inline" in content
    assert "subagent-blocked" in content
    assert "execution_surface: none" in content
```

Add this test before `test_debug_template_uses_stage_and_protocol_structure()`:

```python
def test_debug_template_preserves_blocked_state_and_subagent_boundaries() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "subagent-blocked" in content
    assert "execution_surface: none" in content
    assert "unsafe, unavailable, or unpacketizable" in content
    assert "subagents may collect evidence" in content
    assert "must not update the debug file" in content
    assert "must not declare the root cause final" in content
    assert "must not transition the session state" in content
```

- [ ] **Step 2: Update mandatory-subagent classification tests**

In `tests/test_subagent_mandatory_template_guidance.py`, remove `"debug"` from `MANDATORY_COMMANDS`.

Add:

```python
COMPLEXITY_BASED_COMMANDS = ("debug",)
```

Add this test after `test_plan_and_tasks_use_adaptive_execution_instead_of_mandatory_partial()`:

```python
def test_debug_uses_complexity_based_execution_instead_of_mandatory_subagents() -> None:
    content = _read_command("debug").lower()

    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "subagent-blocked" in content
    assert "execution_model: subagent-mandatory" not in content
```

In `test_mandatory_subagent_templates_block_remaining_leader_path_fallbacks()`, remove `"debug"` from `targeted_commands`.

In `test_task4_templates_do_not_reintroduce_ordinary_local_leader_framing()`, replace the final debug assertions:

```python
    assert "apply the smallest fix that addresses the confirmed root cause" not in debug_content
    assert "packetize the smallest safe fix that addresses the confirmed root cause" in debug_content
    assert "delegate it through a validated subagent lane" in debug_content
    assert "record `subagent-blocked` with the escalation or recovery reason instead of making the fix directly" in debug_content
```

with:

```python
    assert "apply the minimum code change needed to address the confirmed root cause" in debug_content
    assert "when `execution_model: subagent-assisted`" in debug_content
    assert "delegate the fix through a validated subagent lane" in debug_content
    assert "when the fix cannot proceed safely" in debug_content
    assert "record `subagent-blocked`" in debug_content
```

- [ ] **Step 3: Update alignment helper usage for debug**

In `tests/test_alignment_templates.py`, add this helper after `_assert_adaptive_plan_tasks_contract()`:

```python
def _assert_complexity_based_debug_contract(text: str) -> None:
    lowered = text.lower()
    assert 'choose_subagent_dispatch(command_name="debug"' in text
    assert "execution_model: leader-inline | subagent-assisted | blocked" in lowered
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in lowered
    assert "execution_surface: leader-inline | native-subagents | none" in lowered
    assert "subagent-blocked" in lowered
    assert "execution_surface: none" in lowered
    assert "execution_model: subagent-mandatory" not in lowered
```

Search for direct assertions that read `templates/commands/debug.md` and expect `execution_model: subagent-mandatory`. Replace those debug-specific expectations with `_assert_complexity_based_debug_contract(content)`. Do not change `specify`, `implement`, `map-scan`, `map-build`, `prd-scan`, or `prd-build` mandatory assertions.

- [ ] **Step 4: Run debug template tests and confirm RED**

Run:

```powershell
uv run pytest -q tests/test_debug_template_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_alignment_templates.py
```

Expected: fails because `templates/commands/debug.md` still contains the mandatory subagent wording.

- [ ] **Step 5: Replace the debug execution section**

In `templates/commands/debug.md`, replace the `## Mandatory Subagent Execution` section with:

```markdown
## Complexity-Based Debug Execution

`sp-debug` is leader-owned and evidence-first. Choose the execution path from the shape of the investigation, then record the decision in the debug session file.

Use `leader-inline` when the investigation is small, focused, and has a short evidence chain, such as one failing test, one clear error, one local module, or one reproduction path.

Use `subagent-assisted` when the investigation has multiple independent evidence lanes, broad surface area, multiple plausible causes, multiple modules or logs to inspect, independent repro or verification lanes, or meaningful parallelism.

Use `blocked` when the next safe step is unsafe, unavailable, or unpacketizable. Preserve the blocked state as `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`.

Persist these fields in the debug session:

- `execution_model: leader-inline | subagent-assisted | blocked`
- `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`
- `execution_surface: leader-inline | native-subagents | none`
- `dispatch_reason: [why this execution path was selected]`
- `blocked_reason: [required for subagent-blocked or none]`

Subagents may collect evidence or execute a bounded lane. They must not update the debug file, declare the root cause final, transition the session state, mark the session resolved, or archive the session.
```

- [ ] **Step 6: Update debug role bullets**

In the `## Role` section of `templates/commands/debug.md`, replace:

```markdown
- Subagents own the substantive task lanes assigned through task contracts.
```

with:

```markdown
- Subagents own only the bounded evidence or fix lanes assigned through task contracts.
```

Replace:

```markdown
- You are not the default evidence worker for every lane; substantive evidence work belongs on subagent lanes after observer framing and task contracts are ready.
- When the investigation splits into safe bounded lanes, route, integrate, and decide rather than manually performing every lane sequentially.
```

with:

```markdown
- You may perform focused leader-inline evidence work when the investigation is small and single-lane.
- When the investigation splits into safe bounded lanes, route, integrate, and decide rather than manually performing every lane sequentially.
```

- [ ] **Step 7: Update debug session lifecycle fixing rule**

In `templates/commands/debug.md`, in `## Session Lifecycle`, replace step 4 bullets:

```markdown
   - Packetize the smallest safe fix that addresses the confirmed root cause and delegate it through a validated subagent lane.
   - If the fix lane cannot be safely packetized or dispatched, record `subagent-blocked` with the escalation or recovery reason instead of making the fix directly.
```

with:

```markdown
   - Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`.
   - When `execution_model: subagent-assisted`, delegate the fix through a validated subagent lane and integrate the returned handoff on the leader path.
   - When the fix cannot proceed safely, cannot be packetized, or cannot be verified, record `subagent-blocked` with `execution_surface: none` and a concrete blocked reason instead of layering a speculative fix.
```

- [ ] **Step 8: Update capability-aware investigation routing**

In `templates/commands/debug.md`, in `## Capability-Aware Investigation`, replace the decision-field and decision-order bullets with:

```markdown
- [AGENT] Use the shared policy function with the current capability snapshot when the investigation has safe delegated lanes: `choose_subagent_dispatch(command_name="debug", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: leader-inline | subagent-assisted | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `dispatch_reason`, and `blocked_reason` when blocked.
- Treat runtime safety as a dispatch-blocking decision. If the next step is unsafe, unavailable, or unpacketizable, use `subagent-blocked`, record `execution_surface: none`, and stop instead of widening brittle native fan-out.
- Debug routing decision order:
  - Small focused investigation with one short evidence chain -> `leader-inline`.
  - One safe validated evidence lane where isolation improves quality -> `one-subagent` on `native-subagents` when available.
  - Two or more independent evidence lanes -> `parallel-subagents` on `native-subagents` when available.
  - No safe lane, shared mutable state, missing contract, incomplete packet, unavailable delegation, or unsafe next step -> `subagent-blocked` with `execution_surface: none` and a recorded reason.
```

Replace:

```markdown
- Dispatch that single subagent only when the evidence-lane contract is complete: probe intent, required evidence, authoritative inputs, and validation targets must all be recorded before dispatch.
```

with:

```markdown
- Dispatch a subagent only when the evidence-lane contract is complete: probe intent, required evidence, authoritative inputs, and validation targets must all be recorded before dispatch.
```

- [ ] **Step 9: Update Fix and Verify protocol**

In `templates/commands/debug.md`, replace:

```markdown
- Apply the minimum code change needed to address that root cause.
```

with:

```markdown
- Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`; when `execution_model: subagent-assisted`, delegate the fix through a validated subagent lane and integrate the returned evidence on the leader path.
```

Add this bullet immediately after it:

```markdown
- If the fix cannot proceed safely, cannot be packetized for the selected execution path, or cannot be verified, record `subagent-blocked` with `execution_surface: none` and a concrete `blocked_reason`.
```

- [ ] **Step 10: Update the debug command partial**

In `templates/command-partials/debug/shell.md`, add this bullet to the `## Context` list:

```markdown
- Debug execution is complexity-based: small focused investigations may stay leader-inline, while broad or independent evidence lanes use one or more subagents.
```

Add this bullet to `## Guardrails`:

```markdown
- No subagent-assisted work may continue without a safe lane; blocked debug execution records `subagent-blocked`, `execution_surface: none`, and a concrete blocked reason.
```

- [ ] **Step 11: Run debug template tests and confirm GREEN**

Run:

```powershell
uv run pytest -q tests/test_debug_template_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_alignment_templates.py
```

Expected: tests pass, or failures point only to assertions that still intentionally reference old debug mandatory wording and need the same direct replacement.

- [ ] **Step 12: Commit the debug template change**

Run:

```powershell
git add tests/test_debug_template_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_alignment_templates.py templates/commands/debug.md templates/command-partials/debug/shell.md
git commit -m "feat: make debug execution complexity based"
```

## Task 4: Update Shared Integration Renderers

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `src/specify_cli/integrations/base.py`

- [ ] **Step 1: Update rendered base Markdown expectations**

In `tests/integrations/test_integration_base_markdown.py`, update `test_debug_and_quick_commands_have_shared_leader_and_routing_sections()`:

Replace debug assertions:

```python
        assert "execution_model: subagent-mandatory" in debug_content or "execution model: `subagents-first`" in debug_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in debug_content
        assert "execution_surface: native-subagents" in debug_content or "execution surface: `native-subagents`" in debug_content
```

with:

```python
        assert "execution_model: leader-inline | subagent-assisted | blocked" in debug_content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in debug_content
        assert "execution_surface: leader-inline | native-subagents | none" in debug_content
        assert "small focused investigation" in debug_content
        assert "subagent-assisted" in debug_content
```

Replace quick assertions:

```python
        assert "quick execution routing" in quick_content
        assert "execution_model: subagent-mandatory" in quick_content or "execution model: `subagents-first`" in quick_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in quick_content
        assert "execution_surface: native-subagents" in quick_content
```

with:

```python
        assert "quick execution routing" in quick_content
        assert "understanding checkpoint" in quick_content
        assert "understanding_confirmed: true" in quick_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in quick_content
        assert "execution_surface: native-subagents" in quick_content
```

- [ ] **Step 2: Update rendered base skills expectations**

In `tests/integrations/test_integration_base_skills.py`, make the same replacement in `test_debug_and_quick_skills_have_shared_leader_and_routing_sections()`.

- [ ] **Step 3: Update non-Codex generated skill expectations**

In `tests/integrations/test_cli.py`, update `test_non_codex_shared_workflow_skills_use_canonical_strategy_language()` so the mandatory loop excludes debug:

```python
        for skill_name in ("sp-specify", "sp-explain"):
            content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "execution_model: subagent-mandatory" in content
            assert "dispatch_shape: one-subagent | parallel-subagents" in content
            assert "execution_surface: native-subagents" in content
            assert "specify team" not in content
```

Add these debug assertions after `debug_content` is read:

```python
        assert "execution_model: leader-inline | subagent-assisted | blocked" in debug_content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in debug_content
        assert "execution_surface: leader-inline | native-subagents | none" in debug_content
        assert "small focused investigation" in debug_content
        assert "subagent-assisted" in debug_content
```

Add these quick assertions after the project cognition assertions:

```python
        assert "understanding checkpoint" in quick_content
        assert "understanding_confirmed" in quick_content
```

- [ ] **Step 4: Run integration base tests and confirm RED**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_base_markdown.py::TestMarkdownIntegrationBase::test_debug_and_quick_commands_have_shared_leader_and_routing_sections tests/integrations/test_integration_base_skills.py::TestSkillsIntegrationBase::test_debug_and_quick_skills_have_shared_leader_and_routing_sections
```

If the class names differ in the current checkout, run:

```powershell
uv run pytest -q tests/integrations/test_integration_base_markdown.py -k "debug_and_quick" tests/integrations/test_integration_base_skills.py -k "debug_and_quick"
```

Also run the non-Codex generated skill test:

```powershell
uv run pytest -q tests/integrations/test_cli.py::TestCLI::test_non_codex_shared_workflow_skills_use_canonical_strategy_language
```

If the class name differs in the current checkout, run:

```powershell
uv run pytest -q tests/integrations/test_cli.py -k "canonical_strategy_language"
```

Expected: failures show stale shared renderer text in `base.py` or generated skill assertions that still expect old debug mandatory wording.

- [ ] **Step 5: Update `_append_debug_leader_gate()`**

In `src/specify_cli/integrations/base.py`, inside `_append_debug_leader_gate()`, replace the addendum body after the project cognition line with this wording:

```python
            "Before applying fixes or running investigation actions:\n"
            "- Read the current debug session state and choose `execution_model: leader-inline | subagent-assisted | blocked` from the investigation shape.\n"
            "- Use `leader-inline` for a small focused investigation with one short evidence chain.\n"
            "- Use `subagent-assisted` when there are two or more independent evidence-gathering lanes, broad surface area, or meaningful parallelism.\n"
            "- If the next step is unsafe, unavailable, or unpacketizable, record `subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason` before stopping.\n"
            "- Rejoin only at the current investigation join point, then integrate returned results on the leader path.\n"
            "\n"
            "**Hard rule:** During `investigating`, the leader must not let subagents mutate the debug file, declare the root cause final, or advance the session state.\n"
```

- [ ] **Step 6: Update `_append_debug_routing_contract()`**

In `_append_debug_routing_contract()`, replace the addendum body with:

```python
        addendum = (
            "\n"
            f"## {agent_name} Investigation Routing Contract\n\n"
            f"When running `sp-debug` in {agent_name}, treat `investigating` as a complexity-based leader decision.\n"
            "- Execution model: `leader-inline | subagent-assisted | blocked`.\n"
            "- Dispatch shape: `leader-inline`, `one-subagent`, `parallel-subagents`, or `subagent-blocked`.\n"
            "- Execution surface: `leader-inline`, `native-subagents`, or `none`.\n"
            f"- Subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Integration-native join point: {descriptor.native_join_hint}\n"
            f"- Fallback path: {managed_team_hint}\n"
            "- Small focused investigation -> `leader-inline`.\n"
            "- One safe isolated evidence lane -> `one-subagent` when the current runtime supports it safely.\n"
            "- Two or more independent evidence lanes -> `parallel-subagents` when the current runtime supports it safely.\n"
            "- Unsafe, unavailable, or unpacketizable next step -> `subagent-blocked` with `execution_surface: none` and `blocked_reason`.\n"
            "- Suitable subagent tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing subagent lanes.\n"
            "- Subagents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, or transition the session state.\n"
            "- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
        )
```

- [ ] **Step 7: Update `_append_quick_leader_gate()`**

In `_append_quick_leader_gate()`, insert these bullets after the `STATUS.md` bullet:

```python
            "- If `understanding_confirmed` is not `true`, present the Understanding Checkpoint and wait for user confirmation before implementation work.\n"
            "- The checkpoint must cover `Problem understood`, `Planned outcome`, `Scope boundary`, `Execution approach`, and `Validation`.\n"
            "- Do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded in `STATUS.md`.\n"
```

Replace:

```python
            "- Define the smallest safe delegated lane or ready batch, and choose the `subagents-first` dispatch shape for that batch.\n"
```

with:

```python
            "- After understanding is confirmed, define the smallest safe delegated lane or ready batch, and choose the dispatch shape for that batch.\n"
```

- [ ] **Step 8: Update `_append_quick_routing_contract()`**

In `_append_quick_routing_contract()`, replace:

```python
            f"When running `sp-quick` in {agent_name}, use `subagents-first` execution after `STATUS.md` exists.\n"
```

with:

```python
            f"When running `sp-quick` in {agent_name}, do not start execution routing until `STATUS.md` exists and `understanding_confirmed: true` is recorded.\n"
```

Add this bullet after the execution surface bullet:

```python
            "- Understanding checkpoint: confirm the problem, planned outcome, scope boundary, execution approach, and validation evidence before dispatch.\n"
```

- [ ] **Step 9: Update `_augment_debug_skill()`**

In `_augment_debug_skill()`, update the generated leader gate and `Subagent Evidence Collection` addenda with the same debug wording from Steps 4 and 5. Keep `spawn_agent`, `wait_agent`, and `close_agent` in Codex-capable text, but remove blanket phrases that say debug is `subagents-first` for the whole investigating stage.

The first sentence of the evidence section should become:

```python
            f"When running `sp-debug` in {agent_name}, choose leader-inline or subagent-assisted evidence collection from the investigation shape.\n"
```

- [ ] **Step 10: Update `_augment_quick_skill()`**

In `_augment_quick_skill()`, add the quick checkpoint bullets from Step 6 and replace:

```python
            f"When running `sp-quick` in {agent_name}, use `subagents-first` execution after `STATUS.md` exists.\n"
```

with:

```python
            f"When running `sp-quick` in {agent_name}, start execution routing only after `STATUS.md` exists and `understanding_confirmed: true` is recorded.\n"
```

- [ ] **Step 11: Run integration base tests and confirm GREEN**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_base_markdown.py -k "debug_and_quick" tests/integrations/test_integration_base_skills.py -k "debug_and_quick"
uv run pytest -q tests/integrations/test_cli.py -k "canonical_strategy_language"
```

Expected: tests pass.

- [ ] **Step 12: Commit shared renderer changes**

Run:

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py src/specify_cli/integrations/base.py
git commit -m "feat: align shared quick debug renderers"
```

## Task 5: Update Cursor Quick Addendum

**Files:**
- Modify: `tests/integrations/test_integration_cursor_agent.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`

- [ ] **Step 1: Update Cursor generated quick test expectations**

In `tests/integrations/test_integration_cursor_agent.py`, rename:

```python
def test_cursor_generated_sp_quick_prefers_subagent_execution(tmp_path):
```

to:

```python
def test_cursor_generated_sp_quick_confirms_understanding_before_execution(tmp_path):
```

Replace:

```python
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
```

with:

```python
    assert "understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
```

Replace:

```python
    assert "dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis" in content
```

with:

```python
    assert "do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded" in content
```

Replace:

```python
    assert "the next concrete action must be dispatch" in content
```

with:

```python
    assert "start execution routing only after `status.md` exists and `understanding_confirmed: true` is recorded" in content
```

- [ ] **Step 2: Run Cursor integration test and confirm RED**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_cursor_agent.py::test_cursor_generated_sp_quick_confirms_understanding_before_execution
```

Expected: fails because Cursor-specific quick augmentation still says `subagents-first execution after STATUS.md exists`.

- [ ] **Step 3: Update Cursor leader gate**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, in `_augment_quick_skill()`, add these bullets after the `STATUS.md` bullet in the `Cursor Leader Gate` addendum:

```python
                "- If `understanding_confirmed` is not `true`, present the Understanding Checkpoint and wait for user confirmation before implementation work.\n"
                "- The checkpoint must cover `Problem understood`, `Planned outcome`, `Scope boundary`, `Execution approach`, and `Validation`.\n"
                "- Do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded in `STATUS.md`.\n"
```

Replace:

```python
                "- Define the smallest safe delegated lane or ready batch.\n"
```

with:

```python
                "- After understanding is confirmed, define the smallest safe delegated lane or ready batch.\n"
```

- [ ] **Step 4: Update Cursor quick execution addendum**

In the `Cursor Subagent Execution` addendum, replace:

```python
            "When running `sp-quick` in Cursor, use subagents-first execution after `STATUS.md` exists.\n"
```

with:

```python
            "When running `sp-quick` in Cursor, start execution routing only after `STATUS.md` exists and `understanding_confirmed: true` is recorded.\n"
```

Replace:

```python
            "- Dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis.\n"
```

with:

```python
            "- Dispatch `one-subagent` or `parallel-subagents` only after the Understanding Checkpoint is confirmed.\n"
```

- [ ] **Step 5: Run Cursor integration test and confirm GREEN**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_cursor_agent.py
```

Expected: Cursor tests pass.

- [ ] **Step 6: Commit Cursor changes**

Run:

```powershell
git add tests/integrations/test_integration_cursor_agent.py src/specify_cli/integrations/cursor_agent/__init__.py
git commit -m "feat: align cursor quick checkpoint"
```

## Task 6: Update Codex Generated Asset Tests

**Files:**
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/test_quick_skill_mirror.py`

- [ ] **Step 1: Update Codex debug generated test expectations**

In `tests/integrations/test_integration_codex.py`, in `test_codex_generated_sp_debug_includes_leader_led_native_investigation_guidance()`, add these assertions after the project cognition assertions:

```python
    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "small focused investigation" in content
    assert "subagent-assisted" in content
    assert "execution_surface: none" in content
```

Replace any assertion in that test requiring debug `subagents-first` with the assertions above.

- [ ] **Step 2: Update Codex quick generated test expectations**

In `test_codex_generated_sp_quick_supports_lightweight_tracked_execution()`, replace:

```python
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
```

with:

```python
    assert "understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
```

Add:

```python
    assert "problem understood" in content
    assert "planned outcome" in content
    assert "scope boundary" in content
    assert "execution approach" in content
    assert "confirmed_validation" in content
```

- [ ] **Step 3: Update quick skill mirror expectations**

In `tests/test_quick_skill_mirror.py`, replace:

```python
    assert "execution_model: subagent-mandatory" in body
```

with:

```python
    assert "understanding checkpoint" in body
    assert "understanding_confirmed: true" in body
```

- [ ] **Step 4: Run Codex generated asset tests**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_codex.py::test_codex_generated_sp_debug_includes_leader_led_native_investigation_guidance tests/integrations/test_integration_codex.py::test_codex_generated_sp_quick_supports_lightweight_tracked_execution tests/test_quick_skill_mirror.py
```

Expected: pass after Tasks 2, 3, and 4; failures indicate stale Codex-specific renderer wording that must be removed from `src/specify_cli/integrations/base.py` because Codex uses the shared augmentation path.

- [ ] **Step 5: Commit Codex test alignment**

Run:

```powershell
git add tests/integrations/test_integration_codex.py tests/test_quick_skill_mirror.py
git commit -m "test: align codex quick debug generated assets"
```

## Task 7: Update Passive Skills And Docs

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_alignment_templates.py` if README or handbook assertions quote the old quick/debug wording.
- Modify: `tests/test_agent_context_managed_block.py` if managed AGENTS block assertions quote old quick/debug wording.
- Modify: `tests/test_passive_skill_guidance.py` if passive skill assertions quote old mandatory-subagent wording.

- [ ] **Step 1: Find stale docs and passive skill wording**

Run:

```powershell
rg -n "sp-debug|sp-quick|subagent-mandatory|subagents-first|mandatory-subagent|leader \\+ subagents|execution_model: subagent-mandatory" README.md PROJECT-HANDBOOK.md templates/passive-skills tests
```

Expected: output includes the passive skills and docs listed in this task. Keep output available while editing.

- [ ] **Step 2: Update workflow routing passive skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace the guidance around quick/debug execution defaults with:

```markdown
- For `sp-quick`, perform the workflow's one-time Understanding Checkpoint before substantive execution; after confirmation, use delegated lanes when the quick task has safe packetized work.
- For `sp-debug`, use leader-inline for small focused investigations and subagent-assisted execution for broad, independent, or parallel evidence lanes.
- For `sp-map-scan`, `sp-map-build`, and `sp-implement`, leader + subagents remains the default execution shape for independent bounded lanes when the current runtime supports delegation.
```

- [ ] **Step 3: Update subagent-driven-development passive skill**

In `templates/passive-skills/subagent-driven-development/SKILL.md`, replace the sentence that lists subagents as execution workers behind `sp-quick`, `sp-debug`, map, and implement with:

```markdown
Subagents are execution workers behind packetized `sp-quick` work after understanding confirmation, broad or independent `sp-debug` evidence lanes, `sp-map-scan`, `sp-map-build`, and `sp-implement`.
```

Replace any red flag saying debug must not run leader-inline because it looks small with:

```markdown
- Doing leader-inline work after a `sp-debug` route selected `subagent-assisted` or after independent evidence lanes are available, without recording why the investigation remains small and focused.
```

- [ ] **Step 4: Update dispatching-parallel-agents passive skill**

In `templates/passive-skills/dispatching-parallel-agents/SKILL.md`, keep `sp-debug` as a valid parallel route but clarify:

```markdown
`sp-debug` dispatches parallel agents only when the investigation exposes independent evidence lanes; small focused investigations may stay leader-inline under the debug session contract.
```

- [ ] **Step 5: Update README workflow guidance**

In `README.md`, update the lightweight work and orchestration sections:

Replace statements that say `sp-debug` remains mandatory-subagent with:

```markdown
- `sp-debug` is complexity-based: small focused investigations may run leader-inline, while broad or independent evidence lanes use one or more subagents. Unsafe or unavailable dispatch remains `subagent-blocked` with `execution_surface: none`.
```

Add to the quick routing guide:

```markdown
- `sp-quick` performs one Understanding Checkpoint before substantive execution. The agent states the understood problem, planned outcome, scope boundary, execution approach, and validation evidence, then waits for confirmation before continuing.
```

- [ ] **Step 6: Update PROJECT-HANDBOOK maintainer guidance**

In `PROJECT-HANDBOOK.md`, update the workflow contract generation section so it says:

```markdown
`sp-quick` now includes a one-time Understanding Checkpoint before substantive execution. `sp-debug` is complexity-based: leader-inline for small focused investigations, subagent-assisted for broad or independent evidence lanes, and blocked with `execution_surface: none` when the next safe step cannot proceed.
```

- [ ] **Step 7: Run passive/doc tests**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py tests/test_passive_skill_guidance.py tests/test_agent_context_managed_block.py
```

Expected: tests pass, or failures point to remaining old wording in docs/passive skills or assertions that should be updated to the new quick/debug contract.

- [ ] **Step 8: Commit docs and passive skill updates**

Run:

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/dispatching-parallel-agents/SKILL.md README.md PROJECT-HANDBOOK.md tests
git commit -m "docs: update quick debug execution guidance"
```

## Task 8: Full Targeted Verification

**Files:**
- No production edits expected.

- [ ] **Step 1: Run template and integration regression set**

Run:

```powershell
uv run pytest -q `
  tests/orchestration/test_models.py `
  tests/test_quick_template_guidance.py `
  tests/test_debug_template_guidance.py `
  tests/test_subagent_mandatory_template_guidance.py `
  tests/test_alignment_templates.py `
  tests/test_quick_skill_mirror.py `
  tests/integrations/test_integration_base_markdown.py `
  tests/integrations/test_integration_base_skills.py `
  tests/integrations/test_cli.py `
  tests/integrations/test_integration_codex.py `
  tests/integrations/test_integration_cursor_agent.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Search for stale contradictory wording**

Run:

```powershell
rg -n "sp-debug.*subagent-mandatory|debug.*subagents-first|debug.*execution_model: subagent-mandatory|sp-quick.*runs? to completion without confirmation|quick.*subagents-first execution after `?STATUS\\.md`? exists|execution_model: leader-inline \\| subagent-assisted \\| blocked" templates src tests README.md PROJECT-HANDBOOK.md docs\\superpowers\\specs\\2026-05-23-quick-debug-execution-design.md
```

Expected:

- No stale `sp-debug` mandatory/subagents-first wording remains outside historical docs or tests for other workflows.
- `execution_model: leader-inline | subagent-assisted | blocked` appears in debug template/session/docs/tests only, not in `src/specify_cli/orchestration/models.py`.

- [ ] **Step 3: Inspect git diff**

Run:

```powershell
git diff --stat
git diff -- templates src tests README.md PROJECT-HANDBOOK.md
```

Expected:

- No unrelated generated artifacts.
- No broad runtime rewrite of orchestration schema.
- Quick checkpoint appears in templates and generated integration addenda.
- Debug complexity-based execution appears in templates and generated integration addenda.

- [ ] **Step 4: Commit verification-only fixes if needed**

If Step 1 or Step 2 required small cleanup edits, commit them:

```powershell
git add templates src tests README.md PROJECT-HANDBOOK.md
git commit -m "chore: finish quick debug execution alignment"
```

If no cleanup edits were needed, do not create an empty commit.

## Task 9: Final Review Checklist

**Files:**
- No file edits expected.

- [ ] **Step 1: Confirm source spec coverage**

Open `docs/superpowers/specs/2026-05-23-quick-debug-execution-design.md` and check each design section against the implemented diff:

```powershell
Get-Content docs\\superpowers\\specs\\2026-05-23-quick-debug-execution-design.md
git diff f075a04..HEAD --stat
```

Expected coverage:

- Quick checkpoint is present.
- Quick status/resume gate is present.
- Debug leader-inline and subagent-assisted paths are present.
- Debug blocked path is present.
- Integration renderers are updated.
- Integration-rendered asset tests are updated.

- [ ] **Step 2: Confirm final repository status**

Run:

```powershell
git status --short
git log --oneline -n 10
```

Expected: clean worktree except for user-owned unrelated changes. Recent commits should correspond to the tasks above.

- [ ] **Step 3: Prepare final implementation report**

Report these items:

```markdown
Implemented:
- `sp-quick` Understanding Checkpoint and `STATUS.md` confirmation gate.
- `sp-debug` complexity-based execution and blocked state preservation.
- Shared and Cursor-specific integration renderers.
- Generated asset tests for Markdown, skills, Codex, and Cursor.
- README, handbook, and passive skill guidance.

Verified:
- Targeted pytest command from Task 8 completed successfully.
- Stale wording search from Task 8 found no contradictory quick/debug execution guidance.

Runtime schema decision:
- Shared orchestration `ExecutionModel` remains `subagent-mandatory | adaptive`.
- Debug `leader-inline | subagent-assisted | blocked` is session/template vocabulary only.
```
