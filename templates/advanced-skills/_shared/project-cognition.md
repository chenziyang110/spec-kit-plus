# Project cognition

Use project cognition as the default navigation layer, not as proof of current
behavior.

Reuse one cognition context capsule only while its exact task/query, workflow
intent/binding, target project, scope, required facets, negative constraints,
permissions, relevant live-source/evidence digests, and runtime identity remain
unchanged. Keep the original `expansion_ref.id`, `query_fingerprint`,
`active_generation_id`, `navigation_digest`, and contract versions with it;
claim revisions are covered by that navigation snapshot, including same-generation
changes. Before reusing a prior capsule for an unchanged phase pass, perform one
actual read-only `{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}`
using that ID and an available section such as `related_paths`. Require the
inner cognition payload's `status=ok`, usable `readiness=query_ready|review`,
`expansion_contract_version=2`, matching
ID, query fingerprint, active generation, and the advisory `epistemic_contract`.
A native outer exit code 0 alone is not proof. Missing, stale, incompatible,
invalid, or unsuccessful expansion disables reuse; follow its recovery action
and refresh supported intake or use live evidence within the workflow boundary.

A verified capsule does not restart Compass or Learning after each preparatory
capability/API, artifact query, script dry run, or board call. These calls alone
also do not require another Expand check. Refresh on target, task/query, intent,
scope/facet, constraint, permission, runtime, relevant source/evidence, generation,
status, or claim-revision drift, contradictory evidence, and required resume or
recovery gates. Preserve live verification and mutation-closeout freshness.
Learning reuse separately requires unchanged applicable lessons, Learning
index/source evidence, and project rules; a graph digest does not prove Learning
unchanged. If relevant lessons/rules drift or their applicability cannot be
confirmed, repeat the owning read-only Learning start/list/show intake.

Before using snapshot reuse, claim-evidence paging, or catalog continuation,
require their respective capability IDs: `cognition.expansion.snapshot.v2`,
`cognition.claim-evidence.page.v1`, and `cognition.catalog.snapshot.v1`. Verify
only the needed set once with
`{{specify-subcmd:specify-runtime api ensure --capabilities <comma-separated-capability-ids> --format json}}`;
reuse its proof while runtime identity is unchanged. Older runtimes may fall back
once to `api list`. Missing capability disables the affected route; use supported
fresh Compass/live evidence instead of assuming newer contracts. These IDs are
capabilities, not CLI commands.

Archived specifications are excluded from default discovery and are never
current authority. Read one only for explicit lineage or provenance, identify
the exact historical claim, and verify it against current live evidence before
use. An archive cannot override the live repository, an active approved
contract, or confirmed user direction.

If the active workflow cannot safely continue after permitted self-recovery,
read `references/blocker-resolution.md` before returning a blocked result.

## Intake

The only entry-intake exception is an explicitly selected context-direct branch
from `spx-quick` or `spx-debug`. Its pre-intake gate already enumerated the
bounded owner, consumers, risks, and verification evidence from the active
conversation, so it skips Compass navigation. It still uses this reference's
exact-path mutation closeout contract after source changes. Insufficient
evidence, a full-workflow choice, or scope expansion restores normal intake.

When no valid unchanged capsule is available, run
`{{specify-subcmd:specify-runtime cognition compass --intent <intent> --query="<request>" --format json}}`,
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
- When `compass_state=blocked`, `degraded=true`, and
  `coverage_diagnostics[].kind=stale_cognition_degraded_navigation`, consume the
  returned bounded `minimal_live_reads` only as stale route hints. Verify every
  selected path against the live repository, never treat the hints as fresh
  truth, and preserve the returned recovery action. Without that marker, do not
  infer routes from an empty blocked packet.
- Follow `expansion_ref` only when coverage or contradictory live evidence requires more map detail.
  Use its `expansion_ref.id` as `<id>` and one required key from
  `expansion_ref.available_sections` as `<section>`:
  `{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}`.
  A missing, stale, or invalid expansion is not fresh evidence; follow its
  returned recovery action before reusing the affected route.
- Escalate to lexicon, agent-authored semantic intake, and a precise
  `{{specify-subcmd:specify-runtime cognition query --intent <intent> --query-plan <query-plan-json> --format json}}`
  only for unresolved terminology, multilingual intent, or material coverage
  gaps.
- `query` is an exact binding consumer, not a natural-language search endpoint.
  Never submit only `--query`, `raw_query`, `normalized_query`, or rewritten search
  words. Inspect catalog semantic cards and bind exact current `concept_id` values
  in `selected_concepts` with the same `lexicon_generation_id`, or exact paths.
  Stop catalog paging only when every required facet has a valid binding and live
  evidence: owners, necessary consumers/dependencies, verification routes, and
  negative constraints, with ambiguity/conflicts resolved and `missing_facets`
  empty. The first word match or one bound owner is insufficient. Otherwise,
  while `catalog_page.has_more=true`, execute `catalog_page.next_argv` exactly;
  keep its `revision`, `navigation_digest`, and `snapshot_bound` proof and the
  `offset`, `limit`, `returned`, and `total` accounting. The project launcher may
  replace only argv's executable; do not reconstruct `--offset`, `--catalog-revision`,
  query, intent, or other continuation flags. A stale catalog/expansion requires
  fresh intake rather than combining pages from different snapshots. Do not
  claim no match or complete coverage until the relevant pages are exhausted;
  preserve unresolved terminology, missing facets, and index gaps as
  `insufficient_index`. `resolution_state=resolved_exact` proves binding only;
  `binding_required`, `invalid_binding`, and `stale_binding` require repair.

  For required claim details, use the selected expansion's `claim_evidence`
  section. Preserve `total_count`, `returned_count`, `offset`, and `has_more`,
  including exact zero counts; follow its `next_argv` exactly while needed.
  The full risk summary remains binding even when details are paged; returned
  claims are not the whole denominator. Never rebuild continuation flags, infer
  absent metadata as zero, or treat paging as live proof or write permission.
- Treat graph claims as route candidates. The live repository, tests,
  configuration, runtime output, and authoritative docs establish facts.

For UI work, use the same intake to locate likely real entry points,
token/theme/component owners, reusable patterns, required states, responsive
rules, visual/accessibility tests, and reference assets. Carry only verified
live routes into the plan context capsule; do not add a UI-specific cognition
runtime or treat a graph owner label as proof.

`baseline_kind=greenfield_empty` is advisory only while the repository has no
project-code evidence. If the runtime reports
`greenfield_baseline_has_project_code`, real workflow-owned or stale paths have
invalidated that identity. Preserve
`recommended_next_action.action_id=project_cognition.rebuild` and its Advanced
workflow route; this conflict must not be routed to `$spx-map-update` or treated
as an ordinary empty graph.

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

## Triggered contracts


Compass, semantic intake, and graph evidence select bounded routes; they do not
authorize source edits or a final claim. The owning workflow still decides its
write boundary from live evidence and its own stage contract.

Read only the reference whose trigger applies; installing a reference does not
make it part of every intake.

- Before semantic routing affects permission, source-write scope, resume, or a
  root-cause, fixed, completed, or release-safe claim, read
  [semantic audit and resume](project-cognition-semantic-audit.md). On resume,
  read it before reusing any persisted semantic route or `claim_ready`.
- Before an owning mutation workflow changes project source, runtime, templates,
  generated assets, config, tests, state contracts, or behavior-bearing docs,
  read [mutation closeout and recovery](project-cognition-closeout.md). Also read
  it when resuming unfinished closeout, a blocked queued intent, or predecessor
  recovery. Entry-time advisory navigation never waives this closeout gate.
  Planning-only artifacts and read-only answers do not trigger mutation closeout.

These references preserve the owning workflow's authorization and final-claim
gates; neither cognition navigation nor recovery advice enters another workflow.

## Exact Task Scope Availability

After the owning runtime compiles the canonical current task packet, and before
dependent graph consumption, require `specify-runtime api ensure --capabilities
cognition.scope-availability.v2 --format json`, then run `specify-runtime cognition
check --task-packet <exact-project-relative-packet-path> --format json`. Use the
compiler's returned packet path; do not assemble a substitute packet or infer
complete read dependencies from prose. Quick confirmation items declare optional
`read_scope` as an explicit array of exact paths, including required UI contract
and original reference inputs when applicable. Missing legacy `read_scope` is
unknown; explicit `[]` is a complete empty declaration. Null, non-arrays and
non-string paths refuse. Read metadata follows execution `write_scope` digest
exclusion; it never changes registered UI approval or grants worker write scope.

Carry native `availability`, `scope_ready`, `global_status`, `debt_assessments`,
`reasons`, `minimal_live_reads` and `binding` separately. Only an actual version 2
ready result permits scoped advisory graph navigation; proven unrelated debt
remains visible globally. Blocked/degraded/unavailable or unknown proof suspends
dependent graph consumption and uses bounded current live reads, with gaps
explicit. Do not erase blocked results or treat advisory warnings as uniform
protection. Commands without a canonical packet keep the global check and cannot
assert unrelated debt. This route applies with hooks and without hooks on every
CLI and both profiles.

At handoff/resume and before reusing graph context, rerun the same native check
with `--availability-json <previous-native-binding-json>` against the current
canonical packet. Changed source/packet/status/dependency/claim bytes or an old
contract invalidate reuse; repair the owning proof and obtain a new result. Scope
readiness never declares the project globally fresh, grants source write
authority, sets workflow `claim_ready`, or replaces independent Review and human
Accept. Preserve normal packet/Work/UI prerequisite and approval gates.
