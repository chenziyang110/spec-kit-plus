## Pre-Intake Context Sufficiency Gate

For `sp-quick` and `sp-debug`, this is the first action. Run it before run
bootstrap, workspace/session discovery or creation, the Constitution, Learning,
Project Cognition, repository search, source reads, reproduction, logs, tests,
delegation, or any other tool call.
No tool call may be used to decide whether the current context is sufficient.

Assess only evidence already present in the active conversation context,
including live file contents, diffs, test output, runtime output, and explicit
user decisions already returned earlier in the conversation. Do not use model
memory, an old summary without current evidence, or the absence of a warning as
proof. The goal is not to prove that the whole repository is known. The goal is
to decide whether the complete bounded change and its validation surface are
already evidenced without another discovery step.

### Eligibility

Offer context-direct execution only when every applicable item is proven by
evidence already present in the active conversation context:

- the requested outcome, scope, and mutation authority are unambiguous;
- the exact owning files or symbols and the relevant current content or patch
  anchors are visible;
- direct consumers, shared or generated surfaces, and verification entry points
  are named and bounded, with no unresolved propagation question;
- the existing evidence is current, internally consistent, and sufficient to
  preserve unrelated work;
- there is no unresolved product, design, security, privacy, migration,
  compatibility, rollout, destructive-action, external-side-effect, or
  consequence decision;
- the change is one bounded coherent edit, not large, cross-cutting, multi-item,
  multi-owner, acceptance-heavy, or in need of resumable state; and
- the exact test, executable reproduction, or mechanically decisive check is
  already known.

For Debug, also require a reproduced failure signal, a proven failure mechanism
or root cause, no live competing hypothesis, explicit fix authority, and a
bounded regression check. A plausible cause, familiar-looking symptom, or
surface-only repair is insufficient.

Unknown means insufficient. If any item is unknown, stale, conflicting, or
would need one more read/search/query to establish, do not show a choice. Enter
the full Quick branch or full Debug branch automatically and apply its normal
Learning, Project Cognition, confirmation, state, planning, and execution
contracts. Large, cross-cutting, multi-item work always uses the full Quick
branch even when several relevant files happen to be visible. Debug work
without a proven failure mechanism always uses the full Debug branch.

### User Choice

When every item passes, present one compact recommendation containing:

- the exact outcome and proposed bounded write scope;
- the already-visible evidence for owner, consumers, risk boundary, and
  verification;
- why no discovery step is needed; and
- the fallback trigger that would end context-direct execution.

Then ask the user to choose exactly one option through the host's native choice
UI when available, otherwise as a numbered prompt:

- Quick: **Direct change (Recommended)** or **Continue full sp-quick**.
- Debug: **Direct fix (Recommended)** or **Continue full sp-debug**.

Do not infer the answer, auto-select the recommendation, or mix both branches.
Wait for the user's choice. If the user chooses the full branch, run it without
asking this question again.

### Context-Direct Branch

When the user selects the context-direct option:

- skip entry-time `learning start` and skip entry-time `cognition compass`;
- do not run broad search, semantic intake, Learning lookup, or Project
  Cognition navigation to reconfirm evidence already listed in the choice;
- do not run full-workflow bootstrap and must not create Quick or Debug workflow state;
  create no confirmation artifacts, plans, packets, or subagent lanes;
- make only the confirmed bounded change and preserve unrelated work; a patch
  anchor mismatch or newly discovered consumer, consequence, ambiguity, or
  larger scope ends context-direct execution and resumes the matching full
  workflow before further mutation;
- behavior-changing work still requires a failing test or executable reproduction
  before production edits and fresh verification afterward; and
- report the exact changed paths, checks, residual risk, and why the evidence
  surface was sufficient.

Skipping entry discovery does not waive safety, user-owned external-effect
gates, TDD, verification, review of the resulting diff, or post-change Project Cognition closeout.
Source/runtime/template/config/test/generated-asset changes
still run the owning workflow's delta closeout against exact changed paths. That
closeout updates changed truth; it must not rerun entry-time Compass navigation.
Because context-direct has no Quick workspace or Debug session, stamp its hard
gate with `{{specify-subcmd:specify-runtime cognition mutation-receipt --workflow
<sp-quick|sp-debug> --scope-dir .specify/project-cognition --result-state
ready|no_op|mark-dirty|partial --reason "<text>" --format json}}`; do not call the
Quick workspace wrapper or invent a workflow artifact only to hold the receipt.
Context-direct has its own explicit discovery-skip exception and does not
consume or capture Learning unless the task expands and enters the full
workflow. This exception does not change `sp-fast`, whose normal entry performs
consume-only Learning intake before Project Cognition.
