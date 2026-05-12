# sp-implement Wave Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a four-slot `sp-implement` wave budget, tighten `sp-tasks` batch-versus-lane wording, and carry the same parallel-wave discipline into generated native-subagent skills.

**Architecture:** Keep `sp-tasks` as the integration-neutral owner of batch, lane, and join-point structure while moving all runtime wave-budget behavior into `sp-implement` and shared integration augmentation. Lock the change with template and integration regressions so future edits cannot drift back to either whole-batch single-lane delegation or unlimited fan-out.

**Tech Stack:** Python, Markdown workflow templates, integration post-processing, pytest

---

## File Structure

### Planning and template surfaces

- `templates/commands/tasks.md`
  - Shared task-generation guidance. This file should define batch and lane semantics but must not define runtime wave slicing.
- `templates/commands/implement.md`
  - Shared implementation execution contract. This file should define the four-slot wave budget, fixed slot names, and the whole-batch prohibition.

### Integration surface

- `src/specify_cli/integrations/base.py`
  - Shared skill augmentation logic. This file should inject wave-dispatch wording into generated `sp-implement` skills for native-subagent-capable integrations.

### Test surfaces

- `tests/test_alignment_templates.py`
  - Shared template assertions for `tasks` and `implement`.
- `tests/integrations/test_integration_codex.py`
  - Generated Codex skill assertions for `spawn_agent`, `wait_agent`, `close_agent`, wave fan-out, and the whole-batch prohibition.
- `tests/integrations/test_integration_claude.py`
  - Generated Claude skill assertions so the shared integration rule is not Codex-only.

### Reference documents to inspect while implementing

- `docs/superpowers/specs/2026-05-11-sp-implement-wave-budget-design.md`
  - Approved design. Treat this as the source of truth for requirements.
- `docs/superpowers/specs/2026-04-30-subagents-first-workflow-design.md`
  - Existing execution vocabulary contract.
- `docs/superpowers/specs/2026-04-23-multi-agent-task-shaping-design.md`
  - Existing task-shaping and batch/join-point guidance.

---

### Task 1: Lock the new contract with failing tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Add failing shared-template assertions for `sp-tasks`**

```python
def test_tasks_template_wave_budget_contract() -> None:
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "parallel-eligible" in lowered
    assert "batch range labels such as `t012-t021` are summaries, not executable lane identities" in lowered
    assert "lane-level execution unit" in lowered
```

- [ ] **Step 2: Add failing shared-template assertions for `sp-implement`**

```python
def test_implement_template_wave_budget_contract() -> None:
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "max_parallel_subagents = 4" in content
    assert "implement-slot-1" in content
    assert "implement-slot-4" in content
    assert "dispatches every selected lane before waiting" in lowered
    assert "must not own the whole ready parallel batch" in lowered or "whole ready parallel batch" in lowered
```

- [ ] **Step 3: Add failing Codex integration assertions**

```python
def test_codex_generated_sp_implement_includes_wave_budget_contract(tmp_path):
    content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "implement-slot-1" in content
    assert "max_parallel_subagents = 4" in content
    assert "launch all selected lanes in the current `parallel-subagents` wave before waiting" in content
    assert "do not assign the whole ready parallel batch to one implementer subagent" in content
```

- [ ] **Step 4: Add failing Claude integration assertions**

```python
def test_claude_generated_sp_implement_includes_wave_budget_contract(tmp_path):
    content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "parallel-subagents" in content
    assert "launch all selected lanes in the current `parallel-subagents` wave before waiting" in content
    assert "do not assign the whole ready parallel batch to one implementer subagent" in content
```

- [ ] **Step 5: Run the targeted tests and verify they fail**

Run:

```bash
pytest tests/test_alignment_templates.py -q
pytest tests/integrations/test_integration_codex.py -q
pytest tests/integrations/test_integration_claude.py -q
```

Expected:

```text
FAIL ... missing wave-budget contract assertions for tasks/implement templates and generated integration skills
```

- [ ] **Step 6: Commit the RED state test changes**

```bash
git add tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py
git commit -m "test: lock sp-implement wave budget contract"
```

### Task 2: Tighten `sp-tasks` batch-versus-lane wording

**Files:**
- Modify: `templates/commands/tasks.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the failing wording target to the plan checklist**

```text
Goal of this edit:
- `[P]` means lane-level parallel eligibility
- `T012-T021`-style range labels are batch summaries, not executable lane identities
- `sp-tasks` still must not define runtime wave slicing
```

- [ ] **Step 2: Update `tasks.md` with explicit batch-versus-lane guidance**

```markdown
- `[P]` marks a lane-level task as parallel-eligible when dependencies,
  write-set isolation, and validation are satisfied.
- A `parallel batch` is the current ready set of isolated lane-level tasks
  bounded by a join point.
- Batch range labels such as `T012-T021` are summaries for the batch and must
  not be treated as one executable lane identity.
- `sp-tasks` must identify the member lanes of a batch explicitly enough that
  downstream execution does not infer one batch-owner implementer task from the
  range label alone.
- Runtime wave slicing remains the responsibility of `sp-implement`, not
  `sp-tasks`.
```

- [ ] **Step 3: Re-run the focused template test and verify the new tasks assertions pass while implement/integration assertions still fail**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected:

```text
FAIL only on the remaining implement wave-budget assertions
```

- [ ] **Step 4: Commit the `sp-tasks` wording change**

```bash
git add templates/commands/tasks.md tests/test_alignment_templates.py
git commit -m "docs: tighten tasks batch and lane semantics"
```

### Task 3: Add the four-slot wave budget to the shared implement template

**Files:**
- Modify: `templates/commands/implement.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the fixed budget and slot names to the shared contract**

```markdown
- Fixed runtime budget:

  ```text
  max_parallel_subagents = 4
  ```

- Fixed execution slots:
  - `implement-slot-1`
  - `implement-slot-2`
  - `implement-slot-3`
  - `implement-slot-4`
```

- [ ] **Step 2: Add the dispatch-wave execution rule**

```markdown
- When `parallel-subagents` is selected, choose the current wave from the ready
  batch and dispatch at most four validated isolated lanes.
- Dispatch every selected lane in the current wave before waiting.
- Wait only at the current wave join point after the full wave has been
  launched.
```

- [ ] **Step 3: Add the whole-batch prohibition**

```markdown
- A single implementation subagent may own one validated lane packet, but it
  must not own the whole ready parallel batch.
- Do not dispatch a batch-wide objective such as `Implement T012-T021
  migrations` as one implementation lane.
- Do not treat a batch range label as one `WorkerTaskPacket`.
```

- [ ] **Step 4: Add wave-to-wave progression guidance**

```markdown
- If the ready batch contains more than four dispatch-ready lanes, execute
  multiple waves.
- After each wave, consume and validate every structured handoff, update
  execution state, then decide whether the next wave may launch.
- Do not cross the batch join point until all lanes in the ready batch are
  accepted or explicitly blocked/deferred under the workflow contract.
```

- [ ] **Step 5: Run the template test and verify the shared assertions pass**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected:

```text
PASS for tasks/implement template assertions; integration tests may still fail
```

- [ ] **Step 6: Commit the shared implement-template change**

```bash
git add templates/commands/implement.md tests/test_alignment_templates.py
git commit -m "docs: add sp-implement wave budget contract"
```

### Task 4: Carry the same wave rule into shared integration augmentation

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Locate the shared `sp-implement` augmentation block**

Run:

```bash
rg -n "For each ready parallel batch|spawn_agent|wait_agent|whole ready parallel batch" src/specify_cli/integrations/base.py
```

Expected:

```text
Find the `_augment_implement_skill` addendum that currently injects `spawn_agent`, `wait_agent`, and `close_agent` guidance.
```

- [ ] **Step 2: Extend the addendum with the wave-budget rule**

```python
addendum = (
    "\n"
    f"## {agent_name} Subagent Wave Budget\n\n"
    "- Fixed runtime budget: `max_parallel_subagents = 4`.\n"
    "- Use execution slots `implement-slot-1` through `implement-slot-4` for current-wave bookkeeping.\n"
    "- When `parallel-subagents` is selected, launch all selected lanes in the current `parallel-subagents` wave before waiting.\n"
    "- Wait only at the current wave join point after the full wave has been launched.\n"
    "- Do not assign the whole ready parallel batch to one implementer subagent.\n"
)
```

- [ ] **Step 3: Keep the shared wording integration-neutral**

```text
Review checklist:
- mention native-subagent primitives only through existing integration-specific names
- keep `sp-teams` out of ordinary `sp-implement` generated skills
- do not add Codex-only wording into the shared template block
```

- [ ] **Step 4: Run the focused Codex and Claude integration tests**

Run:

```bash
pytest tests/integrations/test_integration_codex.py -q
pytest tests/integrations/test_integration_claude.py -q
```

Expected:

```text
PASS with generated skills now containing the shared wave-budget wording
```

- [ ] **Step 5: Commit the integration augmentation change**

```bash
git add src/specify_cli/integrations/base.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py
git commit -m "feat: add native subagent wave budget guidance"
```

### Task 5: Run end-to-end focused verification and review for leakage

**Files:**
- Modify: `docs/superpowers/plans/2026-05-11-sp-implement-wave-budget-implementation.md`

- [ ] **Step 1: Run the focused verification suite**

Run:

```bash
pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Spot-check the generated skill wording for Codex**

Run:

```bash
pytest tests/integrations/test_integration_codex.py -q
```

Expected:

```text
PASS and generated `.codex/skills/sp-implement/SKILL.md` contains `spawn_agent`, `wait_agent`, the four-slot budget, and the whole-batch prohibition.
```

- [ ] **Step 3: Spot-check the generated skill wording for Claude**

Run:

```bash
pytest tests/integrations/test_integration_claude.py -q
```

Expected:

```text
PASS and generated `.claude/skills/sp-implement/SKILL.md` contains the shared wave contract without Codex-specific leakage.
```

- [ ] **Step 4: Record verification results in this plan**

```markdown
## Verification Notes

- `pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q`
- Confirmed `templates/commands/tasks.md` distinguishes batch summaries from executable lanes.
- Confirmed `templates/commands/implement.md` defines `max_parallel_subagents = 4`, `implement-slot-1..4`, full-wave dispatch before wait, and the whole-batch prohibition.
- Confirmed shared integration augmentation propagates the same wave rule into generated native-subagent-capable skills.
```

- [ ] **Step 5: Commit the verification note update**

```bash
git add docs/superpowers/plans/2026-05-11-sp-implement-wave-budget-implementation.md
git commit -m "docs: record sp-implement wave budget verification"
```

## Self-Review Notes

### Spec coverage

- `sp-tasks` batch-versus-lane clarification: covered by Task 2.
- `sp-implement` four-slot wave budget and slot naming: covered by Task 3.
- Shared integration propagation: covered by Task 4.
- Regression and verification coverage: covered by Tasks 1 and 5.

### Placeholder scan

- No `TODO`, `TBD`, or deferred implementation placeholders are left in the task steps.
- Every code-changing task points to an exact file and includes concrete wording or code snippets.

### Type and naming consistency

- Uses one fixed budget name: `max_parallel_subagents = 4`.
- Uses one fixed slot naming scheme: `implement-slot-1..4`.
- Uses one fixed prohibition phrase: whole ready parallel batch must not be assigned to one implementer subagent.

## Verification Notes

- `pytest tests/test_alignment_templates.py -q`
- `pytest tests/integrations/test_integration_codex.py -q -k "native_spawn_agent_routing or generated_implement_skill_mentions_optimization_scope_and_reopen or generated_specify_skill_mentions_structured_handoff_and_reopen or generated_sp_specify_uses_brainstorming_kernel_wording or generated_shared_workflow_skills_include_native_spawn_agent_guidance"`
- `pytest tests/integrations/test_integration_claude.py -q -k "generated_implement_skill_includes_shared_leader_gate"`
- `pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q -k "wave_budget_contract or native_spawn_agent_routing or generated_implement_skill_includes_shared_leader_gate or generated_shared_workflow_skills_include_native_spawn_agent_guidance"`
- Confirmed `templates/commands/tasks.md` now distinguishes lane-level `[P]` tasks from batch summaries such as `T012-T021`.
- Confirmed `templates/commands/implement.md` now defines `max_parallel_subagents = 4`, `implement-slot-1..4`, full-wave dispatch before wait, and the whole-batch prohibition.
- Confirmed `src/specify_cli/integrations/base.py` now propagates the four-slot wave discipline into generated native-subagent-capable `sp-implement` skills.
- Residual unrelated failures remain in broader integration inventory tests from pre-existing working-tree drift around `.specify/project-cognition/status.json`; those were not introduced by this wave-budget change and were intentionally excluded from focused verification.
