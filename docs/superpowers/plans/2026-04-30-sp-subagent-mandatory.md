# sp-* Subagent Mandatory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every ordinary `sp-*` workflow state that substantive tasks default to and must use subagents.

**Architecture:** Update canonical orchestration vocabulary first, then command templates, passive skills, integration-generated guidance, and docs. Ordinary `sp-*` commands use native subagent task execution and explicit task orchestration. Team-oriented command templates remain separate.

**Tech Stack:** Python 3, pytest, Markdown command templates, Spec Kit Plus integration generators.

---

## File Structure

- Modify: `src/specify_cli/orchestration/models.py`
  - Owns canonical execution model, dispatch shape, and execution surface literals.
- Modify: `src/specify_cli/orchestration/policy.py`
  - Owns `choose_subagent_dispatch()` for ordinary `sp-*` commands.
- Modify: `src/specify_cli/integrations/base.py`
  - Owns shared generated guidance injected into integrations.
- Modify: `src/specify_cli/integrations/codex/__init__.py`
  - Owns Codex-specific `spawn_agent`, `wait_agent`, and `close_agent` wording.
- Modify: `templates/commands/*.md`
  - Owns source text for generated ordinary `sp-*` workflows.
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
  - Owns passive route selection guidance.
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
  - Owns shared subagent execution contract.
- Modify: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
  - Owns multi-lane subagent orchestration guidance.
- Modify docs and project map:
  - `AGENTS.md`
  - `README.md`
  - `PROJECT-HANDBOOK.md`
  - `.specify/project-map/root/ARCHITECTURE.md`
  - `.specify/project-map/root/CONVENTIONS.md`
  - `.specify/project-map/root/WORKFLOWS.md`
  - `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`
  - `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
  - `.specify/project-map/index/status.json`
- Modify and add tests:
  - `tests/orchestration/test_models.py`
  - `tests/orchestration/test_policy.py`
  - `tests/orchestration/test_implement_strategy_routing.py`
  - `tests/test_subagent_mandatory_template_guidance.py`
  - `tests/test_passive_skill_guidance.py`
  - `tests/test_fast_template_guidance.py`
  - `tests/test_quick_template_guidance.py`
  - `tests/test_debug_template_guidance.py`
  - `tests/test_map_scan_build_template_guidance.py`
  - `tests/test_testing_workflow_guidance.py`
  - `tests/test_alignment_templates.py`
  - `tests/integrations/test_integration_base_markdown.py`
  - `tests/integrations/test_integration_base_toml.py`
  - `tests/integrations/test_integration_base_skills.py`
  - `tests/integrations/test_integration_codex.py`
  - `tests/integrations/test_integration_claude.py`
  - `tests/integrations/test_integration_cursor_agent.py`
  - `tests/codex_team/test_codex_guidance_routing.py`

## Shared Target Language

Use this exact sentence in ordinary `sp-*` templates and generated guidance:

```text
All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.
```

Use this orchestration sentence near leader sections:

```text
The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.
```

Use this task-contract sentence wherever commands describe dispatch:

```text
Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.
```

---

### Task 1: Lock Orchestration Vocabulary With Failing Tests

**Files:**
- Modify: `tests/orchestration/test_models.py`
- Modify: `tests/orchestration/test_policy.py`
- Modify: `tests/orchestration/test_implement_strategy_routing.py`

- [ ] **Step 1: Update model literal tests**

In `tests/orchestration/test_models.py`, replace `test_dispatch_shape_and_execution_surface_literals_are_canonical` with:

```python
def test_dispatch_shape_and_execution_surface_literals_are_canonical():
    assert get_args(SubagentExecutionModel) == ("subagent-mandatory",)
    assert get_args(DispatchShape) == (
        "one-subagent",
        "parallel-subagents",
    )
    assert get_args(ExecutionSurface) == (
        "native-subagents",
    )
```

Delete tests that assert ordinary `sp-*` commands can use non-subagent execution surfaces.

Replace `test_one_subagent_attempt_default_is_command_specific` with:

```python
def test_one_subagent_attempt_default_applies_to_ordinary_sp_commands():
    for command_name in (
        "analyze",
        "auto",
        "checklist",
        "clarify",
        "constitution",
        "debug",
        "deep-research",
        "explain",
        "fast",
        "implement",
        "map-build",
        "map-scan",
        "plan",
        "quick",
        "research",
        "specify",
        "tasks",
        "taskstoissues",
        "test",
        "test-build",
        "test-scan",
    ):
        assert should_attempt_one_subagent(command_name) is True
```

- [ ] **Step 2: Update policy tests for mandatory subagent output**

In `tests/orchestration/test_policy.py`, replace old decision expectations with:

```python
def test_choose_subagent_dispatch_routes_one_ready_lane_to_one_native_subagent() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "mandatory-one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"
```

```python
def test_choose_subagent_dispatch_routes_multiple_ready_lanes_to_parallel_native_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "plan"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "mandatory-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"
```

```python
def test_choose_subagent_dispatch_uses_one_subagent_for_ordinary_sp_commands() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    for command_name in (
        "specify",
        "tasks",
        "explain",
        "debug",
        "quick",
        "test-scan",
        "map-build",
    ):
        decision = choose_subagent_dispatch(
            command_name=command_name,
            snapshot=snapshot,
            workload_shape={
                "safe_subagent_lanes": 1,
                "packet_ready": True,
                "overlapping_write_sets": False,
            },
        )

        assert decision.dispatch_shape == "one-subagent"
        assert decision.reason == "mandatory-one-subagent"
        assert decision.execution_surface == "native-subagents"
```

Keep `classify_batch_execution_policy` and `classify_review_gate_policy` tests unless imports need cleanup.

- [ ] **Step 3: Run orchestration tests and verify RED**

Run:

```powershell
pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py -q
```

Expected: FAIL because production orchestration vocabulary has not been updated yet.

- [ ] **Step 4: Commit failing tests**

```powershell
git add tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
git commit -m "test: require mandatory subagent orchestration vocabulary"
```

---

### Task 2: Implement Canonical Orchestration Vocabulary

**Files:**
- Modify: `src/specify_cli/orchestration/models.py`
- Modify: `src/specify_cli/orchestration/policy.py`

- [ ] **Step 1: Update model literals and `ExecutionDecision`**

In `src/specify_cli/orchestration/models.py`, change the top-level literals and canonical set to:

```python
SubagentExecutionModel = Literal["subagent-mandatory"]
DispatchShape = Literal["one-subagent", "parallel-subagents"]
ExecutionSurface = Literal["native-subagents"]
NativeWorkerSurface = Literal["unknown", "none", "native-cli", "spawn_agent"]
DelegationConfidence = Literal["low", "medium", "high"]
_CANONICAL_DISPATCH_SHAPES = frozenset({"one-subagent", "parallel-subagents"})
```

Update `ExecutionDecision`:

```python
@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision selecting the subagent shape for an ordinary sp-* command."""

    command_name: str
    dispatch_shape: DispatchShape
    reason: str
    created_at: str = field(default_factory=utc_now)
    execution_surface: ExecutionSurface | None = None
    execution_model: SubagentExecutionModel = "subagent-mandatory"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dispatch_shape",
            _normalize_dispatch_shape(self.dispatch_shape),
        )
        object.__setattr__(self, "execution_surface", "native-subagents")
```

Replace `_ONE_SUBAGENT_ATTEMPT_COMMANDS` and `should_attempt_one_subagent()` with:

```python
_ORDINARY_SP_COMMANDS = frozenset(
    {
        "analyze",
        "auto",
        "checklist",
        "clarify",
        "constitution",
        "debug",
        "deep-research",
        "explain",
        "fast",
        "implement",
        "map-build",
        "map-scan",
        "plan",
        "quick",
        "research",
        "specify",
        "tasks",
        "taskstoissues",
        "test",
        "test-build",
        "test-scan",
    }
)


def should_attempt_one_subagent(command_name: str) -> bool:
    """Return whether an ordinary sp-* command should dispatch one subagent for one ready lane."""

    return command_name.strip().lower() in _ORDINARY_SP_COMMANDS
```

Update `_derive_execution_surface()`:

```python
def _derive_execution_surface(dispatch_shape: DispatchShape) -> ExecutionSurface:
    _normalize_dispatch_shape(dispatch_shape)
    return "native-subagents"
```

- [ ] **Step 2: Update policy decision logic**

In `src/specify_cli/orchestration/policy.py`, replace `choose_subagent_dispatch()` with:

```python
def choose_subagent_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    """Choose the mandatory subagent dispatch shape for ordinary sp-* commands."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS) or 0
    dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
    reason = "mandatory-parallel-subagents" if safe_lanes > 1 else "mandatory-one-subagent"

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape=dispatch_shape,
        reason=reason,
        execution_surface="native-subagents",
    )
```

Run ruff later in Task 8. Remove unused private constants when linting reports them.

- [ ] **Step 3: Run orchestration tests and verify GREEN**

Run:

```powershell
pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit orchestration implementation**

```powershell
git add src/specify_cli/orchestration/models.py src/specify_cli/orchestration/policy.py tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
git commit -m "feat: make ordinary workflows subagent mandatory"
```

---

### Task 3: Add Template Guidance Tests for All Ordinary Commands

**Files:**
- Create: `tests/test_subagent_mandatory_template_guidance.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_testing_workflow_guidance.py`

- [ ] **Step 1: Create coverage test for ordinary command templates**

Create `tests/test_subagent_mandatory_template_guidance.py`:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORDINARY_COMMANDS = (
    "analyze",
    "auto",
    "checklist",
    "clarify",
    "constitution",
    "debug",
    "deep-research",
    "explain",
    "fast",
    "implement",
    "map-build",
    "map-scan",
    "plan",
    "quick",
    "research",
    "specify",
    "tasks",
    "taskstoissues",
    "test",
    "test-build",
    "test-scan",
)

TEAM_COMMANDS = ("implement-teams", "team")


def _read_command(name: str) -> str:
    return (PROJECT_ROOT / "templates" / "commands" / f"{name}.md").read_text(encoding="utf-8")


def test_all_ordinary_sp_commands_require_subagents_for_substantive_tasks() -> None:
    for command_name in ORDINARY_COMMANDS:
        content = _read_command(command_name).lower()

        assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content, command_name
        assert "the leader orchestrates:" in content, command_name
        assert "before dispatch, every subagent lane needs a task contract" in content, command_name
        assert "structured handoff" in content, command_name


def test_team_commands_keep_team_surface_separate() -> None:
    for command_name in TEAM_COMMANDS:
        content = _read_command(command_name).lower()

        assert "team" in content, command_name
```

- [ ] **Step 2: Update focused template tests**

In the existing focused tests, add these assertions to the main guidance test for each target command:

```python
assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
assert "the leader orchestrates:" in content
assert "before dispatch, every subagent lane needs a task contract" in content
assert "structured handoff" in content
assert "execution_model: subagent-mandatory" in content
assert "dispatch_shape: one-subagent | parallel-subagents" in content
assert "execution_surface: native-subagents" in content
```

Apply this to:

- `tests/test_fast_template_guidance.py`
- `tests/test_quick_template_guidance.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_map_scan_build_template_guidance.py`
- `tests/test_testing_workflow_guidance.py`

- [ ] **Step 3: Update fast template test name**

In `tests/test_fast_template_guidance.py`, rename `test_fast_template_stays_lightweight` to:

```python
def test_fast_template_uses_lightweight_subagent_contract() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "no spec.md" in content or "do not create spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "subagent" in content
    assert "task contract" in content
```

- [ ] **Step 4: Run template tests and verify RED**

Run:

```powershell
pytest tests/test_subagent_mandatory_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_testing_workflow_guidance.py -q
```

Expected: FAIL because templates have not been updated yet.

- [ ] **Step 5: Commit failing template tests**

```powershell
git add tests/test_subagent_mandatory_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_testing_workflow_guidance.py
git commit -m "test: require subagent mandatory command templates"
```

---

### Task 4: Update Ordinary Command Templates

**Files:**
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/auto.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/explain.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/research.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/taskstoissues.md`
- Modify: `templates/commands/test.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/commands/test-scan.md`

- [ ] **Step 1: Add the mandatory section to each ordinary command**

For every ordinary command file listed above, add this section after the template include or after frontmatter if no include exists:

```markdown
## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.
```

- [ ] **Step 2: Update command-local role sections**

For command-local leader or role sections, use this wording:

```markdown
- You are the workflow leader and orchestrator.
- You own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates.
- Subagents own the substantive task lanes assigned through task contracts.
```

- [ ] **Step 3: Update fast command process**

In `templates/commands/fast.md`, replace the execution process with:

```markdown
3. **Dispatch the fast lane**
   - Prepare the smallest task contract for the fast-path lane.
   - Keep the allowed write scope local and explicit.
   - Dispatch one subagent for the lane.
   - Wait for the structured handoff before verification.
```

Keep the existing lightweight scope, no spec, no plan, and no tasks artifact rules.

- [ ] **Step 4: Keep team-oriented command templates separate**

Do not add the ordinary command section to:

```text
templates/commands/implement-teams.md
templates/commands/team.md
```

- [ ] **Step 5: Run template tests and verify GREEN**

Run:

```powershell
pytest tests/test_subagent_mandatory_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_testing_workflow_guidance.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit command templates**

```powershell
git add templates/commands tests/test_subagent_mandatory_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_testing_workflow_guidance.py
git commit -m "feat: require subagents in ordinary command templates"
```

---

### Task 5: Update Passive Skills and Their Tests

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- Modify: `tests/test_passive_skill_guidance.py`

- [ ] **Step 1: Update passive skill tests**

In `tests/test_passive_skill_guidance.py`, add:

```python
def test_workflow_routing_states_subagent_mandatory_rule() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "task contract" in content
    assert "structured handoff" in content
```

Update the subagent-driven test:

```python
def test_subagent_driven_development_requires_mandatory_subagent_contract() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/SKILL.md").lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "native subagents" in content
    assert "validated `workertaskpacket`" in content
    assert "must not dispatch from raw task text" in content
    assert "structured handoff" in content
    assert "spec compliance review" in content
    assert "code quality review" in content
```

Update the parallel dispatch test:

```python
def test_dispatching_parallel_agents_uses_mandatory_native_subagents() -> None:
    content = _read("templates/passive-skills/dispatching-parallel-agents/SKILL.md").lower()

    assert "2+ independent lanes" in content
    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "native subagents" in content
    assert "write-set" in content
    assert "structured handoff" in content
    assert "task contract" in content
```

- [ ] **Step 2: Run passive skill tests and verify RED**

Run:

```powershell
pytest tests/test_passive_skill_guidance.py -q
```

Expected: FAIL because passive skills have not been updated yet.

- [ ] **Step 3: Update workflow routing skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace `## Subagent Routing` with:

```markdown
## Subagent Routing

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

- Dispatch `one-subagent` when one task contract is ready.
- Dispatch `parallel-subagents` when two or more independent task contracts have isolated write sets.
- Keep `sp-*` workflows as the visible daily surface. This passive skill should guide into them, not become a competing workflow.
```

- [ ] **Step 4: Update subagent-driven development skill**

In `templates/passive-skills/subagent-driven-development/SKILL.md`, replace `## Core Rule` and `## Process` with:

```markdown
## Core Rule

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

Route first, orchestrate second, dispatch third.

- Route into the smallest correct `sp-*` workflow before implementation, investigation, planning, analysis, explanation, or artifact work begins.
- Compile and validate a `WorkerTaskPacket` or equivalent task contract before any subagent work begins.
- Dispatch `one-subagent` when one task contract is ready.
- Dispatch `parallel-subagents` when two or more independent task contracts have isolated write sets.
- Do not dispatch from raw task text alone.

## Process

1. **Select the owning workflow**: Use the `sp-*` workflow that owns the state and artifacts.
2. **Build the task contract**: Every lane needs objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.
3. **Dispatch native subagents**: The leader owns packet quality, lane selection, and integration.
4. **Join on evidence**: Wait for every subagent's structured handoff. The handoff must name changed files or read evidence, verification run, failures, open risks, and acceptance status.
5. **Review in order**: Run spec compliance review first. Run code quality review after spec compliance passes. Then run the workflow's required validation commands and update tracker/state artifacts.
```

- [ ] **Step 5: Update parallel dispatch skill**

In `templates/passive-skills/dispatching-parallel-agents/SKILL.md`, update current routing vocabulary to:

```markdown
Current routing vocabulary:

- All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.
- Dispatch `one-subagent` when one task contract is ready.
- Dispatch `parallel-subagents` when two or more independent task contracts have isolated write sets.
- The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.
```

- [ ] **Step 6: Run passive skill tests and verify GREEN**

Run:

```powershell
pytest tests/test_passive_skill_guidance.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit passive skill updates**

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/dispatching-parallel-agents/SKILL.md tests/test_passive_skill_guidance.py
git commit -m "feat: make passive routing subagent mandatory"
```

---

### Task 6: Update Integration Injection Guidance and Tests

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_cursor_agent.py`
- Modify: `tests/codex_team/test_codex_guidance_routing.py`

- [ ] **Step 1: Update integration tests to assert generated mandatory language**

In the integration guidance tests, add assertions against generated ordinary command files:

```python
assert "All substantive tasks in ordinary `sp-*` workflows default to and must use subagents." in content
assert "Before dispatch, every subagent lane needs a task contract" in content
assert "structured handoff" in content
assert "execution_model: subagent-mandatory" in content.lower()
assert "dispatch_shape: one-subagent | parallel-subagents" in content.lower()
assert "execution_surface: native-subagents" in content.lower()
```

In `tests/codex_team/test_codex_guidance_routing.py`, assert:

```python
assert "execution_model: subagent-mandatory" in lower
assert "dispatch_shape: one-subagent | parallel-subagents" in lower
assert "execution_surface: native-subagents" in lower
assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lower
```

- [ ] **Step 2: Run integration guidance tests and verify RED**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_cursor_agent.py tests/codex_team/test_codex_guidance_routing.py -q
```

Expected: FAIL because integration augmentation has not been updated yet.

- [ ] **Step 3: Update shared delegation surface contract injection**

In `src/specify_cli/integrations/base.py`, update `_append_delegation_surface_contract()` addendum to:

```python
        addendum = (
            "\n"
            f"## {agent_name} {heading}\n\n"
            "- All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.\n"
            "- Execution model: `subagent-mandatory`\n"
            "- Dispatch shape: `one-subagent` or `parallel-subagents`\n"
            "- Execution surface: `native-subagents`\n"
            "- The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.\n"
            "- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.\n"
            f"- Native subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Join behavior: {descriptor.native_join_hint}\n"
            f"- Worker result contract: {descriptor.result_contract_hint}\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result handoff path: {descriptor.result_handoff_hint}\n"
        )
```

Update `_augment_implement_skill()`, `_augment_debug_skill()`, and `_augment_quick_skill()` to use the same mandatory language. Keep team-oriented augmentation methods separate.

- [ ] **Step 4: Update Codex-specific skill augmentation**

In `src/specify_cli/integrations/codex/__init__.py`, update ordinary command addendum headings to:

```text
Mandatory Subagent Dispatch
```

Use this content shape for ordinary Codex skills:

```python
(
    "\n"
    f"## {agent_name} Mandatory Subagent Dispatch\n\n"
    f"When running `{command_name}` in {agent_name}, all substantive tasks default to and must use subagents.\n"
    "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
    "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
    "- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.\n"
    f"- Use `wait_agent` only at documented join points.\n"
    f"- Use `close_agent` after integrating finished subagent results.\n"
)
```

Keep `sp-implement-teams` augmentation on its existing team surface.

- [ ] **Step 5: Run integration tests and verify GREEN**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_cursor_agent.py tests/codex_team/test_codex_guidance_routing.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit integration updates**

```powershell
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/codex/__init__.py tests/integrations tests/codex_team/test_codex_guidance_routing.py
git commit -m "feat: inject mandatory subagent guidance"
```

---

### Task 7: Update Documentation and Project Map

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `.specify/project-map/root/ARCHITECTURE.md`
- Modify: `.specify/project-map/root/CONVENTIONS.md`
- Modify: `.specify/project-map/root/WORKFLOWS.md`
- Modify: `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`
- Modify: `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- Modify: `.specify/project-map/index/status.json`

- [ ] **Step 1: Update AGENTS.md rules**

In `AGENTS.md`, update delegated execution defaults with:

```markdown
- All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.
- The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.
- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.
```

Update managed rules to use:

```markdown
- Ordinary `sp-*` execution uses `execution_model: subagent-mandatory`.
- Dispatch shape is `one-subagent` or `parallel-subagents`.
- Execution surface is `native-subagents`.
```

- [ ] **Step 2: Update README workflow guidance**

In `README.md`, update sections that describe `sp-*` execution so ordinary workflow guidance uses:

```markdown
Ordinary `sp-*` workflows use mandatory subagent execution for substantive tasks. The leader orchestrates task contracts, dispatch, structured handoffs, integration, verification, and state updates.
```

- [ ] **Step 3: Update handbook and project-map docs**

In each project-map doc listed for this task, use:

```markdown
Execution-oriented generated workflows teach a mandatory subagent model:

- `execution_model: subagent-mandatory`
- `dispatch_shape: one-subagent | parallel-subagents`
- `execution_surface: native-subagents`

Every substantive ordinary `sp-*` task is packetized before dispatch and returns a structured handoff before the leader integrates results.
```

In `PROJECT-HANDBOOK.md`, update the change-propagation hotspot to:

```markdown
- Mandatory subagent workflow vocabulary propagates into orchestration tests, generated workflow tests, integration tests, README/quickstart guidance, context scripts, and project-map docs.
```

- [ ] **Step 4: Update project-map refresh metadata**

In `.specify/project-map/index/status.json`, preserve existing unrelated fields and update:

```json
{
  "last_refresh_reason": "mandatory-subagent-workflow-refactor",
  "last_refresh_scope": "targeted",
  "last_refresh_basis": "manual-implementation-refresh",
  "dirty": false,
  "dirty_reasons": [],
  "stale_reasons": []
}
```

- [ ] **Step 5: Run documentation-focused tests**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/test_runtime_story_docs.py tests/test_sp_instruction_structure.py tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py -q
```

Expected: PASS after updating expected strings if those tests encode old vocabulary.

- [ ] **Step 6: Commit docs and map updates**

```powershell
git add AGENTS.md README.md PROJECT-HANDBOOK.md .specify/project-map tests/test_agent_context_managed_block.py tests/test_runtime_story_docs.py tests/test_sp_instruction_structure.py tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py
git commit -m "docs: document mandatory subagent workflow model"
```

---

### Task 8: Run Focused Regression and Clean Up Stragglers

**Files:**
- Modify only files surfaced by failing focused tests.

- [ ] **Step 1: Search for old ordinary workflow vocabulary drift**

Run:

```powershell
rg -n "subagents-first|direct execution|inline execution|self execution|execution_model: subagents-first" templates src tests README.md AGENTS.md PROJECT-HANDBOOK.md .specify/project-map
```

Expected: no ordinary workflow matches outside historical planning/spec documents.

- [ ] **Step 2: Run core focused test suite**

Run:

```powershell
pytest tests/orchestration tests/test_subagent_mandatory_template_guidance.py tests/test_passive_skill_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_testing_workflow_guidance.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration focused test suite**

Run:

```powershell
pytest tests/integrations tests/codex_team/test_codex_guidance_routing.py -q
```

Expected: PASS.

- [ ] **Step 4: Run wider regression**

Run:

```powershell
pytest -q
```

Expected: PASS. If runtime is too long, run:

```powershell
pytest tests/orchestration tests/integrations tests/codex_team tests/test_*template_guidance.py tests/test_passive_skill_guidance.py tests/test_runtime_story_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit final fixes**

```powershell
git add templates src tests README.md AGENTS.md PROJECT-HANDBOOK.md .specify/project-map
git commit -m "test: align mandatory subagent workflow regressions"
```

---

### Task 9: Final Review and Handoff

**Files:**
- Read: `git diff --stat HEAD~8..HEAD`
- Read: `git log --oneline -8`

- [ ] **Step 1: Verify ordinary command coverage**

Run:

```powershell
@(
  "analyze","auto","checklist","clarify","constitution","debug","deep-research",
  "explain","fast","implement","map-build","map-scan","plan","quick","research",
  "specify","tasks","taskstoissues","test","test-build","test-scan"
) | ForEach-Object {
  $path = "templates/commands/$_.md"
  if (-not (Select-String -Path $path -SimpleMatch "All substantive tasks in ordinary ``sp-*`` workflows default to and must use subagents")) {
    throw "Missing mandatory subagent rule in $path"
  }
}
```

Expected: no output and exit code 0.

- [ ] **Step 2: Verify team command separation**

Run:

```powershell
Select-String -Path templates\\commands\\implement-teams.md,templates\\commands\\team.md -Pattern "team"
```

Expected: team language remains in team templates.

- [ ] **Step 3: Inspect final git state**

Run:

```powershell
git status --short
git log --oneline -8
```

Expected: clean worktree after the final commit; recent commits correspond to the plan tasks.

- [ ] **Step 4: Final response**

Report:

```text
Implemented mandatory subagent workflow model across orchestration vocabulary, ordinary command templates, passive skills, integration-generated guidance, docs, and project-map docs.
Verification run:
- List every verification command from Task 8 that ran, with PASS/FAIL.
Remaining risk:
- State "None known" when all verification commands passed.
- If a verification command could not run, name the command and the concrete reason.
```
