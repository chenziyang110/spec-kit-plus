# Inline Map Update Equivalence Design

**Date:** 2026-05-30
**Status:** Awaiting user review
**Owner:** Codex
**Related design:** `docs/superpowers/specs/2026-05-28-inline-project-cognition-closeout-design.md`

## Summary

Source-changing `sp-*` workflows must not finish by only recording changed
paths and leaving project cognition stale. When a workflow changes
project-related files or behavior, its inline project cognition update must
produce the same runtime effect that `sp-map-update` would produce for those
workflow-owned changes.

This design turns that requirement into two concrete changes:

- create one shared inline update prompt template and have source-changing
  workflows reference it instead of duplicating closeout wording
- make the lower-level `project-cognition update` path share the same update
  engine and persistence semantics as `sp-map-update`

The user-facing rule is simple: after an `sp-*` workflow changes requirements,
code, templates, tests, config, generated assets, state contracts, or
behavior-bearing docs, inline map update is not a lightweight path log. It is
the workflow-local form of `sp-map-update`.

## Problem

The current guidance says workflows should run inline project cognition update,
but the runtime can still produce a recorded-only result.

Current runtime evidence:

- `tools/project-cognition/internal/update/state.go` records changed paths and
  marks status stale or blocked.
- The delta-session path is still boundary-oriented and returns empty affected
  graph data.
- `tools/project-cognition/internal/store/store.go` hardcodes
  `affected_nodes_json`, `affected_claims_json`, and `affected_slices_json` to
  empty arrays with `result_state="recorded"`.
- A real downstream run produced an update id and changed path list, but no
  affected nodes, claims, slices, or refreshed `path_index` coverage.

That behavior is not equivalent to `sp-map-update`. It creates a durable
breadcrumb, but it does not refresh the map enough for the next workflow to rely
on the runtime state as updated.

There is also a prompt-maintenance problem. Inline closeout language appears in
multiple partials, passive skills, integration addenda, and tests. That makes it
easy for one generated surface to drift back toward "record and tell the user to
run map-update later."

## Goals

- Make inline update strongly equivalent to `sp-map-update` for
  workflow-owned changed paths and affected surfaces.
- Use one shared generated prompt template for inline update closeout semantics.
- Keep `sp-map-update` as the external/manual entrypoint for user edits,
  interrupted workflow repair, explicit map maintenance, and follow-up repair.
- Ensure a successful inline update writes meaningful affected graph data, path
  adoption, status freshness, and validation results.
- Ensure partial or blocked inline updates are reported as partial or blocked,
  not as clean project cognition completion.
- Preserve live code, tests, scripts, config, and authoritative docs as the
  proof source. Project cognition remains navigation and memory, not proof.

## Non-Goals

- Do not run `sp-map-scan -> sp-map-build` for ordinary changed-path refresh
  when a usable baseline exists.
- Do not re-enter the generated `sp-map-update` command from every workflow.
  Workflows call the shared lower-level update engine.
- Do not absorb unrelated pre-existing dirty user changes into the workflow's
  inline update.
- Do not make artifact-only planning workflows rewrite cognition content just
  because they wrote feature artifacts.
- Do not treat ignored, vendored, generated, or nested-reference paths as graph
  evidence when `.cognitionignore` excludes them.

## Terms

**Strong equivalence** means inline update and `sp-map-update` share the same
lower-level engine, DB writes, path adoption logic, validation semantics, and
status outcomes for the same changed paths and evidence. They do not need the
same command UI.

**Workflow-owned changed paths** are files changed by the active workflow after
its start boundary. They exclude unrelated user changes that existed before the
workflow or landed outside the workflow's ownership.

**Affected closure** is the graph and evidence surface that must be refreshed
because of the changed paths. It includes directly owned nodes plus relevant
claims, slices, owners, consumers, routes, generated surfaces, state contracts,
verification evidence, known unknowns, and minimal live reads.

**Recorded-only update** is a legacy or failure-class result that stores changed
paths without refreshing affected graph content. It must not be treated as
successful inline closeout.

## Design

### 1. Shared Inline Update Template

Add a shared command partial:

```text
templates/command-partials/common/inline-project-cognition-update.md
```

This partial owns the generated workflow language for mutation closeout. It
defines:

- when inline update is required
- how to identify workflow-owned changed paths
- what ledger evidence to pass to the updater
- the supported command shapes for delta-session and changed-path update
- how to interpret `ready`, `partial_refresh`, `needs_rebuild`, `blocked`, and
  no-op outcomes
- the rule that `update_id` alone is not success
- the fallback rule for `mark-dirty`
- the role boundary between inline update and external `sp-map-update`

Source-changing workflows reference this partial instead of carrying bespoke
copies of the same text. Integration-specific addenda, including the shared
integration base and Cursor-specific generated output, must consume the same
source text. Tests assert that those rendered outputs do not drift from the
shared contract.

### 2. Workflow Inclusion

The shared inline update partial is mandatory for workflows that normally edit
source or behavior:

- `sp-fast`
- `sp-quick`
- `sp-implement`
- `sp-debug`

It is conditional for workflows that are usually artifact-only but may mutate
project surfaces in this repository or downstream projects:

- `sp-specify`
- `sp-clarify`
- `sp-deep-research`
- `sp-plan`
- `sp-tasks`
- `sp-analyze`

Worker prompts that can make implementation edits must also carry the same
closeout requirement in their handoff contract. Passive routing skills should
point to the shared rule instead of restating a weaker variant.

### 3. Shared Runtime Engine

`project-cognition update` and the map-update workflow use the same runtime
update service. The generated workflow still calls the lower-level command, but
the lower-level command no longer performs a recorded-only write.

The engine accepts:

- changed paths and scope paths
- delta-session events
- optional safe commit range for boundary resolution
- workflow name or reason
- affected behavior surfaces
- verification evidence
- known unknowns and confidence notes

The public CLI contract must expose those inputs. Existing
`--changed-path`, `--scope`, `--reason`, `--delta-session`, and
`--commit-range` flags are not enough for strong-equivalence closeout because
they cannot carry behavior surfaces, verification evidence, known unknowns, or
confidence notes.

The engine performs:

1. Normalize changed paths and apply `.cognitionignore`.
2. Separate workflow-owned paths from pre-existing dirty paths when a boundary
   is available.
3. Resolve the affected closure from `path_index`, graph edges, claims, slices,
   generated surfaces, route contracts, and delta-session evidence.
4. Classify each changed path as adopted, reviewed, ignored, ambiguous,
   unadoptable, or requiring rebuild.
5. Update graph evidence and path coverage for adoptable paths.
6. Record partial facts, low-confidence facts, known unknowns, and minimal live
   reads for uncertain closure.
7. Persist an `updates` row with meaningful affected node, claim, and slice
   data.
8. Run the same readiness and validation checks that `sp-map-update` uses
   before claiming a clean refresh.
9. Publish status with the correct freshness, readiness, result state, and next
   action.

The non-delta path and delta-session path must converge on this engine. Delta
sessions improve boundary and evidence quality; they must not force a weaker
boundary-only update.

### 4. Non-Delta Input Contract

Add `project-cognition update --payload-file <json>` as the canonical non-delta
input path. Generated workflows may use either:

```text
project-cognition update \
  --delta-session "$DELTA_SESSION_ID" \
  --reason workflow-finalize \
  --format json
```

or:

```text
project-cognition update \
  --payload-file ".specify/project-cognition/updates/<update-id>.json" \
  --reason workflow-finalize \
  --format json
```

The old path-only shape remains a compatibility interface:

```text
project-cognition update \
  --changed-path "<path>" \
  --scope "<affected-scope>" \
  --reason workflow-finalize \
  --format json
```

For source-changing workflow closeout, the compatibility path is not enough to
claim strong equivalence unless the engine can prove the complete affected
closure from live runtime state alone. When evidence beyond paths exists, the
workflow must either append it to a delta session before final update or write a
payload file.

The payload file has this minimum schema:

```json
{
  "workflow": "sp-implement",
  "reason": "workflow-finalize",
  "changed_paths": ["src/example.ts"],
  "scope_paths": ["src"],
  "behavior_surfaces": ["API route contract"],
  "generated_surfaces": ["generated command output"],
  "state_contracts": ["workflow-state project_cognition_refresh"],
  "verification": [
    {
      "command": "bun run verify",
      "result": "passed",
      "artifact": "artifacts/quality-runs/example/report.md"
    }
  ],
  "known_unknowns": ["live baseline timed out"],
  "confidence_notes": ["path adoption is provisional until validate-build"],
  "user_decisions": ["inline update must be map-update-equivalent"],
  "boundary": {
    "commit_range": "base..head",
    "initial_dirty_paths": [],
    "workflow_owned_paths": ["src/example.ts"]
  }
}
```

Implementations may add fields, but they must preserve the minimum names above
so generated prompt templates, fake runtimes, and tests can share one contract.

### 5. Persistence Semantics

`RecordUpdate` evolves from a three-field helper into a structured update write.
It must accept affected graph ids, result state, path accounting, confidence
metadata, verification references, known unknowns, and minimal live reads.

For a meaningful update, the `updates` row must not hardcode empty affected
arrays. Empty affected arrays are allowed only when all changed paths are
ignored, the update is a no-op, or the result explicitly records why no graph
surface can be affected.

For adopted paths, `path_index` must be inserted or updated with the active
generation, relation, confidence, evidence id, and fresh `updated_at`. If a path
cannot be safely adopted, the update records why and returns the smallest live
read set needed to continue without pretending the map is fresh.

### 6. Result States

Inline update returns one of these closeout states:

- `ready`: affected graph content and path coverage were refreshed, validation
  passed, status is fresh and ready, and the workflow may claim project
  cognition closeout complete.
- `no_op`: no graph-relevant paths remained after ignore and ownership
  filtering; the workflow may complete if ordinary verification passed.
- `partial_refresh`: useful update data was written, but affected closure still
  has ambiguity, missing coverage, low-confidence facts, or required live reads.
  The workflow must report partial cognition closeout and cannot describe the
  project cognition state as clean.
- `needs_rebuild`: the runtime found a true rebuild condition, such as
  first/missing/unusable brownfield baseline, schema failure, zero active
  generation path index outside `greenfield_empty`, `explicit_rebuild_requested`,
  or `baseline_identity_invalid`.
- `blocked`: runtime state, validation, boundary resolution, DB access, or
  verification trust prevented a useful update.

`recorded` is not a successful closeout state. If legacy code still emits
`recorded`, generated workflows must treat it as blocked or partial until the
runtime is upgraded.

The runtime JSON contract must make this unambiguous:

- `UpdatePayload` gains `result_state` and `status_update` fields.
- `status_update` contains the status fields the command changed or preserved:
  `status`, `freshness`, `readiness`, `recommended_next_action`, `dirty`,
  `stale_paths`, `stale_reasons`, `last_update_id`, and
  `last_update_outcome`.
- `updates.result_state` stores the same value as `UpdatePayload.result_state`.
- `status.last_update_outcome` stores the same value as
  `UpdatePayload.result_state`; the existing `update_outcome` field remains only
  for boundary or compatibility diagnostics.
- Generated workflows key clean closeout on `result_state`, not on `update_id`
  or `readiness` alone.

Status mapping:

| `result_state` | `UpdatePayload.readiness` | `status.freshness` | `status.readiness` | `status.recommended_next_action` |
| --- | --- | --- | --- | --- |
| `ready` | `query_ready` | `fresh` | `query_ready` | `use_project_cognition` |
| `no_op` | current or `query_ready` | unchanged | unchanged | unchanged, or `use_project_cognition` if already ready |
| `partial_refresh` | `review` | `partial_refresh` | `review` | `review_project_cognition_update` |
| `needs_rebuild` | `needs_rebuild` | `stale` | `needs_rebuild` | `run_map_scan_build` |
| `blocked` | `blocked` | `stale` | `blocked` | `review_project_cognition_update` or a more specific recovery action |
| `recorded` | `blocked` or `review` | `stale` | `blocked` or `review` | `review_project_cognition_update` |

`no_op` must not clear unrelated pre-existing dirty state. `ready` clears only
the stale and dirty state that the update proves it refreshed.

### 7. Workflow Closeout Behavior

For source-changing workflows, option A is the product contract:

- `ready` or `no_op` allows normal completion when ordinary tests and quality
  gates also pass.
- `partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded` prevents
  a clean completion claim.
- The workflow may say implementation work is done, but its final state must
  clearly name the cognition closeout issue, evidence files, and exact recovery
  command.
- `mark-dirty` is used only when inline update cannot record useful update
  data, cannot identify workflow-owned scope, or cannot be trusted because
  verification/workflow completion is not trustworthy.

This fixes the downstream failure mode where an `sp-implement` closeout says it
updated project cognition but actually left only a changed-path record and a
blocked readiness state.

### 8. `sp-map-update` Role

`sp-map-update` remains the user-invoked maintenance workflow for:

- manual user edits outside an active workflow
- interrupted workflows that missed closeout
- explicit operator map maintenance
- follow-up repair after partial or blocked inline update
- ordinary existing-baseline gaps discovered outside workflow-owned mutation

It calls the same update engine, but it owns a different interaction pattern:
operator review, external changed-path discovery, manual corrections, and
follow-up maintenance. Inline update is the same effect applied at workflow
closeout with better local evidence.

`templates/commands/map-update.md` must explicitly build a payload or delta
session and call the lower-level helper:

```text
project-cognition update \
  --payload-file ".specify/project-cognition/updates/<map-update-id>.json" \
  --reason map-update \
  --format json
```

After that helper returns, `sp-map-update` runs validation and freshness
finalization based on `result_state`. It must not describe agent-side direct DB
or runtime-record edits as a complete map update unless those edits happen
through the shared helper. Tests must assert that the map-update template calls
the same helper path as inline update.

### 9. Required Surface Changes

Implementation planning must cover these surfaces or include an explicit
stand-down note explaining why a listed surface is unaffected:

- Runtime CLI: `tools/project-cognition/internal/cli/cli.go` adds
  `--payload-file` for `project-cognition update` and emits `result_state`.
- Runtime update engine: `tools/project-cognition/internal/update/**` converges
  delta and non-delta update paths on one strong-equivalence engine.
- Runtime store/schema: `tools/project-cognition/internal/store/**` supports
  structured update writes, affected graph fields, path adoption metadata, and
  any schema compatibility needed for old rows.
- Delta and boundary inputs: `tools/project-cognition/internal/delta/**` and
  `tools/project-cognition/internal/boundary/**` normalize sessions, payloads,
  commit ranges, and dirty-start boundaries into the shared engine input.
- Runtime validation and gates:
  `tools/project-cognition/internal/validation/**`,
  `tools/project-cognition/internal/buildgate/**`, and
  `tools/project-cognition/internal/runtimegate/**` participate in the
  `result_state` decision.
- Shared partial:
  `templates/command-partials/common/inline-project-cognition-update.md`.
- Workflow templates:
  `templates/commands/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze,map-update}.md`.
- Workflow shell partials:
  `templates/command-partials/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze}/shell.md`
  where those partials contain closeout wording.
- Worker prompts:
  `templates/worker-prompts/{quick-worker,implementer,debug-investigator,debug-thinker,code-quality-reviewer,spec-reviewer}.md`
  when the worker can mutate project-related files.
- Passive skills:
  `templates/passive-skills/spec-kit-project-cognition-gate/`,
  `templates/passive-skills/spec-kit-workflow-routing/`,
  `templates/passive-skills/subagent-driven-development/`, and any passive
  skill that repeats inline update closeout semantics.
- Integration rendering: `src/specify_cli/integrations/base.py`,
  `src/specify_cli/integrations/cursor_agent/__init__.py`, and generated-output
  tests under `tests/integrations/**`.
- Fake/runtime test fixtures: `tests/project_cognition_fake.py` and Go tests
  under `tools/project-cognition/internal/**`.
- Documentation: `README.md`, `PROJECT-HANDBOOK.md`,
  `templates/project-handbook-template.md`, `docs/quickstart.md`, and
  `docs/installation.md`.
- Alignment tests: `tests/test_alignment_templates.py`,
  `tests/test_command_surface_semantics.py`, and targeted tests that assert no
  surface treats `recorded` or `update_id` alone as clean closeout.

### 10. Tests

Implementation must include regression coverage for:

- Go runtime: `project-cognition update` populates affected graph fields and
  does not emit recorded-only success for graph-relevant changed paths.
- Go runtime: delta-session and non-delta update paths converge on the same
  result semantics.
- Go runtime: adopted paths update `path_index`; ambiguous paths return
  `minimal_live_reads` and partial state.
- Go runtime: ignored paths stay out of graph evidence and can produce no-op.
- Go runtime: rebuild conditions route to `needs_rebuild` without using
  map-scan/build for ordinary existing-baseline gaps.
- Go runtime: `UpdatePayload.result_state`, `updates.result_state`, and
  `status.last_update_outcome` use the same value.
- Go runtime: non-delta strong-equivalence closeout requires `--payload-file`
  unless complete closure is provable from live runtime state alone.
- Map-update template: `sp-map-update` calls `project-cognition update` through
  the shared helper before validation and freshness finalization.
- Template alignment: source-changing workflows include the shared inline
  update partial.
- Integration output: shared base and Cursor-specific addenda carry the same
  strong-equivalence rule.
- Documentation: README, handbook, quickstart, installation docs, and passive
  skills describe inline update as map-update-equivalent rather than
  recorded-only.
- Fake runtime fixtures: tests that currently simulate project cognition update
  must distinguish `ready`, `partial_refresh`, `needs_rebuild`, and `blocked`.

## Acceptance Criteria

- Generated `sp-*` workflows have one shared inline update contract instead of
  multiple drifting copies.
- A source-changing workflow cannot treat `last_update_id` or
  `result_state="recorded"` as clean project cognition closeout.
- Non-delta strong-equivalence closeout has a canonical
  `project-cognition update --payload-file <json>` input path; path-only update
  cannot cleanly complete unless closure is provable from runtime state alone.
- `sp-map-update` calls the same lower-level `project-cognition update` helper
  before validation and freshness finalization.
- `UpdatePayload.result_state`, `updates.result_state`, and
  `status.last_update_outcome` agree for every completed update attempt.
- `project-cognition update` writes affected node, claim, or slice data when a
  graph-relevant changed path has an affected closure.
- Adoptable changed paths update active-generation path coverage.
- A clean inline update publishes fresh/ready status through the same semantics
  used by `sp-map-update`.
- Partial inline update records useful cognition data and blocks clean closeout
  until repaired, waived by an explicit maintainer policy, or followed by
  `sp-map-update`.
- True rebuild conditions still route to `sp-map-scan -> sp-map-build`, while
  ordinary existing-baseline gaps stay in update.

## Compatibility

Existing recorded-only update rows remain historical facts. New code must not
reinterpret those rows as ready refreshes. When reading older rows, workflows and
runtime diagnostics should surface them as partial, blocked, or legacy recorded
state unless a later ready refresh supersedes them.

Generated projects that do not yet have the upgraded runtime still receive the
shared prompt contract. If their runtime returns legacy `recorded`, the prompt
contract tells the agent to report partial or blocked closeout instead of
claiming success.

## Self-Review Notes

This design intentionally supersedes the weaker interpretation of the
2026-05-28 closeout design. The earlier design established that workflows own
inline closeout. This design adds the stronger requirement that inline closeout
must have `sp-map-update` effect, and that shared prompt text alone is
insufficient without runtime update-engine equivalence.
