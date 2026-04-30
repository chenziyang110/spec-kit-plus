---
description: Use when you want one state-driven entrypoint that resumes the recommended next Spec Kit Plus workflow step without manually naming the exact command.
workflow_contract:
  when_to_use: A resumable Spec Kit Plus workflow state already exists and you want the canonical next step selected from repository state instead of from chat memory.
  primary_objective: Inspect the authoritative state surfaces, choose exactly one safe canonical next command, then continue under that command's shared contract.
  primary_outputs: No standalone artifact of its own; `sp-auto` resumes the routed workflow and inherits that workflow's outputs, validations, and state updates.
  default_handoff: Follow the routed command's contract and preserve its canonical `next_command`; do not rewrite downstream state to `/sp-auto`.
---

## Workflow Contract Summary

{{spec-kit-include: ../command-partials/common/execution-note.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Objective

Use `sp-auto` as a resume entrypoint and launcher/router, not as a competing workflow.
Its job is to read current repository state, identify the recommended next Spec Kit Plus workflow step, and continue under that workflow's existing contract.

## Context

- Primary inputs are the repository's authoritative workflow state surfaces, not chat memory.
- `sp-auto` does not create a new long-lived state file of its own.
- It exists to continue the already-canonical workflow step recorded elsewhere.

## Process

- Inspect the current repository state surfaces in priority order.
- Resolve exactly one safe canonical next command.
- Continue under that command's full shared contract instead of improvising a blended workflow.

## Output Contract

- Report the routed command and the state file that justified it.
- Preserve the downstream workflow's canonical `next_command` and artifact semantics.
- If no safe route exists, return a read-only diagnostic explaining the missing or conflicting state.

## Guardrails

- `sp-auto` does not replace `sp-specify`, `sp-plan`, `sp-tasks`, `sp-analyze`, `sp-implement`, `sp-debug`, `sp-quick`, `sp-fast`, `sp-test`, `sp-test-scan`, or `sp-test-build`.
- `sp-auto` must never invent a new phase progression from chat memory when repository state already records the next step.
- Always obey the recorded upstream gate.
- Do not rewrite the underlying workflow state to `/sp.auto`; preserve the canonical downstream `next_command` such as `/sp.plan`, `/sp.tasks`, `/sp.analyze`, `/sp.implement`, `/sp.debug`, `/sp.quick`, `/sp.fast`, `/sp.clarify`, or `/sp.deep-research`.
- If state is missing, stale, conflicting, or cannot identify one safe next step, stop in read-only diagnosis and report the exact blocker instead of improvising a route.

## Operating Rules

## Authoritative State Surfaces

Inspect the available state surfaces in this order and prefer the most specific active truth source that does not violate an upstream gate:

1. Active feature `workflow-state.md`
   - Treat `FEATURE_DIR/workflow-state.md` as the primary phase-lock and `next_command` source for feature workflows such as `/sp.plan`, `/sp.tasks`, `/sp.analyze`, `/sp.implement`, `/sp.clarify`, and `/sp.deep-research`.
   - If a feature-level `workflow-state.md` explicitly points upstream, obey it even when later-stage artifacts also exist.

2. Active implementation execution state
   - Read `FEATURE_DIR/implement-tracker.md` together with `workflow-state.md`.
   - If execution is still active and `workflow-state.md` allows `/sp.implement`, resume `/sp.implement`.
   - If `workflow-state.md` still requires `/sp.analyze`, `/sp.plan`, `/sp.tasks`, `/sp.clarify`, or `/sp.deep-research`, obey that recorded upstream gate before resuming implementation.

3. Project-level testing state
   - Read `.specify/testing/testing-state.md`.
   - If it records a clear `next_command`, route to that command exactly as written.

4. Quick-task state
   - Read unfinished `.planning/quick/*/STATUS.md` files.
   - If one active quick task clearly owns the next action, route to `/sp.quick`.
   - If the recorded next command is a bounded local repair lane, `/sp.fast` is allowed only when the state explicitly justifies that smaller route.

5. Debug session state
   - Read active `.planning/debug/*.md` session files.
   - If a live investigation owns the current next action, route to `/sp.debug`.

## Route Resolution

Choose exactly one routed command.

- Prefer the route that is already recorded in the highest-authority active state file.
- If multiple state surfaces are active, prefer the more execution-proximate surface only when it does not conflict with an explicit upstream `next_command`.
- Never bypass `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, `/sp.tasks`, or `/sp.analyze` just because downstream artifacts already exist.
- Never treat `sp-auto` itself as the next recorded workflow step. It is only the entrypoint the user uses instead of typing the canonical command manually.

## Execution Contract

Once the routed command is chosen:

1. Announce the routed command and the state file that justified it.
2. Read `.specify/templates/commands/<target>.md` when available, or follow the routed command's shared contract from the generated local integration surface if that is the active source of truth.
3. Continue under the routed command's rules, artifacts, validations, delegation policy, and completion criteria for the rest of the turn.
4. Do not blend multiple workflows into one ad hoc pass. Route once, then execute that workflow faithfully.

## Diagnostic Fallback

If no safe route can be selected:

- stay read-only
- report which state files were checked
- report what was missing or conflicting
- tell the user which canonical workflow must be run manually or which state artifact must be repaired first

## Expected Routed Outcomes

Typical canonical targets include:

- `/sp.clarify`
- `/sp.deep-research`
- `/sp.plan`
- `/sp.tasks`
- `/sp.analyze`
- `/sp.implement`
- `/sp.debug`
- `/sp.quick`
- `/sp.fast`
- `/sp.specify`

Use `/sp.specify` only when repository state or the absence of any usable downstream state makes a new or re-opened requirement-alignment pass the safest truthful next step.
