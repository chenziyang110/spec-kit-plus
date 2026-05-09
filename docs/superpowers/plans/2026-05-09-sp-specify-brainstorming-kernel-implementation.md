# sp-specify Brainstorming Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `sp-specify` into a public entry shell with a persisted `brainstorming` truth layer, deterministic routing and complexity locks, structured handoff contracts, and downstream `plan/tasks/implement` consumption that reduces intent drift across the entire delivery chain.

**Architecture:** Ship this as a staged workflow-contract migration instead of one invasive rewrite. First add the new `brainstorming` truth artifacts, scaffolding, and semantic validators while keeping current `spec.md`-family artifacts alive. Next, rewrite `sp-specify` and integration renderers so the new truth layer becomes authoritative and compiles into the existing spec package. Then teach `sp-plan`, `sp-tasks`, and `sp-implement` to consume explicit handoff JSON and enforce reopen/unknown/complexity contracts instead of reinterpreting prose or chat memory.

**Tech Stack:** Markdown workflow templates, Bash/PowerShell scaffolding scripts, Python 3.13 (`specify_cli` hooks/integrations/CLI), pytest

---

## Scope Check

This plan stays in one execution lane because the approved design is one
coupled product change, not multiple independent subsystems:

- `sp-specify` entry and questioning behavior
- feature-directory truth artifacts and file layout
- semantic artifact validation and checkpoint serialization
- cross-integration renderer augmentation
- downstream `sp-plan`, `sp-tasks`, and `sp-implement` contract consumption
- docs and regression locks

Splitting these into separate plans would create a partially migrated workflow
where upstream and downstream stages disagree about truth ownership.

## File Structure

```text
MODIFY: top-level workflow templates and truth scaffolds
  templates/commands/specify.md
    Purpose: replace fixed-heavy-only requirement discovery with a staged brainstorming kernel, deterministic locks, route/complexity/unknown rules, and compile-to-specify artifact flow.
  templates/command-partials/specify/shell.md
    Purpose: redefine `sp-specify` as a public entry shell whose first-class responsibility is truth locking before compilation.
  templates/workflow-state-template.md
    Purpose: extend the stage-state truth surface with brainstorming lock fields, unknown/reopen metadata, and downstream handoff pointers.
  templates/spec-template.md
    Purpose: consume compiled intent truth rather than acting as the only requirement truth owner.
  templates/alignment-template.md
    Purpose: carry route, complexity, unresolved soft unknowns, and reopen/handoff decisions in a stable compiled form.
  templates/context-template.md
    Purpose: preserve implementation-facing context derived from the brainstorming truth model.
  templates/references-template.md
    Purpose: preserve evidence and truth-source references that justify locked route and intent decisions.
  templates/specify-draft-template.md
    Purpose: evolve the current draft into a durable brainstorming companion document synced to structured truth files.

CREATE: brainstorming truth templates and machine-readable handoff skeletons
  templates/brainstorming-facts-template.json
    Purpose: seed explicit fact fields, evidence provenance, and unresolved-field objects.
  templates/brainstorming-route-template.json
    Purpose: seed deterministic route selection, matched rules, rejected routes, and blocking conditions.
  templates/brainstorming-intent-template.json
    Purpose: seed goal/non-goal/success criteria/invariant/optimization-scope truth.
  templates/brainstorming-complexity-template.json
    Purpose: seed the fixed `T1/T2/T3/T4` complexity ladder, matched triggers, and scope.
  templates/brainstorming-handoff-specify-template.json
    Purpose: seed the machine-readable compile input for `sp-specify`.
  templates/plan-contract-template.json
    Purpose: seed the machine-readable planning contract emitted from `sp-plan`.
  templates/task-index-template.json
    Purpose: seed task packet indexing and packet metadata truth emitted from `sp-tasks`.
  templates/task-packet-template.json
    Purpose: seed per-task machine-readable implementation packet structure.
  templates/implement-execution-state-template.json
    Purpose: seed execution-state truth separate from Markdown tracker prose.

MODIFY: feature scaffolding and packaged assets
  scripts/bash/create-new-feature.sh
    Purpose: scaffold the new brainstorming directory, JSON truth files, companion markdown, and handoff skeletons.
  scripts/powershell/create-new-feature.ps1
    Purpose: scaffold the same truth layer on Windows.
  scripts/bash/common.sh
    Purpose: export brainstorming and handoff paths so shell workflows can consume them without guessing.
  scripts/powershell/common.ps1
    Purpose: export the same paths for PowerShell workflows.
  pyproject.toml
    Purpose: bundle all new truth templates and handoff skeletons into packaged assets.

MODIFY: hook and serialization layer
  src/specify_cli/hooks/artifact_validation.py
    Purpose: validate the new brainstorming truth files, their headings/schema minimums, and hard/soft unknown gate rules.
  src/specify_cli/hooks/checkpoint_serializers.py
    Purpose: serialize workflow state plus brainstorming/reopen/handoff fields for resume and hook consumers.
  src/specify_cli/hooks/state_validation.py
    Purpose: reject illegal state transitions when brainstorming locks or handoff gates are incomplete.
  src/specify_cli/hooks/workflow_boundary.py
    Purpose: enforce explicit reopen instead of silent upstream mutation when later stages detect truth gaps.

MODIFY: integration renderers and Codex augmentation
  src/specify_cli/integrations/base.py
    Purpose: update shared `sp-specify` augmentation from fixed-heavy-only language to brainstorming-kernel language, plus add downstream handoff guidance where applicable.
  src/specify_cli/integrations/codex/__init__.py
    Purpose: align Codex native subagent guidance to brainstorming lock steps, deterministic route evaluation, and downstream contract consumption.
  src/specify_cli/agents.py
    Purpose: ensure newly introduced templates and paths rewrite into generated-project `.specify/...` surfaces correctly.

MODIFY: downstream workflow contracts
  templates/commands/plan.md
    Purpose: consume `handoff-to-plan.json` and the locked route/intent/complexity context as authoritative planning inputs.
  templates/command-partials/plan/shell.md
    Purpose: teach the summary shell that planning starts from structured handoff truth, not just prose artifacts.
  templates/commands/tasks.md
    Purpose: consume `handoff-to-tasks.json`, propagate complexity and allowed optimization scope, and emit task packet contracts.
  templates/command-partials/tasks/shell.md
    Purpose: summarize the new task packet and handoff responsibilities.
  templates/commands/implement.md
    Purpose: consume `handoff-to-implement.json`, obey locked invariants and optimization latitude, and reopen instead of redefining intent.
  templates/worker-prompts/implementer.md
    Purpose: make worker execution consume packetized invariants, complexity, and stop-and-reopen conditions.

MODIFY: docs and user guidance
  README.md
    Purpose: explain the new internal `brainstorming -> specify -> plan -> tasks -> implement` truth-preserving chain without forcing a new public command.
  docs/quickstart.md
    Purpose: update current workflow explanations so users understand that `specify` now begins with a deterministic brainstorming kernel.
  PROJECT-HANDBOOK.md
    Purpose: document the new workflow contract and artifact truth layer for repository maintenance.

MODIFY: regression tests
  tests/test_alignment_templates.py
    Purpose: lock template wording, new truth artifacts, route/complexity/unknown rules, and downstream contract references.
  tests/test_specify_guidance_docs.py
    Purpose: lock doc-level wording for the new `sp-specify` internal model.
  tests/test_specify_anti_surface_guidance.py
    Purpose: ensure the richer brainstorming flow still blocks vague release patterns and false readiness.
  tests/hooks/test_artifact_hooks.py
    Purpose: validate new artifact presence, headings, JSON minimums, and hard unknown gates.
  tests/hooks/test_state_hooks.py
    Purpose: validate workflow-state serialization and reopen/path semantics.
  tests/hooks/test_workflow_boundary_hooks.py
    Purpose: enforce explicit reopen instead of illegal downstream mutation or command skipping.
  tests/integrations/test_cli.py
    Purpose: verify generated projects receive the new templates and path wiring.
  tests/integrations/test_integration_codex.py
    Purpose: verify Codex skill augmentation teaches the new kernel and downstream consumption model.
  tests/integrations/test_integration_base_skills.py
    Purpose: verify shared skill generation preserves the new deterministic questioning and handoff rules.

READ-ONLY: approved design input
  docs/superpowers/specs/2026-05-09-sp-specify-brainstorming-kernel-design.md
    Purpose: approved product contract; implementation must not drift from it.
```

## Verification Commands

Minimum trustworthy verification for this rollout:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_specify_anti_surface_guidance.py -q
uv run pytest tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_workflow_boundary_hooks.py -q
uv run pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_skills.py -q
```

If hook/state changes broaden:

```bash
uv run pytest tests/hooks -q
```

If CLI packaging or generated-asset behavior broadens:

```bash
uv run pytest tests/integrations -q
```

---

### Task 1: Lock the new brainstorming truth layer in failing tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_specify_anti_surface_guidance.py`

- [ ] **Step 1: Add failing template assertions for the new brainstorming truth artifacts**

Add a new test to `tests/test_alignment_templates.py`:

```python
def test_specify_template_requires_brainstorming_truth_layer_and_handoff_chain() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "brainstorming kernel" in lowered
    assert "facts-lock" in lowered
    assert "route-lock" in lowered
    assert "intent-lock" in lowered
    assert "complexity-lock" in lowered
    assert "brainstorming/facts.json" in content
    assert "brainstorming/route.json" in content
    assert "brainstorming/intent.json" in content
    assert "brainstorming/complexity.json" in content
    assert "handoff-to-specify.json" in content
    assert "dynamic is allowed only" in lowered or "dynamic routing only" in lowered
    assert "hard unknown" in lowered
    assert "reopen" in lowered
```

Also add:

```python
def test_plan_tasks_and_implement_templates_consume_structured_handoff_contracts() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")

    assert "handoff-to-plan.json" in plan
    assert "route, intent, complexity" in plan.lower()
    assert "handoff-to-tasks.json" in tasks
    assert "task packet" in tasks.lower()
    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement.lower()
    assert "allowed optimization scope" in implement.lower()
    assert "stop-and-reopen conditions" in implement.lower()
```

- [ ] **Step 2: Add failing doc-guidance assertions**

Extend `tests/test_specify_guidance_docs.py` with:

```python
def test_guidance_docs_teach_specify_as_public_shell_with_internal_brainstorming() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        lowered = content.lower()
        assert "brainstorming" in lowered
        assert "public entrypoint" in lowered or "public shell" in lowered
        assert "facts" in lowered and "route" in lowered and "intent" in lowered
        assert "sp-implement" in content
        assert "structured handoff" in lowered
```

- [ ] **Step 3: Add failing anti-surface assertions for unknown and reopen handling**

Extend `tests/test_specify_anti_surface_guidance.py` with:

```python
def test_specify_template_does_not_allow_chat_only_conclusions_or_ignored_unknowns() -> None:
    content = _read("templates/commands/specify.md").lower()

    assert "conversation memory is not a valid handoff surface" in content
    assert "unknown is not an ignored value" in content or "unknown is a pending decision object" in content
    assert "resolve-now" in content
    assert "resolve-by-evidence" in content
    assert "defer-with-contract" in content
    assert "waive-with-risk" in content
    assert "reopen" in content
```

- [ ] **Step 4: Run the focused red suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_specify_anti_surface_guidance.py -q -k "brainstorming or handoff or unknown or reopen"
```

Expected: FAIL because the current templates and docs still describe the older `sp-specify` model and do not reference the new truth layer.

- [ ] **Step 5: Commit**

```bash
git add tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_specify_anti_surface_guidance.py
git commit -m "test: lock brainstorming kernel contract"
```

---

### Task 2: Scaffold the brainstorming truth artifacts and package them

**Files:**
- Create: `templates/brainstorming-facts-template.json`
- Create: `templates/brainstorming-route-template.json`
- Create: `templates/brainstorming-intent-template.json`
- Create: `templates/brainstorming-complexity-template.json`
- Create: `templates/brainstorming-handoff-specify-template.json`
- Modify: `templates/specify-draft-template.md`
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/powershell/create-new-feature.ps1`
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
- Modify: `pyproject.toml`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add failing scaffold and packaging tests**

Add to `tests/test_alignment_templates.py`:

```python
def test_feature_scaffolding_and_packaging_include_brainstorming_truth_templates() -> None:
    pyproject = _read("pyproject.toml")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")

    for path in (
        "templates/brainstorming-facts-template.json",
        "templates/brainstorming-route-template.json",
        "templates/brainstorming-intent-template.json",
        "templates/brainstorming-complexity-template.json",
        "templates/brainstorming-handoff-specify-template.json",
    ):
        assert path in pyproject

    assert "BRAINSTORMING_FACTS" in sh_common
    assert "BRAINSTORMING_ROUTE" in sh_common
    assert "BRAINSTORMING_INTENT" in sh_common
    assert "BRAINSTORMING_COMPLEXITY" in sh_common
    assert "HANDOFF_TO_SPECIFY" in sh_common

    assert "BRAINSTORMING_FACTS" in ps_common
    assert "BRAINSTORMING_ROUTE" in ps_common
    assert "BRAINSTORMING_INTENT" in ps_common
    assert "BRAINSTORMING_COMPLEXITY" in ps_common
    assert "HANDOFF_TO_SPECIFY" in ps_common

    assert "brainstorming/facts.json" in sh_create
    assert "brainstorming/route.json" in sh_create
    assert "brainstorming/intent.json" in sh_create
    assert "brainstorming/complexity.json" in sh_create
    assert "handoff-to-specify.json" in sh_create

    assert "brainstorming\\facts.json" in ps_create or "brainstorming/facts.json" in ps_create
    assert "handoff-to-specify.json" in ps_create
```

Add to `tests/integrations/test_cli.py`:

```python
def test_init_installs_brainstorming_truth_templates(tmp_path: Path):
    project = tmp_path / "demo"
    result = runner.invoke(app, ["init", str(project), "--ai", "codex", "--ignore-agent-tools"])
    assert result.exit_code == 0
    templates_dir = project / ".specify" / "templates"
    assert (templates_dir / "brainstorming-facts-template.json").exists()
    assert (templates_dir / "brainstorming-route-template.json").exists()
    assert (templates_dir / "brainstorming-intent-template.json").exists()
    assert (templates_dir / "brainstorming-complexity-template.json").exists()
    assert (templates_dir / "brainstorming-handoff-specify-template.json").exists()
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_cli.py -q -k "brainstorming_truth_templates or brainstorming truth templates"
```

Expected: FAIL because these templates and scaffold paths do not exist yet.

- [ ] **Step 3: Create the JSON template skeletons**

Create `templates/brainstorming-facts-template.json`:

```json
{
  "version": 1,
  "status": "active",
  "fields": {
    "has_existing_repo": { "value": "unknown", "evidence": [] },
    "has_source_of_truth_code": { "value": "unknown", "evidence": [] },
    "has_prd_input": { "value": "unknown", "evidence": [] },
    "requires_behavioral_equivalence": { "value": "unknown", "evidence": [] },
    "requires_module_extraction": { "value": "unknown", "evidence": [] },
    "requires_cross_language_port": { "value": "unknown", "evidence": [] },
    "allows_internal_redesign": { "value": "unknown", "evidence": [] },
    "has_compatibility_constraints": { "value": "unknown", "evidence": [] },
    "success_criteria_explicit": { "value": "unknown", "evidence": [] }
  },
  "unknowns": []
}
```

Create `templates/brainstorming-route-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "primary_route": null,
  "matched_rules": [],
  "rejected_routes": [],
  "blocking_unknowns": []
}
```

Create `templates/brainstorming-intent-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "goal": "",
  "non_goals": [],
  "success_criteria": [],
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "open_questions": []
}
```

Create `templates/brainstorming-complexity-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "complexity_level": null,
  "scope": "capability",
  "matched_rules": [],
  "execution_mode": null
}
```

Create `templates/brainstorming-handoff-specify-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "facts_file": "brainstorming/facts.json",
  "route_file": "brainstorming/route.json",
  "intent_file": "brainstorming/intent.json",
  "complexity_file": "brainstorming/complexity.json",
  "soft_unknowns": [],
  "compile_ready": false
}
```

- [ ] **Step 4: Expand `specify-draft-template.md` into a brainstorming companion**

Append sections to `templates/specify-draft-template.md`:

```markdown
## Facts Lock Notes

- [field]: [current evidence-backed state]

## Route Lock Notes

- primary_route: [pending route]
- matched_rules:
  - [rule id]

## Intent Lock Notes

- goal: [locked goal]
- non_goals:
  - [explicit non-goal]
- must_preserve:
  - [invariant]
- allowed_optimization_scope:
  - [bounded optimization area]

## Complexity Lock Notes

- complexity_level: [T1 | T2 | T3 | T4]
- matched_rules:
  - [complexity rule id]

## Unknown Register

- id: [U-001]
  field: [field name]
  blocking_level: [hard | soft]
  resolver: [user | evidence | research]
  latest_resolve_phase: [brainstorming | specify | plan | tasks]
```

- [ ] **Step 5: Teach create-feature scripts and path helpers about the new layer**

In `scripts/bash/common.sh`, add:

```bash
    printf 'BRAINSTORMING_FACTS=%q\n' "$feature_dir/brainstorming/facts.json"
    printf 'BRAINSTORMING_ROUTE=%q\n' "$feature_dir/brainstorming/route.json"
    printf 'BRAINSTORMING_INTENT=%q\n' "$feature_dir/brainstorming/intent.json"
    printf 'BRAINSTORMING_COMPLEXITY=%q\n' "$feature_dir/brainstorming/complexity.json"
    printf 'HANDOFF_TO_SPECIFY=%q\n' "$feature_dir/brainstorming/handoff-to-specify.json"
```

In `scripts/powershell/common.ps1`, add:

```powershell
        BRAINSTORMING_FACTS = Join-Path $featureDir 'brainstorming/facts.json'
        BRAINSTORMING_ROUTE = Join-Path $featureDir 'brainstorming/route.json'
        BRAINSTORMING_INTENT = Join-Path $featureDir 'brainstorming/intent.json'
        BRAINSTORMING_COMPLEXITY = Join-Path $featureDir 'brainstorming/complexity.json'
        HANDOFF_TO_SPECIFY = Join-Path $featureDir 'brainstorming/handoff-to-specify.json'
```

In `scripts/bash/create-new-feature.sh`, create the directory and copy the templates:

```bash
BRAINSTORMING_DIR="$FEATURE_DIR/brainstorming"
mkdir -p "$BRAINSTORMING_DIR"

copy_json_template() {
    local template_name="$1"
    local dest="$2"
    local template
    template=$(resolve_template "$template_name" "$REPO_ROOT") || true
    if [ -n "$template" ] && [ -f "$template" ] && [ ! -f "$dest" ]; then
        cp "$template" "$dest"
    fi
}

copy_json_template "brainstorming-facts-template" "$BRAINSTORMING_DIR/facts.json"
copy_json_template "brainstorming-route-template" "$BRAINSTORMING_DIR/route.json"
copy_json_template "brainstorming-intent-template" "$BRAINSTORMING_DIR/intent.json"
copy_json_template "brainstorming-complexity-template" "$BRAINSTORMING_DIR/complexity.json"
copy_json_template "brainstorming-handoff-specify-template" "$BRAINSTORMING_DIR/handoff-to-specify.json"
```

Mirror the same behavior in `scripts/powershell/create-new-feature.ps1`.

- [ ] **Step 6: Add wheel force-include entries in `pyproject.toml`**

Add:

```toml
"templates/brainstorming-facts-template.json" = "specify_cli/core_pack/templates/brainstorming-facts-template.json"
"templates/brainstorming-route-template.json" = "specify_cli/core_pack/templates/brainstorming-route-template.json"
"templates/brainstorming-intent-template.json" = "specify_cli/core_pack/templates/brainstorming-intent-template.json"
"templates/brainstorming-complexity-template.json" = "specify_cli/core_pack/templates/brainstorming-complexity-template.json"
"templates/brainstorming-handoff-specify-template.json" = "specify_cli/core_pack/templates/brainstorming-handoff-specify-template.json"
```

- [ ] **Step 7: Re-run the scaffold suite and verify it passes**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_cli.py -q -k "brainstorming_truth_templates or init_installs_brainstorming_truth_templates"
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/brainstorming-facts-template.json templates/brainstorming-route-template.json templates/brainstorming-intent-template.json templates/brainstorming-complexity-template.json templates/brainstorming-handoff-specify-template.json templates/specify-draft-template.md scripts/bash/create-new-feature.sh scripts/powershell/create-new-feature.ps1 scripts/bash/common.sh scripts/powershell/common.ps1 pyproject.toml tests/test_alignment_templates.py tests/integrations/test_cli.py
git commit -m "feat: scaffold brainstorming truth artifacts"
```

---

### Task 3: Extend workflow-state serialization and artifact validation for the new truth model

**Files:**
- Modify: `templates/workflow-state-template.md`
- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `src/specify_cli/hooks/state_validation.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `tests/hooks/test_state_hooks.py`

- [ ] **Step 1: Add failing hook tests for the new truth and unknown gates**

Add to `tests/hooks/test_artifact_hooks.py`:

```python
def test_specify_artifact_validation_requires_brainstorming_truth_files(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "brainstorming").mkdir()

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert not result.ok
    assert any("facts.json" in error.message for error in result.errors)
    assert any("route.json" in error.message for error in result.errors)
```

Add to `tests/hooks/test_state_hooks.py`:

```python
def test_serialize_workflow_state_preserves_brainstorming_lock_and_reopen_fields(tmp_path: Path):
    state = tmp_path / "workflow-state.md"
    state.write_text(
        "# Workflow State: Demo\n\n"
        "## Current Command\n\n"
        "- active_command: `sp-specify`\n"
        "- status: `active`\n\n"
        "## Phase Mode\n\n"
        "- phase_mode: `planning-only`\n"
        "- summary: `brainstorming route lock`\n\n"
        "## Fixed Lifecycle State\n\n"
        "- current_stage: `route-lock`\n"
        "- current_domain: `none`\n"
        "- next_action: `resolve blocking route unknowns`\n"
        "- blocker_reason: `missing route predicate`\n"
        "- final_handoff_decision: `undecided`\n",
        encoding="utf-8",
    )

    payload = serialize_workflow_state(state)
    assert payload["current_stage"] == "route-lock"
    assert payload["blocker_reason"] == "missing route predicate"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py -q -k "brainstorming_truth_files or route_lock"
```

Expected: FAIL because the validator and serializer do not know about the new files or stages yet.

- [ ] **Step 3: Extend `workflow-state-template.md`**

Add sections:

```markdown
## Brainstorming Locks

- facts_lock: [pending | active | closed]
- route_lock: [pending | active | closed]
- intent_lock: [pending | active | closed]
- complexity_lock: [pending | active | closed]

## Unknown Handling

- hard_unknown_count: [0]
- soft_unknown_count: [0]
- next_unknown_to_resolve: [field or none]

## Reopen Contract

- reopen_source: [none | specify | plan | tasks | implement]
- reopen_target: [none | brainstorming | specify | plan | tasks]
- reopen_reason: [why a prior truth layer must be reopened]

## Handoff Files

- handoff_to_specify: [path or none]
- handoff_to_plan: [path or none]
- handoff_to_tasks: [path or none]
- handoff_to_implement: [path or none]
```

- [ ] **Step 4: Update `serialize_workflow_state`**

In `src/specify_cli/hooks/checkpoint_serializers.py`, parse and expose:

```python
brainstorming_locks = section_body(text, "Brainstorming Locks")
unknown_handling = section_body(text, "Unknown Handling")
reopen_contract = section_body(text, "Reopen Contract")
handoff_files = section_body(text, "Handoff Files")
```

Add returned fields:

```python
"facts_lock": extract_field(brainstorming_locks, "facts_lock"),
"route_lock": extract_field(brainstorming_locks, "route_lock"),
"intent_lock": extract_field(brainstorming_locks, "intent_lock"),
"complexity_lock": extract_field(brainstorming_locks, "complexity_lock"),
"hard_unknown_count": extract_field(unknown_handling, "hard_unknown_count"),
"soft_unknown_count": extract_field(unknown_handling, "soft_unknown_count"),
"next_unknown_to_resolve": extract_field(unknown_handling, "next_unknown_to_resolve"),
"reopen_source": extract_field(reopen_contract, "reopen_source"),
"reopen_target": extract_field(reopen_contract, "reopen_target"),
"reopen_reason": extract_field(reopen_contract, "reopen_reason"),
"handoff_to_specify": extract_field(handoff_files, "handoff_to_specify"),
"handoff_to_plan": extract_field(handoff_files, "handoff_to_plan"),
"handoff_to_tasks": extract_field(handoff_files, "handoff_to_tasks"),
"handoff_to_implement": extract_field(handoff_files, "handoff_to_implement"),
```

- [ ] **Step 5: Extend artifact validation**

In `src/specify_cli/hooks/artifact_validation.py`, add required files for `specify`:

```python
"specify": (
    "spec.md",
    "alignment.md",
    "context.md",
    "specify-draft.md",
    "workflow-state.md",
    "brainstorming/facts.json",
    "brainstorming/route.json",
    "brainstorming/intent.json",
    "brainstorming/complexity.json",
    "brainstorming/handoff-to-specify.json",
),
```

Add a helper to validate required `unknown` objects:

```python
def _validate_unknown_objects(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object"]
    unknowns = payload.get("unknowns", [])
    if unknowns is None:
        return []
    if not isinstance(unknowns, list):
        return [f"{label} unknowns must be a list"]
    errors: list[str] = []
    for index, item in enumerate(unknowns):
        if not isinstance(item, dict):
            errors.append(f"{label} unknowns[{index}] must be an object")
            continue
        for key in ("field", "question", "blocking_level", "resolver", "latest_resolve_phase", "status"):
            if not str(item.get(key, "")).strip():
                errors.append(f"{label} unknowns[{index}] missing {key}")
    return errors
```

Call it for `facts.json` and `handoff-to-specify.json` where appropriate.

- [ ] **Step 6: Re-run the focused hook suite**

Run:

```bash
uv run pytest tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py -q -k "brainstorming_truth_files or route_lock"
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/workflow-state-template.md src/specify_cli/hooks/checkpoint_serializers.py src/specify_cli/hooks/artifact_validation.py src/specify_cli/hooks/state_validation.py tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py
git commit -m "feat: validate brainstorming truth layer"
```

---

### Task 4: Rewrite `sp-specify` around the brainstorming kernel and deterministic locks

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/command-partials/specify/shell.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/references-template.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_anti_surface_guidance.py`

- [ ] **Step 1: Add failing assertions for the staged lock flow and deterministic questioning**

Add to `tests/test_alignment_templates.py`:

```python
def test_specify_template_replaces_fixed_heavy_only_lifecycle_with_brainstorming_lock_flow() -> None:
    content = _read("templates/commands/specify.md").lower()

    assert "facts-lock" in content
    assert "route-lock" in content
    assert "intent-lock" in content
    assert "complexity-lock" in content
    assert "only ask questions tied to explicit unresolved fields or rule predicates" in content
    assert "conversation memory is not a valid handoff surface" in content
    assert "primary route" in content
    assert "t1 local" in content
    assert "t4 reconstruction" in content
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_specify_anti_surface_guidance.py -q -k "brainstorming_lock_flow or explicit unresolved fields"
```

Expected: FAIL because the template still teaches the older fixed-heavy contract.

- [ ] **Step 3: Rewrite `templates/commands/specify.md`**

Replace the current fixed-heavy lifecycle sections with:

```md
## Brainstorming Kernel

- `sp-specify` is the public entry shell.
- Before traditional specification compilation, run the internal brainstorming kernel.
- The kernel progresses through these deterministic locks:
  1. `facts-lock`
  2. `route-lock`
  3. `intent-lock`
  4. `complexity-lock`
- Persist each lock result before progressing.
- If a conclusion is not written to the relevant truth file, it is not a valid workflow conclusion.
```

Add explicit questioning rules:

```md
- Ask questions only when a required field or route predicate remains unresolved.
- Each question must map to a field, rule, or lock state.
- After every answer, update the relevant truth file immediately.
- Do not use freeform brainstorming chat as a substitute for field closure.
```

Add deterministic route and complexity rules:

```md
- Route selection is valid only when `route.json` records a primary route, matched rules, and any rejected-route reasoning.
- Complexity selection is valid only when `complexity.json` records the chosen `T1 Local`, `T2 Structured`, `T3 Cross-Boundary`, or `T4 Reconstruction` level and the matched trigger rules.
```

Add unknown handling rules:

```md
- `unknown` is a pending decision object, not a default exit state.
- Every unresolved `unknown` must carry `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Do not hand off past the current gate while a hard unknown remains unresolved.
```

- [ ] **Step 4: Reframe the summary shell and compiled artifact templates**

In `templates/command-partials/specify/shell.md`, rewrite the objective block:

```md
## Objective

Turn arbitrary incoming work into a locked, auditable, machine-readable intent chain before compiling the familiar specification package.
```

In `templates/spec-template.md`, add sections:

```md
## Brainstorming Truth Inputs

- Route: [compiled from route.json]
- Complexity: [compiled from complexity.json]
- Must Preserve:
  - [compiled invariant]
- Allowed Optimization Scope:
  - [compiled scope]
```

In `templates/alignment-template.md`, add:

```md
## Route And Complexity Summary

- Primary Route: [route]
- Complexity Level: [T1 | T2 | T3 | T4]
- Hard Unknowns Cleared: [yes/no]
- Reopen Required: [yes/no]
```

In `templates/context-template.md`, add:

```md
## Brainstorming-Derived Execution Context

- Truth Owner: [repo | prd | mixed]
- Compatibility Constraints:
  - [constraint]
- Allowed Internal Redesign:
  - [yes/no and notes]
```

In `templates/references-template.md`, add:

```md
## Truth Sources Used For Route And Intent Lock

- [source path or user-supplied reference]
```

- [ ] **Step 5: Re-run the `sp-specify` template suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_specify_anti_surface_guidance.py -q -k "brainstorming_lock_flow or route_and_complexity or unknown"
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/commands/specify.md templates/command-partials/specify/shell.md templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/references-template.md tests/test_alignment_templates.py tests/test_specify_anti_surface_guidance.py
git commit -m "refactor: add brainstorming kernel to sp-specify"
```

---

### Task 5: Align shared and Codex integration renderers with the new `sp-specify` model

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/agents.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add failing integration tests**

Add to `tests/integrations/test_integration_base_skills.py`:

```python
def test_generated_specify_skill_teaches_brainstorming_kernel_contract(tmp_path):
    target = tmp_path / "codex-skill"
    integration = CodexIntegration()
    manifest = IntegrationManifest.empty("codex")
    integration.setup(target, manifest)
    skill = target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    content = skill.read_text(encoding="utf-8").lower()
    assert "brainstorming kernel" in content
    assert "facts-lock" in content
    assert "route-lock" in content
    assert "intent-lock" in content
    assert "complexity-lock" in content
```

Add to `tests/integrations/test_integration_codex.py`:

```python
def test_codex_generated_specify_skill_mentions_structured_handoff_and_reopen(tmp_path):
    target = tmp_path / "codex-specify"
    integration = CodexIntegration()
    manifest = IntegrationManifest.empty("codex")
    integration.setup(target, manifest)
    content = (target / ".codex" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "structured handoff" in content
    assert "reopen" in content
    assert "conversation memory is not a valid handoff surface" in content
```

- [ ] **Step 2: Run the focused integration tests to verify they fail**

Run:

```bash
uv run pytest tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q -k "brainstorming_kernel_contract or structured_handoff_and_reopen"
```

Expected: FAIL because the generated skills still append the fixed-heavy-only guidance.

- [ ] **Step 3: Replace the old fixed-heavy addendum in `src/specify_cli/integrations/base.py`**

Rename and repurpose `_append_specify_fixed_heavy_guidance` into a new helper that appends:

```python
addendum = (
    "\n"
    "## Brainstorming Kernel\n\n"
    "- `sp-specify` is the public entry shell and must begin with the internal brainstorming kernel.\n"
    "- Progress through `facts-lock`, `route-lock`, `intent-lock`, and `complexity-lock` before compiling the final specification package.\n"
    "- Ask questions only for unresolved fields or rule predicates.\n"
    "- Dynamic routing is valid only when it is derived from persisted facts and explicit rules.\n"
    "- Conversation memory is not a valid handoff surface; only persisted truth files count.\n"
    "- Downstream stages must reopen upstream truth explicitly instead of silently mutating it.\n"
)
```

Wire the helper back into the generated `sp-specify` skill path.

- [ ] **Step 4: Update Codex-specific augmentation**

In `src/specify_cli/integrations/codex/__init__.py`, replace the fixed-heavy-only `sp-specify` addendum with:

```python
"When running `sp-specify` in Codex, use native subagents only for bounded lanes that support the current brainstorming lock step or compiled specification validation.\n"
"- The lock sequence is `facts-lock`, `route-lock`, `intent-lock`, and `complexity-lock` before final specification compilation.\n"
"- Do not let subagents invent route or complexity conclusions outside the persisted truth files.\n"
"- Use join points before route closure, before complexity closure, and before final handoff compilation.\n"
```

- [ ] **Step 5: Ensure path rewriting covers the new templates and artifact locations**

In `src/specify_cli/agents.py`, verify and, if needed, extend the rewrite logic so references to `templates/brainstorming-*.json` resolve into `.specify/templates/brainstorming-*.json` in generated projects.

- [ ] **Step 6: Re-run the integration suite**

Run:

```bash
uv run pytest tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q -k "brainstorming_kernel_contract or structured_handoff_and_reopen"
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/codex/__init__.py src/specify_cli/agents.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py
git commit -m "refactor: align integrations with brainstorming kernel"
```

---

### Task 6: Teach `sp-plan` and `sp-tasks` to consume structured handoff truth

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `templates/command-partials/plan/shell.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/command-partials/tasks/shell.md`
- Create: `templates/plan-contract-template.json`
- Create: `templates/task-index-template.json`
- Create: `templates/task-packet-template.json`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing downstream contract tests**

Add to `tests/test_alignment_templates.py`:

```python
def test_plan_and_tasks_templates_consume_machine_readable_handoff_truth() -> None:
    plan = _read("templates/commands/plan.md").lower()
    tasks = _read("templates/commands/tasks.md").lower()

    assert "handoff-to-plan.json" in plan
    assert "route, intent, complexity" in plan
    assert "plan-contract.json" in plan

    assert "handoff-to-tasks.json" in tasks
    assert "task-index.json" in tasks
    assert "task-packets" in tasks
    assert "allowed optimization scope" in tasks
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py -q -k "machine_readable_handoff_truth"
```

Expected: FAIL because these templates do not yet reference the new JSON contracts.

- [ ] **Step 3: Create the contract template skeletons**

Create `templates/plan-contract-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "route": null,
  "complexity_level": null,
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "acceptance_obligations": [],
  "handoff_to_tasks_ready": false
}
```

Create `templates/task-index-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "tasks": [],
  "parallel_batches": [],
  "join_points": []
}
```

Create `templates/task-packet-template.json`:

```json
{
  "version": 1,
  "task_id": "",
  "objective": "",
  "complexity_level": null,
  "authoritative_inputs": [],
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "required_validation": [],
  "stop_and_reopen_conditions": []
}
```

- [ ] **Step 4: Update `sp-plan`**

In `templates/commands/plan.md`, add to `Load context`:

```md
- Read `FEATURE_DIR/brainstorming/handoff-to-specify.json` when present and treat it as the authoritative pre-plan truth package.
- Write `FEATURE_DIR/plan/plan-contract.json` or `FEATURE_DIR/plan-contract.json` as the machine-readable planning contract.
- Write `FEATURE_DIR/specify/handoff-to-plan.json` or equivalent canonical handoff artifact before reporting planning completion.
```

In `templates/command-partials/plan/shell.md`, add:

```md
- Primary inputs include the compiled brainstorming truth and any handoff-to-plan contract, not only the prose spec artifacts.
```

- [ ] **Step 5: Update `sp-tasks`**

In `templates/commands/tasks.md`, add:

```md
- Read `handoff-to-plan.json` as authoritative task-generation input when present.
- Emit `task-index.json` and per-task packet JSON alongside `tasks.md`.
- Carry complexity level, must-preserve invariants, allowed optimization scope, and stop-and-reopen conditions into each task packet.
```

In `templates/command-partials/tasks/shell.md`, add:

```md
- Task generation produces both human-readable `tasks.md` and machine-readable execution packets for downstream implementers.
```

- [ ] **Step 6: Re-run the focused template suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py -q -k "machine_readable_handoff_truth"
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/commands/plan.md templates/command-partials/plan/shell.md templates/commands/tasks.md templates/command-partials/tasks/shell.md templates/plan-contract-template.json templates/task-index-template.json templates/task-packet-template.json tests/test_alignment_templates.py
git commit -m "feat: add structured plan and task handoff contracts"
```

---

### Task 7: Teach `sp-implement` and implementer workers to obey the new execution contract

**Files:**
- Modify: `templates/commands/implement.md`
- Modify: `templates/worker-prompts/implementer.md`
- Create: `templates/implement-execution-state-template.json`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_testing_workflow_guidance.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add failing implement-contract tests**

Add to `tests/test_alignment_templates.py`:

```python
def test_implement_template_requires_structured_execution_contract_from_tasks() -> None:
    implement = _read("templates/commands/implement.md").lower()
    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement
    assert "allowed optimization scope" in implement
    assert "stop-and-reopen conditions" in implement
    assert "cannot redefine the product goal" in implement or "must not redefine the product goal" in implement
```

Add to `tests/integrations/test_integration_codex.py`:

```python
def test_codex_generated_implement_skill_mentions_optimization_scope_and_reopen(tmp_path):
    target = tmp_path / "codex-implement"
    integration = CodexIntegration()
    manifest = IntegrationManifest.empty("codex")
    integration.setup(target, manifest)
    content = (target / ".codex" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "allowed optimization scope" in content
    assert "must-preserve invariants" in content
    assert "reopen" in content
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py -q -k "structured_execution_contract_from_tasks or optimization_scope_and_reopen"
```

Expected: FAIL because `sp-implement` does not yet reference the new handoff file or terminology.

- [ ] **Step 3: Create `templates/implement-execution-state-template.json`**

Create:

```json
{
  "version": 1,
  "status": "gathering",
  "current_batch": null,
  "complexity_level": null,
  "active_packet_ids": [],
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "open_reopen_conditions": []
}
```

- [ ] **Step 4: Update `sp-implement`**

In `templates/commands/implement.md`, add under `Load and analyze the implementation context`:

```md
- Read `handoff-to-implement.json` when present and treat it as the authoritative execution contract.
- Do not reinterpret product intent from chat memory when `handoff-to-implement.json` disagrees or is more specific.
- Treat `must-preserve invariants`, `allowed optimization scope`, `required validation`, and `stop-and-reopen conditions` as binding execution fields.
```

Add a hard rule:

```md
- If a needed change would violate the current execution contract or require redefining the user's locked goal, stop and reopen the upstream truth layer instead of implementing through ambiguity.
```

- [ ] **Step 5: Update the implementer worker prompt**

In `templates/worker-prompts/implementer.md`, add:

```md
## Execution Contract Inputs

- `must_preserve`: invariant surfaces that cannot drift
- `allowed_optimization_scope`: areas where higher-quality redesign is allowed
- `stop_and_reopen_conditions`: conditions that require leader escalation instead of local guessing

If the packet asks for a change that conflicts with these fields, return `needs_context` or `blocked`; do not guess.
```

- [ ] **Step 6: Re-run the implement-focused suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/test_testing_workflow_guidance.py -q -k "structured_execution_contract_from_tasks or optimization_scope_and_reopen or implement"
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/commands/implement.md templates/worker-prompts/implementer.md templates/implement-execution-state-template.json tests/test_alignment_templates.py tests/test_testing_workflow_guidance.py tests/integrations/test_integration_codex.py
git commit -m "feat: bind sp-implement to structured execution contract"
```

---

### Task 8: Update top-level docs and run the full migration verification suite

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_runtime_story_docs.py`

- [ ] **Step 1: Add failing documentation tests**

Add to `tests/test_runtime_story_docs.py`:

```python
def test_readme_describes_specify_brainstorming_truth_chain() -> None:
    content = Path("README.md").read_text(encoding="utf-8").lower()
    assert "brainstorming" in content
    assert "structured handoff" in content
    assert "sp-implement" in content
```

- [ ] **Step 2: Run the focused doc tests to verify they fail**

Run:

```bash
uv run pytest tests/test_specify_guidance_docs.py tests/test_runtime_story_docs.py -q -k "brainstorming_truth_chain or internal_brainstorming"
```

Expected: FAIL because the docs still describe the older shape.

- [ ] **Step 3: Update the docs**

In `README.md`, add a short workflow explanation:

```md
`specify` remains the public entrypoint, but it now begins with an internal brainstorming kernel that locks facts, route, intent, and complexity before compiling the traditional spec package and handing off to `plan`, `tasks`, and `implement`.
```

In `docs/quickstart.md`, add:

```md
Think of `specify` as a public shell: it first runs the deterministic brainstorming layer, then compiles the planning-ready package.
```

In `PROJECT-HANDBOOK.md`, update the workflow surface entry so it names:

- brainstorming truth artifacts
- deterministic routing
- downstream structured handoff contracts through `sp-implement`

- [ ] **Step 4: Run the full verification suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_specify_anti_surface_guidance.py -q
uv run pytest tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_workflow_boundary_hooks.py -q
uv run pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/quickstart.md PROJECT-HANDBOOK.md tests/test_specify_guidance_docs.py tests/test_runtime_story_docs.py
git commit -m "docs: teach brainstorming kernel workflow chain"
```

---

## Self-Review

**Spec coverage**

- `sp-specify` as public shell with internal `brainstorming` kernel: covered by Tasks 1, 4, and 5.
- persisted `facts/route/intent/complexity` truth model: covered by Tasks 2 and 3.
- deterministic route/complexity/unknown/reopen rules: covered by Tasks 3 and 4.
- downstream `sp-plan -> sp-tasks -> sp-implement` structured handoff chain: covered by Tasks 6 and 7.
- `sp-implement` as high-standard executor inside locked intent: covered by Task 7.
- docs and user guidance realignment: covered by Task 8.

No spec requirement is intentionally left without a task.

**Placeholder scan**

- No `TBD`, `TODO`, or “implement later” placeholders remain.
- Every task names exact files and concrete verification commands.
- The plan intentionally avoids pretending to know final JSON schema details beyond the approved v1 skeletons; where schemas may evolve, the task still gives concrete initial structures to implement.

**Type consistency**

- The lock-step names are consistent: `facts-lock`, `route-lock`, `intent-lock`, `complexity-lock`.
- Complexity ladder names are consistent: `T1 Local`, `T2 Structured`, `T3 Cross-Boundary`, `T4 Reconstruction`.
- Handoff filenames are consistent across tasks: `handoff-to-specify.json`, `handoff-to-plan.json`, `handoff-to-tasks.json`, `handoff-to-implement.json`.

Plan complete and saved to `docs/superpowers/plans/2026-05-09-sp-specify-brainstorming-kernel-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
