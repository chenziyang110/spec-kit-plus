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

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

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
- Use the lane registry as a candidate-discovery cache, not as the truth source.
- `sp-auto` does not create a new long-lived state file of its own.
- It exists to continue the already-canonical workflow step recorded elsewhere.

## Process

- For every feature-bearing candidate, first run `{{specify-subcmd:workflow show --feature-dir <feature-dir> --format json}}`, then `{{specify-subcmd:workflow next --feature-dir <feature-dir> --format json}}`. `FEATURE_DIR/workflow-runtime.json` is the required-stage phase lock. Consume the returned structured `next_argv`; never reconstruct or infer the required phase action from Markdown fields.
- When `next_argv` names `workflow complete-stage`, route to the current required-stage owner so it can finish and validate that stage. When it names `workflow transition --to <stage>`, route to that destination stage and pass the exact argv. When active `accept` returns `workflow closeout`, route to the current accept owner so human acceptance can resume; only completed `accept` has no successor.
- A blocked runtime intentionally has no `next_argv`. Preserve its tutorial and wait for the declared evidence; once present, fill only the required evidence input in `data.resolution_action` and execute its runtime-owned base argv. `show_argv` refreshes state but never resolves it.
- Inspect the current repository state surfaces in priority order.
- When concurrent lanes exist, resolve candidates by command semantics first and run reconcile before any resume decision.
- If the selected lane has a materialized worktree, continue from that isolated worktree context instead of assuming the leader workspace is the active feature root.
- Resolve exactly one safe canonical next command.
- Continue under that command's full shared contract instead of improvising a blended workflow.

## Output Contract

- Report the routed command and the state file that justified it.
- Preserve the downstream workflow's canonical `next_command` and artifact semantics.
- If no safe route exists, return a read-only diagnostic plus a self-unblock recommendation explaining the missing or conflicting state and the safest repair or canonical command.

## Guardrails

- `sp-auto` does not replace `sp-specify`, `sp-plan`, `sp-tasks`, `sp-analyze`, `sp-implement`, `sp-review`, `sp-accept`, `sp-debug`, `sp-quick`, or `sp-fast`.
- `sp-auto` must never invent a new phase progression from chat memory when repository state already records the next step.
- Always obey the recorded upstream gate.
- Do not rewrite the underlying workflow state to `/sp.auto`; preserve the canonical downstream `next_command` such as `/sp.plan`, `/sp.tasks`, `/sp.implement`, `/sp.review`, `/sp.accept`, `/sp.debug`, `/sp.quick`, `/sp.fast`, `/sp.clarify`, or `/sp.deep-research`. Preserve `/sp.analyze` only when an existing state file explicitly records that legacy or diagnostic route.
- If state is missing, stale, conflicting, or cannot identify one safe next step, stop in read-only diagnosis and report the exact blocker instead of improvising a route.
- Do not guess when multiple resumable lanes exist.
- Never auto-resume an `uncertain` lane.

## Operating Rules

## Authoritative State Surfaces

Inspect the available state surfaces in this order and prefer the most specific active truth source that does not violate an upstream gate:

1. Active feature phase runtime and rich state
   - Treat `FEATURE_DIR/workflow-runtime.json` plus `workflow show`/`workflow next` as the primary required-stage phase lock. `FEATURE_DIR/workflow-state.md` is rich workflow-owned resume/evidence context and may add an auxiliary gate, but it cannot skip or reverse the runtime stage.
   - Use only the runtime's structured `next_argv` for `complete-stage`, forward `transition`, blocker resume, or terminal status. Legacy `next_command` and `active_command` fields are fallback hints only when no runtime file exists for a noncanonical auxiliary workflow.
   - Clean completed task-generation state with `active_command: sp-tasks`, `status: completed`, `phase_mode: task-generation-only`, and `next_command: /sp.implement` should route directly to `/sp.implement`; preserve `/sp.analyze` only when a feature-level state file explicitly records that legacy or diagnostic route.
   - If a feature-level `workflow-state.md` contains evidence that explicitly
     invalidates an upstream stage, do not jump around the CLI phase lock. Use
     `workflow reopen` with the current revision, reason, evidence, and complete
     invalidated-artifact set when that evidence is sufficient. A mapped stage
     already active resumes its owner; the same completed stage is reactivated
     through reopen. Otherwise route to analyze or the current owner to produce
     a valid reopen decision.

2. Active implementation execution state
   - Read `FEATURE_DIR/implement-tracker.md` together with `workflow-state.md`.
   - If execution is still active and `workflow-state.md` allows `/sp.implement`, resume the canonical `/sp.implement` route.
   - If trusted execution is completed and `next_command: /sp.review`, route to canonical `/sp.review`; do not repeat implementation or skip system Review.
   - If `workflow-state.md` still requires `/sp.analyze`, `/sp.plan`, `/sp.tasks`, `/sp.clarify`, or `/sp.deep-research`, reconcile that gate with the CLI runtime. Execute an evidence-backed `workflow reopen` for a backward move or same-completed-stage reactivation; do not route to an upstream command while the runtime still owns a later stage.

3. Post-implementation system Review state
   - If trusted implementation closeout exists and `review-state.json` is absent, `reviewing`, `repairing`, `blocked`, failed, or stale, route to canonical `/sp.review` before human acceptance.
   - Treat Review as approved only when the implementation fingerprint is fresh, every mandatory real-entrypoint scenario passes with required integrated evidence, and no blocking finding remains.

4. Post-Review human acceptance state
   - If trusted Review closeout exists and `human-acceptance.json` is `draft`, `ready`, `in_progress`, `blocked`, `rejected`, or `stale`, route to canonical `/sp.accept` before integration or delivery.
   - Treat `accepted` as complete only when the Review/summary fingerprint is fresh and every required scenario has explicit human PASS.

5. Quick-task state
   - Read unfinished `.planning/quick/*/STATUS.md` files.
   - If one active quick task clearly owns the next action, route to the canonical `/sp.quick` token.
   - If the recorded next command is a bounded local repair lane, canonical `/sp.fast` is allowed only when the state explicitly justifies that smaller route.

6. Debug session state
   - Read active `.planning/debug/*.md` session files.
   - If a live investigation owns the current next action, route to the canonical `/sp.debug` token.

7. Discussion handoff state
   - Read active `.specify/discussions/*/discussion-state.json` files when no higher-authority feature, implementation, quick, or debug state has already selected a unique route; use Markdown only for legacy recovery.
   - Treat `status: handoff-ready` plus `next_command: /sp.specify` or `sp-specify` as a `/sp.specify` candidate only when `handoff_consumption_status` is not `consumed`.
   - If `handoff_consumption_status: consumed`, `status: completed`, `consumed_by_feature_dir` is populated, or `next_command: none`, do not count that discussion as a resumable candidate.
   - If a handoff-ready discussion's `handoff-to-specify.json` path is already referenced by a feature `brainstorming/handoff-to-specify.json` as `source_contract`, treat it as a consumed-stale cleanup item, not a competing route. Recommend `{{specify-subcmd:discussion mark-consumed <slug> --feature-dir <feature-dir>}}` as the repair evidence, or perform that repair only when the active workflow allows state cleanup before routing.
   - If multiple unconsumed handoff-ready discussions remain, stop and ask for a specific slug instead of guessing.

## Route Resolution

Choose exactly one routed command.

- If lane state exists, consult the lane registry first to discover candidate lanes, then reconcile against real workflow artifacts before selecting a route.
- Auto-resume only when there is exactly one unique safe candidate.
- If multiple candidates remain after reconcile, stop and present a minimal choice instead of guessing.
- Prefer the route that is already recorded in the highest-authority active state file.
- If multiple state surfaces are active, prefer the more execution-proximate surface only when it does not conflict with an explicit upstream `next_command`.
- Never bypass canonical upstream gates such as `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, or `/sp.tasks` just because downstream artifacts already exist. Treat `/sp.analyze` as an upstream gate only when persisted workflow state explicitly records that legacy or diagnostic route.
- Never treat `sp-auto` itself as the next recorded workflow step. It is only the entrypoint the user uses instead of typing the canonical command manually.

## Execution Contract

Once the routed command is chosen:

1. Announce the routed command and the state file that justified it.
2. Carry a temporary routed-pass mode named `auto_default_recommendation: true` into the target command. This is an execution hint for this turn only; do not persist it as the target workflow's canonical `next_command`.
3. Read `.specify/templates/commands/<target>.md` when available, or follow the routed command's shared contract from the generated local integration surface if that is the active source of truth.
4. Continue under the routed command's rules, artifacts, validations, delegation policy, and completion criteria for the rest of the turn.
5. Do not blend multiple workflows into one ad hoc pass. Route once, then execute that workflow faithfully.

## Recommended Default Continuation

When `auto_default_recommendation: true` is active, the routed command must auto-resolve a question or confirmation gate by accepting the recommended/default continuation when all of these are true:

- The target workflow would otherwise stop only to ask the user to answer a bounded question, choose from a bounded list, or confirm a previously presented safe default.
- The list or confirmation gate has one single explicitly recommended option or one safe default continuation.
- The recommended/default option preserves the user's current stated intent, keeps the current scope, and does not discard or defer an upstream capability signal.
- There is no explicit user disagreement, no unresolved planning-critical ambiguity, no out-of-scope conflict, no scope reduction, no security-sensitive decision, no destructive or irreversible action, and no external-cost or credential-affecting decision.

If those conditions hold, record the recommended option as accepted by `sp-auto` in the routed workflow's state or summary and continue. Do not invoke a structured question tool, do not render a textual question block, and do not stop only to ask the user to reply `1`, `2`, or `3` when the only safe pending action is accepting that single recommended option.

If the recommended/default continuation cannot satisfy every condition, do not guess and do not wait silently for user input. Write a self-unblock recommendation that names the blocker, the safest recommended user decision or canonical command, the evidence that would make automatic continuation safe next time, and any reversible repair the agent can perform before stopping under the routed workflow's normal confirmation gate.

## Diagnostic Fallback

If no safe route can be selected:

- stay read-only
- report which state files were checked
- report what was missing or conflicting
- perform any reversible state-inspection or reconcile step allowed by this contract before giving up
- tell the user which canonical workflow must be run manually or which state artifact must be repaired first
- include the exact evidence that would let a future `sp-auto` run continue automatically

## Expected Routed Outcomes

Typical canonical targets include:

- `/sp.clarify`
- `/sp.deep-research`
- `/sp.plan`
- `/sp.tasks`
- `/sp.analyze`
- `/sp.implement`
- `/sp.review`
- `/sp.accept`
- `/sp.debug`
- `/sp.quick`
- `/sp.fast`
- `/sp.specify`

Use canonical `/sp.specify` only when repository state or the absence of any usable downstream state makes a new or re-opened requirement-alignment pass the safest truthful next step.
When no safe route can be selected and the user must invoke that fallback manually, tell them to run `{{invoke:specify}}`.
