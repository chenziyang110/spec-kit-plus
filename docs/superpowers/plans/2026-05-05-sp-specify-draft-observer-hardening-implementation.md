# sp-specify Draft Observer Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved `sp-specify` hardening so requirement discovery is continuously recorded in a durable draft artifact, challenged by an observer subagent at fixed points, resumed from written state, and blocked from false planning readiness when high-risk gaps remain.

**Architecture:** Land the change shared-first across templates, scripts, hooks, and integration renderers. First add the durable `specify-draft.md` artifact and creation/scaffolding path, then teach `sp-specify` and `workflow-state.md` to carry observer and coverage state, then add semantic artifact validation and regression tests so the new contract is enforceable instead of advisory.

**Tech Stack:** Markdown templates, Bash/PowerShell scripts, Python (`specify_cli` hooks/integrations), pytest

---

## File Structure

| File | Responsibility | Change Type |
|------|----------------|-------------|
| `templates/specify-draft-template.md` | New draft artifact skeleton for clarification ledger and recovery capsule | create |
| `templates/spec-template.md` | Keep final planning-facing spec clean while aligning with draft-sync model | modify |
| `templates/alignment-template.md` | Record observer gate outcomes, coverage mode outcomes, and blocker handling | modify |
| `templates/context-template.md` | Carry stable affected-surface, change-propagation, and implementation-facing context | modify |
| `templates/workflow-state-template.md` | Persist draft/observer/coverage/resume fields required by the new contract | modify |
| `templates/commands/specify.md` | Main workflow contract: create/resume draft, run observer at fixed points, enforce core/full coverage, update artifacts incrementally | modify |
| `templates/worker-prompts/specify-observer.md` | New read-only observer worker contract for gap detection and escalation output | create |
| `scripts/bash/create-new-feature.sh` | Scaffold `specify-draft.md` alongside `spec.md` and `context.md` | modify |
| `scripts/powershell/create-new-feature.ps1` | Scaffold `specify-draft.md` alongside `spec.md` and `context.md` | modify |
| `scripts/bash/common.sh` | Expose `SPECIFY_DRAFT` in feature-path exports | modify |
| `scripts/powershell/common.ps1` | Expose `SPECIFY_DRAFT` in feature-path exports | modify |
| `pyproject.toml` | Bundle the new top-level template into the wheel/core pack | modify |
| `src/specify_cli/hooks/checkpoint_serializers.py` | Parse new workflow-state and draft-related fields for resume and validation | modify |
| `src/specify_cli/hooks/artifact_validation.py` | Enforce `specify-draft.md` presence plus observer/coverage/ready semantics | modify |
| `src/specify_cli/integrations/base.py` | Shared question-driven integration notes and, if needed, shared skill augmentation language for `sp-specify` | modify |
| `src/specify_cli/integrations/codex/__init__.py` | Codex-specific `sp-specify` augmentation for observer dispatch/join points | modify |
| `tests/test_alignment_templates.py` | Shared template and script contract assertions | modify |
| `tests/hooks/test_artifact_hooks.py` | Hook-level semantic validation tests for `sp-specify` | modify |
| `tests/hooks/test_state_hooks.py` | Resume/state field validation coverage for `sp-specify` additions | modify |
| `tests/contract/test_hook_cli_surface.py` | Hook CLI shape checks when validation failures surface the new semantics | modify |
| `tests/integrations/test_cli.py` | Generated project asset presence checks for the new template | modify |
| `docs/superpowers/specs/2026-05-05-sp-specify-draft-observer-hardening-design.md` | Approved design baseline, read-only reference | read-only |

## Delivery Scope

This plan implements the approved first shipping slice:

- create a new durable `specify-draft.md` artifact
- scaffold it in feature creation scripts and bundle it in packaged assets
- make `sp-specify` update the draft continuously and record resume-critical fields
- add a new observer worker contract plus fixed observer trigger points
- add `core` versus `full` coverage mode and hard escalation triggers
- extend artifact validation so `Aligned: ready for plan` is blocked when the new semantics are not satisfied
- ship the behavior as a shared cross-integration `sp-specify` contract, with Codex-specific runtime augmentation where that integration already adds subagent guidance

This plan intentionally does not implement:

- a second runtime subsystem beyond the existing workflow/hook/template surfaces
- a visual companion or browser workflow
- implementation of downstream planning changes beyond what is required to keep shared templates and validation consistent
- a brand-new CLI command surface for observer control

## Verification Commands

The minimum trustworthy verification slice for this work is:

```bash
uv run pytest tests/test_alignment_templates.py -q
uv run pytest tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
uv run pytest tests/integrations/test_cli.py -q -k "shared_workflow_skills or shared_infra_skips_existing_files"
```

If `sp-specify` integration augmentation changes broaden beyond the expected files, add:

```bash
uv run pytest tests/integrations/test_integration_codex.py -q
```

---

### Task 1: Scaffold and package the new `specify-draft.md` artifact

**Files:**
- Create: `templates/specify-draft-template.md`
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/powershell/create-new-feature.ps1`
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
- Modify: `pyproject.toml`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Write the failing template and script contract tests**

Add this new test to `tests/test_alignment_templates.py`:

```python
def test_specify_draft_template_and_feature_scripts_scaffold_draft_artifact():
    draft_template = _read("templates/specify-draft-template.md")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")
    pyproject = _read("pyproject.toml")

    assert "# Specification Draft Ledger:" in draft_template
    assert "## Recovery Capsule" in draft_template
    assert "## Observer Findings" in draft_template
    assert "SPECIFY_DRAFT_FILE" in sh_create
    assert "specify-draft-template" in sh_create
    assert "$specifyDraftFile = Join-Path $featureDir 'specify-draft.md'" in ps_create
    assert "Resolve-Template -TemplateName 'specify-draft-template'" in ps_create
    assert "SPECIFY_DRAFT=%q\\n" in sh_common
    assert "SPECIFY_DRAFT = Join-Path $featureDir 'specify-draft.md'" in ps_common
    assert '"templates/specify-draft-template.md" = "specify_cli/core_pack/templates/specify-draft-template.md"' in pyproject
```

Extend `tests/integrations/test_cli.py` with:

```python
def test_init_installs_specify_draft_template(tmp_path: Path):
    project = tmp_path / "demo"
    result = runner.invoke(app, ["init", str(project), "--ai", "codex", "--ignore-agent-tools"])
    assert result.exit_code == 0
    assert (project / ".specify" / "templates" / "specify-draft-template.md").exists()
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_cli.py -q -k "specify_draft_template or shared_workflow_skills or shared_infra_skips_existing_files"
```

Expected: FAIL because there is no `specify-draft-template.md`, the scripts do not scaffold it, and the wheel does not force-include it.

- [ ] **Step 3: Create the new draft template**

Create `templates/specify-draft-template.md` with this initial scaffold:

```markdown
# Specification Draft Ledger: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Active draft
**Purpose**: Durable clarification ledger, observer findings, and resume anchor for `sp-specify`

## Current Focus

- current_capability: [active capability name]
- current_stage: [discovery | clarification | observer-review | capability-closure | final-handoff]
- coverage_mode: [core | full]
- observer_status: [not-run | pending | completed | blocked]

## Recovery Capsule

- last_question_asked: [most recent user-facing question]
- last_answer_summary: [one-line summary of the user's latest answer]
- next_question_target: [highest-value next clarification target]
- open_blockers:
  - [planning-critical blocker]
- recently_closed_items:
  - [recently resolved item]

## Confirmed Facts

- [fact confirmed by user or repository evidence]

## Low-Risk Inferences

- [reasonable default preserved as an inference]

## Unresolved Items

- [open item that still affects planning]

## Observer Findings

### Missing Questions

- [question the observer says still needs to be asked]

### Affected Surfaces

- [directly affected surface]

### Adjacent Workflows

- [adjacent workflow or consumer surface to review]

### Assumption Risks

- [assumption that could invalidate planning]

### Capability Gaps

- [gap preventing capability closure]

### Contrarian Candidate

- [the strongest alternative interpretation to test]

### Release Blockers

- [observer-defined blocker to resolve before handoff]

## Question Ledger

- Q: [...]
  A: [...]
  Disposition: [resolved | inferred | deferred | force-carried]
```

- [ ] **Step 4: Teach feature-creation scripts and path helpers about the draft artifact**

In `scripts/bash/common.sh`, add the exported path:

```bash
    printf 'SPECIFY_DRAFT=%q\n' "$feature_dir/specify-draft.md"
```

In `scripts/powershell/common.ps1`, add:

```powershell
        SPECIFY_DRAFT = Join-Path $featureDir 'specify-draft.md'
```

In `scripts/bash/create-new-feature.sh`, add:

```bash
SPECIFY_DRAFT_FILE="$FEATURE_DIR/specify-draft.md"
```

and scaffold it:

```bash
    if [ ! -f "$SPECIFY_DRAFT_FILE" ]; then
        SPECIFY_DRAFT_TEMPLATE=$(resolve_template "specify-draft-template" "$REPO_ROOT") || true
        if [ -n "$SPECIFY_DRAFT_TEMPLATE" ] && [ -f "$SPECIFY_DRAFT_TEMPLATE" ]; then
            cp "$SPECIFY_DRAFT_TEMPLATE" "$SPECIFY_DRAFT_FILE"
        else
            touch "$SPECIFY_DRAFT_FILE"
        fi
    fi
```

Also extend JSON/plain output:

```bash
    --arg specify_draft_file "$SPECIFY_DRAFT_FILE"
```

and:

```bash
echo "SPECIFY_DRAFT_FILE: $SPECIFY_DRAFT_FILE"
```

In `scripts/powershell/create-new-feature.ps1`, add:

```powershell
$specifyDraftFile = Join-Path $featureDir 'specify-draft.md'
```

and:

```powershell
    if (-not (Test-Path -PathType Leaf $specifyDraftFile)) {
        $specifyDraftTemplate = Resolve-Template -TemplateName 'specify-draft-template' -RepoRoot $repoRoot
        if ($specifyDraftTemplate -and (Test-Path $specifyDraftTemplate)) {
            Copy-Item $specifyDraftTemplate $specifyDraftFile -Force
        } else {
            New-Item -ItemType File -Path $specifyDraftFile -Force | Out-Null
        }
    }
```

and include `SPECIFY_DRAFT_FILE` in output objects.

- [ ] **Step 5: Bundle the new template into packaged assets**

In `pyproject.toml`, add this wheel force-include entry next to the other top-level templates:

```toml
"templates/specify-draft-template.md" = "specify_cli/core_pack/templates/specify-draft-template.md"
```

- [ ] **Step 6: Re-run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_cli.py -q -k "specify_draft_template or shared_workflow_skills or shared_infra_skips_existing_files"
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add templates/specify-draft-template.md scripts/bash/create-new-feature.sh scripts/powershell/create-new-feature.ps1 scripts/bash/common.sh scripts/powershell/common.ps1 pyproject.toml tests/test_alignment_templates.py tests/integrations/test_cli.py
git commit -m "feat: scaffold specify draft artifact"
```

---

### Task 2: Extend shared templates and workflow-state for draft, observer, and coverage semantics

**Files:**
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/spec-template.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/hooks/test_state_hooks.py`

- [ ] **Step 1: Write the failing template/state assertions**

Add these assertions to `tests/test_alignment_templates.py`:

```python
def test_alignment_and_context_templates_capture_observer_and_coverage_outcomes():
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    workflow_state = _read("templates/workflow-state-template.md")
    spec_template = _read("templates/spec-template.md")

    assert "## Observer Gate" in alignment
    assert "## Coverage Mode Outcomes" in alignment
    assert "## Planning-Critical Blockers" in alignment
    assert "## Change Propagation Matrix" in context
    assert "## Observer-Carried Risks" in context
    assert "draft_file" in workflow_state.lower()
    assert "coverage_mode" in workflow_state
    assert "observer_status" in workflow_state
    assert "specify-draft.md" in workflow_state
    assert "clean result-state document only" in _read("templates/commands/specify.md")
    assert "should not degrade into a running transcript of every question" in spec_template
```

Add this state-validation test to `tests/hooks/test_state_hooks.py`:

```python
def test_validate_state_accepts_specify_workflow_with_draft_and_observer_fields(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: refine capability requirements",
                "",
                "## Profile Obligations",
                "",
                "- activated_gates:",
                "  - observer-gate",
                "  - coverage-mode-gate",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "- workflow-state.md",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "",
                "## Resume Checklist",
                "",
                "- draft_file: `specify-draft.md`",
                "- coverage_mode: `full`",
                "- observer_status: `completed`",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/hooks/test_state_hooks.py -q -k "observer_and_coverage or draft_and_observer_fields or validate_state"
```

Expected: FAIL because the templates and workflow-state skeleton do not yet carry those sections or fields.

- [ ] **Step 3: Extend the shared templates**

In `templates/alignment-template.md`, insert:

```markdown
## Observer Gate

- **Status**: [not-run | completed | blocked | revised]
- **Last observer pass**: [global-entry | capability-closure | final-handoff]
- **Contrarian candidate**: [strongest competing interpretation the observer surfaced]

## Coverage Mode Outcomes

- **Capability**: [Name]
- **Coverage mode**: [core | full]
- **Escalation triggers hit**: [List of triggers that forced full coverage]

## Planning-Critical Blockers

- [Blocker] -> [Disposition: resolved | inferred | deferred | force-carried] -> [Why this disposition is acceptable]
```

In `templates/context-template.md`, add:

```markdown
## Change Propagation Matrix

| Change Surface | Direct Consumers | Indirect Consumers | Risk |
| --- | --- | --- | --- |
| [surface] | [consumer] | [indirect consumer] | [risk summary] |

## Observer-Carried Risks

- [Risk surfaced by the observer that downstream planning must preserve]
```

In `templates/workflow-state-template.md`, add under `Resume Checklist`:

```markdown
- draft_file: `specify-draft.md`
- coverage_mode: `core | full`
- observer_status: `not-run | pending | completed | blocked`
- last_observer_pass: `global-entry | capability-closure | final-handoff`
```

and ensure `Allowed Artifact Writes` / `Authoritative Files` examples mention `specify-draft.md`.

In `templates/spec-template.md`, keep the file planning-facing by adding this reminder above `## Alignment State`:

```markdown
<!--
  This file is the planning-ready result-state artifact.
  Active clarification history, observer findings, and recovery details belong in `specify-draft.md`,
  not as a running transcript here.
-->
```

- [ ] **Step 4: Re-run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/hooks/test_state_hooks.py -q -k "observer_and_coverage or draft_and_observer_fields or validate_state"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/alignment-template.md templates/context-template.md templates/workflow-state-template.md templates/spec-template.md tests/test_alignment_templates.py tests/hooks/test_state_hooks.py
git commit -m "feat: add draft observer fields to shared templates"
```

---

### Task 3: Add the observer worker contract and wire `sp-specify` to create, resume, and update the draft

**Files:**
- Create: `templates/worker-prompts/specify-observer.md`
- Modify: `templates/commands/specify.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing template assertions**

Add this new test to `tests/test_alignment_templates.py`:

```python
def test_specify_template_requires_draft_sync_observer_passes_and_coverage_escalation():
    content = _read("templates/commands/specify.md")
    observer_prompt = _read("templates/worker-prompts/specify-observer.md")
    codex = _read("src/specify_cli/integrations/codex/__init__.py")
    lowered = content.lower()

    assert "specify-draft.md" in content
    assert "create or resume `SPECIFY_DRAFT_FILE` immediately after `FEATURE_DIR` is known" in lowered
    assert "after every clarification answer, update `SPECIFY_DRAFT_FILE`" in lowered
    assert "observer should run at exactly three fixed points" in lowered
    assert "coverage_mode: `core | full`" in content
    assert "cross-module impact" in lowered
    assert "external boundary, contract, or integration behavior" in lowered
    assert "performance or capacity risk" in lowered
    assert "must not declare `Aligned: ready for plan`" in content
    assert "# Specify Observer Worker Prompt" in observer_prompt
    assert "missing_questions" in observer_prompt
    assert "release_blockers" in observer_prompt
    assert "sp-specify" in codex
    assert "before capability closure and before the final packet" in codex.lower() or "before capability closure" in codex.lower()
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run pytest tests/test_alignment_templates.py -q -k "draft_sync_observer_passes_and_coverage_escalation"
```

Expected: FAIL because neither the observer prompt nor the strengthened specify contract exists yet.

- [ ] **Step 3: Create the observer worker prompt**

Create `templates/worker-prompts/specify-observer.md` with this contract:

```markdown
# Specify Observer Worker Prompt

Use this worker when the `sp-specify` leader needs a structured critique of the
current understanding before capability closure or final handoff.

## Controller Requirements

- Provide the user request summary, current capability, current coverage mode, and the latest `specify-draft.md` state.
- Provide the relevant project-map and handbook summary.
- State whether this is the global-entry, capability-closure, or final-handoff observer pass.

## Worker Contract

- Gather critique only; do not ask the user questions directly.
- Do not rewrite `spec.md`, `alignment.md`, `context.md`, or `workflow-state.md`.
- Return structured gaps, not prose-only encouragement.

## Minimum Return Payload

- missing_questions
- affected_surfaces
- adjacent_workflows
- assumption_risks
- capability_gaps
- contrarian_candidate
- escalation_triggers_hit
- coverage_mode
- release_blockers
- next_best_question_targets

## Guardrails

- Prefer requirement-shaping gaps over implementation speculation.
- Treat cross-module, contract, migration, async, configuration, security, observability, and performance/capacity risks as escalation triggers.
- If no planning-critical blocker exists, say so explicitly instead of inventing one.
```

- [ ] **Step 4: Update `templates/commands/specify.md` with the new workflow contract**

Make these concrete edits in `templates/commands/specify.md`:

1. In frontmatter, expand the objective and outputs:

```yaml
  primary_objective: 'Produce a planning-ready specification package grounded in repository reality, while preserving active discovery in `specify-draft.md`.'
  primary_outputs: '`FEATURE_DIR/specify-draft.md`, `FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md`, and `FEATURE_DIR/workflow-state.md`.'
```

2. Right after `FEATURE_DIR` is known in the branch-creation block, define:

```markdown
- Set `SPECIFY_DRAFT_FILE` to `FEATURE_DIR/specify-draft.md`.
```

3. In both `Workflow Phase Lock` field lists, include:

```markdown
- `allowed_artifact_writes: spec.md, alignment.md, context.md, references.md, specify-draft.md, workflow-state.md, checklists/requirements.md`
- `authoritative_files: spec.md, alignment.md, context.md, references.md, specify-draft.md`
```

4. Add a new section after `Load context`:

```markdown
## Draft Capture and Resume Discipline

- [AGENT] Create or resume `SPECIFY_DRAFT_FILE` immediately after `FEATURE_DIR` is known.
- Treat `SPECIFY_DRAFT_FILE` as the durable clarification ledger and resume anchor for `sp-specify`.
- After every clarification answer, update `SPECIFY_DRAFT_FILE` before asking the next question.
- Record at least: current capability, current stage, coverage mode, observer status, confirmed facts, low-risk inferences, unresolved items, recent Q/A disposition, and the next question target.
```

5. Add a new section describing fixed observer passes:

```markdown
## Observer Challenge Stage

- The observer should run at exactly three fixed points:
  1. once after initial framing and repository/context loading
  2. once before each capability is marked sufficiently aligned
  3. once before the final handoff decision
- Use `.specify/templates/worker-prompts/specify-observer.md` as the default read-only observer contract whenever the current integration can dispatch a specify observer lane.
- The observer output must be written into `SPECIFY_DRAFT_FILE`.
- The leader must not ignore observer blockers; each blocker must be resolved, inferred, deferred, or force-carried explicitly.
```

6. Add a new coverage-mode section:

```markdown
## Coverage Mode Escalation

- Every capability begins in `coverage_mode: core`.
- Upgrade the capability to `coverage_mode: full` when any of these triggers are present:
  - cross-module impact
  - external boundary, contract, or integration behavior
  - migration or compatibility preservation
  - asynchronous, event-driven, queue, or state-propagation behavior
  - configuration-driven behavior
  - security, permission, or trust-boundary semantics
  - observability or rollback requirements
  - performance or capacity risk
- If a capability escalates to `full`, do not close it until the full matrix questions were answered or explicitly force-carried.
```

7. Strengthen the final gates so the template says:

```markdown
- Do not declare `Aligned: ready for plan` while planning-critical observer blockers remain untreated.
- Do not declare `Aligned: ready for plan` when a high-risk capability escalated to `full` but only `core` coverage was recorded.
```

- [ ] **Step 5: Update Codex `sp-specify` augmentation**

In `src/specify_cli/integrations/codex/__init__.py`, replace the `sp-specify`
augmentation string with a version that keeps the existing dispatch guidance and adds:

```python
                "- Suggested bounded lanes include repository and local context analysis, references analysis, ambiguity/risk analysis, and the read-only specify observer pass.\n"
                f"- Use `wait_agent` only at the documented join points before capability decomposition, before capability closure, and before the final packet consistency pass.\n"
```

Do not add Codex-only user-visible behavior beyond the subagent dispatch guidance.

- [ ] **Step 6: Re-run the focused test and verify it passes**

Run:

```bash
uv run pytest tests/test_alignment_templates.py -q -k "draft_sync_observer_passes_and_coverage_escalation"
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add templates/worker-prompts/specify-observer.md templates/commands/specify.md src/specify_cli/integrations/codex/__init__.py tests/test_alignment_templates.py
git commit -m "feat: add specify observer workflow contract"
```

---

### Task 4: Extend artifact validation from file presence to draft/observer/coverage semantics

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Write the failing semantic validation tests**

Add these tests to `tests/hooks/test_artifact_hooks.py`:

```python
def test_validate_artifacts_blocks_specify_when_draft_artifact_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("specify-draft.md" in message for message in result.errors)
```

```python
def test_validate_artifacts_blocks_specify_when_recovery_capsule_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n\n## Observer Gate\n\n- **Status**: completed\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n\n## Change Propagation Matrix\n\n| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n| --- | --- | --- | --- |\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "specify-draft.md").write_text("# Specification Draft Ledger: Demo\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Recovery Capsule" in message for message in result.errors)
```

```python
def test_validate_artifacts_blocks_specify_when_full_coverage_trigger_lacks_evidence(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Coverage Mode Outcomes\n\n- **Capability**: Sync API\n- **Coverage mode**: core\n- **Escalation triggers hit**: cross-module impact\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n| --- | --- | --- | --- |\n| API | UI | reporting | medium |\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n## Recovery Capsule\n\n- current_capability: Sync API\n\n## Observer Findings\n\n### Release Blockers\n\n- none\n",
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("full coverage" in message.lower() for message in result.errors)
```

Add this CLI surface test to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_validate_artifacts_blocks_specify_when_semantic_ready_state_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "specify", "--feature-dir", str(feature_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("specify-draft.md" in message for message in payload["errors"])
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q -k "specify_when_draft_artifact_is_missing or recovery_capsule_is_missing or full_coverage_trigger_lacks_evidence or semantic_ready_state_is_missing"
```

Expected: FAIL because `artifact_validation.py` only checks file presence and reference-implementation sections.

- [ ] **Step 3: Extend `artifact_validation.py` with specify draft semantics**

Make these concrete edits in `src/specify_cli/hooks/artifact_validation.py`:

1. Add `specify-draft.md` to `FILE_REQUIRED_ARTIFACTS["specify"]` and `REQUIRED_ARTIFACTS["specify"]`.

2. Add these specify-specific constants near the top:

```python
SPECIFY_DRAFT_REQUIRED_HEADINGS = (
    "## Recovery Capsule",
    "## Observer Findings",
)

SPECIFY_ALIGNMENT_REQUIRED_HEADINGS = (
    "## Observer Gate",
    "## Coverage Mode Outcomes",
)

SPECIFY_CONTEXT_REQUIRED_HEADINGS = (
    "## Change Propagation Matrix",
)
```

3. Add a new helper:

```python
def _validate_specify_draft_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    draft_path = feature_dir / "specify-draft.md"
    alignment_path = feature_dir / "alignment.md"
    context_path = feature_dir / "context.md"

    errors.extend(_validate_markdown_headings(draft_path, SPECIFY_DRAFT_REQUIRED_HEADINGS, "specify-draft.md"))
    errors.extend(_validate_markdown_headings(alignment_path, SPECIFY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"))
    errors.extend(_validate_markdown_headings(context_path, SPECIFY_CONTEXT_REQUIRED_HEADINGS, "context.md"))

    alignment = alignment_path.read_text(encoding="utf-8", errors="replace").lower()
    if "escalation triggers hit" in alignment and "coverage mode" in alignment:
        if "coverage mode**: core" in alignment and "cross-module impact" in alignment:
            errors.append("specify artifacts require full coverage evidence when escalation triggers such as cross-module impact were recorded")

    return errors
```

4. In `validate_artifacts_hook()`, for `command_name == "specify"`, run:

```python
        validation_errors.extend(_validate_specify_draft_artifacts(feature_dir))
```

before the profile-specific checks.

- [ ] **Step 4: Re-run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q -k "specify_when_draft_artifact_is_missing or recovery_capsule_is_missing or full_coverage_trigger_lacks_evidence or semantic_ready_state_is_missing"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: validate specify draft observer semantics"
```

---

### Task 5: Run the full regression slice and verify generated asset propagation

**Files:**
- Modify: none
- Test: `tests/test_alignment_templates.py`
- Test: `tests/hooks/test_state_hooks.py`
- Test: `tests/hooks/test_artifact_hooks.py`
- Test: `tests/contract/test_hook_cli_surface.py`
- Test: `tests/integrations/test_cli.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Run the full shared template and hook regression slice**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS

- [ ] **Step 2: Run generated-asset propagation tests**

Run:

```bash
uv run pytest tests/integrations/test_cli.py -q -k "specify_draft_template or shared_workflow_skills or shared_infra_skips_existing_files"
```

Expected: PASS, proving the new top-level template is installed into generated projects.

- [ ] **Step 3: Run Codex integration regression if the `sp-specify` augmentation changed**

Run:

```bash
uv run pytest tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 4: Review the final diff**

Run:

```bash
git diff --stat HEAD~4..HEAD
```

Expected: shows only the planned template, script, packaging, hook, and test files above.

- [ ] **Step 5: Commit the verification checkpoint**

```bash
git commit --allow-empty -m "chore: verify specify draft observer hardening"
```

---

## Self-Review

### Spec coverage

- Durable draft artifact and continuous synchronization: covered by Tasks 1 and 3.
- Observer worker contract and fixed trigger points: covered by Task 3.
- Core vs full coverage and escalation triggers: covered by Tasks 2, 3, and 4.
- Resume semantics and recovery capsule: covered by Tasks 1, 2, and 4.
- Semantic validation for false readiness: covered by Task 4.
- Shared cross-integration propagation: covered by Tasks 1, 3, and 5.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to earlier task” placeholders remain.
- Every file-changing step uses exact repository paths.
- Every verification step uses an exact command and explicit expected outcome.

### Type consistency

- Artifact name is consistently `specify-draft.md`.
- Coverage modes are consistently `core` and `full`.
- Observer statuses are consistently `not-run | pending | completed | blocked`.
- The observer payload fields remain consistent across template, validation, and tests:
  - `missing_questions`
  - `affected_surfaces`
  - `adjacent_workflows`
  - `assumption_risks`
  - `capability_gaps`
  - `contrarian_candidate`
  - `release_blockers`

## Final Verification

Run before executing this plan end-to-end:

```bash
uv run pytest tests/test_alignment_templates.py -q
uv run pytest tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
uv run pytest tests/integrations/test_cli.py -q -k "specify_draft_template or shared_workflow_skills or shared_infra_skips_existing_files"
uv run pytest tests/integrations/test_integration_codex.py -q
```
