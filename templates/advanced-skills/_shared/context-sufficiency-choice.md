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

Use the host's native choice UI when available and wait. Never infer or
auto-select the answer.

If full is selected, apply the normal workflow. If direct is selected, skip
entry-time `learning start` and `cognition compass`; create no Quick/Debug run,
workspace, session, checkpoint, plan, packet, or delegation state.
Before source writes, run `specify-runtime execution overview --format json`
and inspect its `execution-overview-v1` activities and signals across Fast,
Debug, Implement, and Quick. It reconciles expired Work; do not infer
concurrency from a separate empty board snapshot. Resolve any `block` signal
and review any `warn` signal, then create one bounded Work item through
`specify-runtime work begin` with exact
`--task-ref quick:<direct-id>` or `--task-ref debug:<direct-id>`, confirmed
scope, summary, agent, and adapter; retain its id and fence, then require the
all-or-none
`data.work_claim` receipt from `specify-runtime work claim --current-work-id
<id> --current-work-fence <fence> --task-ref <same-task-ref>
--write-scope-json <complete-json-array> --format json`. Then perform only
the confirmed bounded edit; preserve unrelated work; run a failing test or
executable reproduction before behavior edits and fresh verification after;
and report exact paths, evidence, and residual risk. A stale patch anchor,
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
