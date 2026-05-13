# Analyze/Tasks Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-analyze` report a complete blocker bundle and make `sp-tasks` self-audit task-layer readiness so repeated task/analyze loops are treated as workflow quality failures.

**Architecture:** This is a generated-workflow contract change. Update the source templates first, then protect the behavior with template contract tests and generated-integration projection tests. Keep `sp-analyze` read-only for planning artifacts and keep `sp-tasks -> sp-analyze` mandatory except when `sp-tasks` escalates directly to an upstream workflow because required truth is missing.

**Tech Stack:** Markdown command templates, Python pytest template assertions, README/handbook documentation, existing integration projection tests.

---

## File Structure

- Modify `templates/commands/analyze.md`: add complete blocker bundle, stable finding ID reuse, revalidation attribution, anti-loop, and analyze-gate workflow-state persistence guidance.
- Modify `templates/commands/tasks.md`: add remediation mode, analyze-compatible task self-audit, direct upstream escalation, updated report requirements, and anti-loop language.
- Modify `templates/tasks-template.md`: add `Analyze Remediation Mapping` and a compact task self-audit output section to generated `tasks.md` structure.
- Modify `templates/workflow-state-template.md`: add an `Analyze Gate` section so downstream workflows can persist blocker bundles and artifact fingerprint basis.
- Modify `README.md`: document complete blocker bundle, abnormal repeated loops, direct upstream escalation, and task self-audit behavior in operator guidance.
- Modify `PROJECT-HANDBOOK.md`: document the new workflow contract surface for maintainers.
- Modify `tests/test_alignment_templates.py`: add/extend template assertions for analyze, tasks, workflow-state, and docs-sensitive contract wording.
- Modify `tests/test_tasks_reporting_guidance.py`: add tasks-template assertions for remediation mapping and task self-audit output.
- Modify `tests/test_specify_guidance_docs.py`: add README guidance assertions if not covered cleanly by `test_alignment_templates.py`.
- Modify `tests/integrations/test_integration_codex.py`: extend generated Codex `sp-analyze` skill assertions if projection tests fail or if coverage should explicitly protect generated skills.

## Task 1: Add Failing Tests for `sp-analyze` Convergence Contract

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add assertions to the existing analyze test**

In `tests/test_alignment_templates.py`, update `test_analyze_template_expands_to_context_and_locked_decision_drift()` by appending these assertions near the existing `Recommended Next Command` and `Recommended Re-entry` assertions:

```python
    assert "complete blocker bundle" in lowered
    assert "Blocker Bundle" in content
    assert "finish the full detection matrix before selecting the single recommended next command" in lowered
    assert "Stable Finding Identity" in content
    assert "fingerprint-first" in lowered
    assert "reuse the prior ID" in content
    assert "Allocate a new ID only for a genuinely new fingerprint" in content
    assert "Revalidation Attribution" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
    assert "No more than one task-layer remediation cycle is expected" in content
    assert "Do not treat repeated task/analyze loops as normal workflow" in content
```

- [ ] **Step 2: Add assertions to analyze workflow-state persistence coverage**

In the same test function, after the assertion for ``"`next_command: /sp.constitution`"`` add:

```python
    assert "Analyze Gate" in content
    assert "gate_status" in content
    assert "gate_cycle" in content
    assert "highest_invalid_stage" in content
    assert "blocker_bundle" in content
    assert "artifact_fingerprint_basis" in content
```

- [ ] **Step 3: Run the focused analyze template test and verify it fails**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_analyze_template_expands_to_context_and_locked_decision_drift -q
```

Expected: FAIL because `templates/commands/analyze.md` does not yet contain the new blocker bundle, stable identity, attribution, and analyze-gate persistence language.

## Task 2: Implement `sp-analyze` Complete Blocker Bundle Guidance

**Files:**
- Modify: `templates/commands/analyze.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add convergence rule to Operating Constraints**

In `templates/commands/analyze.md`, under the existing `**Closed-loop requirement**` paragraph, insert:

```markdown
**Convergence requirement**: Complete the full detection matrix before selecting the single `Recommended Next Command`. Do not stop analysis after finding enough evidence to route backward. The report must include the complete blocker bundle for the current artifact set, grouped by invalid stage, so downstream remediation does not discover same-artifact blockers one cycle at a time.
```

- [ ] **Step 2: Add stable identity and revalidation rules after Workflow Phase Lock**

After the `## Workflow Phase Lock` section and before `## Workflow Quality Requirements`, insert:

```markdown
## Analyze Gate Convergence Contract

- Use stable finding IDs that survive revalidation. Category-only IDs such as `BG2` are too coarse, and run-local sequence numbers are not stable by themselves.
- Use a fingerprint-first ID contract:
  - Build a canonical finding fingerprint from category, invalid stage, artifact, requirement or section key when available, normalized summary, and remediation requirement.
  - Before assigning IDs, load the previous `Analyze Gate` ledger from `workflow-state.md` when it exists.
  - Match current findings to previous open or recently cleared findings by fingerprint first, and reuse the prior ID when the fingerprint matches.
  - Allocate a new ID only for a genuinely new fingerprint.
  - For new fingerprints, allocate the next unused category sequence after sorting by category, artifact, section key, and normalized summary.
- When revalidating after a blocked analyze gate, any new blocker must include one attribution:
  - `missed_by_previous_analyze`: detectable in the prior artifact set and should have been included in the earlier blocker bundle.
  - `introduced_by_remediation`: remediation changed `tasks.md` or downstream state in a way that introduced the issue.
  - `upstream_artifact_changed`: an authoritative input changed since the prior analyze pass.
  - `detector_scope_changed`: the workflow template or analysis instructions changed the detector scope between runs.
- If there is no evidence for `introduced_by_remediation`, `upstream_artifact_changed`, or `detector_scope_changed`, use `missed_by_previous_analyze`.
- No more than one task-layer remediation cycle is expected. If revalidation finds new task-layer blockers that were detectable before remediation, classify them as a previous analyze miss or a tasks self-audit failure. Do not treat repeated task/analyze loops as normal workflow.
```

- [ ] **Step 3: Update the report structure with a Blocker Bundle section**

In `### 7. Produce Compact Analysis Report`, after the findings table instructions and before `**Coverage Summary Table:**`, insert:

```markdown
**Blocker Bundle:**

| Invalid Stage | Blocking Finding IDs | Required Re-entry | Notes |
|---------------|----------------------|-------------------|-------|
| clarify | [IDs or none] | `{{invoke:clarify}}` | Reopen spec/context truth, then regenerate downstream artifacts |
| deep-research | [IDs or none] | `{{invoke:deep-research}}` | Prove unresolved implementation chain before planning |
| plan | [IDs or none] | `{{invoke:plan}}` | Repair planning truth, then regenerate tasks |
| tasks | [IDs or none] | `{{invoke:tasks}}` | Repair task decomposition and rerun analyze |
| execution-only | [IDs or none] | `{{invoke:implement}}` or `{{invoke:debug}}` | No upstream artifact regeneration required |
```

- [ ] **Step 4: Update persist workflow gate instructions**

In `### 9.5 Persist Workflow Gate Result`, add this block before the command-specific `next_action` bullets:

```markdown
Always update or preserve the `Analyze Gate` section in `WORKFLOW_STATE_FILE` with:
- `gate_status: cleared | blocked`
- `gate_cycle: [integer]`
- `highest_invalid_stage: clarify | deep-research | plan | tasks | execution-only | none`
- `blocker_bundle: [finding ID | invalid stage | status | compact summary]`
- `artifact_fingerprint_basis: [spec.md/context.md/plan.md/tasks.md summaries or hashes when available]`

When revalidation finds a new blocker, record its attribution in the blocker bundle or report body using `missed_by_previous_analyze`, `introduced_by_remediation`, `upstream_artifact_changed`, or `detector_scope_changed`.
```

- [ ] **Step 5: Run the focused analyze test and verify it passes**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_analyze_template_expands_to_context_and_locked_decision_drift -q
```

Expected: PASS.

- [ ] **Step 6: Commit the analyze template change**

Run:

```powershell
git add tests/test_alignment_templates.py templates/commands/analyze.md
git commit -m "feat: add analyze blocker bundle contract"
```

Expected: commit succeeds with only those two files staged.

## Task 3: Add Failing Tests for Workflow-State Analyze Gate

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Extend workflow-state template test**

In `test_workflow_state_template_supports_analyze_gate_phase()`, add:

```python
    assert "## Analyze Gate" in content
    assert "gate_status" in content
    assert "gate_cycle" in content
    assert "highest_invalid_stage" in content
    assert "blocker_bundle" in content
    assert "artifact_fingerprint_basis" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
```

- [ ] **Step 2: Run the focused workflow-state test and verify it fails**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_state_template_supports_analyze_gate_phase -q
```

Expected: FAIL because `templates/workflow-state-template.md` does not yet include `## Analyze Gate`.

## Task 4: Implement Workflow-State Analyze Gate Section

**Files:**
- Modify: `templates/workflow-state-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the Analyze Gate section**

In `templates/workflow-state-template.md`, insert this section after `## Reopen Contract` and before `## Handoff Files`:

```markdown
## Analyze Gate

- gate_status: [not-run | cleared | blocked]
- gate_cycle: [0]
- highest_invalid_stage: [none | clarify | deep-research | plan | tasks | execution-only]
- blocker_bundle:
  - [finding-id | invalid-stage | open | compact summary and remediation requirement]
- artifact_fingerprint_basis:
  - spec.md: [summary or hash when available]
  - context.md: [summary or hash when available]
  - plan.md: [summary or hash when available]
  - tasks.md: [summary or hash when available]
- new_finding_attribution: [none | missed_by_previous_analyze | introduced_by_remediation | upstream_artifact_changed | detector_scope_changed]
```

- [ ] **Step 2: Run the focused workflow-state test and verify it passes**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_state_template_supports_analyze_gate_phase -q
```

Expected: PASS.

- [ ] **Step 3: Run recovery-section workflow-state test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_state_template_documents_recovery_sections -q
```

Expected: PASS. If it fails because the test expects a fixed section sequence, update that test to include `Analyze Gate` as a recovery section.

- [ ] **Step 4: Commit the workflow-state template change**

Run:

```powershell
git add tests/test_alignment_templates.py templates/workflow-state-template.md
git commit -m "feat: add analyze gate workflow state"
```

Expected: commit succeeds with only those two files staged.

## Task 5: Add Failing Tests for `sp-tasks` Self-Audit and Remediation Mode

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_tasks_reporting_guidance.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_tasks_reporting_guidance.py`

- [ ] **Step 1: Add a new tasks command contract test**

Append this test to `tests/test_alignment_templates.py` near `test_tasks_template_fail_closes_into_analyze_before_implement()`:

```python
def test_tasks_template_requires_analyze_compatible_self_audit_and_remediation_mode():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "Analyze-Compatible Task Self-Audit" in content
    assert "buildable `FR-*`" in content
    assert "locked planning decision" in lowered
    assert "Implementation Constitution" in content
    assert "Task Guardrail Index" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content
    assert "Analyze Remediation Mapping" in content
    assert "resolved | deferred | not_applicable | escalated" in content
    assert "Escalation is terminal for the current `sp-tasks` run" in content
    assert "sets `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content
    assert "No more than one task-layer remediation cycle is expected" in content
    assert "Do not treat repeated task/analyze loops as normal workflow" in content
```

- [ ] **Step 2: Add tasks-template output assertions**

Append this test to `tests/test_tasks_reporting_guidance.py`:

```python
def test_tasks_template_includes_analyze_remediation_mapping_and_self_audit():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "## Analyze Remediation Mapping" in content
    assert "| Finding ID | Disposition | Task/Section Evidence | Notes |" in content
    assert "resolved" in lowered
    assert "deferred" in lowered
    assert "not_applicable" in content
    assert "escalated" in lowered
    assert "## Analyze-Compatible Task Self-Audit" in content
    assert "buildable `FR-*`" in content
    assert "Task Guardrail Index" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content
```

- [ ] **Step 3: Run the new focused tests and verify they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_tasks_template_requires_analyze_compatible_self_audit_and_remediation_mode tests/test_tasks_reporting_guidance.py::test_tasks_template_includes_analyze_remediation_mapping_and_self_audit -q
```

Expected: FAIL because `tasks.md` and `tasks-template.md` do not yet contain the new sections.

## Task 6: Implement `sp-tasks` Self-Audit, Remediation, and Escalation Guidance

**Files:**
- Modify: `templates/commands/tasks.md`
- Modify: `templates/tasks-template.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_tasks_reporting_guidance.py`

- [ ] **Step 1: Add remediation and anti-loop phase-lock guidance**

In `templates/commands/tasks.md`, under `## Workflow Phase Lock` after “Implementation remains blocked until...”, insert:

```markdown
- If `WORKFLOW_STATE_FILE` records a blocked `sp-analyze` gate with `next_command: /sp.tasks`, enter remediation mode before regenerating `tasks.md`.
- In remediation mode, read the prior `Analyze Gate` blocker bundle first. Do not start from a blank task-generation pass.
- No more than one task-layer remediation cycle is expected. If repeated `sp-tasks -> sp-analyze` loops occur for blockers that were detectable before remediation, treat that as a previous analyze miss or a tasks self-audit failure, not as normal workflow.
```

- [ ] **Step 2: Add task-generation remediation mode instructions**

In `templates/commands/tasks.md`, inside step `4. **Execute task generation workflow**`, insert this block before “Load plan.md and extract tech stack...”:

```markdown
    - **Analyze remediation mode**: If `workflow-state.md` contains an open `Analyze Gate` blocker bundle for `sp-tasks`, map each task-layer finding to exactly one disposition: `resolved | deferred | not_applicable | escalated`.
    - `resolved`: fix the issue in this task pass and name the task, guardrail, checkpoint, packet field, or section evidence.
    - `deferred`: keep the issue explicit with the downstream condition that must clear it.
    - `not_applicable`: state why the prior finding no longer applies and cite the artifact evidence.
    - `escalated`: stop task generation for the current pass because the missing truth belongs to `plan`, `clarify`, or `deep-research`.
    - Escalation is terminal for the current `sp-tasks` run. If required upstream truth is missing, write the escalation evidence into `workflow-state.md` and set `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`. Do not send the user back through `/sp.analyze` first.
```

- [ ] **Step 3: Add Analyze-Compatible Task Self-Audit instructions**

Still inside step `4. **Execute task generation workflow**`, add this block before “Validate task completeness”:

```markdown
    - **Analyze-Compatible Task Self-Audit**: Before finalizing `tasks.md`, run the task-layer subset of the `sp-analyze` checks against the generated task package.
    - Confirm every buildable `FR-*` and buildable success criterion has at least one task, checkpoint, or explicit deferred note.
    - Confirm every locked planning decision that affects implementation, compatibility, rollout, validation, sequencing, architecture shape, or guardrails appears in `tasks.md`.
    - Confirm `Implementation Constitution` rules from `plan.md` are preserved through a guardrail phase, `Task Guardrail Index`, task notes, or explicit escalation.
    - Confirm the `Task Guardrail Index` maps applicable guardrails to concrete implementation tasks.
    - Confirm each `[P]` task or explicit parallel batch has objective, write set, required references, forbidden drift, validation command, and done condition.
    - Confirm task packet readiness covers `DP1`, `DP2`, and `DP3` as far as task generation can determine before implementation.
    - Confirm reference fidelity behavior items map to task IDs, checkpoints, join points, or explicit deferred notes.
    - Confirm unmapped tasks are justified as setup, polish, verification, or cross-cutting work, or remove them.
    - Confirm task dependencies and parallel batches do not contain obvious write-set conflicts.
    - If the self-audit finds task-layer defects, repair them before completing `sp-tasks`. If the defect requires missing upstream truth, escalate instead of producing speculative tasks.
```

- [ ] **Step 4: Update tasks report requirements**

In `templates/commands/tasks.md`, in step `6. **Report**`, add these bullets before “Recommended next command”:

```markdown
    - Analyze remediation summary when remediation mode is active:
      - handled previous analyze findings count
      - resolved count
      - deferred count
      - not_applicable count
      - escalated count
      - evidence sections or task IDs for resolved findings
    - Analyze-Compatible Task Self-Audit result:
      - coverage mapping status
      - locked decision preservation status
      - guardrail mapping status
      - DP1/DP2/DP3 packet-readiness status
      - reference fidelity mapping status
      - unmapped task status
      - write-set conflict status
```

- [ ] **Step 5: Add generated tasks.md sections**

In `templates/tasks-template.md`, add this section after `## Reference Fidelity Mapping`:

```markdown
## Analyze Remediation Mapping

Use this section only when regenerating tasks after a blocked `sp-analyze` gate. Leave it as `No prior analyze blockers for this task package.` for first-pass task generation.

| Finding ID | Disposition | Task/Section Evidence | Notes |
|------------|-------------|-----------------------|-------|
| No prior analyze blockers | not_applicable | First task-generation pass | No remediation mapping required |

Allowed dispositions: `resolved`, `deferred`, `not_applicable`, `escalated`.
If any finding is `escalated`, stop task generation and set `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` in `workflow-state.md`.
```

Then add this section after `## Task Shaping Rules`:

```markdown
## Analyze-Compatible Task Self-Audit

Before final handoff to `sp-analyze`, confirm:

- Buildable `FR-*` and buildable success criteria have task, checkpoint, or deferred-note coverage.
- Locked planning decisions that affect implementation, compatibility, rollout, validation, sequencing, architecture shape, or guardrails are preserved in this task package.
- `Implementation Constitution` rules from `plan.md` are preserved through the implementation guardrails phase, `Task Guardrail Index`, task notes, or explicit escalation.
- `Task Guardrail Index` entries map applicable guardrails to concrete implementation tasks.
- Each `[P]` task or explicit parallel batch has objective, write set, required references, forbidden drift, validation command, and done condition.
- Task packet readiness covers `DP1`, `DP2`, and `DP3` as far as task generation can determine before implementation.
- Reference fidelity behavior items map to task IDs, checkpoints, join points, or explicit deferred notes.
- Unmapped tasks are justified as setup, polish, verification, or cross-cutting work, or removed.
- Task dependencies and parallel batches do not contain obvious write-set conflicts.
```

- [ ] **Step 6: Run focused tasks tests and verify they pass**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_tasks_template_requires_analyze_compatible_self_audit_and_remediation_mode tests/test_tasks_reporting_guidance.py::test_tasks_template_includes_analyze_remediation_mapping_and_self_audit -q
```

Expected: PASS.

- [ ] **Step 7: Run existing tasks reporting tests**

Run:

```powershell
pytest tests/test_tasks_reporting_guidance.py tests/test_alignment_templates.py::test_tasks_template_fail_closes_into_analyze_before_implement -q
```

Expected: PASS. This confirms the new behavior did not remove mandatory analyze handoff.

- [ ] **Step 8: Commit tasks template changes**

Run:

```powershell
git add tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py templates/commands/tasks.md templates/tasks-template.md
git commit -m "feat: add tasks analyze self audit"
```

Expected: commit succeeds with only those files staged.

## Task 7: Update Operator Documentation and Tests

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Test: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add README guidance assertions**

In `tests/test_specify_guidance_docs.py`, append this test:

```python
def test_guidance_docs_explain_analyze_tasks_convergence_contract() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")

    for content in (readme, handbook):
        lowered = content.lower()
        assert "complete blocker bundle" in lowered
        assert "analyze-compatible task self-audit" in lowered
        assert "repeated `tasks -> analyze -> tasks` loops are abnormal" in content
        assert "No more than one task-layer remediation cycle is expected" in content
        assert "directly to `plan`, `clarify`, or `deep-research`" in content
```

- [ ] **Step 2: Run doc guidance test and verify it fails**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_analyze_tasks_convergence_contract -q
```

Expected: FAIL because README and PROJECT-HANDBOOK do not yet explain the convergence contract.

- [ ] **Step 3: Update README closed-loop remediation guidance**

In `README.md`, under `Closed-loop remediation after `analyze`:`, add these bullets after the current task-only defect bullet:

```markdown
- `analyze` should finish a complete blocker bundle before selecting the single recommended next command; do not treat one discovered blocker as permission to stop the rest of the analysis pass.
- `tasks` should run an analyze-compatible task self-audit before final handoff, covering task coverage, locked decision preservation, task guardrails, DP1/DP2/DP3 readiness, reference fidelity mapping, unmapped tasks, and write-set conflicts.
- Repeated `tasks -> analyze -> tasks` loops are abnormal. No more than one task-layer remediation cycle is expected; if revalidation finds new task-layer blockers that were detectable before remediation, diagnose a previous analyze miss or a tasks self-audit failure.
- If `tasks` discovers missing upstream truth during remediation, route directly to `plan`, `clarify`, or `deep-research`; run `analyze` again only after upstream artifacts are repaired and tasks are regenerated.
```

- [ ] **Step 4: Update PROJECT-HANDBOOK workflow surface summary**

In `PROJECT-HANDBOOK.md`, after the `Enriched task contract generation` bullet, add:

```markdown
- **Analyze/tasks convergence contract**: `sp-analyze` must finish a complete blocker bundle before choosing the single recommended next command, while `sp-tasks` must run an analyze-compatible task self-audit before handoff. Repeated `tasks -> analyze -> tasks` loops are abnormal: no more than one task-layer remediation cycle is expected, and missing upstream truth routes directly to `plan`, `clarify`, or `deep-research` before regenerated tasks return to `analyze`.
```

- [ ] **Step 5: Run doc guidance test and verify it passes**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_analyze_tasks_convergence_contract -q
```

Expected: PASS.

- [ ] **Step 6: Commit docs changes**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md tests/test_specify_guidance_docs.py
git commit -m "docs: explain analyze tasks convergence"
```

Expected: commit succeeds with only those files staged.

## Task 8: Update Generated Codex Projection Coverage if Needed

**Files:**
- Modify: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Run existing Codex projection test**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py::test_codex_ai_skills_include_boundary_guardrail_analysis -q
```

Expected: PASS or FAIL. If PASS and the test already reads generated `sp-analyze`, still add projection assertions to protect the new generated skill content.

- [ ] **Step 2: Extend generated analyze skill assertions**

In `tests/integrations/test_integration_codex.py`, inside `test_codex_ai_skills_include_boundary_guardrail_analysis`, after the existing `Recommended Re-entry` assertion, add:

```python
    assert "Blocker Bundle" in analyze_content
    assert "fingerprint-first" in analyze_content.lower()
    assert "missed_by_previous_analyze" in analyze_content
    assert "No more than one task-layer remediation cycle is expected" in analyze_content
```

- [ ] **Step 3: Run Codex projection test**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py::test_codex_ai_skills_include_boundary_guardrail_analysis -q
```

Expected: PASS. If it fails because projection transforms `{{invoke:...}}` text but not these plain phrases, inspect the generated skill path shown by pytest and assert the transformed phrase that actually appears.

- [ ] **Step 4: Commit projection test change if made**

Run:

```powershell
git add tests/integrations/test_integration_codex.py
git commit -m "test: cover codex analyze convergence projection"
```

Expected: commit succeeds if the file changed. If no projection test change was needed, skip this commit.

## Task 9: Run Focused Regression Suite and Fix Drift

**Files:**
- Modify only files touched in earlier tasks if tests expose wording drift.
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_tasks_reporting_guidance.py`
- Test: `tests/test_specify_guidance_docs.py`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Run focused template and docs tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 2: Run likely affected integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_cli.py -q
```

Expected: PASS. If failures are unrelated to analyze/tasks wording, record them in the final report and do not broaden scope without evidence.

- [ ] **Step 3: Check generated-template formatting**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 4: Inspect final diff**

Run:

```powershell
git diff --stat HEAD
git diff -- templates/commands/analyze.md templates/commands/tasks.md templates/tasks-template.md templates/workflow-state-template.md README.md PROJECT-HANDBOOK.md
```

Expected: diff shows only analyze/tasks convergence guidance and associated tests/docs.

- [ ] **Step 5: Commit any final drift fixes**

If Step 1 or Step 2 required additional fixes, run:

```powershell
git add templates/commands/analyze.md templates/commands/tasks.md templates/tasks-template.md templates/workflow-state-template.md README.md PROJECT-HANDBOOK.md tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_cli.py
git commit -m "fix: align analyze tasks convergence tests"
```

Expected: no commit needed if all previous tasks already committed cleanly.

## Self-Review Checklist

- [ ] The plan covers every spec requirement: complete blocker bundle, stable fingerprint-first IDs, revalidation attribution, task self-audit, remediation mapping, direct upstream escalation, workflow-state persistence, docs, and tests.
- [ ] The plan preserves `sp-tasks -> sp-analyze` as mandatory for normal task output.
- [ ] The plan does not let `sp-analyze` edit planning artifacts.
- [ ] The plan does not make `sp-tasks` repair upstream artifacts.
- [ ] The plan names exact files and exact test commands.
- [ ] The plan has no vague implementation steps without concrete text or assertions.
