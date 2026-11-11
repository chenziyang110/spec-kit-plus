# Closeout after repository changes

**Product goal:** project cognition is not optional polish. Every source-changing
mutation (`sp-implement` / `spx-implement`, `sp-quick`, `sp-fast`, `sp-debug`,
`sp-review` when it repairs code, `sp-map-update`) must refresh cognition so a
new project’s map continuously improves—path_index, routes, claims, and
compass utility grow with each iteration. Skipping update because the graph is
still greenfield/empty is invalid; record `no_op` or `mark-dirty` with reason,
then attempt a real update on the next mutation.

Before mutation closeout, require
`{{specify-subcmd:specify-runtime api ensure --capabilities cognition.closeout.recovery.v1,cognition.worker-delta.v1,cognition.closeout.binding.v1,cognition.scoped-registration.v1 --format json}}`.
A missing capability requires runtime repair or upgrade before closeout.
For non-Do source changes, after accepted joins call the planner before beginning
a binding or running the existing final verification. Do calls the planner at
knowledge closeout with its existing proof, without repeating completed work.
Only an owning mutation skill may perform cognition
closeout. Its `SKILL.md` provides the exact registry-owned `sp-*` workflow literal
and `specify-runtime cognition closeout-plan` command; never derive that ID from
the SPX skill name, an environment variable, or chat state.
Add `--scope-dir <feature-or-scope> --scope-mode explicit` and one
`--changed-path <repo-relative-path>` flag per workflow-owned changed path.
A rename owns both its old and new path; pass and preserve both endpoints in
`boundary.workflow_owned_paths`, and reject a rename when either endpoint is
outside that boundary. These paths are the mutation closeout scope; unrelated
dirty, untracked, or committed-since-baseline repository paths must not enter
`changed_paths`. If no workflow-owned path can be named, preserve the scope
blocker and recover the native owner before closeout.

For source-changing work other than Do, next expand
`{{specify-subcmd:specify-runtime api show cognition.closeout.binding.v1 --format json}}`
and use its native `cognition closeout binding begin` route after accepted joins,
with this owning skill's canonical workflow, exact scope and live Work identity.
Prefer planner-returned `binding_begin_argv` and `binding_begin_input`; ambiguous
Work candidates require selecting the exact existing owner, never inventing one.
Runtime derives work/attempt, current source/dependency bytes, owned delta and
canonical accepted-output versions. Supply semantic inputs only; never invent
binding hashes, binding timestamps, generated IDs or an accepted-output list.
Validation observation times come from real tool results. Run the existing
final verification against that basis, then `seal` the returned binding ID with
truthful observations. Use inline JSON or stdin; `@path` is only an existing
registered/runtime-owned artifact, not a new agent-authored input file.
For non-Do source changes, carry the current sealed binding through the native
binding flag to shared apply and consume its current `check` before the terminal
claim. Changed bytes/dependencies,
either rename endpoint, wrong task/scope/attempt, stale accepted output or parent
proof invalidate affected evidence. Preserve old attempts and reverify the affected
basis; do not rebind old passing logs to changed source. Legacy evidence stays
audit-only. Runtime binds observations; it does not authenticate tools or agents,
and independent semantic acceptance remains required. Keep Implement/Review's
existing logical gates. Do consumes its existing stronger
session/epoch/definition/source validation proof and lock order. Its knowledge
closeout requires no new generic begin/seal cycle or rerun of completed operations.
Do supplies that existing proof to its native knowledge closeout instead of the
generic sealed binding and `check` requirement.
Only E2E retained test-asset source changes need this binding; read-only
runs, traces and disposable outputs do not invent source mutation.
When Quick's planner is blocked by a missing or incompatible cognition store,
negotiate `cognition.closeout.bound-fallback.v1`. Native binding `begin` and
`seal` can still bind the current joined Quick Work, accepted outputs and
source. Begin with canonical `workflow=sp-quick`, the exact quick workspace
and semantic input `{"work_id":"<current joined native Quick Work>"}`, run
fresh final checks, then seal the returned binding ID. Recover a blocked or
interrupted Work through its owner first. This bounded recovery applies to
Quick; other workflows retain their owning recovery routes.
After the existing verification and sealing when required, fill only the returned
agent-owned evidence fields, then execute structured `apply_argv`; `update_argv`
is a low-level compatibility/debug primitive, not the workflow closeout path.
Preserve candidate `owner_surfaces`, `consumer_surfaces`, `interfaces`,
`evidence_refs` and `invalidated_claim_refs` alongside behavior, generated-chain,
state/config and verification evidence. Account for the complete actual delta,
including retained failed edits, deleted paths and both rename endpoints, against
live owners, consumers, interfaces, state/config contracts, generated chains,
verification entrypoints and invalidated aliases. Truncated closures and unknown
relations remain unresolved obligations in the full denominator.

Validate worker candidates against current accepted outputs and bounded live
source. Preserve unaffected facts and unrelated evidence; dependent old facts
become stale when their evidence changes. Generic passing tests cannot revive
them. New components, owners, relations and claims need runtime-owned scoped
compilation/registration with evidence-specific states. Provisional path coverage
does not establish those facts or semantic completion. Never replace a whole
generation with a partial package, invent registration identity/integrity fields,
or enter a full map workflow merely to add a local fact.

For new or changed semantic facts, use the shared apply registration draft.
In inline mode, add `scoped_registration` to the completed planner payload and
send that same payload to `apply_argv` stdin. In delta mode, first append the
required closeout evidence, then send only the registration draft to the returned
`registration_apply_argv` stdin. Preserve its delta-session and other argv tokens;
carry the current sealed binding flag when required.
Expand `{{specify-subcmd:specify-runtime api show cognition.scoped-registration.v1 --format json}}`
for its current draft contract. The shape is
`{"schema":"cognition-scoped-registration-draft.v1","delta":{...},"result":{"state":"registered","reason":"<evidence-based change>"}}`.
`delta` contains all changed paths, evidence source paths, semantic rows,
aliases/path mappings, retirements and the full obligation summary. Use stable
semantic local keys for new row IDs and references; retain exact live IDs for
existing graph references. Runtime derives hashes, maps local keys together,
binds the native proof and persists the prepared request in the existing intent.
Supply truthful verification observations and their actual times. Shared apply
registers into the same update journal before validation and receipt. Partial
registration or unresolved debt blocks the terminal claim and preserves exact
recovery; do not run standalone scoped-register around shared apply.

Consume the native current guarded publication/recovery contract inside this
existing gate, carrying the exact accepted Work/source proof; Do retains its
existing stronger native proof without another begin/seal cycle. Keep incomplete
registration, missing evidence, retired aliases and unresolved consumer/test
obligations explicit in the terminal result. Scope completion does not publish
global freshness or workflow `claim_ready`, or replace Review/human Accept.
Actual current queries must let a later consumer find the new owner, consumer
and verification entry without presenting retired facts as current answers.
For `update_mode=inline_json`, `apply_argv` contains `--payload-json -`: serialize
the completed payload draft and write the completed payload JSON to stdin. Never
replace `-` with payload JSON in process argv and never create a payload file.
Set
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
`apply_argv` owns the deterministic tail. Read `scope_result_state` separately
from the project-wide `result_state` and `global_freshness`. When scope and
global results are `ready|no_op`, shared apply runs
`{{specify-subcmd:specify-runtime cognition validate-build --format json}}` then
`{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}` and
stamps the current-update-bound receipt. Only `status=ok` with
`readiness=query_ready` creates the validate-build receipt bound to the latest
update ID, outcome, and active generation. Clean completion requires that
receipt-bound finalizer to succeed; until then Compass/query remains in
`pending finalization`. `closeout_state=scope_ready` means this explicit workflow scope
succeeded while unrelated project-wide debt remains visible in
`global_debt_reasons`; it is closeable without falsely finalizing global
freshness. Missing `verification[result=passed]` returns
`closeout_status=needs_agent_input` before update mutation. For a scope-level
`partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`, runtime must
not run `complete-refresh`; preserve the truthful state and recovery action.
A failed, stale, blocked, or non-`query_ready` validation also must not run
`complete-refresh`. In every non-eligible branch, runtime must not run
`complete-refresh`.

Shared apply persists a mutation intent before recovery and holds the same update lock
across older-intent drain, status repair, one direct predecessor,
the current update, validation, bound finalization, and the scope receipt.
Reruns are idempotent and another closeout drains older intents first. It never
cross-binds updates, must not scan older unrelated history, or finalize failed or
non-`query_ready` validation; the compact result remains
`predecessor_recovery`, and an unfinished predecessor remains
`pending_finalization`.

Blocked predecessor recovery writes non-closeable
`predecessor_recovery_blocked` with exact paths and keeps the intent, so current mutation accounting remains durable. Keep the
parent workflow active. For bounded path-led identity debt run returned
`specify-runtime cognition identity-repair plan`, then its digest-bound
`specify-runtime cognition identity-repair apply`; afterward run
`specify-runtime cognition closeout replay --scope-dir <scope> --format json`.
Only replay may replace that receipt. Do not downgrade a replayable intent to
`mark-dirty` or send agent-repairable recovery to the user.

For `repair_update_or_replay_intent` or blocked queued intent recovery, keep the
parent workflow active. Stop retrying the same failing apply while the intent
and cause are unchanged. Execute returned `recovery_argv`, or
`{{specify-subcmd:specify-runtime cognition closeout inspect --intent-id <blocked_intent_id> --format json}}`;
omit the ID only to list compact pending cards. Inspect is read-only, needs no
blocked scope receipt, and returns the selected scope/workflow/state,
`input_digest`, verification diagnostics, and `recommended_next_action`.
An absent or older successful receipt does not justify guessing `--scope-dir .`.
If inspect directly offers `replay_argv`, execute it unchanged without requiring
repair or replacement fields.

Execute applicable returned `repair_argv` unchanged. A new repair uses
`cognition closeout repair --intent-id <ID> --expected-digest <input_digest>
--verification-json - --format json` with the complete truthful structured
verification array on stdin. Records require
actual `command`, exact `result`, and optional `artifact`. Never invent verification commands
or passing results; run missing checks or recover trustworthy evidence first.
Empty stdin cannot start a repair; only a previously journaled repair may resume
without resupplying evidence when runtime permits it. Repair changes only
defective verification of an uncommitted intent, archives the original, and
creates a digest-bound successor preserving other semantics, scope, paths, and
delta content. `intent_repaired` is not readiness: follow returned
`replacement_intent_id`, `replacement_input_digest`, and `replay_argv`.
Exact replay uses `cognition closeout replay --intent-id <ID> --expected-digest
<SHA256>`; any supplied scope must match. Legacy scope replay requires its
matching blocked receipt. Reinspect on digest drift. After replay, resume the
original closeout and verify its own allowed receipt. Do not edit or delete intent JSON,
fabricate receipts, bypass the queue, or downgrade to `mark-dirty`;
do not rebuild merely because verification was malformed. When no safe action
is available, preserve the exact blocker, required evidence, and resume action.

Successful shared apply stamps the hard gate receipt itself before terminal
close. Do not stamp a second receipt. Only a runtime-authorized Quick
`mark-dirty` fallback uses this standalone command:

```text
{{specify-subcmd:specify-runtime cognition mutation-receipt --workflow sp-quick --scope-dir <quick-workspace> --result-state mark-dirty --binding-id <sealed-current-binding-id> --reason "<text>" --format json}}
```

Runtime blocks `implement closeout` and implement/review `workflow complete-stage`
without an allowed receipt. Quick uses the same receipt under its workspace
(via shared apply, or
`quick cognition-closeout <id> --result-state mark-dirty --binding-id <sealed-current-binding-id> --reason "<text>" --format json`
for the authorized bound fallback). Runtime requires a missing/incompatible
graph, no pending intent, unchanged source/dependency bytes, complete accepted
outputs and a current sealed native binding with fresh passing observations.
Unbound legacy receipts remain audit-only for proof-required closeout.
Preserve graph debt and the returned guarded archive/repair action in the
result. A bound fallback does not archive the store or publish freshness.
Fast/debug use the same shared apply before claiming completion even when they
lack a formal stage machine.

Specification, plan, task, checklist, test-design, research, and other
planning-only artifact changes do not make the code map dirty and do not
require cognition closeout.
