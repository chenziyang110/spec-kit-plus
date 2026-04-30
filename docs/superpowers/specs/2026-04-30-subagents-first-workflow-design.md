# Subagents-First Workflow Design

## Goal

Replace the current strategy vocabulary with a simpler workflow contract:

```text
Leader + subagents, subagents-first.
```

Generated `sp-*` workflows should no longer ask the agent to reason from
`single-lane`, `native-multi-agent`, or `sidecar-runtime` as peer strategy
choices. Those names make local execution look like an ordinary option and
force the agent to interpret topology vocabulary before acting. The new contract
should make the leader responsible for coordination and make subagent dispatch
the default whenever it is safe.

## Reference Model

The local `F:\github\superpowers` repository uses a clearer public model:

- `subagent-driven-development`: dispatch a fresh subagent per task, then review
  and integrate.
- `dispatching-parallel-agents`: dispatch one agent per independent problem
  domain when work can run concurrently.
- `executing-plans` / Inline Execution: fallback for environments without
  subagent capability or for work that should stay in one session.
- Main session language uses `controller` or `coordinator`, not low-level lane
  topology names.

Spec Kit Plus should adopt the same operator shape, adapted to its durable
workflow state, packet/result validation, and multi-integration generated
surfaces.

## Terms

Use these terms in generated workflow guidance, documentation, status templates,
and integration addenda:

- `leader`: the invoking agent session. It owns scope, state, dispatch,
  join-point integration, validation, and final reporting.
- `subagents-first`: the execution model for workflows that can delegate work.
- `one-subagent`: dispatch shape for one safe delegated lane.
- `parallel-subagents`: dispatch shape for two or more independent safe lanes.
- `leader-inline-fallback`: recorded exception path when delegation is not safe
  or not available.
- `native-subagents`: execution surface for runtime-native subagent APIs such as
  Codex `spawn_agent` or Claude native subagents.
- `managed-team`: execution surface for durable team runtime escalation when a
  workflow explicitly supports it.
- `leader-inline`: execution surface for local work performed by the leader
  after fallback has been recorded.

Avoid these terms in agent-facing generated guidance:

- `single-lane`
- `native-multi-agent`
- `sidecar-runtime`
- `leader-local` as a strategy name

`leader-inline` may appear only as a fallback surface, not as a selectable
strategy.

## Execution Decision

Every applicable workflow should teach the same decision tree:

```text
1. Can the current work be delegated safely?
   - no: record leader-inline-fallback and execute on the leader path
   - yes: continue

2. How many independent safe delegated lanes exist?
   - one: dispatch one-subagent
   - two or more: dispatch parallel-subagents

3. At the join point:
   - wait for required structured handoffs
   - validate packet/result integrity where the workflow supports it
   - integrate on the leader path
   - update workflow state
   - choose the next wave or finish
```

This should be phrased as a dispatch readiness check, not as a strategy menu.
The agent should not be told to choose from several peer modes. It should first
try to prepare safe subagent work, then fall back only when that fails.

## Fallback Rule

`leader-inline-fallback` is allowed only when at least one of these is true:

- the current runtime has no usable subagent dispatch surface
- the workflow's packet or equivalent contract is incomplete
- the lane lacks enough context, constraints, validation targets, or handoff
  expectations for isolated execution
- write sets or shared mutable state make delegation unsafe
- the work is tightly coupled and cannot be split without reducing correctness
- the required result channel is missing or the returned handoff is invalid
- a managed-team escalation was attempted or ruled out according to the
  workflow-specific contract

Before doing concrete leader-inline work, the workflow must record the fallback
reason in the active state artifact, such as `implement-tracker.md`,
`.planning/quick/<id>/STATUS.md`, a debug session file, map/test state, or the
workflow's equivalent state file.

## Core Model Changes

Because backward compatibility is not required for this refactor, replace the
old core vocabulary rather than aliasing it indefinitely.

Target model:

```python
ExecutionModel = Literal["subagents-first"]
DispatchShape = Literal[
    "one-subagent",
    "parallel-subagents",
    "leader-inline-fallback",
]
ExecutionSurface = Literal[
    "native-subagents",
    "managed-team",
    "leader-inline",
]
```

The shared decision helper should return a decision containing:

- `execution_model`
- `dispatch_shape`
- `execution_surface`
- `reason`
- `fallback_from`, when a fallback occurred
- `created_at`

The policy input can continue to reason over workload shape, runtime capability,
write-set overlap, packet readiness, delegation confidence, and durable
coordination availability. The output should no longer encode topology as
`single-lane` or `multi-lane`.

## Workflow Surface Changes

Apply the new contract across the generated `sp-*` workflow surface:

- `sp-specify`: leader dispatches subagents for bounded context, reference,
  ambiguity, risk, and capability-decomposition lanes when safe.
- `sp-plan`: leader dispatches subagents for research, data model, contracts,
  quickstart, risk, and validation-scenario lanes when safe.
- `sp-tasks`: leader dispatches subagents for story decomposition, dependency
  graph, write-set analysis, guardrail mapping, and batch planning when safe.
- `sp-implement`: leader dispatches implementation and review subagents from
  validated `WorkerTaskPacket` contracts; leader-inline execution is a recorded
  fallback only.
- `sp-quick`: leader creates or resumes `STATUS.md`, selects the smallest safe
  dispatch shape, and dispatches before broad leader-side implementation.
- `sp-debug`: leader owns the hypothesis and session state; subagents collect
  bounded evidence. Resolution remains leader-owned.
- `sp-map-scan`: leader dispatches read-only subagents for inventory and
  classification; final ledger ownership remains leader-owned.
- `sp-map-build`: leader dispatches atlas evidence/synthesis subagents from scan
  packets; final atlas writes and reverse coverage remain leader-owned.
- `sp-test`: remains a router. It should not dispatch directly; it routes to
  `sp-test-scan` or `sp-test-build`.
- `sp-test-scan`: leader dispatches read-only scout subagents from scan packets.
- `sp-test-build`: leader dispatches test-building and review subagents from
  validated build packets.
- `sp-deep-research`: leader dispatches independent research or spike tracks
  when safe; sequential research is a fallback with a recorded reason.
- `sp-explain`: default to leader explanation for small artifacts, but dispatch
  cross-check subagents when independent verification would materially improve
  correctness.

The workflow wording should use one consistent shape:

```text
You are the leader. Use subagents by default when safe. Use parallel subagents
when independent lanes can run concurrently. Use leader-inline fallback only
after recording why delegation is unavailable or unsafe.
```

## Generated State Templates

Generated state templates should replace fields such as:

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

When no fallback occurred, `fallback_reason` should be `none` or omitted by the
workflow-specific template. When `dispatch_shape` is
`leader-inline-fallback`, the fallback reason is required.

## Integration Surface Changes

Shared integration augmentation should inject the same subagents-first contract
for Markdown, TOML, and skills-based integrations.

Codex-specific guidance should map `native-subagents` to `spawn_agent`,
`wait_agent`, and `close_agent`, while keeping `sp-teams` only for workflows
that intentionally use durable team state.

Claude-specific guidance should describe native subagents as the default
dispatch surface when available and remove old wording that treats
`single-lane` as a local-execution ambiguity.

Cursor-specific guidance should keep its stronger rule: once the first lane is
defined, dispatch before broad local deep-dive analysis. The wording should use
`one-subagent` and `parallel-subagents`.

Integrations without native subagent support should not pretend to support
subagents. Their generated guidance should explicitly route to
`leader-inline-fallback` or a supported managed-team path and record why.

## Documentation Changes

Update user-facing documentation to teach:

- the main workflow remains `specify -> plan`
- execution-oriented workflows use a leader + subagents model
- `[AGENT]` still marks required AI action and does not itself imply delegation
- `[P]` still means parallel-safe task ordering, but concrete dispatch is governed
  by subagent readiness and write-set safety
- `sp-teams` is a durable coordination path, not the ordinary way to express
  subagent-first work

README, quickstart, generated context scripts, and project-map docs should stop
listing the old strategy vocabulary as current behavior.

## Tests And Verification

Update tests in the same change as the implementation. The test suite should
assert:

- generated workflow templates do not contain agent-facing `single-lane`,
  `native-multi-agent`, or `sidecar-runtime` guidance
- generated status templates contain `execution_model`, `dispatch_shape`, and
  `execution_surface`
- policy decisions return `one-subagent`, `parallel-subagents`, or
  `leader-inline-fallback`
- `leader-inline-fallback` decisions require a reason
- Codex generated skills mention `spawn_agent`, `wait_agent`, and `close_agent`
  for native subagent dispatch
- `sp-implement`, `sp-quick`, and `sp-debug` preserve leader ownership of state,
  join points, validation, and final reporting
- map/test workflows preserve read-only subagent rules where applicable
- docs and project-map guidance no longer advertise the old strategy vocabulary

Focused verification entry points:

```text
pytest tests/orchestration -q
pytest tests/integrations -q
pytest tests/codex_team -q
pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_quick_skill_mirror.py -q
pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q
```

Run `pytest -q` before final completion when feasible because generated
workflow wording is broad and cross-cutting.

## Map Maintenance

This change alters workflow names, integration contracts, orchestration
vocabulary, and generated verification entry points. The implementation must
refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/` docs, or
mark the project map dirty with a concrete reason if the refresh cannot happen
in the same pass.

Expected affected project-map topics:

- `root/WORKFLOWS.md`
- `root/CONVENTIONS.md`
- `root/INTEGRATIONS.md`
- `root/ARCHITECTURE.md`
- `root/TESTING.md`
- `modules/specify-cli-core/ARCHITECTURE.md`
- `modules/templates-generated-surfaces/WORKFLOWS.md`

## Non-Goals

- Do not redesign the full Spec Kit user workflow. `specify -> plan` remains the
  mainline.
- Do not remove leader ownership. Subagents execute bounded work; they do not
  own workflow state or final acceptance.
- Do not make `sp-teams` the default subagent path. It remains for durable team
  state and lifecycle control beyond an in-session burst.
- Do not weaken packet/result validation. The new vocabulary should make
  delegation safer, not looser.
- Do not preserve old strategy names in generated guidance for compatibility.
  The requested refactor intentionally favors a clean break.

## Acceptance Criteria

- Agent-facing generated workflows consistently teach `subagents-first`.
- No generated `sp-*` command or skill uses `single-lane`,
  `native-multi-agent`, or `sidecar-runtime` as an active strategy name.
- Orchestration policy returns dispatch-shape decisions instead of old strategy
  decisions.
- Leader-inline work is always represented as fallback with a reason.
- Existing cross-CLI generated surfaces remain truthful about each runtime's
  actual subagent capability.
- Documentation, tests, and project-map artifacts agree on the new vocabulary.
