# Quick task contract

Keep one resumable truth surface in `STATUS.md` and one terminal account in
`SUMMARY.md`. Create `STATUS.md` through `artifact scaffold --kind quick-status`,
then mutate only targeted frontmatter/sections through leased `artifact patch`
calls. Create an absent terminal `SUMMARY.md` with `artifact scaffold --kind
quick-summary`, then patch only its named sections through fresh leases; query
and patch an existing summary on resume. Never submit, reconstruct, or directly
write either file.

`STATUS.md` must keep only information needed to resume safely:

- intent and observable acceptance;
- in-scope and explicitly excluded behavior;
- confirmed `ordered_work_items` with stable `Q1`, `Q2`, ... ids, deliverable-level dependencies, and one-to-one `work_item_acceptance`;
- current `work_item_status` and execution `batches` for safe ordered resume;
- expected or changed paths;
- current focus, next action, blocker, and material decisions;
- verification commands/results and remaining risk.

Its runtime-managed `test_design_gate` records exactly
`not_selected|selected|required` and a `projection_binding`. For
selected/required input, run `specify-runtime test-design projection-verify
[--feature-dir <feature-dir>] --projection-ref <project-relative-ref>
--expected-sha256 <sha256>` before reading the typed pointer-only selection.
Project scope omits `--feature-dir`. The projection and canonical Test Design
publication remain read-only: Quick must not patch, replace, weaken, or copy
their cases, data, coverage, gaps, or audit. Missing or stale selected input
routes to the independent `$spx-test-design` producer; it does not require a
completed Plan. `not_selected` has no fabricated projection binding.

Stage the user-owned decision first. The Quick projection basis is the
runtime-owned `.planning/quick/<id>/confirmation.json` produced by
`quick checkpoint-stage`, never the mutable `STATUS.md` that later receives the
`projection_binding`.

The user-facing checkpoint is the runtime-owned Decision Checkpoint in
`references/human-confirmation.md`, followed conditionally by its UI card.
Stage it with `specify-runtime quick checkpoint-stage`, render the staged
response's returned `views.decision`, bind approval with
`quick checkpoint-confirm --digest`, then use the confirmation response's
returned `views.delivery` for the initial Delivery Map. Reserve
`checkpoint-show --view pulse` for later pulse refreshes or explicit rerender.
Store user-owned decisions—including
ordered work items, dependencies, and work-item acceptance—and
`ui_confirmation` separately from Delivery Map / `agent_execution_plan`. One
reply confirms both cards when UI applies. The confirmed order is
deliverable-level. Internal implementation sequencing, lanes, and batches remain
agent-owned and never enter `confirmation_digest`. For registered design
adoption, `decision.ui_confirmation.design_binding` contains exact `scope`,
`design_change_id`, `design_change_ref`, `design_change_sha256`, and
`design_contract_ref` before confirmation. The digest therefore protects the
binding the user reviewed; the independent top-level `STATUS.md`
`ui_design_binding` adoption copy is patched only afterward and must exact-match
that confirmed decision.

An unconfirmed checkpoint blocks broad investigation, delegation,
implementation, and validation until runtime marks it confirmed or inherited.
A confirmed discussion handoff with no semantic delta stages as `inherited` and
skips re-confirmation; show the binding summary plus Delivery Map/Pulse instead.
For a semantic delta, keep the complete resulting decision for digest
validation and stage `source.kind=delta`, `source.delta_summary`, plus exact
`source.changed_decision_fields`. Runtime renders only those paths plus
necessary work-item or design-binding context; the display list never enters
the digest.

When Quick consumes a confirmed discussion handoff, first patch
the resolver's exact `discussion_slug` as `source_discussion_slug`, plus
`source_contract`, resolver-returned `review_digest`, resolver-returned
`state_sha256`, and resolver-returned `recommended_consumer` into `STATUS.md`
through leased `specify-runtime artifact patch` calls. Verify those five fields
before mark-consumed.
Then mark the source consumed with
`{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`;
the legacy option name accepts the Quick workspace, whose `STATUS.md` is the
required consumption evidence.

Do not reopen confirmation when repository evidence only adds files, call
sites, tests, or implementation detail needed for the same confirmed outcome
within the confirmed boundary, risk, and authority. Patch the affected
`STATUS.md` fields through a fresh `specify-runtime artifact patch` lease and continue.
Reopen only for a material change to outcome, boundaries, a confirmed work item,
deliverable-level order or dependency, work-item acceptance, confirmed UI
direction, user-visible behavior, risk, authority, migration or compatibility
obligations, an independent capability, or an explicit stop condition; first set
the checkpoint back to an unconfirmed staged decision and pause substantive work.

Before presenting the amendment, explain in user-facing prose the new evidence,
why the previous confirmation no longer covers the work, the consequence of
omitting it, the current mutation state and safe pause point, and the exact
incremental decision the user owns. Only after that explanation, present
`## Quick Checkpoint Amendment` by re-staging a delta Decision Checkpoint with
only the changed rows or decisions and an `Unchanged` statement; do not repeat
the full initial Quick Checkpoint. Persist the confirmed delta with
`checkpoint-confirm` before resuming, and do not request duplicate confirmation
when the user already approved that exact delta.

For a UI-only material delta, keep the Quick amendment heading, include only
the changed UI Confirmation fields. State that the main checkpoint is unchanged.
The reason-first explanation remains mandatory; do not replay either complete initial table.

Patch `STATUS.md` through its artifact CLI owner at scope changes, before/after
delegated joins, on blockers, and at terminal verification—not after every
command. Repository evidence may resolve
technical questions; ask the user only for product choices or authority the
repository cannot supply.

## Compact execution responses

In the full Quick branch, prefer compact responses after complete intake, not
instead of it. Reuse already loaded Help/Show/Pack metadata. When none is loaded,
replace the Skill's separate executor lookup with one
`{{specify-subcmd:specify-runtime api pack --capabilities quick.item-start,quick.allow-inline,quick.item-accept,quick.item-status --format json}}`.
If Pack is unavailable, use an available read-only Show/Help route or stay full;
optimization discovery must not block otherwise supported work. Reuse metadata
only under the same pinned runtime identity, not on the basis of a capability id.

For each operation independently, require its `output_contract` to advertise
`response_schema: quick-execution-compact-v1`, `flag: --compact`,
`flag_type: standalone_boolean`, `scope: response_presentation_only`,
`default: full`, `fallback: full`, `requires_full_intake: true`,
`mutates_canonical_state: false`, `binding_kind: decision_digest_not_file_hash`,
and exactly `omitted_fields: [confirmation, pulse]`. Missing, null, unknown or
conflicting support means omit the flag for that operation. This is independent
of `execution_contract`: compact output never authorizes leader-direct.

At entry/resume, read the complete current confirmation from the existing
checkpoint response or `quick item-status` without the flag. Keep its exact
project root, workspace, confirmation ref, decision digest and confirmed or
inherited state in the active context. Then append one standalone `--compact`
to negotiated item-start, allow-inline, item-accept and item-status calls while
that context is current; preserve all original selectors, evidence and Work
arguments. Never add it to checkpoint, packet-compile, result, close or archive.

Check the envelope status and blockers first. A compact success must match
`response_schema`, `confirmation_ref`, `confirmation_digest` and
`confirmation_state` to the current intake. Always consume the fresh packet,
`work_claim`, executor flags, `worker_proof` and queue fields when returned.
The digest binds decisions, not current write scope, execution state or authority;
never reuse those merely because the digest matches. Missing required receipts
still block execution. An ordinary full fallback is valid: consume it without
retrying to obtain compact output.

After context loss, a runtime change, binding mismatch, material amendment or
scope reconciliation, refresh through
`{{specify-subcmd:specify-runtime quick item-status <id> --format json}}`
without `--compact`, in the same project root. Reconcile before further writes;
a staged checkpoint still needs its normal confirmation. An unknown response or
ambiguous mutation outcome also requires status reconciliation, never automatic
replay of item-start, allow-inline or item-accept merely to change presentation.

Use returned progress for updates; do not fetch a full pulse after every compact
response. Request `checkpoint-show --view pulse` only when a human-readable
rerender is needed. No polling, new state file, repeated reference read or extra
per-item discovery is needed. Existing verification and terminal gates remain.

## Execution coordination and delivery

Use the event-driven coordination gate alongside those durable transitions:
run `specify-runtime execution overview --format json` before the first
`quick item-start`, after each join before selecting more work, and before
execution guard or material scope expansion. Keep `quick preflight` only as a
compatibility view. Resolve a confirmed
`write_overlap`; treat unfinished/untracked Quick and board-only signals as
advisory context and continue when their product intent and planned paths are
unrelated. Do not poll between these events.

Before `quick item-start`, bind the exact guarded Work/Activity id and fence
through matching `SPECIFY_WORK_ID` / `SPECIFY_WORK_FENCE` or
`--current-work-id` / `--current-work-fence`. Runtime verifies the
canonical `quick:<id>` or `quick:<id>#Qn` task ref and claims the selected Q
item's complete normalized `write_scope` all-or-none before changing the Q item
to `in_progress`. Dispatch only from the returned `work_claim` receipt and
matching execution guard. The
default Quick-level owner claims the active batch and workers inherit that
Quick-level Work authority rather than creating overlapping registrations.

Execute confirmed work items in dependency order through the owning Skill's
capability-negotiated hard Q loop. A supported low-risk, well-understood item
may select `quick item-start <id> --item Qn --leader-direct` before its first
start. Otherwise retain delegated `worker` execution. The returned task packet
and `work_claim` are required in both routes; `requires_worker: false` is not
write authority. Start returns its compiled packet, so a separate
`packet-compile` is optional preview/refresh, not repeated dispatch boilerplate.
Direct execution is distinct from the no-workspace context-direct intake branch:
it preserves the full confirmed Quick workspace, task graph and closeout.

Both normal routes submit one matching result through `result submit --command
quick --lane-id Qn` and then `quick item-accept --item Qn --evidence ...`.
Direct results require non-empty passed `validation_results`, empty blockers,
and all existing scope, identity, reuse and source-continuity checks. Legacy
`quick allow-inline --reason` remains only for real delegated spawn/tool failure;
it cannot waive direct proof. Close requires every item accepted with an audited
`worker`, `leader-direct`, or genuine `leader-inline` mode plus overall evidence.
Do not author canonical execution fields to select or change an executor.

A packet still names one `work_item_id`, its `depends_on` ids, prerequisite
evidence and exact work-item acceptance. Each `work_item_status` is `pending`,
`ready`, `in_progress`, `blocked`, or `accepted`; only `accepted` satisfies a
dependency. Independent delegated items may share a batch only when write scopes
and shared resources do not conflict. Conflicting work is serial; an active
worker cannot be relabelled leader-direct to escape its claim. Resume preserves
the recorded mode. A direct item whose assumptions no longer hold pauses for
reconciliation rather than changing executor in place. One completed batch is
progress, not task completion.

Scale up task-local planning when the task develops cross-capability behavior,
architectural or migration decisions, compatibility or rollout obligations, or
acceptance that cannot be stated compactly. Put the expanded dependency,
consequence, and acceptance material in `PLAN.md`; keep its active batch,
decision, and evidence statuses in `STATUS.md`. Use multiple dependency-aware
batches and join points as needed. None of these conditions require
`$spx-specify`, and the request must not be shrunk to make Quick appear small.

Unsafe write overlap is a Quick blocker until lanes are resequenced or isolated.
An unknown root cause parks the current Quick item through its runtime owner and
starts a Debug-grade diagnostic lane inside Quick; after verified repair, resume
that item without invoking another user-invoked workflow automatically.
`$spx-specify` is used only when
the user explicitly replaces direct delivery with a formal spec-first workflow.

At closeout, `SUMMARY.md` records outcome, changed paths, verification actually
run, skipped checks, residual risk, and recovery state. `STATUS.md` points to it
and reaches `resolved` or `blocked` truthfully.

## Complete source consumption for direct delivery

A Discussion handoff with materials must pass the same ready validator before
Quick inherits it: every original extent accounted for, complete runtime
`reading`/unit delivery, complete `unit_dispositions`, and every
`agent_requirement_contract.source_requirements` record explicitly disposed.
Query the full source ledger through the canonical handoff binding and map all
in-scope REQ IDs into the existing work-item outcomes and acceptance; preserve
negations, conditions, permissions, exceptions, corrections, and source-backed
non-goals/deferrals. Do not shrink source scope because delivery uses Quick.
Undelivered, unmapped, stale, unavailable, or unresolved material is a readiness
blocker even if an old summary, status, or size-based eligibility override says
ready. Legacy materials without runtime reading receipts return to Discussion
for import and rereading, never automatic promotion from a summary. Context-
direct selection cannot bypass these source gates: a material-backed handoff
uses full Quick intake. New original-source material or a changed rule requires
source reconciliation in its owning Discussion before relying on its old
binding. When no semantic delta exists, inherit the already confirmed digest
without another user confirmation; only a real decision change uses the existing
amendment gate. Pure conversation without materials retains normal Quick rules.
