# Discussion To Specify Fidelity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Must-Preserve Ledger, coverage gate, and conflict blocker contract that keeps `sp-discussion` conclusions faithful through `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-implement`.

**Architecture:** This is a cross-workflow template and contract change. The human-facing workflow instructions carry the `MP-*` fidelity semantics, while JSON templates, artifact validation, worker packets, and worker results carry the machine-checkable fields needed to prevent silent drift. The implementation stays compatible with the existing generated artifact chain instead of introducing a separate runtime workflow.

**Tech Stack:** Python 3.11+, Typer CLI, Markdown command templates, JSON templates, dataclass execution packet/result schemas, pytest.

---

## Source Spec

- Design: `docs/superpowers/specs/2026-05-15-discussion-to-specify-fidelity-design.md`
- Existing discussion design: `docs/superpowers/specs/2026-05-13-sp-discussion-design.md`

## File Structure

- Modify `templates/commands/discussion.md`: Require the Must-Preserve Ledger, JSON companion, Markdown/JSON integrity behavior, handoff readiness rules, and explicit conflict blocker in `sp-discussion`.
- Modify `templates/command-partials/discussion/shell.md`: Add summary-level ledger and fidelity handoff obligations for generated integration previews.
- Modify `templates/commands/specify.md`: Upgrade the existing discussion handoff intake into ledger intake, active feature copy, coverage gate, planning gate status, and conflict persistence.
- Modify `templates/brainstorming-handoff-specify-template.json`: Add v2-compatible ledger fields while preserving current core fields.
- Modify `templates/spec-template.md`, `templates/alignment-template.md`, `templates/context-template.md`, and `templates/references-template.md`: Add compact sections that preserve mapped `MP-*` items in the correct compiled artifacts.
- Modify `templates/commands/plan.md` and `templates/plan-template.md`: Treat `MP-*` items as planning obligations and add carry-forward sections.
- Modify `templates/plan-contract-template.json`: Add `mp_obligations`, `open_conflicts`, `hard_unknown_count`, and `planning_gate_status`.
- Modify `templates/commands/tasks.md` and `templates/tasks-template.md`: Preserve implementation-shaping `MP-*` IDs through guardrails, required references, validation checkpoints, and task packets.
- Modify `templates/commands/implement.md` and `templates/command-partials/implement/shell.md`: Require implementers to honor `MP-*` obligations from packets and result handoffs.
- Modify `templates/implement-execution-state-template.json`: Preserve applied `MP-*` obligations, open reopen conditions, and conflict counts during implementation.
- Modify `src/specify_cli/hooks/artifact_validation.py`: Validate the new `brainstorming/handoff-to-specify.json` shape and readiness/status invariants.
- Modify `src/specify_cli/execution/packet_schema.py`: Add structured `MustPreserveObligation` and attach obligations to `WorkerTaskPacket`.
- Modify `src/specify_cli/execution/packet_compiler.py`: Compile implementation-shaping `MP-*` references from plan/tasks artifacts into packets.
- Modify `src/specify_cli/execution/packet_validator.py`: Require preservation obligations to have stable IDs and claims when present.
- Modify `src/specify_cli/execution/result_schema.py`: Add obligation evidence to `WorkerTaskResult`.
- Modify `src/specify_cli/execution/result_validator.py`: Require evidence for packet obligations that affect acceptance or forbidden drift.
- Modify `tests/test_alignment_templates.py`: Add/extend template contract tests for all workflow surfaces.
- Modify `tests/hooks/test_artifact_hooks.py`: Add artifact validation tests for ledger schema, coverage/planning split, Markdown/JSON integrity blocker status, and conflict resolution records.
- Modify `tests/execution/test_packet_schema.py`, `tests/execution/test_packet_validator.py`, and `tests/execution/test_result_validator.py`: Add packet/result contract tests for `MP-*` obligations.
- Modify `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_toml.py`, and `tests/integrations/test_integration_base_skills.py`: Verify generated integration commands and skills contain the shared fidelity contract.
- Modify `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`: Document the fidelity ledger as the protected discussion-to-implementation handoff.

Do not change the generated workflow semantics to automatically invoke `sp-specify` from `sp-discussion`. Do not implement a new Python state machine for `sp-discussion`.

---

### Task 1: Template Contract Tests For Fidelity Surface

**Files:**
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a helper assertion for fidelity ledger language**

Add this helper near the existing helper assertions in `tests/test_alignment_templates.py`:

```python
def _assert_must_preserve_ledger_contract(content: str) -> None:
    lowered = content.lower()
    assert "must-preserve ledger" in lowered
    assert "mp-*" in lowered or "mp-###" in lowered
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "conflict blocker" in lowered or "block" in lowered and "conflict" in lowered
```

- [ ] **Step 2: Add tests for discussion and specify fidelity contracts**

Append these tests near the existing discussion/specify template tests:

```python
def test_discussion_handoff_requires_must_preserve_ledger_contract() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "handoff-to-specify.json" in content
    assert "markdown" in lowered and "json" in lowered
    assert "id" in lowered
    assert "claim" in lowered
    assert "source" in lowered
    assert "downstream_requirement" in content
    assert "owner" in lowered
    assert "latest_resolve_phase" in content
    assert "stop_and_reopen_condition" in content
    assert "do not silently" in lowered


def test_specify_discussion_handoff_has_coverage_and_planning_gate_split() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "entry_source: sp-discussion" in content
    assert "blocked_by_hard_unknowns" in content
    assert "blocked_by_conflict" in content
    assert "blocked_by_incomplete_coverage" in content
    assert "blocked_by_handoff_integrity" in content
    assert "coverage and planning readiness are separate" in lowered
    assert "markdown" in lowered and "json" in lowered and "mismatch" in lowered


def test_compiled_artifact_templates_preserve_must_preserve_ids() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")

    assert "Must-Preserve" in spec
    assert "MP-" in spec
    assert "Must-Preserve" in alignment
    assert "MP-" in alignment
    assert "Must-Preserve" in context
    assert "MP-" in context
    assert "Must-Preserve" in references
    assert "MP-" in references
```

- [ ] **Step 3: Add tests for plan/tasks/implement propagation wording**

Add these tests near `test_plan_tasks_and_implement_templates_consume_structured_handoff_contracts`:

```python
def test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations() -> None:
    plan = _read("templates/commands/plan.md")
    plan_template = _read("templates/plan-template.md")
    tasks = _read("templates/commands/tasks.md")
    tasks_template = _read("templates/tasks-template.md")
    implement = _read("templates/commands/implement.md")
    implement_shell = _read("templates/command-partials/implement/shell.md")

    for content in (plan, plan_template, tasks, tasks_template, implement, implement_shell):
        lowered = content.lower()
        assert "mp-*" in lowered or "mp-" in content
        assert "must-preserve" in lowered
        assert "conflict" in lowered

    assert "Must-Preserve Carry-Forward" in plan_template
    assert "Task Guardrail Index" in tasks_template
    assert "WorkerTaskPacket" in implement
    assert "result handoff" in implement_shell.lower()


def test_structured_json_templates_preserve_fidelity_status_fields() -> None:
    handoff = _read("templates/brainstorming-handoff-specify-template.json")
    plan_contract = _read("templates/plan-contract-template.json")
    implement_state = _read("templates/implement-execution-state-template.json")

    for content in (handoff, plan_contract, implement_state):
        assert '"must_preserve"' in content
        assert "mp_obligations" in content or "must_preserve" in content

    assert '"coverage_status"' in handoff
    assert '"planning_gate_status"' in handoff
    assert '"hard_unknown_count"' in handoff
    assert '"open_conflict_count"' in handoff
    assert '"open_conflicts"' in plan_contract
    assert '"applied_mp_obligations"' in implement_state
```

- [ ] **Step 4: Run the focused template tests and confirm they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_handoff_requires_must_preserve_ledger_contract tests/test_alignment_templates.py::test_specify_discussion_handoff_has_coverage_and_planning_gate_split tests/test_alignment_templates.py::test_compiled_artifact_templates_preserve_must_preserve_ids tests/test_alignment_templates.py::test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations tests/test_alignment_templates.py::test_structured_json_templates_preserve_fidelity_status_fields -q
```

Expected: FAIL because the templates have not yet been upgraded with the fidelity contract.

- [ ] **Step 5: Commit failing tests**

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: capture discussion fidelity template contracts"
```

---

### Task 2: Upgrade Discussion And Specify Template Contracts

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Modify: `templates/commands/specify.md`

- [ ] **Step 1: Add Must-Preserve Ledger instructions to `templates/commands/discussion.md`**

In `templates/commands/discussion.md`, extend `primary_outputs` to include `handoff-to-specify.json` after `handoff-to-specify.md`.

Add this section after `## Handoff To sp-specify`:

```markdown
## Must-Preserve Ledger

When the user explicitly requests handoff, `handoff-to-specify.md` must include a Must-Preserve Ledger. The ledger preserves only semantic units that would cause product or implementation drift if lost.

Ledger item types:

- `goal`
- `scope`
- `non_goal`
- `scenario`
- `decision`
- `reference`
- `tradeoff`
- `blocking_question`

Each ledger item must include:

- `id`: stable `MP-###`
- `type`: one of the ledger item types
- `claim`: the exact conclusion to preserve
- `source`: source file, reference, or user confirmation
- `downstream_requirement`: how later artifacts must carry this forward
- `blocking_level`: `hard` or `soft`
- `owner`: `user`, `evidence`, `downstream-contract`, or `risk-waiver`
- `latest_resolve_phase`: latest phase allowed to resolve or carry the item
- `status`: `pending`, `mapped`, `resolved`, `deferred`, `superseded`, or `dropped`
- `deferred_to`: downstream phase when status is `deferred`
- `stop_and_reopen_condition`: required for deferred items
- `superseded_by`: replacement item or conflict resolution when status is `superseded`
- `mapped_to`: empty in discussion handoff; populated by `sp-specify`

Include ledger items for confirmed goals, selected scope, non-goals, acceptance-shaping scenarios, selected decisions, critical references, selected or rejected trade-offs whose rationale matters, and blocking open questions.
```

- [ ] **Step 2: Add Markdown/JSON integrity instructions to `templates/commands/discussion.md`**

Continue the same section with:

```markdown
## Handoff JSON Companion

When `handoff-to-specify.md` is written, also write `.specify/discussions/<slug>/handoff-to-specify.json` with the same ledger item IDs and key fields.

The Markdown and JSON forms must agree on every ledger item's `id`, `type`, `claim`, `blocking_level`, `owner`, `latest_resolve_phase`, and `status`.

If an existing Markdown handoff and JSON companion disagree, block and refresh the handoff instead of choosing one silently.
```

- [ ] **Step 3: Add handoff readiness wording to `templates/commands/discussion.md`**

Add this paragraph below the existing handoff field list:

```markdown
Do not mark the discussion `handoff-ready` until every confirmed or critical item is represented in the Must-Preserve Ledger. Deferred items require `deferred_to`, `owner`, `latest_resolve_phase`, and `stop_and_reopen_condition`.
```

- [ ] **Step 4: Update `templates/command-partials/discussion/shell.md`**

In the Output Contract list, add:

```markdown
- When explicit handoff is requested, write both `handoff-to-specify.md` and `handoff-to-specify.json` with a Must-Preserve Ledger.
- Do not mark handoff ready if a confirmed goal, non-goal, decision, critical reference, trade-off rationale, or blocking question is missing from the ledger.
```

- [ ] **Step 5: Replace the Discussion Handoff Intake section in `templates/commands/specify.md`**

Replace the existing `## Discussion Handoff Intake` section with:

```markdown
## Discussion Handoff Intake

If the user invokes `sp-specify` with an explicit path to `.specify/discussions/<slug>/handoff-to-specify.md`, or pastes a discussion handoff block, read that handoff before parsing the feature request.

- Treat the discussion handoff as an authoritative input to the brainstorming kernel, not a bypass around it.
- Read `.specify/discussions/<slug>/handoff-to-specify.json` when present.
- If Markdown and JSON disagree on any ledger item's `id`, `type`, `claim`, `blocking_level`, `owner`, `latest_resolve_phase`, or `status`, block with `coverage_status: blocked_by_handoff_integrity` and ask the user to refresh the discussion handoff.
- If Markdown exists but JSON is missing, reconstruct the JSON companion into `FEATURE_DIR/brainstorming/handoff-to-specify.json` and record the reconstruction source.
- If JSON exists but Markdown is missing, block because the user-reviewable handoff source is absent.
- Record `entry_source: sp-discussion` and the handoff path or pasted discussion handoff marker in the generated feature artifacts.
- Copy the Must-Preserve Ledger into `FEATURE_DIR/brainstorming/handoff-to-specify.json`.
- Preserve confirmed requirements, confirmed non-goals, settled decisions, selected technical direction, critical references, and trade-off rationale in `facts.json`, `intent.json`, `complexity.json`, `handoff-to-specify.json`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, or `references.md` according to the existing artifact responsibilities.
- Convert open questions from the handoff into explicit unknowns with `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Do not re-ask settled discussion questions unless repository evidence, constitution rules, or user correction contradicts the handoff.
- If a settled discussion conclusion conflicts with repository evidence, constitution rules, project rules, project cognition evidence, or architecture constraints, block and ask the user to choose keep, revise, drop, or defer with an explicit risk contract. Do not silently reinterpret the ledger item.
```

- [ ] **Step 6: Add coverage gate language to `templates/commands/specify.md`**

After the brainstorming kernel lock rules, add:

```markdown
## Discussion Fidelity Coverage Gate

When `entry_source` is `sp-discussion`, coverage and planning readiness are separate.

- `coverage_status`: `not_started | incomplete | complete | blocked_by_handoff_integrity`
- `planning_gate_status`: `ready | blocked_by_hard_unknowns | blocked_by_conflict | blocked_by_incomplete_coverage | blocked_by_handoff_integrity`

Before recommending `/sp.plan`, write `hard_unknown_count` and `open_conflict_count` to `brainstorming/handoff-to-specify.json`.

Coverage can be complete only when every active `MP-*` item is mapped to at least one artifact, and every resolved, superseded, dropped, or deferred item carries the required evidence fields.

Planning can be ready only when coverage is complete, no hard unknowns remain open, and no conflicts remain open.
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_handoff_requires_must_preserve_ledger_contract tests/test_alignment_templates.py::test_specify_discussion_handoff_has_coverage_and_planning_gate_split -q
```

Expected: PASS.

- [ ] **Step 8: Commit template intake changes**

```powershell
git add templates/commands/discussion.md templates/command-partials/discussion/shell.md templates/commands/specify.md
git commit -m "feat: add discussion fidelity handoff contract"
```

---

### Task 3: Upgrade Structured Handoff JSON Template And Artifact Validation

**Files:**
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/hooks/test_artifact_hooks.py`

- [ ] **Step 1: Add failing hook tests for complete ledger payload**

Append this helper and test to `tests/hooks/test_artifact_hooks.py`:

```python
def _valid_must_preserve_handoff_payload() -> str:
    return """{
      "version": 2,
      "status": "ready",
      "entry_source": "sp-discussion",
      "source_handoff": ".specify/discussions/demo/handoff-to-specify.md",
      "source_handoff_json": ".specify/discussions/demo/handoff-to-specify.json",
      "facts_file": "brainstorming/facts.json",
      "route_file": "brainstorming/route.json",
      "intent_file": "brainstorming/intent.json",
      "complexity_file": "brainstorming/complexity.json",
      "soft_unknowns": [],
      "unknowns": [],
      "compile_ready": true,
      "coverage_status": "complete",
      "planning_gate_status": "ready",
      "hard_unknown_count": 0,
      "open_conflict_count": 0,
      "must_preserve": [
        {
          "id": "MP-001",
          "type": "goal",
          "claim": "Preserve the agreed product outcome.",
          "source": "requirements.md#feature-goal",
          "downstream_requirement": "Carry into spec.md Feature Goal and plan.md Summary.",
          "blocking_level": "hard",
          "owner": "user",
          "latest_resolve_phase": "specify-compile",
          "status": "mapped",
          "deferred_to": null,
          "stop_and_reopen_condition": null,
          "superseded_by": null,
          "mapped_to": ["spec.md#Feature Goal"]
        }
      ],
      "conflicts": []
    }"""


def test_specify_artifact_validation_accepts_complete_must_preserve_handoff(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n\n## Fidelity Requirements\n", encoding="utf-8")
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        "workflow.artifacts.validate",
        project,
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
```

- [ ] **Step 2: Add failing hook tests for status invariants**

Append:

```python
def test_specify_artifact_validation_blocks_ready_gate_with_open_conflict(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    payload = _valid_must_preserve_handoff_payload().replace(
        '"open_conflict_count": 0',
        '"open_conflict_count": 1',
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        "workflow.artifacts.validate",
        project,
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("planning_gate_status" in message and "open conflicts" in message for message in result.errors)


def test_specify_artifact_validation_blocks_complete_coverage_with_unmapped_active_item(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    payload = _valid_must_preserve_handoff_payload().replace(
        '"mapped_to": ["spec.md#Feature Goal"]',
        '"mapped_to": []',
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        "workflow.artifacts.validate",
        project,
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-001" in message and "mapped_to" in message for message in result.errors)
```

- [ ] **Step 3: Run the new hook tests and confirm they fail**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_accepts_complete_must_preserve_handoff tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_blocks_ready_gate_with_open_conflict tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_blocks_complete_coverage_with_unmapped_active_item -q
```

Expected: FAIL until validation supports the new handoff schema.

- [ ] **Step 4: Update `templates/brainstorming-handoff-specify-template.json`**

Replace its content with:

```json
{
  "version": 2,
  "status": "pending",
  "entry_source": null,
  "source_handoff": null,
  "source_handoff_json": null,
  "facts_file": "brainstorming/facts.json",
  "route_file": "brainstorming/route.json",
  "intent_file": "brainstorming/intent.json",
  "complexity_file": "brainstorming/complexity.json",
  "soft_unknowns": [],
  "unknowns": [],
  "must_preserve": [],
  "conflicts": [],
  "coverage_status": "not_started",
  "planning_gate_status": "blocked_by_incomplete_coverage",
  "hard_unknown_count": 0,
  "open_conflict_count": 0,
  "compile_ready": false
}
```

- [ ] **Step 5: Add validation helpers to `artifact_validation.py`**

Add these constants near other required-key constants:

```python
MP_REQUIRED_KEYS = frozenset(
    {
        "id",
        "type",
        "claim",
        "source",
        "downstream_requirement",
        "owner",
        "latest_resolve_phase",
        "status",
        "mapped_to",
    }
)

MP_ACTIVE_STATUSES = frozenset({"pending", "mapped"})
MP_CLOSED_STATUSES = frozenset({"resolved", "superseded", "dropped", "deferred"})
MP_VALID_STATUSES = MP_ACTIVE_STATUSES | MP_CLOSED_STATUSES
MP_VALID_TYPES = frozenset(
    {
        "goal",
        "scope",
        "non_goal",
        "scenario",
        "decision",
        "reference",
        "tradeoff",
        "blocking_question",
    }
)
MP_VALID_COVERAGE_STATUSES = frozenset(
    {"not_started", "incomplete", "complete", "blocked_by_handoff_integrity"}
)
MP_VALID_PLANNING_GATE_STATUSES = frozenset(
    {
        "ready",
        "blocked_by_hard_unknowns",
        "blocked_by_conflict",
        "blocked_by_incomplete_coverage",
        "blocked_by_handoff_integrity",
    }
)
```

Add these functions after `_validate_unknown_objects`:

```python
def _validate_must_preserve_items(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    items = payload.get("must_preserve", [])
    if items is None:
        return errors
    if not isinstance(items, list):
        return [f"{label} must_preserve must be a list"]

    coverage_status = str(payload.get("coverage_status") or "").strip()
    for index, item in enumerate(items):
        item_label = f"{label} must_preserve[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        mp_id = str(item.get("id") or f"item {index}").strip()
        missing = sorted(key for key in MP_REQUIRED_KEYS if not str(item.get(key, "")).strip() and key != "mapped_to")
        for key in missing:
            errors.append(f"{item_label} {mp_id} missing {key}")
        if not str(item.get("id") or "").startswith("MP-"):
            errors.append(f"{item_label} id must start with MP-")
        if str(item.get("type") or "").strip() not in MP_VALID_TYPES:
            errors.append(f"{item_label} {mp_id} has invalid type")
        status = str(item.get("status") or "").strip()
        if status not in MP_VALID_STATUSES:
            errors.append(f"{item_label} {mp_id} has invalid status")
        mapped_to = item.get("mapped_to")
        if not isinstance(mapped_to, list):
            errors.append(f"{item_label} {mp_id} mapped_to must be a list")
            mapped_to = []
        if coverage_status == "complete" and status in MP_ACTIVE_STATUSES and not mapped_to:
            errors.append(f"{item_label} {mp_id} is active but missing mapped_to coverage")
        if status == "deferred":
            for key in ("deferred_to", "owner", "latest_resolve_phase", "stop_and_reopen_condition"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{item_label} {mp_id} deferred item missing {key}")
        if status == "superseded" and not str(item.get("superseded_by") or "").strip():
            errors.append(f"{item_label} {mp_id} superseded item missing superseded_by")
    return errors


def _validate_conflict_records(payload: dict[str, Any], label: str) -> list[str]:
    conflicts = payload.get("conflicts", [])
    if conflicts is None:
        return []
    if not isinstance(conflicts, list):
        return [f"{label} conflicts must be a list"]

    errors: list[str] = []
    for index, item in enumerate(conflicts):
        conflict_label = f"{label} conflicts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{conflict_label} must be an object")
            continue
        status = str(item.get("status") or "").strip()
        resolution = str(item.get("resolution") or "none").strip()
        if status not in {"open", "closed"}:
            errors.append(f"{conflict_label} has invalid status")
        if resolution not in {"keep", "revise", "drop", "defer", "none"}:
            errors.append(f"{conflict_label} has invalid resolution")
        if status == "closed":
            if resolution == "none":
                errors.append(f"{conflict_label} closed conflict missing resolution")
            if not str(item.get("user_decision_source") or "").strip():
                errors.append(f"{conflict_label} closed conflict missing user_decision_source")
            if resolution == "revise" and not str(item.get("superseded_by") or "").strip():
                errors.append(f"{conflict_label} revise resolution missing superseded_by")
            if resolution in {"drop", "defer"} and not str(item.get("approved_risk_contract") or "").strip():
                errors.append(f"{conflict_label} {resolution} resolution missing approved_risk_contract")
    return errors


def _validate_handoff_to_specify_payload(payload: Any, label: str) -> list[str]:
    errors = _validate_unknown_objects(payload, label)
    if not isinstance(payload, dict):
        return errors

    coverage_status = str(payload.get("coverage_status") or "").strip()
    planning_gate_status = str(payload.get("planning_gate_status") or "").strip()
    if coverage_status and coverage_status not in MP_VALID_COVERAGE_STATUSES:
        errors.append(f"{label} has invalid coverage_status")
    if planning_gate_status and planning_gate_status not in MP_VALID_PLANNING_GATE_STATUSES:
        errors.append(f"{label} has invalid planning_gate_status")

    errors.extend(_validate_must_preserve_items(payload, label))
    errors.extend(_validate_conflict_records(payload, label))

    hard_unknown_count = payload.get("hard_unknown_count", 0)
    open_conflict_count = payload.get("open_conflict_count", 0)
    if planning_gate_status == "ready":
        if isinstance(hard_unknown_count, int) and hard_unknown_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open hard unknowns")
        if isinstance(open_conflict_count, int) and open_conflict_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open conflicts")
        if coverage_status != "complete":
            errors.append(f"{label} planning_gate_status ready requires coverage_status complete")
    if coverage_status == "blocked_by_handoff_integrity" and planning_gate_status != "blocked_by_handoff_integrity":
        errors.append(f"{label} handoff integrity blocks must also set planning_gate_status blocked_by_handoff_integrity")
    return errors
```

- [ ] **Step 6: Wire the new helper into `_validate_specify_draft_artifacts`**

Replace the existing `handoff-to-specify.json` validation call:

```python
    errors.extend(
        _validate_brainstorming_json_artifact(
            feature_dir,
            "brainstorming/handoff-to-specify.json",
            validate_unknowns=True,
        )
    )
```

with:

```python
    handoff_payload, handoff_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "handoff-to-specify.json",
        "brainstorming/handoff-to-specify.json",
    )
    if handoff_errors:
        errors.extend(handoff_errors)
    else:
        errors.extend(_validate_handoff_to_specify_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))
```

- [ ] **Step 7: Run focused hook tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_accepts_complete_must_preserve_handoff tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_blocks_ready_gate_with_open_conflict tests/hooks/test_artifact_hooks.py::test_specify_artifact_validation_blocks_complete_coverage_with_unmapped_active_item -q
```

Expected: PASS.

- [ ] **Step 8: Run existing artifact hook smoke tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit JSON template and validation changes**

```powershell
git add templates/brainstorming-handoff-specify-template.json src/specify_cli/hooks/artifact_validation.py tests/hooks/test_artifact_hooks.py
git commit -m "feat: validate discussion fidelity handoff artifacts"
```

---

### Task 4: Add Fidelity Fields To Compiled Spec, Context, Reference, Plan, And Task Templates

**Files:**
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/references-template.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/plan-template.md`
- Modify: `templates/plan-contract-template.json`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/tasks-template.md`

- [ ] **Step 1: Add Must-Preserve sections to spec/alignment/context/references templates**

In `templates/spec-template.md`, under `## Brainstorming Truth Inputs`, add:

```markdown
## Must-Preserve Discussion Inputs

- **Source**: [Discussion handoff path when `entry_source: sp-discussion`]
- **Coverage Status**: [coverage_status from `brainstorming/handoff-to-specify.json`]
- **Planning Gate Status**: [planning_gate_status from `brainstorming/handoff-to-specify.json`]

### Mapped Must-Preserve Items

- `MP-###` [type]: [claim] -> [where this spec preserves it]

### Discussion Conflicts

- [Open conflict ID, MP ID, and required user decision; remove this section when none]
```

In `templates/alignment-template.md`, under the first route/complexity summary, add:

```markdown
## Must-Preserve Coverage

- Coverage Status: [coverage_status]
- Planning Gate Status: [planning_gate_status]
- Hard Unknown Count: [hard_unknown_count]
- Open Conflict Count: [open_conflict_count]

| MP ID | Type | Coverage Disposition | Artifact Mapping | Notes |
| --- | --- | --- | --- | --- |
| MP-### | [type] | [mapped | resolved | deferred | superseded | dropped] | [artifact anchor] | [risk or reopen condition] |
```

In `templates/context-template.md`, under `## Brainstorming-Derived Execution Context`, add:

```markdown
## Must-Preserve Execution Constraints

- `MP-###`: [implementation-shaping decision, reference, non-goal, or trade-off]
- Stop-and-reopen conditions:
  - [condition tied to MP ID]
```

In `templates/references-template.md`, under `## Truth Sources Used For Route And Intent Lock`, add:

```markdown
## Must-Preserve Reference Map

| MP ID | Source | Why It Must Be Preserved | Downstream Consumer |
| --- | --- | --- | --- |
| MP-### | [source path or URL] | [constraint or evidence role] | [spec | context | plan | tasks | implement] |
```

- [ ] **Step 2: Add plan command preservation requirements**

In `templates/commands/plan.md`, after the context loading list item that reads `FEATURE_DIR/brainstorming/handoff-to-specify.json`, add:

```markdown
   - If `brainstorming/handoff-to-specify.json` contains `must_preserve`, treat those `MP-*` items as planning obligations, not background notes.
   - If `planning_gate_status` is not `ready`, stop and route back to `{{invoke:specify}}` or to the user conflict decision named by the handoff.
   - If any `conflicts` item has `status: open`, stop and ask the user to resolve the conflict before planning.
```

In the synthesis instructions near "Copy locked planning decisions", add:

```markdown
   - Add each implementation-shaping `MP-*` item to `plan.md#Must-Preserve Carry-Forward`, `Locked Planning Decisions`, `Implementation Constitution`, or `Alignment Inputs`.
   - Preserve `MP-*` IDs when the plan consumes goals, non-goals, references, decisions, trade-offs, and stop-and-reopen conditions.
```

- [ ] **Step 3: Add plan template section**

In `templates/plan-template.md`, after `## Locked Planning Decisions`, add:

```markdown
## Must-Preserve Carry-Forward

<!--
  Copy implementation-shaping MP-* items from brainstorming/handoff-to-specify.json,
  spec.md, alignment.md, context.md, and references.md.
  Preserve the MP ID so task generation and implementation can prove the original
  discussion conclusion was not lost.
-->

| MP ID | Type | Planning Obligation | Plan Location | Reopen Condition |
| --- | --- | --- | --- | --- |
| MP-### | [goal | scope | non_goal | scenario | decision | reference | tradeoff] | [what the plan must preserve] | [section anchor] | [condition or none] |
```

- [ ] **Step 4: Update `templates/plan-contract-template.json`**

Add fields before `handoff_to_tasks_ready`:

```json
  "mp_obligations": [],
  "open_conflicts": [],
  "hard_unknown_count": 0,
  "planning_gate_status": null,
```

- [ ] **Step 5: Add task command and task template preservation requirements**

In `templates/commands/tasks.md`, after the design documents load list, add:

```markdown
   - Read `plan.md#Must-Preserve Carry-Forward` when present.
   - Carry implementation-shaping `MP-*` items into task guardrails, required references, validation checkpoints, task packets, or explicit deferred notes.
   - If a task would violate an `MP-*` non-goal, decision, reference obligation, or trade-off rationale, stop and route back to the user conflict decision instead of silently generating divergent tasks.
```

In `templates/tasks-template.md`, under `## Planning Inputs`, add:

```markdown
- **Must-preserve discussion obligations**: Copy relevant `MP-*` items from `plan.md`, `spec.md`, `alignment.md`, `context.md`, `references.md`, and `brainstorming/handoff-to-specify.json`. Each implementation-shaping item must appear in the Task Guardrail Index, a required reference, a validation checkpoint, a task packet field, or an explicit deferred note.
```

Under `## Task Guardrail Index`, add:

```markdown
- Include `MP-*` IDs for any task that carries a discussion-derived goal, non-goal, decision, reference, trade-off, acceptance signal, or stop-and-reopen condition.
```

- [ ] **Step 6: Run focused template tests**

Run only the compiled artifact and JSON template tests at this stage:

```powershell
pytest tests/test_alignment_templates.py::test_compiled_artifact_templates_preserve_must_preserve_ids tests/test_alignment_templates.py::test_structured_json_templates_preserve_fidelity_status_fields -q
```

Expected: PASS. The implement propagation test is intentionally left for Task 6 because it depends on `implement.md`, the implement shell partial, and `implement-execution-state-template.json`.

- [ ] **Step 7: Commit compiled artifact and planning changes**

```powershell
git add templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/references-template.md templates/commands/plan.md templates/plan-template.md templates/plan-contract-template.json templates/commands/tasks.md templates/tasks-template.md tests/test_alignment_templates.py
git commit -m "feat: carry discussion fidelity into planning artifacts"
```

---

### Task 5: Add Fidelity Obligations To Worker Packets And Results

**Files:**
- Modify: `src/specify_cli/execution/packet_schema.py`
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/execution/packet_validator.py`
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Add failing packet schema test**

In `tests/execution/test_packet_schema.py`, add:

```python
def test_worker_task_packet_preserves_must_preserve_obligations() -> None:
    packet = WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T017",
        story_id="US1",
        objective="Implement auth flow",
        intent=ExecutionIntent(
            outcome="Implement auth flow without changing the public contract shape",
            constraints=["Do not create a parallel auth stack"],
            success_signals=["login/logout behavior implemented"],
        ),
        scope=PacketScope(
            write_scope=["src/services/auth_service.py"],
            read_scope=["src/contracts/auth.py"],
        ),
        context_bundle=[
            ContextBundleItem(
                path=".specify/project-cognition/status.json",
                kind="project_cognition",
                purpose="Project cognition freshness entrypoint",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="required runtime readiness source",
            )
        ],
        required_references=[
            PacketReference(path="src/contracts/auth.py", reason="preserve MP-002")
        ],
        hard_rules=["Every public function changed must have tests"],
        forbidden_drift=["MP-002: Do not create a parallel auth stack"],
        validation_gates=["pytest tests/unit/test_auth_service.py -q"],
        done_criteria=["login/logout behavior implemented"],
        handoff_requirements=["return changed files"],
        must_preserve_obligations=[
            MustPreserveObligation(
                id="MP-002",
                type="non_goal",
                claim="Do not create a parallel auth stack.",
                source="handoff-to-specify.json",
                downstream_requirement="Keep auth implementation inside existing service boundary.",
                mapped_to=["tasks.md#Task Guardrail Index"],
                stop_and_reopen_condition="Implementation requires a parallel auth stack.",
            )
        ],
    )

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.must_preserve_obligations[0].id == "MP-002"
    assert restored.must_preserve_obligations[0].type == "non_goal"
    assert restored.must_preserve_obligations[0].mapped_to == ["tasks.md#Task Guardrail Index"]
```

Add `MustPreserveObligation` to the import list from `specify_cli.execution.packet_schema`.

- [ ] **Step 2: Add failing packet validator test**

In `tests/execution/test_packet_validator.py`, add:

```python
def test_validate_worker_task_packet_rejects_malformed_must_preserve_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="002",
            type="decision",
            claim="",
            source="handoff-to-specify.json",
            downstream_requirement="Preserve this decision.",
        )
    ]

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "must-preserve" in exc.value.message.lower()
```

Add `MustPreserveObligation` and `validate_worker_task_packet` to imports if not already present.

- [ ] **Step 3: Add failing result evidence test**

In `tests/execution/test_result_validator.py`, add:

```python
def test_validate_worker_task_result_requires_must_preserve_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="MP-002",
            type="non_goal",
            claim="Do not create a parallel auth stack.",
            source="handoff-to-specify.json",
            downstream_requirement="Keep auth implementation inside existing service boundary.",
            mapped_to=["tasks.md#Task Guardrail Index"],
            stop_and_reopen_condition="Implementation requires a parallel auth stack.",
        )
    ]
    sample_packet.required_evidence = ["must_preserve_evidence"]
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "must-preserve evidence" in exc.value.message
```

Add a positive test:

```python
def test_validate_worker_task_result_accepts_must_preserve_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="MP-002",
            type="non_goal",
            claim="Do not create a parallel auth stack.",
            source="handoff-to-specify.json",
            downstream_requirement="Keep auth implementation inside existing service boundary.",
            mapped_to=["tasks.md#Task Guardrail Index"],
            stop_and_reopen_condition="Implementation requires a parallel auth stack.",
        )
    ]
    sample_packet.required_evidence = ["must_preserve_evidence"]
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
        must_preserve_evidence=[
            {
                "mp_id": "MP-002",
                "evidence": "No new auth stack files were added; implementation stayed in src/services/auth_service.py.",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "success"
```

- [ ] **Step 4: Run failing execution tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py::test_worker_task_packet_preserves_must_preserve_obligations tests/execution/test_packet_validator.py::test_validate_worker_task_packet_rejects_malformed_must_preserve_obligation tests/execution/test_result_validator.py::test_validate_worker_task_result_requires_must_preserve_evidence tests/execution/test_result_validator.py::test_validate_worker_task_result_accepts_must_preserve_evidence -q
```

Expected: FAIL until schemas and validators are updated.

- [ ] **Step 5: Add `MustPreserveObligation` dataclass to `packet_schema.py`**

In `src/specify_cli/execution/packet_schema.py`, add after `PacketReference`:

```python
@dataclass(slots=True)
class MustPreserveObligation:
    id: str
    type: str
    claim: str
    source: str
    downstream_requirement: str
    mapped_to: list[str] = field(default_factory=list)
    stop_and_reopen_condition: str = ""
```

Add field to `WorkerTaskPacket`:

```python
    must_preserve_obligations: list[MustPreserveObligation] = field(default_factory=list)
```

In `worker_task_packet_from_json`, add:

```python
    must_preserve_obligations = [
        MustPreserveObligation(**_filter_dataclass_payload(MustPreserveObligation, item))
        for item in payload.get("must_preserve_obligations", [])
        if isinstance(item, dict)
    ]
```

Set:

```python
    packet_payload["must_preserve_obligations"] = must_preserve_obligations
```

- [ ] **Step 6: Validate obligations in `packet_validator.py`**

In `validate_worker_task_packet`, before `return packet`, add:

```python
    for obligation in packet.must_preserve_obligations:
        if not obligation.id.startswith("MP-"):
            raise PacketValidationError("DP1", "must-preserve obligation id must start with MP-")
        if not obligation.type or not obligation.claim or not obligation.source or not obligation.downstream_requirement:
            raise PacketValidationError("DP1", "must-preserve obligation is missing required fields")
```

- [ ] **Step 7: Compile obligations in `packet_compiler.py`**

Add this helper near `_section_or_subsection_values`:

```python
MP_LINE_RE = re.compile(r"\b(MP-\d{3})\b\s*:?\s*(?P<claim>.+)")


def _must_preserve_obligations_from_text(text: str, *, source: str) -> list[MustPreserveObligation]:
    obligations: list[MustPreserveObligation] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = MP_LINE_RE.search(line)
        if not match:
            continue
        mp_id = match.group(1)
        if mp_id in seen:
            continue
        seen.add(mp_id)
        claim = match.group("claim").strip(" -|")
        obligations.append(
            MustPreserveObligation(
                id=mp_id,
                type="execution",
                claim=claim or line.strip(),
                source=source,
                downstream_requirement="Preserve this discussion-derived obligation during implementation.",
                mapped_to=[source],
            )
        )
    return obligations
```

Import `MustPreserveObligation` from `.packet_schema`.

Before constructing `packet`, add:

```python
    must_preserve_obligations = _unique_obligations(
        [
            *_must_preserve_obligations_from_text(plan_text, source="plan.md"),
            *_must_preserve_obligations_from_text(tasks_text, source="tasks.md"),
        ]
    )
```

Add helper:

```python
def _unique_obligations(values: list[MustPreserveObligation]) -> list[MustPreserveObligation]:
    seen: set[str] = set()
    unique: list[MustPreserveObligation] = []
    for value in values:
        if value.id in seen:
            continue
        seen.add(value.id)
        unique.append(value)
    return unique
```

Pass into `WorkerTaskPacket`:

```python
        must_preserve_obligations=must_preserve_obligations,
```

- [ ] **Step 8: Add result evidence field in `result_schema.py`**

Add to `WorkerTaskResult`:

```python
    must_preserve_evidence: list[dict[str, str]] = field(default_factory=list)
```

In `worker_task_result_from_json`, normalize it like other evidence fields:

```python
    result_payload["must_preserve_evidence"] = _normalize_evidence_items(
        result_payload.get("must_preserve_evidence", [])
    )
```

- [ ] **Step 9: Validate result evidence in `result_validator.py`**

In the `success` branch, after required evidence checks, add:

```python
        if packet.must_preserve_obligations or "must_preserve_evidence" in required_evidence:
            if not result.must_preserve_evidence:
                raise PacketValidationError("DP3", "worker result is missing must-preserve evidence")
            evidence_ids = {
                str(item.get("mp_id", "")).strip()
                for item in result.must_preserve_evidence
                if isinstance(item, dict)
            }
            missing_obligations = [
                obligation.id
                for obligation in packet.must_preserve_obligations
                if obligation.id not in evidence_ids
            ]
            if missing_obligations:
                joined = ", ".join(missing_obligations)
                raise PacketValidationError(
                    "DP3",
                    f"worker result is missing must-preserve evidence for: {joined}",
                )
```

- [ ] **Step 10: Run focused execution tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py::test_worker_task_packet_preserves_must_preserve_obligations tests/execution/test_packet_validator.py::test_validate_worker_task_packet_rejects_malformed_must_preserve_obligation tests/execution/test_result_validator.py::test_validate_worker_task_result_requires_must_preserve_evidence tests/execution/test_result_validator.py::test_validate_worker_task_result_accepts_must_preserve_evidence -q
```

Expected: PASS.

- [ ] **Step 11: Run execution package tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: PASS.

- [ ] **Step 12: Commit packet/result contract changes**

```powershell
git add src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_compiler.py src/specify_cli/execution/packet_validator.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py
git commit -m "feat: carry must-preserve obligations in worker packets"
```

---

### Task 6: Update Implement Workflow And Execution State

**Files:**
- Modify: `templates/commands/implement.md`
- Modify: `templates/command-partials/implement/shell.md`
- Modify: `templates/implement-execution-state-template.json`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update implementation execution state template**

Replace `templates/implement-execution-state-template.json` with:

```json
{
  "version": 2,
  "status": "gathering",
  "current_batch": null,
  "complexity_level": null,
  "active_packet_ids": [],
  "must_preserve": [],
  "applied_mp_obligations": [],
  "allowed_optimization_scope": [],
  "open_reopen_conditions": [],
  "open_conflict_count": 0,
  "hard_unknown_count": 0
}
```

- [ ] **Step 2: Update implement command pre-dispatch guidance**

In `templates/commands/implement.md`, near the existing WorkerTaskPacket hard rule, add:

```markdown
- If a task packet contains `must_preserve_obligations`, the worker must preserve those `MP-*` items or return a blocked result with the exact stop-and-reopen condition.
- Do not dispatch a packet that drops a discussion-derived `MP-*` obligation from `tasks.md`, `plan.md`, or `brainstorming/handoff-to-specify.json`.
- A successful worker result must include `must_preserve_evidence` for every packet obligation that affects acceptance, references, forbidden drift, or conflict/reopen conditions.
- If implementation discovers a conflict with an `MP-*` obligation, stop and return a blocked result; do not silently rewrite the product goal, non-goal, selected decision, or reference obligation.
```

- [ ] **Step 3: Update implement shell partial**

In `templates/command-partials/implement/shell.md`, add under Output Contract:

```markdown
- Preserve any `MP-*` obligations carried in task packets, implementation state, or result handoff expectations.
- Worker result handoffs must include must-preserve evidence when packet obligations require it.
```

- [ ] **Step 4: Update template test for implement state**

In `test_implement_execution_state_template_requires_structured_execution_contract_from_tasks`, add:

```python
    assert '"applied_mp_obligations": []' in content
    assert '"open_conflict_count": 0' in content
    assert '"hard_unknown_count": 0' in content
```

- [ ] **Step 5: Run focused implement template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations tests/test_alignment_templates.py::test_structured_json_templates_preserve_fidelity_status_fields tests/test_alignment_templates.py::test_implement_execution_state_template_requires_structured_execution_contract_from_tasks -q
```

Expected: PASS.

- [ ] **Step 6: Commit implement propagation changes**

```powershell
git add templates/commands/implement.md templates/command-partials/implement/shell.md templates/implement-execution-state-template.json tests/test_alignment_templates.py
git commit -m "feat: preserve discussion fidelity during implementation"
```

---

### Task 7: Integration And Documentation Coverage

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`

- [ ] **Step 1: Extend integration contract helpers**

In `tests/integrations/test_integration_base_markdown.py`, add these assertions inside `_assert_discussion_contract(command_content: str)`:

```python
    assert "Must-Preserve Ledger" in command_content
    assert "handoff-to-specify.json" in command_content
    assert "coverage_status" in command_content
    assert "planning_gate_status" in command_content
```

In `tests/integrations/test_integration_base_toml.py`, add the same assertions inside `_assert_discussion_contract(command_content: str)`.

In `tests/integrations/test_integration_base_skills.py`, add these assertions inside `_assert_discussion_contract(skill_content: str)`:

```python
    assert "Must-Preserve Ledger" in skill_content
    assert "handoff-to-specify.json" in skill_content
    assert "coverage_status" in skill_content
    assert "planning_gate_status" in skill_content
```

- [ ] **Step 2: Add specify contract checks for skills integrations**

In `tests/integrations/test_integration_base_skills.py`, add:

```python
    def test_specify_skill_preserves_discussion_fidelity_contract(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        content = (i.skills_dest(tmp_path) / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")
        lowered = content.lower()

        assert "Must-Preserve Ledger" in content
        assert "coverage_status" in content
        assert "planning_gate_status" in content
        assert "blocked_by_handoff_integrity" in content
        assert "entry_source: sp-discussion" in content
        assert "do not silently" in lowered
```

- [ ] **Step 3: Run focused integration tests and confirm failures before docs/template changes are complete**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py::MarkdownIntegrationTests::test_discussion_command_preserves_pre_specification_contract tests/integrations/test_integration_base_toml.py::TomlIntegrationTests::test_discussion_command_preserves_pre_specification_contract tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_discussion_skill_preserves_pre_specification_contract -q
```

If pytest cannot collect abstract mixin tests directly, run the concrete Codex and Gemini integration files:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py -q
```

Expected: FAIL until templates contain the new contract.

- [ ] **Step 4: Update README workflow guidance**

In `README.md`, replace the existing discussion bullet with:

```markdown
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It writes `.specify/discussions/<slug>/` artifacts and creates `handoff-to-specify.md` plus `handoff-to-specify.json` only when the user explicitly requests handoff. The handoff includes a Must-Preserve Ledger so goals, non-goals, decisions, critical references, trade-off rationale, and blocking questions can be carried through `specify`, `plan`, `tasks`, and `implement` without silent drift.
```

- [ ] **Step 5: Update project handbook surfaces**

In `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`, update the pre-spec discussion bullet to include:

```markdown
The handoff uses a Must-Preserve Ledger (`MP-*` items) plus coverage and planning gate status, so downstream workflows must either preserve each protected item or block for a user decision.
```

- [ ] **Step 6: Run integration and docs tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit integration and documentation changes**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md
git commit -m "docs: document discussion fidelity handoff"
```

---

### Task 8: Final Cross-Surface Verification

**Files:**
- No source edits expected unless verification reveals a missed surface.

- [ ] **Step 1: Run the core template and hook tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/hooks/test_artifact_hooks.py -q
```

Expected: PASS.

- [ ] **Step 2: Run execution contract tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: PASS.

- [ ] **Step 3: Run representative integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 4: Run CLI smoke test if prior changes touched registration or packaged templates unexpectedly**

Run:

```powershell
pytest tests/integrations/test_cli.py::test_init_with_codex_skills_generates_expected_files -q
```

Expected: PASS.

- [ ] **Step 5: Inspect the final diff**

Run:

```powershell
git diff --stat HEAD
git diff --check
```

Expected: `git diff --check` prints no whitespace errors. `git diff --stat HEAD` should show only files intentionally modified by this plan.

- [ ] **Step 6: Commit verification fixes if any were needed**

If Step 1-5 required changes:

```powershell
git add <changed-files>
git commit -m "fix: align discussion fidelity surfaces"
```

If no changes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage: This plan covers the ledger schema, handoff JSON, Markdown/JSON integrity, coverage/planning gate split, conflict persistence, downstream plan/task/implement propagation, packet/result evidence, integration tests, and docs.
- Placeholder scan: No task uses TBD/TODO/fill-in placeholders as missing plan content. Bracketed values appear only inside template content that this repository intentionally ships as fillable generated workflow templates.
- Type consistency: `MustPreserveObligation`, `must_preserve_obligations`, and `must_preserve_evidence` are named consistently across schema, compiler, validator, and tests.
- Scope check: The plan stays within generated workflow templates, artifact validation, execution packet contracts, tests, and docs. It does not add a new runtime workflow engine.
