# Subagents-First Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old execution-strategy vocabulary with a clean subagents-first workflow model across orchestration code, generated `sp-*` surfaces, integrations, docs, tests, and project-map guidance.

**Architecture:** Make the Python orchestration model the source of truth first, then update shared templates and integration addenda to consume the new `execution_model`, `dispatch_shape`, and `execution_surface` contract. Tests should fail on the old vocabulary before implementation, then verify generated artifacts teach leader + subagents without exposing `single-lane`, `native-multi-agent`, or `sidecar-runtime` as active strategy choices.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown/TOML command templates, skills-based integration generators, Bash/PowerShell generated context scripts, Spec Kit project-map docs.

---

## Context

Read before editing:

- `docs/superpowers/specs/2026-04-30-subagents-first-workflow-design.md`
- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/CONVENTIONS.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/TESTING.md`
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/policy.py`
- `src/specify_cli/orchestration/delegation.py`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/codex/__init__.py`
- `src/specify_cli/integrations/claude/__init__.py`
- `src/specify_cli/integrations/cursor_agent/__init__.py`

The working tree may contain user changes. Do not reset or revert unrelated files. If a task touches a dirty file, inspect it first and patch only the relevant lines.

## File Structure

Modify:

- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/policy.py`
- `src/specify_cli/orchestration/delegation.py`
- `src/specify_cli/orchestration/__init__.py`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/codex/__init__.py`
- `src/specify_cli/integrations/claude/__init__.py`
- `src/specify_cli/integrations/cursor_agent/__init__.py`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/quick.md`
- `templates/commands/debug.md`
- `templates/commands/map-scan.md`
- `templates/commands/map-build.md`
- `templates/commands/test.md`
- `templates/commands/test-scan.md`
- `templates/commands/test-build.md`
- `templates/commands/deep-research.md`
- `templates/commands/explain.md`
- `templates/commands/implement-teams.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- `README.md`
- `docs/quickstart.md`
- `AGENTS.md`
- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`
- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/CONVENTIONS.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/TESTING.md`
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`

Update tests:

- `tests/orchestration/test_models.py`
- `tests/orchestration/test_policy.py`
- `tests/orchestration/test_implement_strategy_routing.py`
- `tests/orchestration/test_state_store.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`
- `tests/integrations/test_integration_claude.py`
- `tests/integrations/test_integration_cursor_agent.py`
- `tests/integrations/test_cli.py`
- `tests/codex_team/test_codex_guidance_routing.py`
- `tests/codex_team/test_implement_runtime_routing.py`
- `tests/codex_team/test_release_scope_docs.py`
- `tests/test_alignment_templates.py`
- `tests/test_quick_template_guidance.py`
- `tests/test_quick_skill_mirror.py`
- `tests/test_map_scan_build_template_guidance.py`
- `tests/test_extension_skills.py`
- hook/statusline tests that persist old decision payload fields

## Vocabulary Rules

Use these active terms:

- `subagents-first`
- `one-subagent`
- `parallel-subagents`
- `leader-inline-fallback`
- `native-subagents`
- `managed-team`
- `leader-inline`

Remove these as active generated/workflow terms:

- `single-lane`
- `native-multi-agent`
- `sidecar-runtime`
- `leader-local` as a strategy name

Historical specs and plans may still contain old terms. Active templates, generated files, README/quickstart guidance, project-map docs, and generated context scripts must not advertise them as current strategy vocabulary.

---

### Task 1: Add Failing Core Model Tests

**Files:**
- Modify: `tests/orchestration/test_models.py`
- Modify: `tests/orchestration/test_policy.py`
- Modify: `tests/orchestration/test_implement_strategy_routing.py`
- Modify: `tests/orchestration/test_state_store.py`

- [ ] **Step 1: Update model imports in `tests/orchestration/test_models.py`**

Replace imports of `ExecutionStrategy`, `LaneTopology`, `prefers_single_lane_label`, and `single_worker_delegation_default` with the new names:

```python
from specify_cli.orchestration.models import (
    Batch,
    CapabilitySnapshot,
    DispatchShape,
    ExecutionDecision,
    ExecutionModel,
    ExecutionSurface,
    ReviewGatePolicy,
    Session,
    should_attempt_one_subagent,
    utc_now,
)
```

- [ ] **Step 2: Replace the execution decision model test**

Replace `test_execution_decision_has_canonical_fields_defaults_and_values` with:

```python
def test_execution_decision_has_subagents_first_fields_defaults_and_values():
    decision = ExecutionDecision(
        command_name="implement",
        dispatch_shape="one-subagent",
        execution_surface="native-subagents",
        reason="safe-one-subagent",
    )
    field_names = [item.name for item in fields(ExecutionDecision)]

    assert decision.command_name == "implement"
    assert decision.execution_model == "subagents-first"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.reason == "safe-one-subagent"
    assert decision.fallback_from is None
    assert datetime.fromisoformat(decision.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "command_name",
        "dispatch_shape",
        "execution_surface",
        "reason",
        "fallback_from",
        "created_at",
        "execution_model",
    ]
```

- [ ] **Step 3: Replace literal-value tests**

Replace the old strategy/topology literal tests with:

```python
def test_execution_model_dispatch_shape_and_surface_literals_are_canonical():
    assert get_args(ExecutionModel) == ("subagents-first",)
    assert get_args(DispatchShape) == (
        "one-subagent",
        "parallel-subagents",
        "leader-inline-fallback",
    )
    assert get_args(ExecutionSurface) == (
        "native-subagents",
        "managed-team",
        "leader-inline",
    )
```

- [ ] **Step 4: Replace fallback validation tests**

Add this test:

```python
def test_execution_decision_requires_reason_for_leader_inline_fallback():
    decision = ExecutionDecision(
        command_name="debug",
        dispatch_shape="leader-inline-fallback",
        execution_surface="leader-inline",
        reason="runtime-no-subagents",
    )

    assert decision.execution_model == "subagents-first"
    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.execution_surface == "leader-inline"
    assert decision.reason == "runtime-no-subagents"
```

Also add:

```python
def test_should_attempt_one_subagent_is_command_specific():
    assert should_attempt_one_subagent("implement") is True
    assert should_attempt_one_subagent("quick") is True
    assert should_attempt_one_subagent("test-build") is True
    assert should_attempt_one_subagent("debug") is False
    assert should_attempt_one_subagent("explain") is False
```

- [ ] **Step 5: Update policy test imports**

In `tests/orchestration/test_policy.py` and `tests/orchestration/test_implement_strategy_routing.py`, replace:

```python
from specify_cli.orchestration.policy import choose_execution_strategy
```

with:

```python
from specify_cli.orchestration.policy import choose_subagent_dispatch
```

- [ ] **Step 6: Convert policy assertions to dispatch-shape assertions**

For unsafe but subagent-capable implementation work, assert:

```python
decision = choose_subagent_dispatch(
    command_name="implement",
    snapshot=snapshot,
    workload_shape={
        "safe_subagent_lanes": 1,
        "overlapping_write_sets": False,
        "packet_ready": True,
    },
)

assert decision.dispatch_shape == "one-subagent"
assert decision.execution_surface == "native-subagents"
assert decision.reason == "safe-one-subagent"
```

For independent multi-lane work, assert:

```python
decision = choose_subagent_dispatch(
    command_name="implement",
    snapshot=snapshot,
    workload_shape={
        "safe_subagent_lanes": 2,
        "overlapping_write_sets": False,
        "packet_ready": True,
    },
)

assert decision.dispatch_shape == "parallel-subagents"
assert decision.execution_surface == "native-subagents"
assert decision.reason == "safe-parallel-subagents"
```

For missing native support but supported managed team on non-implement commands, assert:

```python
assert decision.dispatch_shape == "parallel-subagents"
assert decision.execution_surface == "managed-team"
assert decision.reason == "managed-team-supported"
```

For fallback, assert:

```python
assert decision.dispatch_shape == "leader-inline-fallback"
assert decision.execution_surface == "leader-inline"
assert decision.reason in {
    "runtime-no-subagents",
    "low-delegation-confidence",
    "unsafe-write-sets",
    "packet-not-ready",
    "no-safe-delegated-lane",
}
```

- [ ] **Step 7: Update state-store persisted payload test**

In `tests/orchestration/test_state_store.py`, replace payloads like:

```python
payload = {"session_id": "session-2", "strategy": "single-lane"}
```

with:

```python
payload = {
    "session_id": "session-2",
    "execution_model": "subagents-first",
    "dispatch_shape": "one-subagent",
    "execution_surface": "native-subagents",
}
```

- [ ] **Step 8: Run the focused model tests and confirm they fail**

Run:

```powershell
pytest tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/orchestration/test_state_store.py -q
```

Expected: failures showing missing `ExecutionModel`, `DispatchShape`, `choose_subagent_dispatch`, renamed capability fields, and old decision fields.

- [ ] **Step 9: Commit the failing test update**

```powershell
git add tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/orchestration/test_state_store.py
git commit -m "test: define subagents-first orchestration model"
```

---

### Task 2: Replace Core Orchestration Vocabulary

**Files:**
- Modify: `src/specify_cli/orchestration/models.py`
- Modify: `src/specify_cli/orchestration/policy.py`
- Modify: `src/specify_cli/orchestration/delegation.py`
- Modify: `src/specify_cli/orchestration/__init__.py`

- [ ] **Step 1: Replace literal aliases and defaults in `models.py`**

In `src/specify_cli/orchestration/models.py`, replace the old execution literals and canonical sets with:

```python
ExecutionModel = Literal["subagents-first"]
DispatchShape = Literal[
    "one-subagent",
    "parallel-subagents",
    "leader-inline-fallback",
]
ExecutionSurface = Literal["native-subagents", "managed-team", "leader-inline"]
NativeWorkerSurface = Literal["unknown", "none", "native-cli", "spawn_agent"]
DelegationConfidence = Literal["low", "medium", "high"]
_ONE_SUBAGENT_DEFAULT_COMMANDS = frozenset({"implement", "quick", "test-build"})
```

- [ ] **Step 2: Rename capability fields in `CapabilitySnapshot`**

Change the dataclass fields to:

```python
@dataclass(slots=True)
class CapabilitySnapshot:
    """Captured integration/runtime capabilities used for dispatch decisions."""

    integration_key: str
    native_subagents: bool = False
    managed_team_supported: bool = False
    structured_results: bool = False
    durable_coordination: bool = False
    native_worker_surface: NativeWorkerSurface = "unknown"
    delegation_confidence: DelegationConfidence = "low"
    model_family: str | None = None
    runtime_probe_succeeded: bool = False
    notes: list[str] = field(default_factory=list)
```

- [ ] **Step 3: Replace `ExecutionDecision`**

Replace the old `ExecutionDecision` class with:

```python
@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision describing how subagents-first execution should proceed."""

    command_name: str
    dispatch_shape: DispatchShape
    execution_surface: ExecutionSurface
    reason: str
    fallback_from: DispatchShape | None = None
    created_at: str = field(default_factory=utc_now)
    execution_model: ExecutionModel = "subagents-first"

    def __post_init__(self) -> None:
        if self.execution_model != "subagents-first":
            raise ValueError(f"Unsupported execution model: {self.execution_model}")
        if self.dispatch_shape == "leader-inline-fallback" and not self.reason.strip():
            raise ValueError("leader-inline-fallback decisions require a reason")
        if self.execution_surface == "leader-inline" and self.dispatch_shape != "leader-inline-fallback":
            raise ValueError("leader-inline surface must be represented as leader-inline-fallback")
```

- [ ] **Step 4: Replace helper functions**

Delete `_normalize_execution_strategy`, `_derive_lane_topology`, `_derive_execution_surface`, `prefers_single_lane_label`, and `single_worker_delegation_default`.

Add:

```python
def should_attempt_one_subagent(command_name: str) -> bool:
    """Return whether one safe delegated lane should still use a subagent by default."""

    return command_name.strip().lower() in _ONE_SUBAGENT_DEFAULT_COMMANDS
```

- [ ] **Step 5: Replace `choose_execution_strategy` with `choose_subagent_dispatch`**

In `src/specify_cli/orchestration/policy.py`, rename the function and switch the input keys to subagent terms:

```python
_SAFE_SUBAGENT_LANE_COUNT_KEYS = (
    "safe_subagent_lanes",
    "subagent_lane_count",
    "ready_subagent_lanes",
)
_PACKET_READY_KEYS = (
    "packet_ready",
    "packets_ready",
    "has_validated_packet",
    "has_validated_packets",
)
```

Implement the decision order:

```python
def choose_subagent_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    command = command_name.strip().lower()
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS)
    safe_lanes = safe_lanes if safe_lanes is not None else 0
    packet_ready = _get_shape_flag(shape, _PACKET_READY_KEYS, default=False)
    has_overlapping_write_sets = _get_shape_flag(
        shape,
        _OVERLAPPING_WRITE_SET_KEYS,
        default=False,
    )

    if has_overlapping_write_sets:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            execution_surface="leader-inline",
            reason="unsafe-write-sets",
        )

    if safe_lanes <= 0:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            execution_surface="leader-inline",
            reason="no-safe-delegated-lane",
        )

    if not packet_ready and should_attempt_one_subagent(command):
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            execution_surface="leader-inline",
            reason="packet-not-ready",
        )

    low_confidence = (
        snapshot.native_subagents
        and snapshot.runtime_probe_succeeded
        and snapshot.delegation_confidence == "low"
    )
    if low_confidence:
        if command != "implement" and snapshot.managed_team_supported and safe_lanes > 1:
            return ExecutionDecision(
                command_name=command_name,
                dispatch_shape="parallel-subagents",
                execution_surface="managed-team",
                reason="managed-team-supported",
                fallback_from="parallel-subagents",
            )
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            execution_surface="leader-inline",
            reason="low-delegation-confidence",
            fallback_from="parallel-subagents" if safe_lanes > 1 else "one-subagent",
        )

    if snapshot.native_subagents:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="parallel-subagents" if safe_lanes > 1 else "one-subagent",
            execution_surface="native-subagents",
            reason="safe-parallel-subagents" if safe_lanes > 1 else "safe-one-subagent",
        )

    if command != "implement" and snapshot.managed_team_supported and safe_lanes > 1:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="parallel-subagents",
            execution_surface="managed-team",
            reason="managed-team-supported",
        )

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape="leader-inline-fallback",
        execution_surface="leader-inline",
        reason="runtime-no-subagents",
        fallback_from="parallel-subagents" if safe_lanes > 1 else "one-subagent",
    )
```

- [ ] **Step 6: Update `delegation.py` descriptor field names and hints**

In `src/specify_cli/orchestration/delegation.py`, rename:

- `sidecar_surface_hint` to `managed_team_hint`
- `native_surface` text to `native_subagent_surface`
- hints that say "No subagent dispatch path" to "No native subagent dispatch path"
- "leader-local fallback" to "leader-inline fallback"

Make the descriptor consume `snapshot.native_subagents` and `snapshot.managed_team_supported`.

- [ ] **Step 7: Update `orchestration/__init__.py` exports**

Export the new names and remove old ones:

```python
from .models import (
    BatchExecutionPolicy,
    Batch,
    CapabilitySnapshot,
    DispatchShape,
    ExecutionDecision,
    ExecutionModel,
    ExecutionSurface,
    ReviewGatePolicy,
    Session,
    should_attempt_one_subagent,
    utc_now,
    utc_now_iso,
)
from .policy import choose_subagent_dispatch
```

Make sure `__all__` contains `choose_subagent_dispatch`, `DispatchShape`, and `ExecutionModel`, and does not contain `ExecutionStrategy`, `LaneTopology`, `Strategy`, `prefers_single_lane_label`, or `single_worker_delegation_default`.

- [ ] **Step 8: Run orchestration tests**

Run:

```powershell
pytest tests/orchestration -q
```

Expected: orchestration tests pass or expose remaining old import names outside the files already edited.

- [ ] **Step 9: Search for old core API names**

Run:

```powershell
rg -n "ExecutionStrategy|LaneTopology|single_worker_delegation_default|prefers_single_lane_label|choose_execution_strategy|sidecar_runtime_supported|native_multi_agent" src tests
```

Expected: no active references outside historical docs or comments that explicitly describe removed terms. Replace any active references before continuing.

- [ ] **Step 10: Commit the core refactor**

```powershell
git add src/specify_cli/orchestration tests/orchestration
git commit -m "refactor: replace execution strategy with subagent dispatch model"
```

---

### Task 3: Update Shared Command Templates

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/test.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/explain.md`
- Modify: `templates/commands/implement-teams.md`

- [ ] **Step 1: Replace policy helper names in all command templates**

Run:

```powershell
rg -n "choose_execution_strategy|single-lane|native-multi-agent|sidecar-runtime|strategy:" templates\commands templates\command-partials
```

For active command guidance, replace `choose_execution_strategy(...)` with `choose_subagent_dispatch(...)`.

- [ ] **Step 2: Replace generic strategy blocks with this common dispatch block**

For templates that currently list strategy names, use this wording as the base:

```markdown
## Subagents-First Execution Model

- [AGENT] Before broad work begins, assess workload shape and the current runtime capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="<COMMAND>", snapshot, workload_shape)`.
- Use `execution_model: subagents-first`.
- Use `dispatch_shape: one-subagent` when exactly one safe delegated lane is ready.
- Use `dispatch_shape: parallel-subagents` when two or more independent safe lanes can run concurrently.
- Use `dispatch_shape: leader-inline-fallback` only when delegation is unavailable or unsafe, and record the fallback reason before leader-inline work begins.
- Use `execution_surface: native-subagents` for runtime-native subagent APIs.
- Use `execution_surface: managed-team` only when the workflow explicitly supports durable team escalation.
- Use `execution_surface: leader-inline` only with `leader-inline-fallback`.
- Re-check the dispatch shape after every join point.
```

Replace `<COMMAND>` with the exact command stem, such as `implement`, `quick`, `map-scan`, or `test-build`.

- [ ] **Step 3: Update `templates/commands/implement.md` leader role**

Replace the old `single-lane` bullets in `## Leader Role` with:

```markdown
- You are not the default implementer for the current batch. When a safe subagent path is available, dispatch the lane instead of personally executing it.
- Use `subagents-first` for every ready batch that can be delegated safely.
- Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready.
- Dispatch `parallel-subagents` when multiple validated packets have isolated write sets and stable upstream inputs.
- Use `leader-inline-fallback` only after recording why subagent dispatch is unavailable, unsafe, or not yet packetized.
```

In the status template inside `implement.md`, replace any old strategy field with:

```yaml
execution_model: subagents-first
dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback
execution_surface: native-subagents | managed-team | leader-inline
fallback_reason: none
```

- [ ] **Step 4: Update `templates/commands/quick.md` status template**

Replace:

```yaml
strategy: single-lane | native-multi-agent | sidecar-runtime
```

with:

```yaml
execution_model: subagents-first
dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback
execution_surface: native-subagents | managed-team | leader-inline
fallback_reason: none
```

Also replace `execution_fallback:` with:

```yaml
fallback_reason: [none unless dispatch_shape is leader-inline-fallback]
```

- [ ] **Step 5: Update `templates/commands/debug.md` investigation routing**

Replace the old strategy bullets with:

```markdown
- During `investigating`, decide whether the current investigation has safe delegated evidence lanes before running multiple independent evidence-gathering actions sequentially.
- Use `one-subagent` for one ready evidence lane when the runtime has native subagents and the handoff expectations are clear.
- Use `parallel-subagents` for two or more independent read-only evidence lanes.
- Use `leader-inline-fallback` only when the current evidence work is tightly coupled, not safely packetized, or no subagent dispatch path exists.
- Subagents collect facts; the leader owns the hypothesis, debug session file, root-cause decision, fix, verification, and human checkpoint.
```

- [ ] **Step 6: Update map/test workflow templates**

In `map-scan.md`, `map-build.md`, `test-scan.md`, and `test-build.md`:

- Replace "strategy" headings with "dispatch shape" or "subagents-first execution".
- Use `safe_subagent_lanes` in workload-shape examples.
- Keep read-only restrictions for scan subagents.
- Keep packet names: `MapScanPacket`, `MapBuildPacket`, `TestScanPacket`, and `TestBuildPacket`.
- Preserve required join points and structured handoff requirements.

- [ ] **Step 7: Update `templates/commands/test.md` router language**

Ensure `sp-test` says:

```markdown
`sp-test` is a compatibility router. It does not dispatch subagents itself. It routes to `sp-test-scan` for read-only evidence fan-out or `sp-test-build` for execution fan-out, and the routed workflow owns subagent dispatch.
```

- [ ] **Step 8: Update `templates/commands/deep-research.md` and examples**

Replace "single-lane research" in active guidance with:

```text
leader-inline research fallback
```

Use this table value for tracks that cannot dispatch:

```markdown
| TRK-001 | leader-inline research fallback | ... |
```

Do not edit historical example files unless tests assert them as active current guidance.

- [ ] **Step 9: Update `templates/commands/explain.md`**

Replace default strategy wording with:

```markdown
Default to leader explanation for small artifacts. Dispatch a cross-check subagent only when an independent verification lane would materially improve correctness.
```

- [ ] **Step 10: Run active template old-term search**

Run:

```powershell
rg -n "single-lane|native-multi-agent|sidecar-runtime|choose_execution_strategy|strategy:" templates\commands templates\command-partials
```

Expected: no active current guidance. If a test fixture intentionally quotes removed vocabulary as an example of what not to emit, the line must say that explicitly.

- [ ] **Step 11: Commit template changes**

```powershell
git add templates/commands templates/command-partials
git commit -m "docs: teach subagents-first command workflows"
```

---

### Task 4: Update Integration Augmentation And Runtime Guidance

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`

- [ ] **Step 1: Update all `CapabilitySnapshot` construction**

Replace keyword arguments:

```python
native_multi_agent=True
sidecar_runtime_supported=True
```

with:

```python
native_subagents=True
managed_team_supported=True
```

Use `managed_team_supported=False` for integrations without a durable managed-team path.

- [ ] **Step 2: Rewrite `_append_implement_leader_gate` in `base.py`**

Replace old strategy wording with:

```markdown
## <Agent> Leader Gate

When running `sp-implement` in <Agent>, you are the **leader**, not the concrete implementer.

- Use subagents by default when the current batch can be delegated safely.
- Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready.
- Dispatch `parallel-subagents` when multiple validated packets have isolated write sets.
- Use `leader-inline-fallback` only after recording why delegation is unavailable, unsafe, or not packetized.
- The leader keeps tracker state, join-point handling, validation, blocker recovery, and final reporting.
- The leader must not edit implementation files directly while subagent execution is active.
```

Keep existing autonomous blocker recovery and `missed_agent_dispatch` learning guidance, but update it to say `leader-inline-fallback`.

- [ ] **Step 3: Rewrite `_augment_implement_skill`, `_augment_debug_skill`, and `_augment_quick_skill` in `base.py`**

Use section headings:

- `## <Agent> Subagents-First Execution`
- `## <Agent> Subagent Evidence Collection`
- `## <Agent> Quick-Task Subagent Execution`

Use these phrases:

- `dispatch_shape`
- `one-subagent`
- `parallel-subagents`
- `leader-inline-fallback`
- `native-subagents`
- `managed-team`
- `leader-inline`

Do not append old strategy names.

- [ ] **Step 4: Update `_append_delegation_surface_contract` and worker-result addenda**

Ensure the generated contract includes:

```markdown
- Execution model: `subagents-first`
- Dispatch shape: `one-subagent`, `parallel-subagents`, or `leader-inline-fallback`
- Native subagent dispatch: ...
- Managed-team fallback: ...
- Leader-inline fallback: record the reason before local execution
```

Keep result contract wording about `reported_status`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, structured handoff, and idle result rejection.

- [ ] **Step 5: Update Codex native guidance**

In `src/specify_cli/integrations/codex/__init__.py`, replace all addenda that say:

```python
"dispatch subagents whenever the selected strategy is `native-multi-agent`"
```

with wording like:

```python
f"When running `sp-plan` in {agent_name}, use the subagents-first dispatch model.\n"
"- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
"- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
"- Use `wait_agent` only at documented join points.\n"
"- Use `close_agent` after integrating finished subagent results.\n"
"- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
```

For `sp-test`, keep it as a router and say it does not dispatch directly.

- [ ] **Step 6: Update Claude dispatch-first gate**

In `src/specify_cli/integrations/claude/__init__.py`, replace `_append_dispatch_first_gate` content with:

```markdown
## Claude Dispatch-First Gate

- For `sp-implement`, attempt native subagent execution before leader-inline fallback.
- Use Claude's native subagent path for `one-subagent` and `parallel-subagents` dispatch shapes whenever the batch is safe to dispatch.
- Prefer subagent fan-out over local deep-dive execution when ready tasks have isolated write sets and stable upstream inputs.
- Do not begin concrete implementation on the leader path while an untried native subagent path is available for the current batch.
- Only use `leader-inline-fallback` after recording the concrete fallback reason in `FEATURE_DIR/implement-tracker.md`.
```

- [ ] **Step 7: Update Cursor quick augmentation**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, replace Cursor quick text so it says:

```markdown
When running `sp-quick` in Cursor, use subagents-first execution after `STATUS.md` exists.
- Define the smallest safe delegated lane or ready batch.
- Dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis.
- Use Cursor's native subagent path when available.
- Use `leader-inline-fallback` only after native subagents and the managed-team path are unavailable or unsafe, and record the fallback reason in `STATUS.md`.
```

- [ ] **Step 8: Run generated integration tests and confirm failures move forward**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected after this task: failures should be assertion updates, not Python import or setup errors.

- [ ] **Step 9: Commit integration implementation**

```powershell
git add src/specify_cli/integrations src/specify_cli/orchestration/delegation.py
git commit -m "refactor: generate subagents-first integration guidance"
```

---

### Task 5: Update Tests For Generated Guidance

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_cursor_agent.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/codex_team/test_codex_guidance_routing.py`
- Modify: `tests/codex_team/test_implement_runtime_routing.py`
- Modify: `tests/codex_team/test_release_scope_docs.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_quick_skill_mirror.py`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Add a reusable assertion helper for active generated content**

In each large generated-surface test file that repeatedly checked old vocabulary, add a helper like:

```python
def _assert_subagents_first_contract(content: str) -> None:
    lowered = content.lower()
    assert "subagents-first" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "leader-inline-fallback" in lowered
    assert "native-subagents" in lowered or "spawn_agent" in lowered or "native subagent" in lowered
    assert "single-lane" not in lowered
    assert "native-multi-agent" not in lowered
    assert "sidecar-runtime" not in lowered
```

For files that inspect historical docs or negative examples, use a narrower helper name such as `_assert_active_generated_guidance_has_no_old_strategy_terms`.

- [ ] **Step 2: Update base integration tests**

Replace assertions such as:

```python
assert "`single-lane` names the topology for one safe execution lane" in content
assert "native-multi-agent" in debug_content
assert "sidecar-runtime" in quick_content
```

with:

```python
_assert_subagents_first_contract(content)
assert "you are the **leader**, not the concrete implementer" in lowered
assert "dispatch subagents first" in lowered or "use subagents by default" in lowered
assert "record the fallback reason" in lowered
```

- [ ] **Step 3: Update Codex generated-skill tests**

In `tests/integrations/test_integration_codex.py`, replace old expectations in `test_codex_generated_sp_implement_includes_native_spawn_agent_routing` with:

```python
assert "subagents-first" in content.lower()
assert "one-subagent" in content.lower()
assert "parallel-subagents" in content.lower()
assert "leader-inline-fallback" in content.lower()
assert "spawn_agent" in content
assert "wait_agent" in content
assert "close_agent" in content
assert "sp-teams" not in content.lower()
assert "single-lane" not in content.lower()
assert "native-multi-agent" not in content.lower()
assert "sidecar-runtime" not in content.lower()
```

For `sp-implement-teams`, assert `managed-team` and `subagents-first` if the shared contract applies, but keep backend-specific `sp-teams` assertions.

- [ ] **Step 4: Update template tests**

In `tests/test_alignment_templates.py`, `tests/test_quick_template_guidance.py`, and `tests/test_quick_skill_mirror.py`, replace active old vocabulary assertions with:

```python
assert "choose_subagent_dispatch" in content
assert "execution_model: subagents-first" in content
assert "dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback" in content
assert "execution_surface: native-subagents | managed-team | leader-inline" in content
assert "leader-inline-fallback" in lowered
assert "single-lane" not in lowered
assert "native-multi-agent" not in lowered
assert "sidecar-runtime" not in lowered
```

- [ ] **Step 5: Update release-scope docs tests**

In `tests/codex_team/test_release_scope_docs.py`, replace README assertions for old strategy names with:

```python
assert "subagents-first" in readme
assert "one-subagent" in readme
assert "parallel-subagents" in readme
assert "leader-inline-fallback" in readme
assert "single-lane" not in readme
assert "native-multi-agent" not in readme
assert "sidecar-runtime" not in readme
```

- [ ] **Step 6: Run focused generated-surface tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py tests/test_map_scan_build_template_guidance.py -q
pytest tests/integrations -q
pytest tests/codex_team -q
```

Expected: failures should point to remaining template/integration text, not outdated test expectations.

- [ ] **Step 7: Commit test updates**

```powershell
git add tests
git commit -m "test: assert subagents-first generated guidance"
```

---

### Task 6: Update Passive Skills, Docs, Context Scripts, And Project Map

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `AGENTS.md`
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `.specify/project-map/root/ARCHITECTURE.md`
- Modify: `.specify/project-map/root/WORKFLOWS.md`
- Modify: `.specify/project-map/root/CONVENTIONS.md`
- Modify: `.specify/project-map/root/INTEGRATIONS.md`
- Modify: `.specify/project-map/root/TESTING.md`
- Modify: `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- Modify: `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`
- Modify: `.specify/project-map/index/status.json` if recording a completed atlas refresh manually

- [ ] **Step 1: Update passive routing skills**

In `spec-kit-workflow-routing`, `subagent-driven-development`, and `dispatching-parallel-agents`, ensure the current rule is:

```markdown
- Use subagents-first execution for bounded delegated work.
- Dispatch one subagent when one safe lane is ready.
- Dispatch parallel subagents when two or more independent lanes can run concurrently.
- Use leader-inline fallback only after recording why delegation is unavailable or unsafe.
- Do not use old strategy labels as routing choices.
```

- [ ] **Step 2: Update README and quickstart**

Replace old release-scope bullets such as:

```markdown
single-lane, native-multi-agent, sidecar-runtime
```

with:

```markdown
`sp-*` execution-oriented workflows use a leader + subagents model:
`subagents-first` execution, `one-subagent` or `parallel-subagents` dispatch,
and `leader-inline-fallback` only when delegation is unavailable or unsafe.
```

Preserve the mainline wording:

```text
specify -> plan
```

- [ ] **Step 3: Update generated context rules**

In `AGENTS.md`, `scripts/bash/update-agent-context.sh`, and `scripts/powershell/update-agent-context.ps1`, replace old delegated-execution defaults with:

```markdown
- Use subagents-first execution for independent, bounded work when delegation preserves quality.
- Dispatch one subagent for one safe delegated lane; dispatch parallel subagents for independent safe lanes.
- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.
- Wait for each subagent's structured handoff before integrating or marking work complete; idle status is not completion evidence.
- Use leader-inline fallback only after recording why delegation is unavailable, unsafe, or not packetized.
- Use `sp-teams` only when durable team state, explicit join-point tracking, result files, or lifecycle control are needed beyond one in-session subagent burst.
```

- [ ] **Step 4: Update project-map docs**

Edit the affected project-map files so they describe:

- orchestration model: `subagents-first`
- dispatch shape: `one-subagent`, `parallel-subagents`, `leader-inline-fallback`
- execution surface: `native-subagents`, `managed-team`, `leader-inline`
- old strategy vocabulary removed from current conventions
- generated workflows and tests now assert new names

Keep low-confidence and known-unknown sections honest. If a module doc was not deeply revalidated, do not claim exhaustive source tracing.

- [ ] **Step 5: Update handbook**

In `PROJECT-HANDBOOK.md`, update high-value capabilities, risky coordination points, and change-propagation hotspots to mention the new dispatch model and verification tests.

- [ ] **Step 6: Search active docs and generated surfaces for old terms**

Run:

```powershell
rg -n "single-lane|native-multi-agent|sidecar-runtime" README.md docs\quickstart.md AGENTS.md scripts\bash\update-agent-context.sh scripts\powershell\update-agent-context.ps1 PROJECT-HANDBOOK.md .specify\project-map templates\commands templates\passive-skills src\specify_cli\integrations tests
```

Expected: no active current guidance or assertions using old strategy names. Historical plan/spec files under `docs/superpowers/` may still contain old vocabulary and should not be rewritten unless they are active tests.

- [ ] **Step 7: Refresh or record project-map freshness**

If the implementation has fully updated `PROJECT-HANDBOOK.md` and `.specify/project-map/**`, run the local helper:

```powershell
$env:PYTHONPATH='src'
python -m specify_cli project-map complete-refresh --reason subagents-first-workflow-refactor --scope full
```

If the helper CLI signature differs, run:

```powershell
$env:PYTHONPATH='src'
python -m specify_cli project-map --help
```

Then use the matching `complete-refresh` or `record-refresh` command. If a full refresh cannot be completed in this pass, mark dirty instead:

```powershell
$env:PYTHONPATH='src'
python -m specify_cli project-map mark-dirty --reason "subagents-first workflow vocabulary changed; atlas refresh required"
```

- [ ] **Step 8: Commit docs and map updates**

```powershell
git add README.md docs/quickstart.md AGENTS.md scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 PROJECT-HANDBOOK.md .specify/project-map templates/passive-skills
git commit -m "docs: document subagents-first workflow vocabulary"
```

---

### Task 7: Full Verification And Cleanup

**Files:**
- Modify only files needed to fix failures from verification.

- [ ] **Step 1: Run focused orchestration tests**

```powershell
pytest tests/orchestration -q
```

Expected: all orchestration tests pass.

- [ ] **Step 2: Run focused template and integration tests**

```powershell
pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py tests/test_map_scan_build_template_guidance.py -q
pytest tests/integrations -q
pytest tests/codex_team -q
```

Expected: all generated-surface tests pass.

- [ ] **Step 3: Run project-map tests**

```powershell
pytest tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/test_map_scan_build_template_guidance.py -q
```

Expected: project-map contract tests pass and no stale old-vocabulary claims remain in map guidance.

- [ ] **Step 4: Run hook/statusline tests that touch persisted decision fields**

```powershell
pytest tests/hooks tests/execution tests/orchestration -q
```

Expected: persisted state, statusline, and hook tests use `execution_model`, `dispatch_shape`, and `execution_surface`.

- [ ] **Step 5: Run old-term gate for active surfaces**

Run:

```powershell
rg -n "single-lane|native-multi-agent|sidecar-runtime|choose_execution_strategy|ExecutionStrategy|LaneTopology|sidecar_runtime_supported|native_multi_agent" src tests templates README.md docs\quickstart.md AGENTS.md PROJECT-HANDBOOK.md .specify\project-map scripts
```

Expected: no active references. If matches remain, classify each:

- active generated/runtime guidance: replace it
- historical plan/spec fixture: leave only if outside active generated surfaces
- negative test text: keep only when the assertion explicitly verifies absence

- [ ] **Step 6: Run full regression**

```powershell
pytest -q
```

Expected: full suite passes. If runtime is too slow or environmental failures occur, capture exact failing commands and reasons in the final report.

- [ ] **Step 7: Inspect git diff**

```powershell
git diff --stat
git diff --check
git status --short
```

Expected: no whitespace errors; changes are limited to the subagents-first refactor surfaces and committed plan/spec docs.

- [ ] **Step 8: Commit final verification fixes**

If Step 1-7 required fixes after the previous commits:

```powershell
git add <changed-files>
git commit -m "test: complete subagents-first workflow verification"
```

If no fixes were needed, do not create an empty commit.

---

## Completion Standard

The implementation is complete only when:

- `ExecutionStrategy`, `LaneTopology`, `single-lane`, `native-multi-agent`, and `sidecar-runtime` are gone from active generated/runtime surfaces.
- `ExecutionDecision` stores `execution_model`, `dispatch_shape`, and `execution_surface`.
- `choose_subagent_dispatch` is the shared policy helper.
- Generated `sp-*` workflows teach leader + subagents, subagents-first.
- `leader-inline-fallback` is always a recorded exception path with a reason.
- Codex generated skills map native subagents to `spawn_agent`, `wait_agent`, and `close_agent`.
- README, quickstart, context scripts, and project-map docs agree on the new vocabulary.
- Focused tests and full `pytest -q` pass, or any environmental blocker is reported with exact evidence.
