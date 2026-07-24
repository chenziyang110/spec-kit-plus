# Project cognition

Use project cognition as the default navigation layer, not as proof of current
behavior.

Archived specifications are excluded from default discovery and are never
current authority. Read one only for explicit lineage or provenance, identify
the exact historical claim, and verify it against current live evidence before
use. An archive cannot override the live repository, an active approved
contract, or confirmed user direction.

If the active workflow cannot safely continue after permitted self-recovery,
read `references/blocker-resolution.md` before returning a blocked result.

## Intake

Run `{{specify-subcmd:specify-runtime cognition compass --intent <intent> --query="<request>" --format json}}`,
using the intent named by the active skill. This placeholder resolves to the
project-pinned cognition binary during installation. If it instead resolves to
an all-caps unavailable-launcher marker, treat that token as a non-executable
status marker: do not run it and do not probe "specify cognition" or
"specify project-cognition". Run
`{{specify-subcmd:specify-runtime doctor --format json}}` for the project-local
binding diagnosis. If it reports `bootstrap_required`, stop at that human-owned
bootstrap boundary; never invoke `uvx`, Python `specify`, or a user-level
runtime from the agent workflow. Re-open this installed reference after the
human repair; if the marker remains, report cognition unavailable and navigate
from live repository evidence within the active skill's safety boundary.

When cognition is available, consume only what helps the task:
`epistemic_contract`, `minimal_live_reads`, lane `first_pass_paths`,
`coverage_diagnostics`, `expansion_ref`, and the structured recovery contract.

Treat `recommended_next_action` as an object. Do not treat
`recommended_next_action` as a string. Read
`recommended_next_action.action_id` for every packet; workflow routes are
present only when the action requires a workflow handoff. A
`readiness=needs_rebuild` packet can still own a resumable action such as
`complete_scan_packets`; never route from readiness alone. Only when
`recommended_next_action.action_id=project_cognition.rebuild`, inspect every
entry in `rebuild_reasons[]`, report its stable `code`, human-readable `message`,
and relevant `evidence`, then select the canonical Advanced steps from
`recommended_next_action.workflow_routes.advanced.steps`. The expected
Advanced route is `spx-map-rebuild`; use this installed integration's projected
invocation syntax when presenting the handoff. Do not guess a rebuild cause or
derive a route from readiness or a legacy action string. For every other action
ID, preserve that action and do not invent rebuild reasons or workflow routes.
When a non-workflow action includes `recommended_next_action.argv`, execute that
exact argv through the project-pinned cognition launcher. In particular,
`project_cognition.repair_status` owns the deterministic `repair-status` action;
do not rewrite graph-store metadata by hand.

- Read `minimal_live_reads` before broad repository search and use
  `first_pass_paths` to choose the next live evidence.
- Follow `expansion_ref` with
  `{{specify-subcmd:specify-runtime cognition expand --ref <expansion-ref> --format json}}`
  only when coverage or contradictory live evidence requires more map detail.
- Escalate to lexicon, agent-authored semantic intake, and a precise
  `{{specify-subcmd:specify-runtime cognition query --intent <intent> --query-plan <query-plan-json> --format json}}`
  only for unresolved terminology, multilingual intent, or material coverage
  gaps.
- Treat graph claims as route candidates. The live repository, tests,
  configuration, runtime output, and authoritative docs establish facts.

For UI work, use the same intake to locate likely real entry points,
token/theme/component owners, reusable patterns, required states, responsive
rules, visual/accessibility tests, and reference assets. Carry only verified
live routes into the plan context capsule; do not add a UI-specific cognition
runtime or treat a graph owner label as proof.

If `recommended_next_action.action_id=project_cognition.rebuild` and the
structured recovery contract names the Advanced rebuild route, recommend the matching maintenance skill,
`$spx-map-rebuild`. Recommend `$spx-map-update` for explicit maintenance,
external changes, or recovery of an interrupted incremental update. Do not
invoke `$spx-map-rebuild` or `$spx-map-update` from the active workflow; a
recovery handoff is not authorization to execute another workflow. For
`blocked` or partial results, report the specific recovery signal and continue
from live evidence only when the active skill's safety boundary permits it.
Never use `complete-refresh` to disguise an incomplete, blocked, or
rebuild-required state.

## State and delegation ownership

When the owning workflow has runtime-managed state, create or resume it before
substantive work, keep only resume-critical truth there, and validate its final
transition before handoff. Chat history and a terminal-looking artifact never
override durable state.

Delegation remains optional. When it is useful, the leader owns canonical
artifacts, global workflow state, acceptance, and final claims. Give workers
bounded inputs, paths, write scopes, acceptance, and return shape; worker
results are evidence, not authority to mutate global state. Persist the
runtime-required lane manifest and one result per delegated lane only when a
durable lane is actually created, do not duplicate runtime events into parallel
logs, and validate every join against fresh integrated evidence.

## Semantic permission, resume, and final claims

Compass, semantic intake, and graph evidence select bounded routes; they do not
authorize source edits or a final claim. The owning workflow still decides its
write boundary from live evidence and its own stage contract.

When semantic routing affects permission, source-write scope, resume, or a
root-cause, fixed, completed, or release-safe claim, persist
`semantic-audit-input.json` and `semantic-audit-output.json` beside the active
workflow state. Use the deterministic runtime rather than reconstructing its
stable schema:

`{{specify-subcmd:specify-runtime cognition semantic-audit --input <semantic-audit-input.json> --format json}}`

On resume, validate the persisted route, active claim, authorization refs, and
verification refs with:

`{{specify-subcmd:specify-runtime cognition semantic-audit-resume --input <resume-validation.json> --format json}}`

If either audit file is missing, stale, or inconsistent, do not reuse
`claim_ready`; rebuild the audit and keep the final claim blocked. A final claim
requires explicit `workflow_authorization` for that claim plus claim-specific
passed verification whose evidence refs match the authorization. Failed,
blocked, skipped, or inconclusive evidence cannot be promoted. Semantic audit
does not authorize source edits, external writes, or a higher permission level;
resume validation grants none of them either. The active SPX workflow remains the owner of those
decisions. If the audit runtime is unavailable, preserve the same evidence and
authorization boundary in workflow state and stay at the lower safe permission;
never infer readiness from chat memory or graph confidence.

## Closeout after repository changes

Only an owning mutation skill may perform cognition closeout. Its `SKILL.md`
provides the exact registry-owned `sp-*` workflow literal and
`specify-runtime cognition closeout-plan` command;
never derive that ID from the SPX skill name, an environment variable, or chat
state. Pass explicit workflow-owned changed paths, fill only the returned
agent-owned evidence fields, then execute the structured `update_argv`. Set
every `unknown_path_dispositions[].agent_disposition`; the runtime binds it to
the matching `path_changes[].disposition`, and missing, duplicate, conflicting,
or unmatched decisions fail before mutation. Delta mode must supply every
returned `--path-disposition` placeholder. An
ignored disposition remains in audit-only `path_changes`, but it must not enter
graph-changing `changed_paths` or create graph adoption/reconciliation records. If its
first two tokens are the bare `specify-runtime cognition` namespace, replace
only those tokens with `{{specify-subcmd:specify-runtime cognition}}` and preserve
every remaining argv token exactly; command strings marked display-only are not
executable instructions. If the update cannot complete, leave freshness
truthful and report the recovery action.

For delta mode, every passing verification argument must use the structured
planner shape `{"command":"<agent-owned verification command>","result":"passed","artifact":"<optional evidence artifact>"}`;
never pass freeform command-result strings or result aliases. Legacy or
free-text verification is audit evidence with `result=recorded` only and cannot
satisfy clean closeout; clean closeout requires structured `result=passed`.
After `update_argv`,
`result_state=ready` or `result_state=no_op` must run
`{{specify-subcmd:specify-runtime cognition validate-build --format json}}`. Only
`status=ok` with `readiness=query_ready` creates the validate-build receipt
bound to the latest update ID, outcome, and active generation; then, and only
then, run `{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}`.
Clean completion requires that receipt-bound finalizer to succeed. For
the interval before it succeeds, the runtime gate withholds Compass/query as
pending finalization. For
`partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`, the skill
must not run `complete-refresh`; preserve the truthful state and returned
recovery action. A failed, stale, blocked, or non-`query_ready` validation also
must not run `complete-refresh`.

Specification, plan, task, checklist, research, and other planning-only artifact
changes do not make the code map dirty and do not require cognition closeout.
