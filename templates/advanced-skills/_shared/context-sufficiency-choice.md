# Pre-intake context sufficiency gate

Apply this before any other reference, workflow bootstrap, artifact operation,
Learning or Project Cognition intake, repository read/search, reproduction, log
or test command, delegation, or other tool call. Assess only evidence already
present in the active conversation context. No tool call may be used to make
this decision.

Offer context-direct only when the request and mutation authority are explicit;
the exact owning files or symbols and current patch anchors are visible; direct
consumers, generated/shared surfaces, risks, and verification entry points are
bounded; the evidence is current and consistent; no product/design/security/
migration/compatibility/rollout/external-effect decision is open; and the work
is one coherent bounded edit. Unknown means insufficient. Large,
cross-cutting, multi-item, multi-owner, acceptance-heavy, or resumable work uses
the full Quick branch.

Debug adds a stricter gate: the context must contain a reproduced failure, a
proven failure mechanism or root cause, no competing hypothesis, explicit fix
authority, the exact bounded repair surface, and a regression check. Otherwise
use the full Debug branch.

When insufficient, do not show a choice; enter the full workflow. When
sufficient, show the exact outcome/write scope, already-visible owner/consumer/
risk/verification evidence, and the fallback trigger, then ask exactly once:

- Quick: **Direct change (Recommended)** or **Continue full sp-quick**.
- Debug: **Direct fix (Recommended)** or **Continue full sp-debug**.

For Quick, first explain the current findings and selected evidence basis,
concrete proposed change and reason, exact scope, affected behavior, expected
result, risks and verification. Choosing **Direct change (Recommended)**
approves that exact bounded proposal once; do not add a redundant implementation
confirmation. Choosing the full branch starts bounded discovery and its normal
concrete Decision Checkpoint. A generic change request or an unexplained menu
is not approval of an unseen proposal.

For Debug, the choice must first explain the discovered defect, proven failure
mechanism and decisive evidence, concrete proposed fix, affected change scope,
expected result, risks, and original-reproduction/regression verification.
Choosing **Direct fix (Recommended)** approves that exact bounded repair; do
not ask a redundant repair confirmation. Choosing the full branch starts its
normal evidence investigation and later evidence-backed repair checkpoint.
Do not turn a generic fix request or an unexplained menu into repair authority.

Use the host's native choice UI when available and wait. Never infer or
auto-select the answer.

If full is selected, apply the normal workflow. If direct is selected, skip
entry-time `learning start` and `cognition compass`; create no Quick/Debug
workspace, session, confirmation checkpoint, plan, packet, or delegation state.
Before source writes, run `specify-runtime execution overview --format json`
and inspect its `execution-overview-v1` activities and signals across Fast,
Debug, Implement, and Quick. It reconciles expired Work; do not infer
concurrency from a separate empty board snapshot. Resolve any `block` signal
and review any `warn` signal. Read `references/execution-bootstrap.md`, then
create one bounded Work/Activity with `specify-runtime execution announce
--workflow quick` or `--workflow debug`, exact `--task-ref quick:<direct-id>`
or `--task-ref debug:<direct-id>`, planned scope, semantic resources, summary,
agent, and adapter. Retain its id and fence, checkpoint `selected`, refresh the
overview, and require the all-or-none `specify-runtime execution guard` with
the exact overview revision and `snapshot_sha256` before source writes. The
digest binds the concurrency view, not an ambient file capture. Then perform only
the confirmed bounded edit; preserve unrelated work; run a failing test or
executable reproduction before behavior edits; checkpoint `validating` and run
fresh verification afterward. Call `specify-runtime execution complete` only
after fresh passing validation and terminal direct-task state, then report exact
paths, evidence, and residual risk. A stale patch anchor,
new consumer, ambiguity, consequence, or scope expansion ends context-direct
and resumes the matching full workflow before further mutation.

The direct branch has its own explicit discovery-skip exception. It does not waive
safety, external-effect gates, TDD, diff review, verification, or post-change
Project Cognition closeout. Run delta closeout only for exact changed paths;
post-change Project Cognition closeout updates new truth and must not rerun
entry navigation. Because there is no workflow workspace/session, stamp the
hard gate with `{{specify-subcmd:specify-runtime cognition mutation-receipt --workflow
<sp-quick|sp-debug> --scope-dir .specify/project-cognition --result-state
ready|no_op|mark-dirty|partial --reason "<text>" --format json}}`; do not create a
Quick/Debug artifact merely to hold the receipt.
This exception does not change `spx-fast`, whose normal entry performs
consume-only Learning intake before Project Cognition.
