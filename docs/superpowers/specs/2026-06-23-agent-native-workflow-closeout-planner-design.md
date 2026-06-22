# Agent-Native Workflow Closeout Planner Design

## Context

The previous project-cognition iteration shipped two important primitives:

- `project-cognition generate-ignore --format json` for agent-reviewed `.cognitionignore` setup before map scans.
- `project-cognition changes --format json` for Git-native changed-path intake with ignore handling, known/unknown path classification, and dirty-runtime repair support.

The repository already has a shared closeout partial at `templates/command-partials/common/inline-project-cognition-update.md`. Many generated `sp-*` workflows include that partial. Today the partial correctly states that workflow-owned source/runtime/template/config/test/generated-asset changes must update project cognition directly instead of handing routine closeout to `sp-map-update`.

The remaining problem is execution quality. The shared partial still asks the agent to manually assemble changed paths, affected surfaces, update payloads, and finalizer decisions. That makes ordinary closeout too dependent on agent memory and per-workflow prompt discipline. The next iteration should make workflow closeout more deterministic while preserving the agent's responsibility for semantic evidence and verification truth.

## Goal

Create an agent-native shared closeout planner that all ordinary source-changing `sp-*` workflows can use during completion.

The target closeout shape is:

```text
workflow changed repository surfaces
-> project-cognition closeout-plan --workflow <workflow-or-alias> --format json
-> planner returns canonical workflow, update_mode, required agent fields, and either delta-session commands or a payload draft
-> agent fills semantic evidence and verification fields
-> if update_mode=delta_session: run delta_append_command, then update_command
-> if update_mode=payload_file: write payload_draft to payload_path, then update_command
-> result_state drives clean closeout, partial closeout, rebuild routing, blocked reporting, or mark-dirty fallback
```

This should reduce routine manual `sp-map-update` usage. `sp-map-update` remains the external/manual maintenance workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.

## Non-Goals

- Do not make `closeout-plan` publish runtime records in the first iteration.
- Do not let the runtime invent verification evidence, user decisions, confidence notes, or behavior semantics.
- Do not remove `project-cognition update`; it remains the command that records refresh data and returns `result_state`.
- Do not remove or silently deprecate delta-session closeout in the first iteration.
- Do not make every workflow fully automatic in one step. The agent still owns semantic judgment.
- Do not route ordinary partial or weak closure to a full rebuild by default.
- Do not require a usable cognition baseline for planning-only workflows that did not mutate source/runtime/template/config/test/generated-asset surfaces.

## Design Principle

The split is:

```text
runtime owns deterministic facts
agent owns execution-time semantic facts
shared partial owns mandatory closeout sequence
```

The runtime can know:

- changed paths from Git
- ignored paths
- known and unknown path-index coverage
- baseline/head commit metadata
- whether runtime state is usable, dirty, repairable, blocked, or rebuild-required
- a safe draft payload shape
- which fields the agent must supply before update
- which finalizer commands are allowed after update

The agent knows:

- what behavior changed
- what verification ran and whether it passed
- which generated surfaces were affected
- which user decisions constrained the change
- which confidence notes and known unknowns are honest
- whether workflow completion itself is trustworthy

The planner should make the agent's required work explicit instead of relying on the agent to remember every closeout field.

## New Runtime Command

Add:

```text
project-cognition closeout-plan --workflow <workflow> --format json
```

Optional first-iteration flags:

```text
--reason <reason>                 # default: workflow-finalize
--intent <intent>                 # forwards intent to change planning when useful
--changed-path <path>             # repeatable explicit path override or supplement
--changed-paths <path>            # alias for repeatable explicit path
--since <base> --head <head>      # explicit commit range when a safe task boundary exists
--payload-path <path>             # optional desired output payload path
--delta-session <id>              # optional active delta session; planner prefers delta_session mode when present
--include-working-tree            # default true
--include-untracked               # default true
```

The command is planner-only in the first iteration. It must not write update records, mutate `status.json`, call `update`, call `record-refresh`, call `complete-refresh`, or call `mark-dirty`.

It may create the parent update directory only if a future implementation chooses to write a draft payload file. The safer first cut is to return a draft JSON object and a recommended payload path without writing it.

`--workflow` accepts common aliases such as `implement`, `sp-implement`, and `/sp.implement`, but the runtime must normalize to one stored form. Payloads, update records, and planner output must use canonical `sp-<workflow>` values such as `sp-implement`, `sp-quick`, or `sp-map-update`. The planner should return both `workflow_input` and `workflow_canonical`; unknown workflow names should block unless a later implementation deliberately adds custom workflow support.

## Planner Flow

`closeout-plan` should internally use existing runtime primitives:

```text
changes
-> classify closeout readiness
-> normalize workflow identity
-> choose update_mode: delta_session when an active delta session is supplied, otherwise payload_file
-> build update payload draft
-> compute required_agent_fields
-> compute recommended_next_command
-> compute finalizer_policy
```

The first iteration does not need a full `affected-closure` command. It should use `changes` output as the deterministic seed and produce a conservative payload draft. Unknown or unbounded impact is represented as required agent work, a top-level unknown-path disposition queue, `minimal_live_reads`, or `partial_refresh` guidance, not invented closure.

When `changes` returns:

- `no_op`: planner returns a no-op plan. If no project-related mutation exists, update is not required.
- `affected_closure`: planner drafts an update payload from included changed paths and asks the agent to fill semantic fields.
- `partial_refresh`: planner drafts a partial-safe payload and requires unknown-path disposition before update. `known_unknowns` and `minimal_live_reads` are required only for dispositions that leave unproven or blocking uncertainty, such as `review_only` or `blocking_known_unknown`; verified `adoptable` paths do not become partial merely because they were initially unknown to `path_index`.
- `needs_rebuild`: planner does not draft a normal update payload; it routes to `sp-map-scan -> sp-map-build`.
- `blocked`: planner reports the blocker and recommends `mark-dirty` only when useful update data cannot be recorded.

## Output Contract

`closeout-plan --format json` should return:

```json
{
  "status": "ok",
  "workflow_input": "implement",
  "workflow": "sp-implement",
  "workflow_canonical": "sp-implement",
  "reason": "workflow-finalize",
  "readiness": "query_ready",
  "baseline_commit": "<commit>",
  "head_commit": "<commit>",
  "working_tree_dirty": true,
  "next_action": "draft_update",
  "update_mode": "payload_file",
  "changes": [],
  "ignored_paths": [],
  "unknown_paths": [
    "src/new-module.ts"
  ],
  "unknown_path_dispositions": [
    {
      "path": "src/new-module.ts",
      "change_level": "new_path",
      "allowed_dispositions": [
        "adoptable",
        "review_only",
        "ignored",
        "blocking_known_unknown"
      ],
      "agent_disposition": null,
      "required_agent_decision": true,
      "planner_reason": [
        "path not present in active path_index"
      ]
    }
  ],
  "known_paths": [],
  "delta_session_id": null,
  "delta_append_command": null,
  "payload_path": ".specify/project-cognition/updates/<update-id>.json",
  "payload_draft": {
    "workflow": "sp-implement",
    "reason": "workflow-finalize",
    "changed_paths": [],
    "scope_paths": [],
    "behavior_surfaces": [],
    "generated_surfaces": [],
    "state_contracts": [],
    "verification": [],
    "known_unknowns": [],
    "confidence_notes": [],
    "user_decisions": [],
    "boundary": {}
  },
  "required_agent_fields": [
    "verification",
    "behavior_surfaces"
  ],
  "recommended_next_command": "write_payload_then_update",
  "update_command": "project-cognition update --payload-file \".specify/project-cognition/updates/<update-id>.json\" --reason workflow-finalize --format json",
  "finalizer_policy": {
    "ready": "clean_closeout_after_verification",
    "no_op": "clean_closeout_when_no_project_mutation",
    "partial_refresh": "report_partial_and_minimal_live_reads",
    "needs_rebuild": "route_map_scan_then_map_build",
    "blocked": "report_blocker_or_mark_dirty_when_no_useful_update_recorded"
  },
  "warnings": [],
  "errors": []
}
```

Field requirements:

- `changes` should carry the same path-level facts as `project-cognition changes` or a stable subset with references to the changes payload.
- `ignored_paths` must never be copied into `payload_draft.changed_paths`, update records, known unknowns, graph evidence, route indexes, or minimal live reads.
- `unknown_paths` are a top-level uncertainty/disposition queue, not automatic blocking `known_unknowns`.
- `unknown_path_dispositions` must require the agent to classify each unknown path as exactly one of `adoptable`, `review_only`, `ignored`, or `blocking_known_unknown`.
- `unknown_path_dispositions[]` item schema is:
  - `path`: repository-relative path from `unknown_paths`.
  - `change_level`: copied from the matching `changes[].change_level`, for example `new_path` for an unindexed new file.
  - `allowed_dispositions`: planner-owned allowed values for this path. First iteration should use `["adoptable", "review_only", "ignored", "blocking_known_unknown"]`.
  - `agent_disposition`: `null` in planner output, then filled by the agent with one value from `allowed_dispositions` before update recording.
  - `required_agent_decision`: `true` when `agent_disposition` is unset and update recording must not proceed.
  - `planner_reason`: runtime-owned explanation, usually copied from or derived from `changes[].reason`.
- `adoptable` means a verified new path is inside the workflow-owned change scope and may enter `changed_paths`/`scope_paths` without becoming a blocking known unknown.
- `review_only` means the path informed the agent but is not adopted into the update payload as changed coverage.
- `ignored` means the path remains excluded and must not enter payloads, records, route indexes, evidence, aliases, or minimal live reads.
- `blocking_known_unknown` is the only unknown-path disposition that should be copied into `payload_draft.known_unknowns`.
- `required_agent_fields` is a gate. The shared partial must instruct the agent not to run `update` until these fields are filled honestly.
- `finalizer_policy` is advisory until `project-cognition update` returns `result_state`; the actual completion gate remains the update result.

Mode-specific fields:

- `update_mode=delta_session` must provide `delta_session_id`, `delta_append_command`, and `update_command`. `delta_append_command` should be the planner-approved `project-cognition delta append ... --format json` command template with repeatable flags for changed paths, behavior surfaces, generated surfaces, verification, and accepted known unknowns after agent disposition. `update_command` must use `project-cognition update --delta-session "<id>" --reason workflow-finalize --format json`.
- `update_mode=payload_file` must provide `payload_path`, `payload_draft`, and `update_command`. `update_command` must use `project-cognition update --payload-file "<payload_path>" --reason workflow-finalize --format json`.

## Shared Partial Update

Update `templates/command-partials/common/inline-project-cognition-update.md` so all including workflows follow this sequence:

1. Determine whether the workflow changed project-related source/runtime/templates/generated assets/config/tests/state contracts/shared surfaces/behavior-bearing docs.
2. If no project-related mutation occurred, do not call `project-cognition update` or `mark-dirty`.
3. If mutation occurred, call:

   ```text
   project-cognition closeout-plan --workflow <active-workflow> [--delta-session "$DELTA_SESSION_ID"] --format json
   ```

4. Consume `workflow_canonical`, `update_mode`, `payload_draft`, `required_agent_fields`, `ignored_paths`, `unknown_paths`, `unknown_path_dispositions`, `delta_append_command`, `recommended_next_command`, and `finalizer_policy`.
5. Fill missing agent-owned fields with live evidence from the completed workflow:
   - `verification`
   - `behavior_surfaces`
   - `generated_surfaces`
   - `state_contracts`
   - `known_unknowns`
   - `confidence_notes`
   - `user_decisions`
   - `boundary`
6. Classify every `unknown_path_dispositions` item before recording the update. Adoptable verified new paths may be recorded; ignored and review-only paths must stay out of changed coverage; only `blocking_known_unknown` items become payload or delta known unknowns.
7. If `update_mode=delta_session`, run the planner's `delta_append_command` after filling the agent-owned repeatable flags, then run the planner's `update_command`.
8. If `update_mode=payload_file`, write the payload file at the planner's `payload_path`, then run the planner's `update_command`.
9. Gate completion on `result_state`, not on `status=ok`, `update_id`, `last_update_id`, or freshness alone.
10. Use `mark-dirty` only when planner/update cannot record useful update data, cannot identify workflow-owned scope, or workflow verification is not trustworthy.

This partial should remain the shared point of truth. Individual workflows should not duplicate the full closeout algorithm.

## Workflow Coverage

First iteration should focus on workflows that already include the shared inline closeout partial:

- `sp-implement`
- `sp-debug`
- `sp-fast`
- `sp-quick`
- `sp-analyze`
- `sp-specify`
- `sp-clarify`
- `sp-plan`
- `sp-tasks`
- `sp-deep-research`
- `sp-map-update`

The design does not require changing every workflow in the same pass if the shared partial can preserve compatibility. Workflow-specific edits are needed only when a workflow bypasses the shared partial or contradicts the planner-first sequence.

Planning-only workflows keep the existing rule: artifact-only planning does not require cognition refresh unless the workflow actually changes source/runtime/template/config/test/generated-asset surfaces in the current run.

`sp-map-update` is a special case. It may use `closeout-plan` only as planner assistance for map-maintenance work that it already owns. If `sp-map-update` has already run `project-cognition update --reason map-update` and finalized with `record-refresh` or `complete-refresh` when appropriate, it must not trigger a second `workflow-finalize` update through the shared closeout partial for the same changed paths.

## Update and Finalizer Semantics

`closeout-plan` does not decide success. `project-cognition update` does.

After the agent records the delta event or writes the payload file and runs update:

- `result_state=ready`: clean cognition closeout is allowed when ordinary verification also passed. If the runtime freshness contract permits, use the returned or documented finalizer path.
- `result_state=no_op`: clean closeout is allowed when no project-related mutation required runtime refresh.
- `result_state=partial_refresh`: report partial cognition closeout, returned `minimal_live_reads`, `known_unknowns`, and confidence notes. Do not call `complete-refresh`.
- `result_state=needs_rebuild`: report the rebuild condition and route to `sp-map-scan -> sp-map-build`. Do not call `complete-refresh`.
- `result_state=blocked`: report the blocker and recovery command. Use `mark-dirty` only if no useful update data was recorded.

`record-refresh` and `complete-refresh` remain explicit runtime finalizers. The closeout partial should not imply that source changes committed after an update require a full rebuild by themselves.

## Error Model

`closeout-plan` should return machine-actionable states:

```text
status=ok
status=blocked
status=error
```

Recommended `next_action` values:

```text
no_op
draft_update
fill_required_agent_fields
append_delta_then_update
write_payload_then_update
route_map_scan_build
mark_dirty_fallback
blocked
```

Blocked output must state the smallest recovery action:

- Git unavailable.
- Runtime status missing or unusable.
- Legacy runtime requires rebuild.
- Ignored path was explicitly supplied.
- Explicit path was invalid.
- Working tree has unsupported conflict status.
- Update payload cannot be safely drafted.

## Tests

Runtime tests:

- `closeout-plan` calls or mirrors `changes` behavior for committed, staged, unstaged, untracked, deleted, renamed, and explicit paths.
- Repairable `mark-dirty` state still produces a draft plan.
- Ignored paths appear only in `ignored_paths` and never in `payload_draft.changed_paths`.
- Unknown paths appear in `unknown_path_dispositions`, not as automatic payload `known_unknowns`.
- `unknown_path_dispositions[]` items include `path`, `change_level`, `allowed_dispositions`, `agent_disposition`, `required_agent_decision`, and `planner_reason`.
- Unknown path disposition tests cover `adoptable`, `review_only`, `ignored`, and `blocking_known_unknown`.
- Verified adoptable unindexed paths can still produce a ready update path and must not be blocked merely because they were initially unknown.
- Only `blocking_known_unknown` dispositions become payload or delta known unknowns.
- `needs_rebuild` and legacy runtime states do not draft normal update payloads.
- `blocked` states include actionable recovery fields.
- Planner output is stable when no changes exist.
- Active delta-session input produces `update_mode=delta_session`, `delta_append_command`, and a delta-session `update_command`.
- No active delta session produces `update_mode=payload_file`, `payload_path`, `payload_draft`, and a payload-file `update_command`.
- Workflow aliases such as `implement`, `sp-implement`, and `/sp.implement` normalize to canonical `sp-implement` in output, payload drafts, and records.

CLI tests:

- Root help lists `closeout-plan`.
- `closeout-plan --format json` emits `payload_draft`, `required_agent_fields`, `recommended_next_command`, and `finalizer_policy`.
- `closeout-plan --delta-session <id> --format json` emits `update_mode=delta_session`, `delta_append_command`, and `update_command`.
- Invalid explicit paths return blocked JSON, not partial payloads.
- Runtime compatibility checks require `closeout-plan` after release.

Template tests:

- `inline-project-cognition-update.md` mentions `project-cognition closeout-plan --workflow`.
- The partial requires filling `required_agent_fields` before `update`.
- The partial preserves the existing delta-session closeout path when the planner returns `update_mode=delta_session`.
- The partial passes an existing `DELTA_SESSION_ID` into `closeout-plan` instead of forcing payload-file mode.
- The partial writes a payload file only when the planner returns `update_mode=payload_file`.
- The partial requires unknown path disposition before payload or delta update recording.
- The partial gates clean completion on `result_state`.
- The partial keeps `mark-dirty` as fallback only.
- `sp-map-update` guidance does not perform duplicate `workflow-finalize` closeout after it has already recorded and finalized a `map-update` update for the same changed paths.
- Existing workflow-generated skill/command tests still see one shared inline closeout contract, not duplicated per-workflow algorithms.

Documentation tests:

- README, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md` describe closeout planner as the ordinary workflow-owned mutation closeout intake.
- Docs preserve the distinction between external `sp-map-update` and workflow-owned closeout.
- Docs preserve delta-session and payload-file closeout as supported update modes.

Release tests:

- Runtime binary support rejects cached/release binaries without `closeout-plan`.
- `vX.Y.Z` release assets must be verified for `project-cognition closeout-plan --help` when this command ships.

## Rollout

Implement in phases:

1. Add design and implementation plan.
2. Add `internal/closeout` planner package and CLI command.
3. Add Python runtime compatibility requirement for `closeout-plan` while retaining the existing `delta append --verification --generated-surface` requirement.
4. Update shared inline closeout partial and focused template tests.
5. Update README/handbook/template docs.
6. Run full project-cognition and template regression tests.
7. Publish a new release because `project-cognition` command surface changes.

This is deliberately planner-first. A later iteration may add an execution mode such as:

```text
project-cognition workflow-closeout --payload-file <agent-completed-payload> --format json
```

That later command should only execute after the first planner contract has proven stable.
