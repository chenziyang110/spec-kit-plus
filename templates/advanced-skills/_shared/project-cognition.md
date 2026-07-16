# Project cognition

Use project cognition as the default navigation layer, not as proof of current
behavior.

If the active workflow cannot safely continue after permitted self-recovery,
read `references/blocker-resolution.md` before returning a blocked result.

## Intake

Run `{{specify-subcmd:project-cognition compass --intent <intent> --query="<request>" --format json}}`,
using the intent named by the active skill. This placeholder resolves to the
project-pinned cognition binary during installation. If it instead resolves to
an all-caps unavailable-launcher marker, treat that token as a non-executable
status marker: do not run it and do not probe "specify cognition" or
"specify project-cognition". Run `{{specify-subcmd:check}}` for the pinned
project diagnosis, then use `{{specify-subcmd:integration repair}}` as the
deterministic runtime recovery entry. Re-open this installed reference after
repair; if the marker remains, report cognition unavailable and navigate from
live repository evidence within the active skill's safety boundary.

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
  `{{specify-subcmd:project-cognition expand --ref <expansion-ref> --format json}}`
  only when coverage or contradictory live evidence requires more map detail.
- Escalate to lexicon, agent-authored semantic intake, and a precise
  `{{specify-subcmd:project-cognition query --intent <intent> --query-plan <query-plan-json> --format json}}`
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

`{{specify-subcmd:project-cognition semantic-audit --input <semantic-audit-input.json> --format json}}`

On resume, validate the persisted route, active claim, authorization refs, and
verification refs with:

`{{specify-subcmd:project-cognition semantic-audit-resume --input <resume-validation.json> --format json}}`

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

After verifying changes to source, runtime, templates, configuration, tests, or
generated behavior, run
`{{specify-subcmd:project-cognition closeout-plan --workflow <canonical-sp-workflow> --intent <intent> --format json}}`.
Fill the returned agent-owned evidence fields, then execute the structured
`update_argv`. If its first token is the bare `project-cognition` name, replace
only that first token with `{{specify-subcmd:project-cognition}}` and preserve
every remaining argv token exactly; command strings marked display-only are not
executable instructions. If the update cannot complete, leave freshness
truthful and report the recovery action.

Specification, plan, task, checklist, research, and other planning-only artifact
changes do not make the code map dirty and do not require cognition closeout.
