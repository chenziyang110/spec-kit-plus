# SP Plan/Tasks Adaptive Lightweight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-plan` and `sp-tasks` adaptive: leader-inline for low-risk light work, native subagents for standard/heavy work when available, and explicit blocked state for high-risk work that cannot be delegated safely.

**Architecture:** The implementation is command-scoped. Add adaptive execution types and policy behavior for `plan` and `tasks`, introduce a new adaptive command partial used only by those two templates, and leave the existing mandatory subagent partial in place for workflows that remain mandatory.

**Tech Stack:** Python 3.13, dataclasses, pytest, Markdown command templates, repository-local template rendering tests, PowerShell shell commands.

---

## Source Spec

Use the approved design:

`docs/superpowers/specs/2026-05-22-sp-plan-tasks-adaptive-lightweight-design.md`

Implementation must preserve these decisions:

- Scope adaptive behavior to `sp-plan` and `sp-tasks`.
- Keep `sp-prd-scan`, `sp-prd-build`, `sp-map-scan`, `sp-map-build`, `sp-implement`, `sp-debug`, and other mandatory workflows on the existing mandatory subagent contract.
- Persist blocked adaptive dispatch as `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and `blocked_reason`.
- Permit standard-mode leader-inline degradation only when native subagents are unavailable and no high-risk trigger is present.
- Make `workload_shape.lightweight_safe` derived by a helper or schema interpretation, not an ad hoc template boolean.
- Keep light-mode `tasks.md` strong enough for later packet compilation or route back to `sp-tasks`.

## File Structure

Production code:

- `src/specify_cli/orchestration/models.py`
  - Owns canonical literals and `ExecutionDecision`.
  - Add adaptive literals, status fields, blocked reason, and capability degradation.
- `src/specify_cli/orchestration/policy.py`
  - Owns dispatch decisions.
  - Add command-scoped adaptive classification helpers and update `choose_subagent_dispatch()`.

Templates:

- Create `templates/command-partials/common/adaptive-execution.md`
  - New partial for `sp-plan` and `sp-tasks` only.
  - Documents light/standard/heavy modes, native availability rules, blocked state, workload-shape keys, and record fields.
- Modify `templates/commands/plan.md`
  - Include adaptive partial instead of mandatory partial.
  - Make delegated planning artifacts conditional.
  - Replace fixed `subagent-mandatory` decision order with adaptive mode selection.
- Modify `templates/commands/tasks.md`
  - Include adaptive partial instead of mandatory partial.
  - Make enriched task-generation artifacts mode-sensitive.
  - Replace blanket test wording with risk and behavior driven validation.
  - Add minimum light-mode `tasks.md` contract.

Documentation:

- `README.md`
  - Update workflow guidance to describe adaptive `plan`/`tasks`.
- `PROJECT-HANDBOOK.md`
  - Update maintainer guidance for generated workflow behavior and enriched task contract wording.

Tests:

- `tests/orchestration/test_models.py`
  - Lock new canonical literals and `ExecutionDecision` fields.
- `tests/orchestration/test_policy.py`
  - Lock adaptive dispatch behavior for light, standard, heavy, blocked, and existing mandatory commands.
- `tests/orchestration/test_implement_strategy_routing.py`
  - Confirm `implement` remains mandatory subagent behavior.
- `tests/test_subagent_mandatory_template_guidance.py`
  - Split ordinary command expectations so `plan` and `tasks` are adaptive exceptions.
- `tests/test_alignment_templates.py`
  - Add adaptive helper assertion for `plan` and `tasks`.
  - Keep mandatory helper for workflows that remain mandatory.
- `tests/test_tasks_reporting_guidance.py`
  - Update task template/reporting assertions for adaptive mode and light-mode minimum contract.
- `tests/test_extension_skills.py`
  - Update generated skills checks for plan/tasks adaptive language and risk-driven testing.
- `tests/integrations/test_cli.py`
  - Update generated Codex/skills surface assertions that currently require `subagent-mandatory` for `sp-plan` and `sp-tasks`.
- `tests/integrations/test_integration_codex.py`
  - Update generated Codex skill content checks for adaptive plan/tasks.
- `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_toml.py`, `tests/integrations/test_integration_base_skills.py`
  - Update only if rendered output assertions still assume `plan`/`tasks` are mandatory.

## Task 1: Add Adaptive Execution Model Tests

**Files:**
- Modify: `tests/orchestration/test_models.py`
- Modify later: `src/specify_cli/orchestration/models.py`

- [ ] **Step 1: Write failing literal and field tests**

In `tests/orchestration/test_models.py`, update imports to include any new type aliases once they exist:

```python
from specify_cli.orchestration.models import (
    Batch,
    CapabilitySnapshot,
    DispatchShape,
    ExecutionSurface,
    ExecutionDecision,
    ExecutionModel,
    Lane,
    ReviewGatePolicy,
    Session,
    WorkflowStatus,
    should_attempt_one_subagent,
    utc_now,
)
```

Replace `test_execution_decision_has_canonical_fields_defaults_and_values()` with:

```python
def test_execution_decision_has_canonical_fields_defaults_and_values():
    decision = ExecutionDecision(
        command_name="implement",
        dispatch_shape="one-subagent",
        reason="default",
    )
    field_names = [item.name for item in fields(ExecutionDecision)]

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "default"
    assert decision.fallback_from is None
    assert decision.created_at
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"
    assert decision.workflow_status == "ready"
    assert decision.execution_mode is None
    assert decision.capability_degraded is False
    assert decision.blocked_reason is None
    assert datetime.fromisoformat(decision.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "command_name",
        "dispatch_shape",
        "reason",
        "fallback_from",
        "created_at",
        "execution_surface",
        "execution_model",
        "workflow_status",
        "execution_mode",
        "capability_degraded",
        "blocked_reason",
    ]
```

Replace `test_dispatch_shape_and_execution_surface_literals_are_canonical()` with:

```python
def test_dispatch_shape_and_execution_surface_literals_are_canonical():
    assert get_args(ExecutionModel) == ("subagent-mandatory", "adaptive")
    assert get_args(WorkflowStatus) == ("ready", "blocked")
    assert get_args(DispatchShape) == (
        "one-subagent",
        "parallel-subagents",
        "leader-inline",
        "leader-inline-fallback",
        "subagent-blocked",
    )
    assert get_args(ExecutionSurface) == (
        "native-subagents",
        "leader-inline",
        "none",
    )
```

Add:

```python
def test_execution_decision_preserves_blocked_adaptive_state():
    decision = ExecutionDecision(
        command_name="tasks",
        dispatch_shape="subagent-blocked",
        reason="heavy-native-unavailable",
        execution_model="adaptive",
        workflow_status="blocked",
        execution_mode="heavy",
        execution_surface="none",
        blocked_reason="native subagents unavailable for heavy task generation",
    )

    assert decision.execution_model == "adaptive"
    assert decision.workflow_status == "blocked"
    assert decision.execution_mode == "heavy"
    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.blocked_reason == "native subagents unavailable for heavy task generation"
```

- [ ] **Step 2: Run model tests and confirm failure**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py
```

Expected: fails because `ExecutionModel`, `WorkflowStatus`, new dispatch/surface literals, and new `ExecutionDecision` fields do not exist yet.

- [ ] **Step 3: Implement the model fields**

In `src/specify_cli/orchestration/models.py`, replace:

```python
SubagentExecutionModel = Literal["subagent-mandatory"]
DispatchShape = Literal["one-subagent", "parallel-subagents", "leader-inline-fallback"]
ExecutionSurface = Literal["native-subagents"]
```

with:

```python
ExecutionModel = Literal["subagent-mandatory", "adaptive"]
SubagentExecutionModel = ExecutionModel
WorkflowStatus = Literal["ready", "blocked"]
ExecutionMode = Literal["light", "standard", "heavy"]
DispatchShape = Literal[
    "one-subagent",
    "parallel-subagents",
    "leader-inline",
    "leader-inline-fallback",
    "subagent-blocked",
]
ExecutionSurface = Literal["native-subagents", "leader-inline", "none"]
```

Update `_CANONICAL_DISPATCH_SHAPES` to include:

```python
_CANONICAL_DISPATCH_SHAPES = frozenset(
    {
        "one-subagent",
        "parallel-subagents",
        "leader-inline",
        "leader-inline-fallback",
        "subagent-blocked",
    }
)
```

Update the `ExecutionDecision` dataclass to:

```python
@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision selecting a workflow dispatch shape."""

    command_name: str
    dispatch_shape: DispatchShape
    reason: str
    fallback_from: DispatchShape | None = None
    created_at: str = field(default_factory=utc_now)
    execution_surface: ExecutionSurface | None = None
    execution_model: ExecutionModel = "subagent-mandatory"
    workflow_status: WorkflowStatus = "ready"
    execution_mode: ExecutionMode | None = None
    capability_degraded: bool = False
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dispatch_shape",
            _normalize_dispatch_shape(self.dispatch_shape),
        )
        if self.fallback_from is not None:
            object.__setattr__(self, "fallback_from", _normalize_dispatch_shape(self.fallback_from))
        if self.execution_surface is None:
            object.__setattr__(self, "execution_surface", _derive_execution_surface(self.dispatch_shape))
        if self.workflow_status == "blocked" and not self.blocked_reason:
            raise ValueError("blocked ExecutionDecision requires blocked_reason")
```

Update `_derive_execution_surface()` to:

```python
def _derive_execution_surface(dispatch_shape: DispatchShape) -> ExecutionSurface:
    normalized = _normalize_dispatch_shape(dispatch_shape)
    if normalized in {"one-subagent", "parallel-subagents"}:
        return "native-subagents"
    if normalized in {"leader-inline", "leader-inline-fallback"}:
        return "leader-inline"
    return "none"
```

- [ ] **Step 4: Run model tests and confirm pass**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit model change**

Run:

```powershell
git add src/specify_cli/orchestration/models.py tests/orchestration/test_models.py
git commit -m "feat: model adaptive execution decisions"
```

Expected: one commit with model and model tests.

## Task 2: Add Adaptive Dispatch Policy Tests and Implementation

**Files:**
- Modify: `tests/orchestration/test_policy.py`
- Modify: `tests/orchestration/test_implement_strategy_routing.py`
- Modify: `src/specify_cli/orchestration/policy.py`

- [ ] **Step 1: Replace policy tests with adaptive cases**

In `tests/orchestration/test_policy.py`, keep the batch/review gate tests. Replace the three `choose_subagent_dispatch` tests with:

```python
def test_plan_lightweight_safe_routes_to_leader_inline() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "lightweight_safe": True,
        },
    )

    assert decision.command_name == "plan"
    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-light-leader-inline"
    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "light"
    assert decision.workflow_status == "ready"
    assert decision.capability_degraded is False


def test_tasks_standard_native_available_routes_to_parallel_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "lightweight_safe": False,
        },
    )

    assert decision.command_name == "tasks"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "adaptive-standard-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.workflow_status == "ready"


def test_tasks_standard_without_native_subagents_degrades_to_leader_inline() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "lightweight_safe": False,
            "high_risk": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-standard-native-unavailable-leader-inline"
    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.capability_degraded is True


def test_plan_heavy_without_native_subagents_blocks() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "touches_schema_or_migration": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "adaptive-heavy-subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "heavy"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "heavy or safety-critical plan work requires native subagents"


def test_plan_unpacketized_heavy_native_subagents_blocks() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "packet_ready": False,
            "touches_security_sensitive_surface": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "heavy or safety-critical plan work cannot be packetized safely"


def test_non_adaptive_ordinary_commands_remain_mandatory_subagent() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    for command_name in ("specify", "implement", "debug", "quick", "map-build"):
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
        assert decision.execution_model == "subagent-mandatory"
```

Add a classifier-specific test:

```python
def test_lightweight_safe_is_derived_from_risk_keys_when_omitted() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "touches_shared_registration_surface": False,
            "cross_project_target": False,
            "reference_fidelity_required": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-light-leader-inline"
```

- [ ] **Step 2: Update implement routing tests to prove mandatory behavior remains**

In `tests/orchestration/test_implement_strategy_routing.py`, no semantic rewrite is required. Add one test at the end:

```python
def test_implement_ignores_lightweight_safe_and_remains_mandatory() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "lightweight_safe": True,
        },
    )

    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "mandatory-one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"
```

- [ ] **Step 3: Run policy tests and confirm failure**

Run:

```powershell
uv run pytest -q tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
```

Expected: policy tests fail because adaptive behavior is not implemented.

- [ ] **Step 4: Implement adaptive policy helpers**

In `src/specify_cli/orchestration/policy.py`, add constants near the key groups:

```python
_ADAPTIVE_COMMANDS = {"plan", "tasks"}
_HIGH_RISK_KEYS = (
    "high_risk",
    "touches_schema_or_migration",
    "touches_schema",
    "touches_migration",
    "touches_security_sensitive_surface",
    "touches_protocol_or_generated_api",
    "touches_protocol_boundary",
    "touches_generated_api",
    "touches_native_or_plugin_bridge",
    "touches_native_bridge",
    "touches_plugin_bridge",
    "touches_shared_registration_surface",
    "touches_shared_surface",
    "touches_shared_registration",
    "cross_project_target",
    "reference_fidelity_required",
    "deep_research_handoff_required",
    "consequence_obligations_require_independent_synthesis",
)
```

Add helpers above `choose_subagent_dispatch()`:

```python
def _command_is_adaptive(command_name: str) -> bool:
    return command_name.strip().lower() in _ADAPTIVE_COMMANDS


def _has_high_risk_trigger(shape: Mapping[str, object]) -> bool:
    return _get_shape_flag(shape, _HIGH_RISK_KEYS, default=False)


def _packet_ready(shape: Mapping[str, object]) -> bool:
    return _get_shape_flag(shape, ("packet_ready", "delegation_packet_ready"), default=False)


def _native_subagents_available(snapshot: CapabilitySnapshot, shape: Mapping[str, object]) -> bool:
    if "native_subagents_available" in shape:
        return _to_bool(shape["native_subagents_available"], default=snapshot.native_subagents)
    return snapshot.native_subagents


def _is_lightweight_safe(shape: Mapping[str, object], safe_lanes: int) -> bool:
    if "lightweight_safe" in shape:
        return _to_bool(shape["lightweight_safe"], default=False)
    return safe_lanes <= 1 and not _has_high_risk_trigger(shape)
```

Replace `choose_subagent_dispatch()` with:

```python
def choose_subagent_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    """Choose dispatch shape for orchestration-aware commands."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    command = command_name.strip().lower()
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS) or 0

    if not _command_is_adaptive(command):
        dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
        reason = "mandatory-parallel-subagents" if safe_lanes > 1 else "mandatory-one-subagent"
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape=dispatch_shape,
            reason=reason,
            execution_surface="native-subagents",
        )

    high_risk = _has_high_risk_trigger(shape)
    native_available = _native_subagents_available(snapshot, shape)
    packet_ready = _packet_ready(shape)
    lightweight_safe = _is_lightweight_safe(shape, safe_lanes)

    if lightweight_safe and not high_risk:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline",
            reason="adaptive-light-leader-inline",
            execution_surface="leader-inline",
            execution_model="adaptive",
            execution_mode="light",
        )

    execution_mode = "heavy" if high_risk else "standard"

    if native_available and packet_ready and safe_lanes > 0:
        dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
        reason = (
            f"adaptive-{execution_mode}-parallel-subagents"
            if safe_lanes > 1
            else f"adaptive-{execution_mode}-one-subagent"
        )
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape=dispatch_shape,
            reason=reason,
            execution_surface="native-subagents",
            execution_model="adaptive",
            execution_mode=execution_mode,
        )

    if high_risk:
        blocked_reason = (
            f"heavy or safety-critical {command} work cannot be packetized safely"
            if native_available
            else f"heavy or safety-critical {command} work requires native subagents"
        )
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="subagent-blocked",
            reason="adaptive-heavy-subagent-blocked",
            execution_surface="none",
            execution_model="adaptive",
            execution_mode="heavy",
            workflow_status="blocked",
            blocked_reason=blocked_reason,
        )

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape="leader-inline",
        reason="adaptive-standard-native-unavailable-leader-inline",
        execution_surface="leader-inline",
        execution_model="adaptive",
        execution_mode="standard",
        capability_degraded=not native_available,
    )
```

- [ ] **Step 5: Run orchestration tests**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit policy change**

Run:

```powershell
git add src/specify_cli/orchestration/policy.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
git commit -m "feat: route plan tasks with adaptive dispatch"
```

Expected: one commit with policy and policy tests.

## Task 3: Add Adaptive Partial and Switch Plan/Tasks Templates

**Files:**
- Create: `templates/command-partials/common/adaptive-execution.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify later: related template tests

- [ ] **Step 1: Create the adaptive execution partial**

Create `templates/command-partials/common/adaptive-execution.md` with:

```markdown
## Adaptive Plan/Tasks Execution

`sp-plan` and `sp-tasks` use adaptive execution. Classify the workload before dispatch, synthesis, or task generation:

- `light`: one bounded lane, low-risk write surface, no cross-project target ambiguity, no schema/migration/security/protocol/generated API/native bridge/shared registration trigger, no reference-fidelity checkpoint, no deep-research handoff requiring independent synthesis, and no `CA-*` or `MP-*` obligation that requires delegated synthesis.
- `standard`: multiple safe lanes, useful parallel evidence collection, cross-module impact, or enough constraints that structured handoffs reduce drift, without a high-risk trigger.
- `heavy`: schema or migration work, security-sensitive surfaces, protocol seams, generated API surfaces, native/plugin bridges, cross-project targets, reference-fidelity work, deep-research planning handoffs, shared registration surfaces, or consequence obligations that require independent operational design.

Persist the decision in `workflow-state.md` and the generated report:

```text
execution_model: adaptive
execution_mode: light | standard | heavy
workflow_status: ready | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
capability_degraded: false | true
mode_reason: evidence-backed reason such as `single low-risk planning lane`
blocked_reason: required when workflow_status is blocked, such as `heavy plan work requires native subagents`
```

Use this `workload_shape` schema when calling `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)` or `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)`:

```text
lightweight_safe: bool derived from risk keys plus single-lane scope
safe_subagent_lanes: int
packet_ready: bool
native_subagents_available: bool
high_risk: bool
touches_schema_or_migration: bool
touches_security_sensitive_surface: bool
touches_protocol_or_generated_api: bool
touches_native_or_plugin_bridge: bool
touches_shared_registration_surface: bool
cross_project_target: bool
reference_fidelity_required: bool
deep_research_handoff_required: bool
consequence_obligations_require_independent_synthesis: bool
```

Native availability rules:

- `light` does not require native subagents and may run leader-inline.
- `standard` uses native subagents when available. If native subagents are unavailable, it may continue leader-inline only when no high-risk trigger is present and the workflow records `capability_degraded: true`.
- `heavy` requires native subagents or an explicitly selected durable team workflow outside this command. If neither is available, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and `blocked_reason`, then stop before synthesis.

Delegation artifacts are required only when delegated lanes are used. Do not create evidence indexes, checkpoints, or structured handoff requirements for a light leader-inline pass unless another explicit integration contract requires them.
```
```

If the nested Markdown fence is awkward in the actual file, use four backticks around the outer code sample. Keep the visible text exactly as above.

- [ ] **Step 2: Switch `plan.md` to adaptive partial**

In `templates/commands/plan.md`, replace:

```markdown
{{spec-kit-include: ../command-partials/common/subagent-execution.md}}
```

with:

```markdown
{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}
```

- [ ] **Step 3: Switch `tasks.md` to adaptive partial**

In `templates/commands/tasks.md`, replace:

```markdown
{{spec-kit-include: ../command-partials/common/subagent-execution.md}}
```

with:

```markdown
{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}
```

- [ ] **Step 4: Run a focused render/read smoke**

Run:

```powershell
uv run pytest -q tests/test_sp_instruction_structure.py
```

Expected: pass. If it fails because new partials are not packaged or parsed, fix the include path or packaging metadata before continuing.

Do not commit yet; template semantics are not updated enough for broader tests.

## Task 4: Update Plan Template Semantics

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing adaptive plan assertions**

In `tests/test_alignment_templates.py`, add a helper near `_assert_subagent_dispatch_contract()`:

```python
def _assert_adaptive_plan_tasks_contract(text: str, command_name: str) -> None:
    assert f'choose_subagent_dispatch(command_name="{command_name}"' in text
    lowered = text.lower()
    assert "execution_model: adaptive" in lowered
    assert "execution_mode: light | standard | heavy" in lowered
    assert "workflow_status: ready | blocked" in lowered
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in lowered
    assert "execution_surface: leader-inline | native-subagents | none" in lowered
    assert "capability_degraded: false | true" in lowered
    assert "blocked_reason" in lowered
    assert "lightweight_safe" in lowered
    assert "touches_schema_or_migration" in lowered
    assert "touches_security_sensitive_surface" in lowered
    assert "cross_project_target" in lowered
```

Update `test_plan_template_documents_subagent_planning_lanes()` or the nearby plan dispatch test so it asserts:

```python
def test_plan_template_uses_adaptive_execution_modes() -> None:
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    _assert_adaptive_plan_tasks_contract(content, "plan")
    assert "light leader-inline planning pass" in lowered
    assert "delegated planning lanes" in lowered
    assert "planning/handoffs/<lane-id>.json" in content
    assert "required only when delegated planning lanes are used" in lowered
    assert "stop before planning synthesis" in lowered
```

Remove or update assertions that require these exact old lines for `plan`:

```python
assert "If exactly one validated isolated plan lane exists, dispatch `one-subagent`." in content
assert "If two or more validated isolated plan lanes exist, dispatch `parallel-subagents`." in content
assert "If no validated isolated plan lane can be packetized, mark `subagent-blocked` and stop." in content
assert "leader-inline execution of substantive lane work is forbidden" in lowered
_assert_subagent_dispatch_contract(content, "plan")
```

- [ ] **Step 2: Run plan template tests and confirm failure**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py -k "plan_template_documents_subagent_planning_lanes or plan_template_uses_adaptive_execution_modes"
```

Expected: fails because `plan.md` still has mandatory wording.

- [ ] **Step 3: Update `plan.md` frontmatter primary outputs**

Change `workflow_contract.primary_outputs` from:

```yaml
primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, `plan-contract.json`, `workflow-state.md`, `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson` under the active `FEATURE_DIR`, plus `data-model.md` and `contracts/` when the feature scope demands them.'
```

to:

```yaml
primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, `plan-contract.json`, and `workflow-state.md` under the active `FEATURE_DIR`; `data-model.md` and `contracts/` when the feature scope demands them; `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson` only when delegated planning lanes are used.'
```

- [ ] **Step 4: Update allowed writes and authoritative files in `plan.md`**

In both places that set `allowed_artifact_writes`, change the line to include conditional language:

```text
allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, workflow-state.md; planning/handoffs/*.json, planning/evidence-index.json, planning/checkpoints.ndjson only when delegated planning lanes are used
```

Change `authoritative_files` to:

```text
authoritative_files: spec.md, alignment.md, context.md, plan.md, research.md, plan-contract.json; planning/handoffs/*.json and planning/evidence-index.json when delegated planning lanes are used
```

- [ ] **Step 5: Replace fixed plan dispatch block**

In `templates/commands/plan.md`, replace the block from:

```markdown
   - [AGENT] Before plan synthesis begins, split the work only into the supported plan lanes: `research`, `data model`, `contracts`, and `quickstart and validation scenarios`.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
```

through:

```markdown
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.
```

with:

```markdown
   - [AGENT] Before plan synthesis begins, classify the workload as `light`, `standard`, or `heavy` using the adaptive execution partial.
   - Build `workload_shape` from explicit risk keys rather than a hand-authored `lightweight_safe` shortcut.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
   - Light leader-inline planning pass:
     - Allowed only when the adaptive decision records `execution_mode: light`, `workflow_status: ready`, and `dispatch_shape: leader-inline`.
     - Do not create `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, or `planning/checkpoints.ndjson` unless another explicit integration contract requires them.
     - Record in `plan.md`, `plan-contract.json`, and `workflow-state.md` that no delegated planning lanes were used and include the evidence-backed mode reason.
   - Standard or heavy delegated planning pass:
     - Before dispatching any planning lane, persist a `planning_checkpoint` record to `planning/checkpoints.ndjson` with the lane id, dispatch shape, authoritative inputs, expected handoff path, and current workflow-state summary.
     - Each delegated planning lane must persist the lane's structured handoff to `planning/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or synthesizes `plan.md`, `research.md`, or `plan-contract.json`.
     - Update `planning/evidence-index.json` after each accepted lane handoff with lane id, handoff path, source artifacts inspected, decisions or constraints contributed, affected plan sections or generated artifacts, blocker status, and integration status.
     - Consume `planning/evidence-index.json` before final synthesis: for every accepted handoff, mark the handoff as `integrated`, `deferred`, or `blocked`, and name the target `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, or `plan-contract.json` section that consumed it.
     - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only lane results. If a lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a valid handoff path.
   - Blocked heavy planning pass:
     - If the adaptive decision records `workflow_status: blocked` or `dispatch_shape: subagent-blocked`, record `blocked_reason` in `workflow-state.md` and stop before planning synthesis.
     - Do not downgrade heavy or safety-critical planning work to leader-inline.
   - When resuming after compaction, re-read `workflow-state.md`; also re-read `planning/checkpoints.ndjson`, `planning/evidence-index.json`, and accepted `planning/handoffs/<lane-id>.json` when delegated planning lanes were used.
   - Persist the decision fields exactly: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `workflow_status: ready | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `capability_degraded: false | true`, `blocked_reason`.
   - Required join points for delegated standard/heavy planning:
     - before final constitution and risk re-check
     - before writing the consolidated implementation plan
   - Record the chosen execution mode, dispatch shape, capability degradation, blocked reason if any, selected lanes, and join points in the planning artifacts you generate.
   - In `plan-contract.json`, include references to accepted `planning/handoffs/<lane-id>.json` files that shaped each major plan decision, research conclusion, generated artifact, risk, guardrail, or escalation when delegated planning lanes were used.
   - Do not mark delegated planning complete while `planning/evidence-index.json` contains an accepted handoff without an explicit consuming artifact section, deferral, or blocker reason.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.
```

- [ ] **Step 6: Update plan reporting evidence paths**

In Step 7 reporting, replace:

```text
planning evidence paths: `planning/evidence-index.json`, `planning/checkpoints.ndjson`, and accepted `planning/handoffs/<lane-id>.json` files
```

with:

```text
planning evidence paths when delegated lanes were used: `planning/evidence-index.json`, `planning/checkpoints.ndjson`, and accepted `planning/handoffs/<lane-id>.json` files; otherwise report `delegated_planning_lanes: none`
```

Add state fields to the final `workflow-state.md` update list:

```text
execution_model: adaptive
execution_mode: light | standard | heavy
workflow_status: ready | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
capability_degraded: false | true
blocked_reason: required when blocked
```

- [ ] **Step 7: Run focused plan tests**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py -k "plan_template_uses_adaptive_execution_modes or plan_template_rejects_cross_project_handoff_without_target_context or plan_tasks_and_implement_templates_consume_structured_handoff_contracts"
```

Expected: selected tests pass.

Do not commit yet; `tasks.md` and shared tests still need updates.

## Task 5: Update Tasks Template Semantics

**Files:**
- Modify: `templates/commands/tasks.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_tasks_reporting_guidance.py`

- [ ] **Step 1: Add failing adaptive task assertions**

In `tests/test_alignment_templates.py`, update the tasks dispatch test near `test_tasks_template_documents_shared_routing_before_decomposition()` so it asserts:

```python
def test_tasks_template_uses_adaptive_execution_modes() -> None:
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    _assert_adaptive_plan_tasks_contract(content, "tasks")
    assert "light leader-inline task-generation pass" in lowered
    assert "minimum light-mode `tasks.md` contract" in lowered
    assert "risk and behavior driven validation" in lowered
    assert "task-generation/handoffs/<lane-id>.json" in content
    assert "only when delegated task-generation lanes are used" in lowered
    assert "stop before task synthesis" in lowered
```

Remove or update assertions that require old fixed task dispatch lines:

```python
_assert_subagent_dispatch_contract(content, "tasks")
assert "Leader-only decomposition is forbidden once a validated lane exists." in content
assert "Persist the decision fields exactly: `execution_model: subagent-mandatory`" in content
```

In `tests/test_tasks_reporting_guidance.py`, update `test_tasks_template_distinguishes_feature_shape_from_batch_strategy()` to assert:

```python
assert "`execution_model: adaptive`" in content
assert "`execution_mode: light | standard | heavy`" in content
assert "`workflow_status: ready | blocked`" in content
assert "`dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`" in content
assert "`execution_surface: leader-inline | native-subagents | none`" in content
assert "`capability_degraded: false | true`" in content
```

Remove old assertions for:

```python
assert "`execution_model: subagent-mandatory`" in content
assert "`execution_surface: native-subagents`" in content
assert "`safe-one-subagent`" in content
assert "`safe-parallel-subagents`" in content
assert "`no-safe-delegated-lane`" in content
assert "`runtime-no-subagents`" in content
```

Add a new test:

```python
def test_tasks_command_documents_risk_driven_validation_and_light_contract():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "risk and behavior driven validation" in lowered
    assert "minimum light-mode `tasks.md` contract" in lowered
    assert "no-new-test rationale" in lowered
    assert "replacement validation" in lowered
    assert "residual risk" in lowered
    assert "route back to `sp-tasks` for packet enrichment" in lowered
```

- [ ] **Step 2: Run focused task tests and confirm failure**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py -k "tasks_template_uses_adaptive_execution_modes" tests/test_tasks_reporting_guidance.py
```

Expected: fails because `tasks.md` still uses mandatory wording and blanket test wording.

- [ ] **Step 3: Update `tasks.md` frontmatter primary outputs**

Change `workflow_contract.primary_outputs` from:

```yaml
primary_outputs: '`FEATURE_DIR/tasks.md`, `FEATURE_DIR/handoff-to-tasks.json`, `FEATURE_DIR/task-index.json`, `FEATURE_DIR/task-packets/*.json`, `FEATURE_DIR/task-generation/handoffs/<lane-id>.json`, `FEATURE_DIR/task-generation/evidence-index.json`, `FEATURE_DIR/task-generation/checkpoints.ndjson`, and `workflow-state.md`.'
```

to:

```yaml
primary_outputs: '`FEATURE_DIR/tasks.md` and `workflow-state.md`; `task-index.json` when useful for light mode; `handoff-to-tasks.json`, `task-packets/*.json`, `task-generation/handoffs/<lane-id>.json`, `task-generation/evidence-index.json`, and `task-generation/checkpoints.ndjson` when standard/heavy mode uses delegated task-generation lanes or downstream delegated implementation needs packets.'
```

- [ ] **Step 4: Update allowed writes and authoritative files in `tasks.md`**

Change the active pass state fields to:

```text
allowed_artifact_writes: tasks.md, workflow-state.md; task-index.json when useful for light mode; handoff-to-tasks.json, task-packets/*.json, task-generation/handoffs/*.json, task-generation/evidence-index.json, task-generation/checkpoints.ndjson when delegated task-generation lanes or downstream delegated implementation need packets
authoritative_files: spec.md, alignment.md, context.md, plan.md, tasks.md; handoff-to-tasks.json, task-index.json, task-packets/*.json, task-generation/handoffs/*.json, task-generation/evidence-index.json when generated
```

- [ ] **Step 5: Replace fixed tasks dispatch block**

In `templates/commands/tasks.md`, replace the block from:

```markdown
    - [AGENT] Before task decomposition begins, split work only into the supported task-generation lanes: `story and phase decomposition`, `dependency graph analysis`, and `write-set and parallel-safety analysis`.
    - [AGENT] Before dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)`
```

through the line:

```markdown
    - Record the chosen dispatch shape, blocked reason if any, selected lanes, and join points in the generated report and implementation strategy section.
```

with:

```markdown
    - [AGENT] Before task decomposition begins, classify the workload as `light`, `standard`, or `heavy` using the adaptive execution partial.
    - Build `workload_shape` from explicit risk keys rather than a hand-authored `lightweight_safe` shortcut.
    - [AGENT] Before dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)`.
    - Before emitting high-risk batches, classify whether they need extra review: `classify_review_gate_policy(workload_shape)`.
    - The chosen dispatch shape applies to the **current ready batch**, not automatically to the entire feature or task graph.
    - Primary decomposition goal: make the next execution step clear and safe. In light mode, produce a compact but complete `tasks.md`; in standard/heavy mode, preserve native-subagent throughput with isolated write sets and dispatch-ready lane packets.
    - Light leader-inline task-generation pass:
      - Allowed only when the adaptive decision records `execution_mode: light`, `workflow_status: ready`, and `dispatch_shape: leader-inline`.
      - Do not create `task-generation/handoffs/<lane-id>.json`, `task-generation/evidence-index.json`, `task-generation/checkpoints.ndjson`, `handoff-to-tasks.json`, or `task-packets/*.json` unless downstream delegated implementation or another explicit integration contract needs them.
      - `task-index.json` is optional but recommended when it is cheap and useful.
      - Record in `tasks.md` and `workflow-state.md` that no delegated task-generation lanes were used and include the evidence-backed mode reason.
    - Standard or heavy delegated task-generation pass:
      - Before dispatching any task-generation lane, persist a `task_generation_checkpoint` record to `task-generation/checkpoints.ndjson` with the lane id, dispatch shape, authoritative inputs, expected handoff path, and current workflow-state summary.
      - Each delegated lane must persist the lane's structured handoff to `task-generation/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or synthesizes `tasks.md`.
      - Update `task-generation/evidence-index.json` after each accepted lane handoff with lane id, handoff path, source artifacts inspected, decisions or constraints contributed, affected task IDs or batch IDs, blocker status, and integration status.
      - Consume `task-generation/evidence-index.json` before final task synthesis: for every accepted handoff, mark the handoff as `integrated`, `deferred`, or `blocked`, and name the target task ID, dependency edge, write-set decision, parallel batch, join point, guardrail, packet field, or escalation that consumed it.
      - Do not synthesize `tasks.md` from chat-only lane results. If a lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a valid handoff path.
    - Blocked heavy task-generation pass:
      - If the adaptive decision records `workflow_status: blocked` or `dispatch_shape: subagent-blocked`, record `blocked_reason` in `workflow-state.md` and stop before task synthesis.
      - Do not downgrade heavy or safety-critical task generation to leader-inline.
    - When resuming after compaction, re-read `workflow-state.md`; also re-read `task-generation/checkpoints.ndjson`, `task-generation/evidence-index.json`, and accepted `task-generation/handoffs/<lane-id>.json` when delegated task-generation lanes were used.
    - Persist the decision fields exactly: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `workflow_status: ready | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `capability_degraded: false | true`, `blocked_reason`.
    - Required join points for delegated standard/heavy task generation:
      - before emitting canonical parallel batches and join points
      - after each delegated parallel batch before dependent work continues
    - Record the chosen execution mode, dispatch shape, capability degradation, blocked reason if any, selected lanes, and join points in the generated report and implementation strategy section.
```

- [ ] **Step 6: Add minimum light-mode task contract**

In `templates/commands/tasks.md`, after the existing paragraph:

```text
The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.
```

add:

```markdown
### Minimum Light-Mode `tasks.md` Contract

For `execution_mode: light`, each implementation-shaping task must still include:

- Task ID, checkbox, phase or story label, and concrete objective.
- Target file path, write scope, or explicit path discovery step.
- Required context pointers using `file.md#section-heading` where plan or spec context matters.
- Dependencies or `none`.
- Constraints and forbidden drift inherited from `plan.md`, `context.md`, `plan-contract.json`, or memory files.
- Validation command or concrete manual check.
- Done condition.
- Test task, or an explicit no-new-test rationale with replacement validation and residual risk.

If later `sp-implement` needs native subagent packets and cannot compile them from these fields, route back to `sp-tasks` for packet enrichment instead of guessing missing write scopes or acceptance criteria.
```

- [ ] **Step 7: Replace blanket test wording**

In `templates/commands/tasks.md`, replace:

```markdown
**Tests are default deliverables**: Generate test tasks by default for affected behavior changes, bug fixes, and regression-sensitive modules. Only omit tests when the change is clearly docs-only/process-only or the plan explicitly allows the omission.
```

with:

```markdown
**Risk and behavior driven validation**: Generate test tasks by default when work changes product behavior, bugfix behavior, refactored logic with regression risk, public API contracts, persistence or migration behavior, security-sensitive behavior, or generated outputs consumed by users or tools. Omit new tests only when the work is clearly docs-only, process-only, prompt/template wording only with existing coverage judged sufficient, config-only with a better lint or smoke check, or low-risk artifact maintenance with an honest focused validation path. When omitting tests, record the no-new-test rationale, replacement validation, and residual risk in `tasks.md`.
```

Replace:

```text
Treat tests as default deliverables for behavior changes, bug fixes, and refactors
If the touched area lacks a reliable automated test surface, add explicit bootstrap tasks to establish the smallest runnable test surface first before implementation tasks for that slice
```

with:

```text
Treat tests as default deliverables for product behavior changes, bug fixes, refactors with regression risk, public API contracts, persistence/migration changes, security-sensitive behavior, and generated outputs consumed by users or tools
If the touched area lacks a reliable automated test surface, add the smallest runnable test surface only when the change risk requires automated proof; otherwise record the no-new-test rationale, replacement validation, and residual risk
```

Replace:

```text
Each phase includes: story goal, independent test criteria, required test tasks for behavior changes/bug fixes/refactors/regression-sensitive modules, implementation tasks
```

with:

```text
Each phase includes: story goal, independent validation criteria, risk-required test tasks, no-new-test rationale where tests are omitted, implementation tasks
```

Replace:

```text
Tests specific to that story for behavior changes, bug fixes, refactors, and regression-sensitive modules
```

with:

```text
Tests specific to that story when risk and behavior driven validation requires them
```

Replace:

```text
For behavior changes, bug fixes, refactors, and regression-sensitive modules: Each affected interface contract → contract test tasks by default before implementation in that story's phase
```

with:

```text
For public API, behavior, bugfix, persistence, security, or regression-sensitive contract changes: affected interface contracts → contract test tasks by default before implementation in that story's phase
```

- [ ] **Step 8: Update tasks reporting evidence paths**

In Step 6 reporting, replace:

```text
task-generation evidence paths: `task-generation/evidence-index.json`, `task-generation/checkpoints.ndjson`, and accepted `task-generation/handoffs/<lane-id>.json` files
```

with:

```text
task-generation evidence paths when delegated lanes were used: `task-generation/evidence-index.json`, `task-generation/checkpoints.ndjson`, and accepted `task-generation/handoffs/<lane-id>.json` files; otherwise report `delegated_task_generation_lanes: none`
```

Add final state fields:

```text
execution_model: adaptive
execution_mode: light | standard | heavy
workflow_status: ready | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
capability_degraded: false | true
blocked_reason: required when blocked
```

- [ ] **Step 9: Run focused task tests**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py -k "tasks_template_uses_adaptive_execution_modes or tasks_template_inherits_implementation_target_boundary or tasks_templates_require_join_point_validation_details" tests/test_tasks_reporting_guidance.py
```

Expected: selected tests pass.

Do not commit yet; broader template locks still need adjustment.

## Task 6: Update Mandatory Subagent Template Tests

**Files:**
- Modify: `tests/test_subagent_mandatory_template_guidance.py`

- [ ] **Step 1: Split ordinary commands into mandatory and adaptive**

Replace:

```python
ORDINARY_COMMANDS = (
    "analyze",
    ...
    "plan",
    ...
    "tasks",
    ...
)
```

with:

```python
MANDATORY_COMMANDS = (
    "analyze",
    "auto",
    "checklist",
    "clarify",
    "constitution",
    "debug",
    "deep-research",
    "explain",
    "implement",
    "map-build",
    "map-scan",
    "quick",
    "research",
    "specify",
    "taskstoissues",
)

ADAPTIVE_COMMANDS = ("plan", "tasks")
```

Update loops that use `ORDINARY_COMMANDS` to use `MANDATORY_COMMANDS`, except tests explicitly checking broad generated command existence.

- [ ] **Step 2: Replace all-ordinary mandatory test**

Replace `test_all_ordinary_sp_commands_require_subagents_for_substantive_tasks()` with:

```python
def test_mandatory_sp_commands_require_subagents_for_substantive_tasks() -> None:
    for command_name in MANDATORY_COMMANDS:
        content = _read_command(command_name).lower()

        assert "execution_model: subagent-mandatory" in content, command_name
        assert "execution_surface: native-subagents" in content, command_name


def test_plan_and_tasks_use_adaptive_execution_instead_of_mandatory_partial() -> None:
    for command_name in ADAPTIVE_COMMANDS:
        content = _read_command(command_name).lower()

        assert "execution_model: adaptive" in content, command_name
        assert "execution_mode: light | standard | heavy" in content, command_name
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content, command_name
        assert "workflow_status: ready | blocked" in content, command_name
        assert "execution_model: subagent-mandatory" not in content, command_name
```

- [ ] **Step 3: Adjust forbidden leader wording tests**

In `test_task4_templates_do_not_reintroduce_ordinary_local_leader_framing()`, loop over `MANDATORY_COMMANDS`, not `ORDINARY_COMMANDS`.

Add:

```python
    for command_name in ADAPTIVE_COMMANDS:
        content = _read_command(command_name).lower()
        assert "leader-inline" in content
        assert "capability_degraded" in content
        assert "subagent-blocked" in content
        assert "managed-team fallback is not part" in content
```

- [ ] **Step 4: Run mandatory/adaptive template tests**

Run:

```powershell
uv run pytest -q tests/test_subagent_mandatory_template_guidance.py
```

Expected: pass.

Do not commit yet; more tests will need coordinated updates.

## Task 7: Update Remaining Template and Generated Skill Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_tasks_reporting_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify if needed: `tests/integrations/test_integration_base_markdown.py`
- Modify if needed: `tests/integrations/test_integration_base_toml.py`
- Modify if needed: `tests/integrations/test_integration_base_skills.py`
- Modify if needed: `tests/integrations/test_integration_cursor_agent.py`

- [ ] **Step 1: Update `_assert_subagent_dispatch_contract` call sites for plan/tasks**

In `tests/test_alignment_templates.py`, do not change `_assert_subagent_dispatch_contract()` itself. It remains for mandatory workflows.

Replace:

```python
_assert_subagent_dispatch_contract(content, "plan")
```

with:

```python
_assert_adaptive_plan_tasks_contract(content, "plan")
```

Replace:

```python
_assert_subagent_dispatch_contract(content, "tasks")
```

with:

```python
_assert_adaptive_plan_tasks_contract(content, "tasks")
```

Keep calls for `specify`, `explain`, `deep-research`, `map-scan`, `map-build`, `prd-scan`, and `prd-build`.

- [ ] **Step 2: Update plan/tasks evidence assertions to conditional language**

Where tests assert exact plan/task evidence phrases, update expectations:

For plan:

```python
assert "planning evidence paths when delegated lanes were used" in content
assert "delegated_planning_lanes: none" in content
assert "planning/handoffs/<lane-id>.json" in content
```

For tasks:

```python
assert "task-generation evidence paths when delegated lanes were used" in content
assert "delegated_task_generation_lanes: none" in content
assert "task-generation/handoffs/<lane-id>.json" in content
```

Keep tests that ensure planning/task evidence is consumed when it exists.

- [ ] **Step 3: Update generated skill assertions in `tests/test_extension_skills.py`**

Find assertions around lines that currently require:

```python
assert "tests as default deliverables" in tasks_body.lower()
assert "behavior changes, bug fixes, and refactors" in tasks_body.lower()
assert "add explicit bootstrap tasks to establish the smallest runnable test surface first" in tasks_body.lower()
```

Replace with:

```python
assert "risk and behavior driven validation" in tasks_body.lower()
assert "no-new-test rationale" in tasks_body.lower()
assert "replacement validation" in tasks_body.lower()
assert "residual risk" in tasks_body.lower()
assert "minimum light-mode `tasks.md` contract" in tasks_body.lower()
```

Where plan/tasks generated skills are expected to include `execution_model: subagent-mandatory`, replace only for `sp-plan` and `sp-tasks` with `execution_model: adaptive`.

- [ ] **Step 4: Update integration CLI generated skill assertions**

In `tests/integrations/test_cli.py`, find loops over:

```python
("sp-specify", "sp-plan", "sp-tasks", "sp-explain", "sp-debug")
```

Split assertions:

```python
mandatory_skills = ("sp-specify", "sp-explain", "sp-debug")
adaptive_skills = ("sp-plan", "sp-tasks")
```

Assert mandatory skills contain `execution_model: subagent-mandatory`.

Assert adaptive skills contain:

```python
assert "execution_model: adaptive" in content
assert "execution_mode: light | standard | heavy" in content
```

- [ ] **Step 5: Update Codex integration generated skill assertions**

In `tests/integrations/test_integration_codex.py`, find loops over:

```python
("sp-specify", "sp-plan", "sp-tasks")
```

Split `sp-specify` as mandatory and `sp-plan`/`sp-tasks` as adaptive.

Update boundary guardrail tests to allow conditional evidence paths:

```python
assert "planning evidence paths when delegated lanes were used" in plan_content
assert "task-generation evidence paths when delegated lanes were used" in tasks_content
```

Keep assertions that `planning/evidence-index.json` and `task-generation/evidence-index.json` are present as conditional artifact names.

- [ ] **Step 6: Run focused template/generated tests**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py
```

Expected: pass. If failures appear in base Markdown/TOML/skills integration tests because generated output still expects mandatory plan/tasks, update only the failed assertions with the same mandatory/adaptive split and rerun:

```powershell
uv run pytest -q tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
```

- [ ] **Step 7: Commit template and test updates**

Run:

```powershell
git add templates/command-partials/common/adaptive-execution.md templates/commands/plan.md templates/commands/tasks.md tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_cursor_agent.py
git commit -m "feat: make plan tasks templates adaptive"
```

Expected: one commit with templates and test locks.

## Task 8: Update README and Handbook Guidance

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify if needed: `tests/test_specify_guidance_docs.py`
- Modify if needed: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Add README guidance**

In `README.md`, near the workflow sequence around `specify -> plan -> tasks -> implement`, add:

```markdown
`plan` and `tasks` use adaptive execution. Low-risk single-lane planning or task generation may run leader-inline and record `execution_mode: light`. Standard work uses native subagents when available and records `capability_degraded: true` if it must continue leader-inline because native subagents are unavailable and no high-risk trigger is present. Heavy or safety-critical work records `dispatch_shape: subagent-blocked` and stops when it cannot be delegated safely.
```

Near the subagent execution docs around the current `sp-* execution-oriented workflows use a leader + subagents model` bullets, replace or qualify the blanket wording:

```markdown
- `sp-plan` and `sp-tasks` are adaptive: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`.
- Workflows that remain mandatory-subagent, such as `sp-implement`, `sp-debug`, `sp-map-scan`, `sp-map-build`, `sp-prd-scan`, and `sp-prd-build`, still use `execution_model: subagent-mandatory`.
```

- [ ] **Step 2: Update handbook guidance**

In `PROJECT-HANDBOOK.md`, update the workflow contract generation bullet that says the downstream chain carries structured handoff contracts through `sp-plan`, `sp-tasks`, and `sp-implement`.

Use:

```markdown
`sp-plan` and `sp-tasks` now use adaptive execution: light leader-inline passes for low-risk single-lane artifact work, standard native-subagent dispatch when available, and heavy blocked dispatch when safety-critical work cannot be delegated. Structured planning and task-generation handoffs remain required when delegated lanes are used.
```

Update the enriched task contract generation bullet:

```markdown
`sp-tasks` produces the minimum executable task contract in light mode and enriched subagent-ready task contracts in standard/heavy mode when downstream delegated implementation needs packets.
```

- [ ] **Step 3: Add or update docs tests if they fail**

Run:

```powershell
uv run pytest -q tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
```

Expected: pass. If a docs test fails because it expects blanket mandatory subagent wording, update the assertion to distinguish adaptive `plan`/`tasks` from still-mandatory workflows.

- [ ] **Step 4: Commit docs**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
git commit -m "docs: describe adaptive plan tasks execution"
```

Expected: one docs/test commit.

## Task 9: Run Integration Projection Tests

**Files:**
- Modify if failing: generated integration tests named by pytest output
- Do not modify production behavior unless generated output is actually wrong

- [ ] **Step 1: Run representative integration rendering tests**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_cursor_agent.py
```

Expected: pass. If failures assert old `execution_model: subagent-mandatory` for `sp-plan` or `sp-tasks`, update those assertions to adaptive. If failures assert mandatory behavior for `sp-implement`, `sp-debug`, `sp-map-scan`, or `sp-map-build`, do not weaken them; fix the template if needed.

- [ ] **Step 2: Run broader integration smoke**

Run:

```powershell
uv run pytest -q tests/integrations
```

Expected: pass. Investigate failures by separating real rendering regressions from stale assertions.

- [ ] **Step 3: Commit any integration assertion updates**

Run:

```powershell
git status --short
```

If files changed, run:

```powershell
git add tests/integrations
git commit -m "test: update integration assertions for adaptive plan tasks"
```

Expected: commit only if additional integration assertion updates were needed.

## Task 10: Run Targeted and Full Verification

**Files:**
- Read: all modified files
- No planned edits unless verification exposes failures

- [ ] **Step 1: Run orchestration tests**

Run:

```powershell
uv run pytest -q tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py
```

Expected: pass.

- [ ] **Step 2: Run workflow template tests**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py
```

Expected: pass.

- [ ] **Step 3: Run docs tests**

Run:

```powershell
uv run pytest -q tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
```

Expected: pass or skip if a file does not exist in this checkout. If a listed file does not exist, use `rg --files tests | rg "guidance|handbook|runtime"` to select the equivalent docs test file.

- [ ] **Step 4: Run integration tests**

Run:

```powershell
uv run pytest -q tests/integrations
```

Expected: pass.

- [ ] **Step 5: Run full suite if targeted tests pass**

Run:

```powershell
uv run pytest -q
```

Expected: pass. If runtime is too long for the current session, run:

```powershell
uv run pytest -q tests/orchestration tests/integrations tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py
```

and record that the full suite was not run.

- [ ] **Step 6: Review final diff**

Run:

```powershell
git diff --stat HEAD
git diff --name-only HEAD
```

Expected: no uncommitted changes if each task committed cleanly. If final fixes remain, stage the concrete files shown by `git diff --name-only HEAD` and commit them with a focused message. For the expected files in this plan, use:

```powershell
git add src/specify_cli/orchestration/models.py src/specify_cli/orchestration/policy.py templates/command-partials/common/adaptive-execution.md templates/commands/plan.md templates/commands/tasks.md README.md PROJECT-HANDBOOK.md tests/orchestration/test_models.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_subagent_mandatory_template_guidance.py tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_cursor_agent.py
git commit -m "test: align adaptive workflow regressions"
```

## Self-Review

Spec coverage:

- Adaptive `light | standard | heavy` policy is covered by Tasks 1-2.
- Explicit blocked state and native-unavailable behavior are covered by Tasks 1-2 and template updates in Tasks 4-5.
- New adaptive partial and plan/tasks command-scoped behavior are covered by Tasks 3-5.
- Light-mode task minimum downstream contract and risk-driven validation are covered by Task 5.
- Mandatory workflows remaining mandatory are covered by Tasks 2, 6, 7, and 9.
- README/handbook guidance is covered by Task 8.
- Integration projection is covered by Task 9.

Placeholder scan:

- The plan contains no TBD/TODO placeholders.
- Conditional steps name exact commands and exact behavior when a file or assertion does not exist.

Type and path consistency:

- `ExecutionModel`, `WorkflowStatus`, `ExecutionMode`, `DispatchShape`, and `ExecutionSurface` names match across model, policy, and tests.
- The adaptive persisted fields match the approved spec.
- Commands use PowerShell syntax because the active shell is PowerShell.
