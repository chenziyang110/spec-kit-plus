# Inline Project Cognition Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every source-changing `sp-*` workflow perform workflow-owned inline project cognition update during closeout, with `sp-map-update` reserved for external/manual maintenance and `mark-dirty` reserved for fallback.

**Architecture:** This is a contract and generated-guidance change over the existing runtime. The implementation updates template tests first, then rewrites shared project-cognition guidance, mutation workflow closeouts, integration addenda, and docs to teach the existing MVP command path: `project-cognition delta append` plus `project-cognition update --delta-session --reason workflow-finalize`, with `update --changed-path/--scope --reason workflow-finalize` as the no-session fallback.

**Tech Stack:** Python `pytest`, Markdown command templates, passive skill templates, `IntegrationBase` generated addenda, existing Go `project-cognition` CLI command contract.

---

## File Structure

- `tests/test_alignment_templates.py`: central regression tests for shared template and workflow contract wording.
- `tests/test_fast_template_guidance.py`: focused regression for `sp-fast` closeout wording.
- `tests/test_debug_template_guidance.py`: focused regression for `sp-debug` closeout wording.
- `tests/test_constitution_defaults.py`: generated constitution template expectations.
- `tests/integrations/test_integration_base_markdown.py`: generated Markdown integration guidance expectations.
- `tests/integrations/test_integration_base_skills.py`: generated skills integration guidance expectations.
- `tests/integrations/test_integration_base_toml.py`: generated TOML integration guidance expectations.
- `tests/integrations/test_integration_cursor_agent.py`: Cursor-specific project cognition advisory expectations.
- `tests/integrations/test_integration_codex.py`: Codex-specific generated skill expectations.
- `templates/command-partials/common/context-loading-gradient.md`: runtime-facing context and mutation closeout contract.
- `templates/command-partials/common/planning-context-loading-gradient.md`: planning-only entry guidance plus source-change escape hatch.
- `templates/command-partials/common/senior-consequence-analysis-gate.md`: consequence gate distinction between entry routing and closeout ownership.
- `templates/command-partials/common/navigation-check.md`: legacy partial, advisory entry-only language.
- `templates/command-partials/fast/shell.md`: fast-path shell contract.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: passive cognition gate used by generated projects.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: passive workflow routing guidance.
- `templates/commands/fast.md`: source-changing closeout wording for fast path.
- `templates/commands/quick.md`: source-changing closeout wording for quick tasks.
- `templates/commands/implement.md`: source-changing closeout wording for implementation.
- `templates/commands/debug.md`: source-changing closeout wording for debug fixes.
- `templates/commands/constitution.md`: governance mutation closeout wording.
- `templates/commands/specify.md`, `templates/commands/clarify.md`, `templates/commands/plan.md`, `templates/commands/tasks.md`: artifact-only exemption plus source/runtime/template mutation escape hatch.
- `templates/project-handbook-template.md`: generated handbook project cognition lifecycle wording.
- `templates/constitution-template.md`: generated constitution cognition principle wording.
- `src/specify_cli/integrations/base.py`: generated addenda for planning skills, checklist skills, and runtime-facing commands.
- `src/specify_cli/integrations/cursor_agent/__init__.py`: Cursor-specific advisory addendum.
- `README.md` and `PROJECT-HANDBOOK.md`: repository-facing lifecycle documentation.

---

### Task 1: Red Tests for Inline Closeout Contract

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Update the mutation workflow regression test**

In `tests/test_alignment_templates.py`, replace `test_mutation_workflows_require_cognition_refresh_or_dirty_outcome_before_closeout` with:

```python
def test_mutation_workflows_require_inline_cognition_update_before_dirty_fallback() -> None:
    for path in (
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
    ):
        content = _read(path).lower()

        assert "project_cognition_refresh" in content
        assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
        assert "project-cognition delta append" in content
        assert "project-cognition update --delta-session" in content
        assert "project-cognition update --changed-path" in content
        assert "persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`" in content
        assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
        assert "project-cognition mark-dirty" in content
        assert "dirty only when inline update" in content

        for stale_closeout_phrase in (
            "actual `{{invoke:map-update}}` refresh",
            "refresh the project cognition runtime through `{{invoke:map-update}}` using the changed paths",
            "if the fast-path change unexpectedly touched",
            "tell the user to run `{{invoke:map-update}}` with the changed paths before the next brownfield workflow proceeds",
            "project_cognition_refresh` recommending",
            "project_cognition_refresh recommending",
            "recommended `{{invoke:map-update}}` refresh when applicable",
            "recommended `{{invoke:map-update}}` refresh when project cognition might be affected",
            "and recommend `{{invoke:map-update}}` with the changed paths",
        ):
            assert stale_closeout_phrase not in content
```

- [ ] **Step 2: Add a shared surface regression test**

In `tests/test_alignment_templates.py`, add this test immediately after the mutation workflow test:

```python
def test_inline_cognition_closeout_shared_surfaces_are_consistent() -> None:
    required_paths = (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/command-partials/common/senior-consequence-analysis-gate.md",
        "templates/command-partials/common/navigation-check.md",
        "templates/command-partials/fast/shell.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        "templates/commands/constitution.md",
        "templates/project-handbook-template.md",
        "templates/constitution-template.md",
    )

    for path in required_paths:
        content = _read(path).lower()
        assert "workflow-owned mutation closeout" in content, path
        assert "external map maintenance" in content, path
        assert "inline project cognition update" in content, path
        assert "sp-map-update is for manual/external maintenance" in content, path

    for path in (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    ):
        content = _read(path).lower()
        assert "entry-time stale or weak cognition is still an advisory navigation concern" in content
        assert "does not waive closeout ownership" in content

    passive_gate = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md").lower()
    assert "do not silently switch into `sp-map-update`" not in passive_gate
    assert "user-invoked workflow handoff" not in passive_gate
```

- [ ] **Step 3: Update fast template expectations**

In `tests/test_fast_template_guidance.py`, replace lines asserting the old `{{invoke:map-update}}` closeout with:

```python
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "project-cognition delta append" in content
    assert "project-cognition update --delta-session" in content
    assert "project-cognition update --changed-path" in content
    assert "persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "dirty only when inline update" in content
    assert "actual `{{invoke:map-update}}` refresh" not in content
    assert "if the fast-path change unexpectedly touched" not in content
```

Keep the existing assertions for `changed_code_paths`, `changed_behavior_surfaces`, `verification_evidence`, `project_cognition_refresh`, `known unknowns`, rebuild conditions, `complete-refresh`, and `manual override/fallback`.

- [ ] **Step 4: Update debug template expectations**

In `tests/test_debug_template_guidance.py`, replace the old closeout assertion:

```python
    assert "refresh the project cognition runtime through `{{invoke:map-update}}` using the changed paths before moving to `awaiting_human_verify` or `resolved`" in content
```

with:

```python
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "project-cognition delta append" in content
    assert "project-cognition update --delta-session" in content
    assert "project-cognition update --changed-path" in content
    assert "persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "dirty only when inline update" in content
```

- [ ] **Step 5: Run red tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_mutation_workflows_require_inline_cognition_update_before_dirty_fallback tests/test_alignment_templates.py::test_inline_cognition_closeout_shared_surfaces_are_consistent tests/test_fast_template_guidance.py::test_fast_template_exists_and_defines_scope_gate tests/test_debug_template_guidance.py::test_debug_template_enforces_resolution_closeout -q
```

Expected: FAIL because templates still use `{{invoke:map-update}}` closeout wording and shared surfaces still preserve user-handoff language.

- [ ] **Step 6: Commit red tests**

```powershell
git add -- tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_debug_template_guidance.py
git commit -m "test: require inline cognition closeout"
```

---

### Task 2: Red Tests for Generated Addenda and Docs

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_cursor_agent.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/test_constitution_defaults.py`

- [ ] **Step 1: Update shared integration runtime guidance assertions**

In each of these files:

- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_base_toml.py`

Update `_assert_runtime_cognition_carry_forward` so the closeout section asserts:

```python
    assert "mutation closeout" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "inline project cognition update" in content
    assert "project-cognition delta append" in content
    assert "project-cognition update --delta-session" in content
    assert "project-cognition update --changed-path" in content
    assert "persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "actual `{{invoke:map-update}}` refresh" not in content
    assert "project_cognition_refresh` recommending" not in content
    assert "project_cognition_refresh recommending" not in content
    assert "recommends `{{invoke:map-update}}` as follow-up map maintenance" not in content
    assert "recommended `{{invoke:map-update}}` refresh when applicable" not in content
```

- [ ] **Step 2: Add generated planning skill assertions**

In `tests/integrations/test_integration_base_skills.py`, inside the test that reads generated `sp-specify`, `sp-plan`, and `sp-tasks` skills, add assertions that artifact-only work stays exempt but actual source/runtime changes require inline update:

```python
        assert "artifact-only" in content
        assert "do not call `project-cognition mark-dirty`" in content
        assert "if this planning workflow makes actual source/runtime/template/config/test/generated-asset changes" in content
        assert "run inline project cognition update" in content
        assert "sp-map-update is for manual/external maintenance" in content
```

Use the local variable name already used in that test for generated skill body content.

- [ ] **Step 3: Update Cursor-specific assertions**

In `tests/integrations/test_integration_cursor_agent.py`, update the Cursor advisory test to assert:

```python
            assert "entry advisory is not closeout ownership" in content
            assert "workflow-owned mutation closeout" in content
            assert "inline project cognition update" in content
            assert "sp-map-update is for manual/external maintenance" in content
```

- [ ] **Step 4: Update Codex-specific assertions**

In `tests/integrations/test_integration_codex.py`, update the generated runtime-facing skill assertions for `sp-quick`, `sp-implement`, and `sp-debug` so they include:

```python
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "project-cognition update --delta-session" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
```

- [ ] **Step 5: Update generated constitution expectation**

In `tests/test_constitution_defaults.py`, replace:

```python
    assert "Recommend `map-update`" in content
```

with:

```python
    assert "Workflow-owned mutation closeout" in content
    assert "run inline project cognition update" in content
    assert "sp-map-update is for manual/external maintenance" in content
```

- [ ] **Step 6: Run red generated-surface tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_codex.py tests/test_constitution_defaults.py -q
```

Expected: FAIL because generated addenda and templates still use the old refresh-or-dirty and follow-up wording.

- [ ] **Step 7: Commit generated-surface red tests**

```powershell
git add -- tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_codex.py tests/test_constitution_defaults.py
git commit -m "test: align generated cognition closeout contract"
```

---

### Task 3: Update Shared Project Cognition Guidance

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/command-partials/fast/shell.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`

- [ ] **Step 1: Replace the mutation closeout rule in `context-loading-gradient.md`**

In `templates/command-partials/common/context-loading-gradient.md`, replace the current `### Mutation Closeout Rule` section with:

```markdown
### Mutation Closeout Rule

Entry-time stale or weak cognition is still an advisory navigation concern unless the user explicitly requested map maintenance. A workflow may continue from live evidence when entry guidance allows it. That entry routing rule does not waive closeout ownership: once the workflow itself changes project-related files or behavior, it must run inline project cognition update for its own changes.

Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run inline project cognition update from the workflow-owned ledger:

1. Append closeout evidence to the current delta session when one exists using `project-cognition delta append --session "$DELTA_SESSION_ID" --event-type workflow_closeout --changed-path "<path>" --behavior-surface "<surface>" --verification "<evidence>" --format json`.
2. Finalize with `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; include `--commit-range "<base>..<head>"` only with `--delta-session` when a safe task commit boundary exists.
3. If no delta session exists, use `project-cognition update --changed-path "<path>" --scope "<affected-scope>" --reason workflow-finalize --format json`.

A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`. Use `project-cognition mark-dirty --reason "<reason>" --format json` only when inline update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.

`sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is not routine cleanup for changes this workflow just made.
```

- [ ] **Step 2: Update entry guidance in `context-loading-gradient.md`**

Keep the `missing` and `stale` bullets as advisory entry guidance, but change "follow-up map maintenance" wording to avoid implying closeout handoff:

```markdown
- `missing` -> if cognition freshness is `missing`, continue with live repository evidence and recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as external baseline maintenance
- `stale` -> if cognition freshness is `stale`, treat map output as advisory and continue with live repository evidence; recommend `{{invoke:map-update}}` only as external/manual maintenance when the user asks for map maintenance or before a separate map repair pass
```

- [ ] **Step 3: Add source-change closeout escape hatch to `planning-context-loading-gradient.md`**

In `templates/command-partials/common/planning-context-loading-gradient.md`, after the existing advisory bullets, add:

```markdown
Planning-only artifact writes do not require project cognition refresh. If this planning workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, it stops being artifact-only for closeout: run inline project cognition update using the workflow-owned changed paths and affected surfaces. `sp-map-update` is for manual/external maintenance, not routine cleanup for changes this workflow just made.
```

Also change the stale bullet to use "external/manual maintenance" instead of "follow-up map maintenance."

- [ ] **Step 4: Update `senior-consequence-analysis-gate.md`**

Replace the final sentence of the first paragraph with:

```markdown
Mutation closeout is separate from entry routing: entry stale may continue, but that does not allow source/runtime mutation workflows to defer closeout. Workflow-owned mutation closeout is not an external map-maintenance handoff; after changing project-related files or behavior, the workflow must run inline project cognition update from its changed paths, affected surfaces, and verification evidence, with `project-cognition mark-dirty` only as fallback when inline update cannot complete.
```

- [ ] **Step 5: Update `navigation-check.md`**

Add this paragraph after the existing bullets:

```markdown
This navigation check is entry-only. Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is separate: if the current workflow changes project-related files or behavior, run inline project cognition update before successful completion. `sp-map-update` is for manual/external maintenance and follow-up repair.
```

- [ ] **Step 6: Update `templates/command-partials/fast/shell.md`**

Replace the current line:

```markdown
- Do not call `project-cognition mark-dirty` as a completion requirement for fast-path work; map maintenance stays follow-up-only unless actual source/runtime changes occur.
```

with:

```markdown
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If fast-path work changes project-related source, runtime, templates, config, tests, generated assets, or behavior-bearing docs, run inline project cognition update from the changed paths before completion; use `project-cognition mark-dirty` only when inline update cannot complete.
```

- [ ] **Step 7: Update `spec-kit-project-cognition-gate/SKILL.md`**

Replace the existing mutation closeout and user-invoked handoff bullets at lines around 142-153 with:

```markdown
- Entry-time stale or weak cognition is still an advisory navigation concern unless the user explicitly requested map maintenance. A workflow may continue from live evidence when entry guidance allows it. That entry routing rule does not waive closeout ownership.
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run inline project cognition update from the workflow-owned ledger.
- Inline update uses the current lower-level runtime path: append closeout evidence with `project-cognition delta append` when a delta session exists, then run `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; without a delta session, run `project-cognition update --changed-path "<path>" --scope "<affected-scope>" --reason workflow-finalize --format json`.
- A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`. Use `project-cognition mark-dirty --reason "<reason>" --format json` only when inline update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.
- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is not routine cleanup for changes this workflow just made.
```

- [ ] **Step 8: Update `spec-kit-workflow-routing/SKILL.md`**

Under the map-update routing bullets, add:

```markdown
- `sp-map-update` is the external/manual maintenance entrypoint for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. A source-changing `sp-*` workflow does not hand off its own verified changes to `sp-map-update`; it runs inline project cognition update during closeout from its workflow-owned changed paths, affected surfaces, and verification evidence.
- Workflow-owned mutation closeout is not external map maintenance. Dirty state is fallback-only after inline update cannot complete.
```

- [ ] **Step 9: Run shared guidance tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_inline_cognition_closeout_shared_surfaces_are_consistent -q
```

Expected: PASS for shared surfaces after this task; mutation workflow tests still fail until Task 4.

- [ ] **Step 10: Commit shared guidance**

```powershell
git add -- templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/planning-context-loading-gradient.md templates/command-partials/common/senior-consequence-analysis-gate.md templates/command-partials/common/navigation-check.md templates/command-partials/fast/shell.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md
git commit -m "docs: define inline cognition closeout guidance"
```

---

### Task 4: Update Workflow Command Templates

**Files:**
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`

- [ ] **Step 1: Define the source-changing closeout paragraph**

Use this exact paragraph in `fast`, `quick`, `implement`, and `debug`, adjusted only for local state names such as `SUMMARY.md`, tracker, or debug session:

```markdown
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, run inline project cognition update from `changed_code_paths`, `changed_behavior_surfaces`, and `verification_evidence` before successful completion.
- Inline update path: append closeout evidence to the current delta session when one exists with `{{specify-subcmd:project-cognition delta append --session "$DELTA_SESSION_ID" --event-type workflow_closeout --changed-path "<path>" --behavior-surface "<surface>" --verification "<evidence>" --format json}}`, then run `{{specify-subcmd:project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json}}`; include `--commit-range "<base>..<head>"` only with `--delta-session` when a safe task commit boundary exists. If no delta session exists, run `{{specify-subcmd:project-cognition update --changed-path "<path>" --scope "<affected-scope>" --reason workflow-finalize --format json}}`.
- Record `project_cognition_refresh` as the inline update result. A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`. Use `{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}` only when inline update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.
- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is not routine cleanup for changes this workflow just made. Escalate to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
```

- [ ] **Step 2: Update `templates/commands/fast.md`**

Replace the bullets around the current `project_cognition_refresh`, "unexpectedly touched", and fallback wording with the paragraph from Step 1. Preserve these nearby requirements:

```markdown
- Include `changed_code_paths` with modified, added, deleted, and renamed paths.
- Include `changed_behavior_surfaces` for commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions affected by the change.
- Include `verification_evidence` with the exact checks run and the result.
```

- [ ] **Step 3: Update `templates/commands/quick.md`**

Replace the closeout bullets around `SUMMARY.md` and `project_cognition_refresh` with the paragraph from Step 1. Preserve the requirement that `SUMMARY.md` reports changed paths, changed behavior surfaces, verification evidence, residual risk, and `project_cognition_refresh`.

- [ ] **Step 4: Update `templates/commands/implement.md`**

Replace the closeout bullets around lines 554-556 with the paragraph from Step 1. Preserve:

```markdown
- Before final completion reporting, record `changed_code_paths` with modified, added, deleted, and renamed paths; `changed_behavior_surfaces` for affected commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions; and `verification_evidence`.
- Only mark the tracker `resolved` after required tasks are complete, blockers are cleared, and the validation pass is truthfully green or explicitly waiting on recorded human verification.
```

- [ ] **Step 5: Update `templates/commands/debug.md`**

Replace the closeout bullets around lines 505-507 with the paragraph from Step 1, adding "before moving to `awaiting_human_verify` or `resolved`" to the first bullet:

```markdown
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If this debug workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, run inline project cognition update from `changed_code_paths`, `changed_behavior_surfaces`, and `verification_evidence` before moving to `awaiting_human_verify` or `resolved`.
```

- [ ] **Step 6: Update `templates/commands/constitution.md`**

Replace the current project cognition bullets around lines 73-75 with:

```markdown
- If the navigation system is stale or weak for an existing usable baseline, continue with live repository evidence and recommend `/sp-map-update` only as external/manual map maintenance when the user asks for map maintenance or before a separate map repair pass. Use `/sp-map-scan` followed by `/sp-map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the constitution amendment changes project-related source, runtime, templates, generated assets, config, tests, state contracts, governance rules that drive agent behavior, or project-cognition coverage facts, run inline project cognition update from the amendment's changed paths and affected surfaces before reporting completion.
- Inline update path: append closeout evidence to the current delta session when one exists with `{{specify-subcmd:project-cognition delta append --session "$DELTA_SESSION_ID" --event-type workflow_closeout --changed-path "<path>" --behavior-surface "<surface>" --verification "<evidence>" --format json}}`, then run `{{specify-subcmd:project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json}}`; without a delta session, run `{{specify-subcmd:project-cognition update --changed-path "<path>" --scope "<affected-scope>" --reason workflow-finalize --format json}}`.
- A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`; use `{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}` only when inline update cannot complete. `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made.
```

- [ ] **Step 7: Update artifact-only workflow escape hatches**

In each file:

- `templates/commands/specify.md`
- `templates/commands/clarify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`

Keep artifact-only guidance, and add this sentence to the existing cognition follow-up closeout paragraph:

```markdown
If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, it stops being artifact-only for closeout: run inline project cognition update from the workflow-owned changed paths and affected surfaces, and use `project-cognition mark-dirty` only when inline update cannot complete. `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made.
```

- [ ] **Step 8: Run workflow template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_mutation_workflows_require_inline_cognition_update_before_dirty_fallback tests/test_fast_template_guidance.py::test_fast_template_exists_and_defines_scope_gate tests/test_debug_template_guidance.py::test_debug_template_enforces_resolution_closeout -q
```

Expected: PASS.

- [ ] **Step 9: Commit workflow templates**

```powershell
git add -- templates/commands/fast.md templates/commands/quick.md templates/commands/implement.md templates/commands/debug.md templates/commands/constitution.md templates/commands/specify.md templates/commands/clarify.md templates/commands/plan.md templates/commands/tasks.md
git commit -m "docs: require inline cognition closeout in workflows"
```

---

### Task 5: Update Integration Rendering Addenda

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`

- [ ] **Step 1: Update planning skill addendum in `IntegrationBase`**

In `src/specify_cli/integrations/base.py`, update `_append_planning_skill_cognition_refresh_guidance()` addendum to:

```python
        addendum = (
            "\n"
            f"{marker}\n\n"
            "- This workflow is artifact-only unless the user explicitly requested source/runtime/template/config/test/generated-asset changes; do not call `project-cognition mark-dirty`, `project-cognition complete-refresh`, or `project-cognition validate-build --format json` just because `sp-specify`, `sp-plan`, or `sp-tasks` wrote planning artifacts.\n"
            "- If this planning workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, it stops being artifact-only for closeout: run inline project cognition update from the workflow-owned changed paths and affected surfaces.\n"
            "- Inline project cognition update uses `project-cognition delta append` followed by `project-cognition update --delta-session \"$DELTA_SESSION_ID\" --reason workflow-finalize --format json` when a delta session exists, or `project-cognition update --changed-path \"<path>\" --scope \"<affected-scope>\" --reason workflow-finalize --format json` when no delta session exists.\n"
            "- A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`; use `project-cognition mark-dirty --reason \"<reason>\" --format json` only when inline update cannot complete.\n"
            "- `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made. Use `/sp-map-scan` followed by `/sp-map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.\n"
        )
```

- [ ] **Step 2: Update runtime project cognition gate addendum**

In `_append_runtime_project_cognition_gate()`, replace the mutation closeout line with:

```python
            "- Mutation closeout is separate from entry routing: entry stale may continue, but workflow-owned mutation closeout is not an external map-maintenance handoff. If the workflow changes source/runtime truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other project-related behavior surfaces, final state must run inline project cognition update from changed paths, affected surfaces, and verification evidence.\n"
            "- Inline project cognition update uses `project-cognition delta append` followed by `project-cognition update --delta-session \"$DELTA_SESSION_ID\" --reason workflow-finalize --format json` when a delta session exists, or `project-cognition update --changed-path \"<path>\" --scope \"<affected-scope>\" --reason workflow-finalize --format json` when no delta session exists. A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`; use `project-cognition mark-dirty --reason \"<reason>\" --format json` only when inline update cannot complete. Dirty only when inline update cannot complete.\n"
            "- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is not routine cleanup for changes this workflow just made.\n"
```

- [ ] **Step 3: Update checklist addendum only for entry routing**

In `_append_checklist_project_cognition_guidance()`, change the `needs_update` line to clarify entry/manual routing:

```python
            "- `needs_update`: for checklist intake, treat this as advisory routing. Use `{{invoke:map-update}}` or `/sp-map-update` only when the user requested map maintenance or checklist quality depends on a separate map repair pass; otherwise continue with returned `minimal_live_reads` and live evidence.\n"
```

- [ ] **Step 4: Update Cursor addendum**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, add these bullets to the Cursor advisory:

```python
            "- Entry advisory is not closeout ownership: stale or weak cognition at entry may remain advisory, but workflow-owned mutation closeout must run inline project cognition update for changes this workflow made.\n"
            "- Inline project cognition update uses `project-cognition delta append` plus `project-cognition update --delta-session \"$DELTA_SESSION_ID\" --reason workflow-finalize --format json` when a delta session exists, or `project-cognition update --changed-path \"<path>\" --scope \"<affected-scope>\" --reason workflow-finalize --format json` when no delta session exists.\n"
            "- `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made.\n"
```

- [ ] **Step 5: Run integration rendering tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit integration rendering changes**

```powershell
git add -- src/specify_cli/integrations/base.py src/specify_cli/integrations/cursor_agent/__init__.py
git commit -m "feat: render inline cognition closeout guidance"
```

---

### Task 6: Update Generated Project Docs and Repository Docs

**Files:**
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/constitution-template.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Update `templates/project-handbook-template.md`**

Replace the line beginning `Use map-update for localized stale cognition recommendations` with:

```markdown
- Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is not external map maintenance: normal `sp-*` workflows that change project-related source, runtime, templates, config, tests, generated assets, state contracts, or behavior-bearing docs must run inline project cognition update from their changed paths and affected surfaces. `sp-map-update` is for manual/external maintenance after user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, zero active-generation path_index rows, explicit_rebuild_requested, or baseline_identity_invalid.
```

- [ ] **Step 2: Update `templates/constitution-template.md`**

Replace the project cognition maintenance paragraph around line 132 with:

```markdown
  Entry-time stale or weak cognition is advisory unless the user requested map
  maintenance. Workflow-owned mutation closeout is not external map maintenance:
  when an `sp-*` workflow changes project-related source, runtime, templates,
  config, tests, generated assets, state contracts, or behavior-bearing docs, it
  MUST run inline project cognition update from its changed paths and affected
  surfaces. `sp-map-update` is for manual/external maintenance after user edits,
  interrupted workflow repair, explicit map maintenance, and follow-up repair.
  Recommend `map-scan` followed by `map-build` only for first/missing/unusable
  baseline, schema failure, zero active-generation `path_index` rows,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.
```

- [ ] **Step 3: Update `README.md` project cognition bullets**

In the project cognition sections near the current map-update lifecycle bullets, add:

```markdown
- Workflow-owned mutation closeout is inline: when an `sp-*` workflow changes project-related source, runtime, templates, config, tests, generated assets, state contracts, or behavior-bearing docs, it should update project cognition directly through the lower-level `project-cognition update` path using its changed paths, affected surfaces, and verification evidence. `sp-map-update` remains the external/manual maintenance workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.
```

Keep the existing map-update-first rebuild policy.

- [ ] **Step 4: Update `PROJECT-HANDBOOK.md` brownfield cognition lifecycle**

In the "Brownfield cognition lifecycle" bullet, insert this sentence after "apply the map-update-first routing policy":

```markdown
Workflow-owned mutation closeout is not external map maintenance: source-changing `sp-*` workflows run inline project cognition update for their own changed paths and affected surfaces, while `sp-map-update` remains the external/manual entrypoint for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.
```

- [ ] **Step 5: Update docs tests**

Update `tests/test_constitution_defaults.py` as described in Task 2. Then update docs tests that assert old handbook phrasing:

In `tests/test_runtime_handbook_contract.py`, replace assertions for:

```python
assert "normal code changes should use `sp-map-update` for bounded incremental refresh from changed paths" in lowered
```

with:

```python
assert "workflow-owned mutation closeout is not external map maintenance" in lowered
assert "run inline project cognition update" in lowered or "runs inline project cognition update" in lowered
assert "sp-map-update remains the external/manual" in lowered or "sp-map-update is for manual/external maintenance" in lowered
```

In `tests/test_specify_guidance_docs.py`, add:

```python
assert "workflow-owned mutation closeout is inline" in readme.lower()
assert "sp-map-update remains the external/manual maintenance workflow" in readme.lower()
```

- [ ] **Step 6: Run docs tests**

Run:

```powershell
pytest tests/test_constitution_defaults.py tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit docs**

```powershell
git add -- templates/project-handbook-template.md templates/constitution-template.md README.md PROJECT-HANDBOOK.md tests/test_constitution_defaults.py tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py
git commit -m "docs: document inline cognition closeout lifecycle"
```

---

### Task 7: Full Focused Verification and Cleanup

**Files:**
- Modify only if a focused test exposes stale wording or broken expectations.

- [ ] **Step 1: Search for stale closeout phrases**

Run:

```powershell
rg -n "actual `\\{\\{invoke:map-update\\}\\}` refresh|refresh the project cognition runtime through `\\{\\{invoke:map-update\\}\\}` using the changed paths|user-invoked workflow handoff|Do not silently switch into `sp-map-update`|map maintenance stays follow-up-only|normal code changes should use `sp-map-update`" templates src tests README.md PROJECT-HANDBOOK.md
```

Expected: no matches, except historical design documents under `docs/superpowers/specs/**` or existing plan files if the search is intentionally widened.

- [ ] **Step 2: Run focused template and integration tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_debug_template_guidance.py tests/test_constitution_defaults.py tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 3: Run packaging asset sanity tests**

Run:

```powershell
pytest tests/test_packaging_assets.py tests/test_passive_skill_guidance.py tests/test_passive_skill_installation.py tests/test_project_handbook_templates.py -q
```

Expected: PASS.

- [ ] **Step 4: Run a final diff check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 5: Review changed files**

Run:

```powershell
git status --short
git diff --stat
```

Expected: changed files match this plan's surfaces; no unrelated files.

- [ ] **Step 6: Commit verification cleanup**

If Step 1 or tests required cleanup edits, commit them:

```powershell
git add -- templates src tests README.md PROJECT-HANDBOOK.md
git commit -m "test: verify inline cognition closeout surfaces"
```

If no cleanup edits were needed after Task 6, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage: Tasks cover MVP runtime command path, non-ready outcome mapping, missing contradictory surfaces, entry routing vs closeout ownership, source-changing workflows, artifact-only exemptions, generated addenda, docs, and tests.
- Runtime safety: The plan does not assume non-delta `project-cognition update --commit-range`; it uses `--commit-range` only with `--delta-session`.
- Dirty semantics: Every source-changing path teaches `review` or `partial_refresh` for persisted non-ready update records and reserves `dirty` for failed/unavailable/unsafe inline update.
- `sp-map-update` role: The plan keeps `sp-map-update` as manual/external maintenance and follow-up repair, not routine cleanup for workflow-owned changes.
- No implementation runtime expansion is required in this pass because the existing CLI supports `delta append`, `update --delta-session`, `update --changed-path`, `update --scope`, `update --reason`, and delta-session `--commit-range`.
