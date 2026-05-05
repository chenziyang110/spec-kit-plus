# PRD Command Subagent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `templates/commands/prd-scan.md` and `templates/commands/prd-build.md` so they match the orchestration quality of `map-scan` and `map-build` while preserving PRD-specific reconstruction semantics and `prd-build`'s build-only boundary.

**Architecture:** Start by tightening template-focused tests so they assert the missing orchestration contract directly. Then expand `prd-scan` with state, packet, dispatch, join-point, and refusal sections, and expand `prd-build` with bundle-only intake, build-packet, dispatch, traceability, and refusal sections. Finish by aligning shared template-level assertions so the PRD commands are covered by the same contract family as the other subagent-mandatory workflows.

**Tech Stack:** Markdown command templates, pytest template-guidance tests, repository-local command contract conventions, Spec Kit workflow wording patterns.

---

## Context

Read before editing:

- `docs/superpowers/specs/2026-05-05-prd-subagent-orchestration-design.md`
- `templates/commands/prd-scan.md`
- `templates/commands/prd-build.md`
- `templates/commands/map-scan.md`
- `templates/commands/map-build.md`
- `tests/test_prd_scan_build_template_guidance.py`
- `tests/test_alignment_templates.py`
- `tests/test_subagent_mandatory_template_guidance.py`
- `tests/test_extension_skills.py`

The repository already contains `prd-scan` and `prd-build`. This plan is an incremental enhancement plan, not a greenfield addition plan. Do not rewrite the lane into atlas-specific wording and do not widen scope into passive skills, runtime helpers, docs, or hooks during this pass.

The working tree already contains unrelated user changes. Do not revert or fold them into this work.

## File Structure

Modify:

- `templates/commands/prd-scan.md` - add executable subagent orchestration structure to the scan command while keeping reconstruction scan semantics.
- `templates/commands/prd-build.md` - add executable bundle-only orchestration structure to the build command while keeping no-reread and synthesis semantics.
- `tests/test_prd_scan_build_template_guidance.py` - add explicit PRD-command assertions for state protocol, packet contracts, worker-result contracts, join points, and build-only restrictions.
- `tests/test_alignment_templates.py` - extend shared alignment assertions so `prd-scan` and `prd-build` are checked against the common subagent dispatch contract style where appropriate.
- `tests/test_subagent_mandatory_template_guidance.py` - add or extend targeted checks that both PRD commands record `subagent-blocked` and stop instead of improvising work outside a validated packet flow.
- `docs/superpowers/plans/2026-05-05-prd-command-subagent-orchestration-implementation.md` - this plan file.

Do not create new PRD command files. Do not touch `templates/command-partials/**` in this implementation.

## Command Naming Rules

Keep these exact spellings consistent in templates and tests:

- `choose_subagent_dispatch(command_name="prd-scan", snapshot, workload_shape)`
- `choose_subagent_dispatch(command_name="prd-build", snapshot, workload_shape)`
- `execution_model: subagent-mandatory`
- `dispatch_shape: one-subagent | parallel-subagents`
- `execution_surface: native-subagents`
- `subagent-blocked`
- `PrdScanPacket`
- `PrdBuildPacket`
- `result_handoff_path`
- `worker-results`
- `bundle_only`

`prd-build` must remain explicitly build-only and must continue to refuse live repository rereads.

---

### Task 1: Lock the missing PRD orchestration contract in tests

**Files:**
- Modify: `tests/test_prd_scan_build_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_subagent_mandatory_template_guidance.py`

- [ ] **Step 1: Add failing `prd-scan` assertions for state protocol, dispatch, packets, and worker-result handling**

Update `tests/test_prd_scan_build_template_guidance.py` by appending this test:

```python
def test_prd_scan_template_defines_state_dispatch_and_packet_contracts() -> None:
    content = _content("templates/commands/prd-scan.md")
    lowered = content.lower()

    assert "project map state protocol" not in lowered
    assert "prd run state protocol" in lowered or "workflow-state.md" in content
    assert 'choose_subagent_dispatch(command_name="prd-scan"' in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "`subagent-blocked`" in content or "subagent-blocked" in content
    assert "accepted_packet_results" in content
    assert "rejected_packet_results" in content
    assert "failed_readiness_checks" in content
    assert "paths_read" in content
    assert "evidence_refs" in content
    assert "recommended_contract_updates" in content
    assert "join_points" in content
    assert "before declaring the package ready for `sp-prd-build`" in content
```

- [ ] **Step 2: Add failing `prd-build` assertions for bundle-only build packets, join points, and no-reread lanes**

Update `tests/test_prd_scan_build_template_guidance.py` by appending this test:

```python
def test_prd_build_template_defines_bundle_only_dispatch_and_traceability_contracts() -> None:
    content = _content("templates/commands/prd-build.md")
    lowered = content.lower()

    assert 'choose_subagent_dispatch(command_name="prd-build"' in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "PrdBuildPacket" in content
    assert "mode: bundle_only" in content
    assert "required_scan_inputs" in content
    assert "required_worker_results" in content
    assert "traceability_targets" in content
    assert "bundle_inputs_read" in content
    assert "traceability_findings" in content
    assert "export_landing_findings" in content
    assert "before writing `master/master-pack.md`" in content
    assert "before reverse coverage / traceability validation" in content
    assert "must not become a second repository scan" in lowered
    assert "must not reread the repository" in lowered or "new repository facts" in lowered
```

- [ ] **Step 3: Extend shared alignment coverage so `prd-scan` and `prd-build` participate in common dispatch-contract expectations**

Update `tests/test_alignment_templates.py` by appending these tests:

```python
def test_prd_scan_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-scan.md")
    _assert_subagent_dispatch_contract(content, "prd-scan")
    lowered = content.lower()
    assert "idle subagent output is not an accepted" in lowered
    assert "record `subagent-blocked`" in lowered or "`subagent-blocked` with a recorded reason" in lowered


def test_prd_build_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-build.md")
    _assert_subagent_dispatch_contract(content, "prd-build")
    lowered = content.lower()
    assert "bundle_only" in lowered
    assert "must not become a second repository scan" in lowered
```

- [ ] **Step 4: Extend subagent-mandatory template guidance coverage for PRD commands**

Update `tests/test_subagent_mandatory_template_guidance.py` by appending:

```python
def test_prd_scan_records_subagent_blocked_instead_of_improvising_scan_work() -> None:
    content = Path("templates/commands/prd-scan.md").read_text(encoding="utf-8").lower()

    assert "subagent-blocked" in content
    assert "stop for escalation or recovery" in content or "stop before" in content


def test_prd_build_records_subagent_blocked_instead_of_rereading_repository() -> None:
    content = Path("templates/commands/prd-build.md").read_text(encoding="utf-8").lower()

    assert "subagent-blocked" in content
    assert "must not become a second repository scan" in content
    assert "new repository facts" in content or "must not reread the repository" in content
```

- [ ] **Step 5: Run the template-focused test set to verify failure before template edits**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py -q
```

Expected: FAIL because the current PRD templates do not yet contain the new dispatch, packet, join-point, and `subagent-blocked` contract language.

- [ ] **Step 6: Commit**

```bash
git add tests/test_prd_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py
git commit -m "test: lock prd command orchestration contract gaps"
```

### Task 2: Expand `prd-scan` to match map-grade scan orchestration

**Files:**
- Modify: `templates/commands/prd-scan.md`
- Test: `tests/test_prd_scan_build_template_guidance.py`

- [ ] **Step 1: Add a PRD-specific state protocol section before broad process details**

Insert a new section in `templates/commands/prd-scan.md` after `## Hard Boundary` with content shaped like:

```md
## PRD Run State Protocol

- `workflow-state.md` under `.specify/prd-runs/<run-id>/` is the resumable state surface for `sp-prd-scan` and `sp-prd-build`.
- [AGENT] Create or resume `workflow-state.md` before substantial scan work.
- If the file already records `active_command: sp-prd-scan` with a non-terminal scan state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-prd-scan`
  - `status: scanning | synthesizing | blocked | ready-for-build`
  - `scan_status: pending | scanning | blocked | complete`
  - `build_status`
  - `freshness_mode`
  - `classification`
  - `selected_capabilities`
  - `selected_boundaries`
  - `selected_artifacts`
  - `current_packet`
  - `accepted_packet_results`
  - `rejected_packet_results`
  - `failed_readiness_checks`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`
```

- [ ] **Step 2: Expand the process with explicit dispatch selection and join points**

Rewrite the `## Process` list in `templates/commands/prd-scan.md` so it includes these exact concepts:

```md
1. Route and initialize the PRD run under `.specify/prd-runs/<run-id>/`.
2. Load brownfield context and select the smallest relevant repository surfaces.
3. Check `.specify/prd/status.json` freshness before scoping the scan.
4. Triage `capability`, `artifact`, and `boundary` objects before broad synthesis.
5. Assign each capability a tier: `critical`, `high`, `standard`, or `auxiliary`.
6. Before broad scan fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="prd-scan", snapshot, workload_shape)`.
7. Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
8. Compile a validated `PrdScanPacket` before dispatch or `subagent-blocked` status.
9. Dispatch one read-only scan lane when one safe validated lane exists, or parallel read-only scan lanes when multiple safe validated lanes exist.
10. Required join points:
    - before freezing ledgers and machine-readable contracts
    - before declaring the package ready for `sp-prd-build`
11. Build `.specify/prd-runs/<run-id>/artifact-contracts.json` and `.specify/prd-runs/<run-id>/reconstruction-checklist.json`.
12. Refuse handoff if any `critical` capability lacks reconstruction-ready support.
```

- [ ] **Step 3: Add explicit `PrdScanPacket` and worker-result contract sections**

Append these sections to `templates/commands/prd-scan.md`:

```md
## Compile And Validate PrdScanPacket Inputs

- [AGENT] Compile a validated `PrdScanPacket` before dispatch or `subagent-blocked` status.
- A valid `PrdScanPacket` must include:
  - `lane_id`
  - `mode: read_only`
  - `scope`
  - `capability_ids`
  - `artifact_ids`
  - `boundary_ids`
  - `required_reads`
  - `excluded_paths`
  - `required_questions`
  - `expected_outputs`
  - `contract_targets`
  - `forbidden_actions`
  - `result_handoff_path`
  - `join_points`
  - `minimum_verification`
  - `blocked_conditions`
- Hard rule: do not dispatch from raw scan prose or broad chat instructions alone.

## PrdScanPacket Dispatch

- If no safe lane exists, the packet is incomplete, or delegation is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before broad scan work continues.
- Idle subagent output is not an accepted scan result.
- The leader must wait for every dispatched lane and consume its structured handoff before finalizing ledgers, writing scan packets, or marking the scan complete.

## Worker Result Contract

Every scan-lane result must include:

- `lane_id`
- `reported_status: done | done_with_concerns | blocked | needs_context`
- `paths_read`
- `key_facts`
- `evidence_refs`
- `recommended_contract_updates`
- `confidence`
- `unknowns`
- `minimum_verification`
- `result_handoff_path`

Reject results that omit `paths_read`, collapse evidence into prose-only summary, hide `unknowns`, or leave contract impact undefined where one is expected.
```

- [ ] **Step 4: Run the PRD template tests and verify the scan-side contract now passes**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py -q
```

Expected: some tests still fail on `prd-build`, but `prd-scan`-focused assertions pass.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd-scan.md tests/test_prd_scan_build_template_guidance.py
git commit -m "feat: add packetized subagent orchestration to prd scan"
```

### Task 3: Expand `prd-build` to match map-grade build orchestration without rereads

**Files:**
- Modify: `templates/commands/prd-build.md`
- Test: `tests/test_prd_scan_build_template_guidance.py`

- [ ] **Step 1: Add mandatory subagent execution and required-input structure to `prd-build`**

Insert these sections near the top of `templates/commands/prd-build.md` after `## Context`:

```md
## Mandatory Subagent Execution

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

Build-support lanes operate on the run bundle, not the live repository.

## Required Inputs

Before writing final exports, read:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.json`
- `.specify/prd-runs/<run-id>/capability-ledger.json`
- `.specify/prd-runs/<run-id>/artifact-contracts.json`
- `.specify/prd-runs/<run-id>/reconstruction-checklist.json`
- `.specify/prd-runs/<run-id>/entrypoint-ledger.json`
- `.specify/prd-runs/<run-id>/config-contracts.json`
- `.specify/prd-runs/<run-id>/protocol-contracts.json`
- `.specify/prd-runs/<run-id>/state-machines.json`
- `.specify/prd-runs/<run-id>/error-semantics.json`
- `.specify/prd-runs/<run-id>/verification-surfaces.json`
- `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`
- `.specify/prd-runs/<run-id>/worker-results/**`
```

- [ ] **Step 2: Add bundle-only build packet validation, dispatch, and worker-result sections**

Append these sections to `templates/commands/prd-build.md`:

```md
## Validate Scan Inputs Before Execution

- Refuse build execution if required scan artifacts are missing or malformed.
- Treat the scan workspace under `.specify/prd-runs/<run-id>/` as the only authoritative fact source for `sp-prd-build`.
- Do not reread the repository to fill gaps.

## Compile And Validate PrdBuildPacket Inputs

- [AGENT] Compile a validated `PrdBuildPacket` before dispatch or `subagent-blocked` status.
- A valid `PrdBuildPacket` must include:
  - `lane_id`
  - `mode: bundle_only`
  - `packet_scope`
  - `required_scan_inputs`
  - `required_contract_files`
  - `required_worker_results`
  - `expected_exports`
  - `traceability_targets`
  - `forbidden_actions`
  - `minimum_verification`
  - `result_handoff_path`
- Hard rule: do not dispatch from raw scan prose alone.

## Execution Dispatch

- [AGENT] Before build-support packet dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="prd-build", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
- One safe validated intake or validation lane -> `one-subagent`.
- Two or more isolated bundle-processing lanes -> `parallel-subagents`.
- Any need for new repository facts, missing build packet, or unavailable delegation -> `subagent-blocked`.

## Build Packet Dispatch

- `subagent-blocked` stops substantive build work. Do not continue by turning `sp-prd-build` into a second repository scan.
- Required join points:
  - before writing `master/master-pack.md`
  - before writing or finalizing `exports/**`
  - before reverse coverage / traceability validation

## Build Worker Result Contract

Every build-support lane result must include:

- `lane_id`
- `reported_status`
- `bundle_inputs_read`
- `traceability_findings`
- `export_landing_findings`
- `confidence`
- `unknowns`
- `recommended_repairs`
- `minimum_verification`
- `result_handoff_path`
```

- [ ] **Step 3: Add traceability/refusal language that enforces the build-only boundary**

Expand `## Quality Gates` or add a new validation section in `templates/commands/prd-build.md` with this content:

```md
## Readiness Refusal Rules

`sp-prd-build` must refuse completion when:

- required scan artifacts are missing or malformed
- worker results are absent or structurally shallow
- critical reconstruction claims cannot be traced back to scan-package evidence
- export landing for critical artifacts is missing
- unresolved critical unknowns remain in the bundle
- the build would need new repository facts to complete honestly

## Traceability Validation

- Every reconstruction claim in the master pack and exports must trace back to scan-package evidence.
- Reject any build-lane output that relies on live repository rereads instead of bundle inputs.
```

- [ ] **Step 4: Run the PRD template tests and verify the build-side contract now passes**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd-build.md tests/test_prd_scan_build_template_guidance.py
git commit -m "feat: add bundle-only subagent orchestration to prd build"
```

### Task 4: Align PRD commands with the shared subagent-mandatory template family

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_subagent_mandatory_template_guidance.py`
- Modify: `templates/commands/prd-scan.md`
- Modify: `templates/commands/prd-build.md`

- [ ] **Step 1: Run the shared alignment tests to expose wording gaps**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py -q
```

Expected: FAIL with missing phrases around `subagent-blocked`, accepted result handling, or shared dispatch-contract wording.

- [ ] **Step 2: Normalize PRD template wording to the shared contract family**

Update `templates/commands/prd-scan.md` and `templates/commands/prd-build.md` so they include the same family-level signals already used by `map-*`, `test-*`, and `debug`, including these phrases where they fit naturally:

```md
- The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.
- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed scope, forbidden actions, acceptance checks, verification evidence, and structured handoff format.
- Idle subagent output is not an accepted result.
- Record `subagent-blocked` with the blocker and stop for escalation or recovery.
```

- [ ] **Step 3: Re-run the shared alignment tests until they pass**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 4: Run the full PRD-related template test slice**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd-scan.md templates/commands/prd-build.md tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py
git commit -m "test: align prd commands with shared subagent workflow contract"
```

### Task 5: Final verification and change review

**Files:**
- Modify: `docs/superpowers/plans/2026-05-05-prd-command-subagent-orchestration-implementation.md`

- [ ] **Step 1: Run the final command-template verification set**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py -q
```

Expected: PASS.

- [ ] **Step 2: Review the PRD template diff for scope control**

Run:

```bash
git diff -- templates/commands/prd-scan.md templates/commands/prd-build.md tests/test_prd_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_subagent_mandatory_template_guidance.py
```

Expected: only PRD template and PRD/shared template test changes; no passive skill, runtime, docs, or hook edits.

- [ ] **Step 3: Review status to confirm unrelated user changes remain untouched**

Run:

```bash
git status --short
```

Expected: the existing unrelated modified files remain present; this work adds only the planned PRD template and test edits.

- [ ] **Step 4: Commit the final verification pass**

```bash
git add docs/superpowers/plans/2026-05-05-prd-command-subagent-orchestration-implementation.md
git commit -m "docs: add prd command orchestration implementation plan"
```
