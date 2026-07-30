---
name: spx-discussion
description: Resumable product and technical discussion for advanced coding models. Use when a rough idea needs durable decisions and options before direct Quick delivery or formal specification.
---

# SPX Discussion

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md`; its feature-state rules apply only after
this discussion is bound to a resolved `FEATURE_DIR`.
Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/discussion-contract.md`. Read `references/consequence-gate.md` on
its triggers.
Read `references/ui-quality-gate.md` when product experience, interface
direction, screen hierarchy, or interaction behavior is part of the decision.

Discover or create the session with the project launcher-backed
`{{specify-subcmd:specify-runtime discussion list --json}}` and
`{{specify-subcmd:specify-runtime discussion init <slug> --json}}` helpers. Resume existing
state with `{{specify-subcmd:specify-runtime discussion resume <slug> --json}}` instead of
reconstructing it from chat memory.

Use the live repository only to ground product boundaries, current behavior,
technical options, and constraints. Keep the visible conversation natural:
surface one decision cluster at a time, explain meaningful tradeoffs, and
distinguish confirmed decisions, working assumptions, rejected options, and
unresolved user choices.

Run a Truth Pass before source-grounded technical advice or affected-surface,
implementation-path, or verification claims. For cross-project work, lock
`target_project_root` before technicalizing and verify facts in that target.

Persist compact semantic checkpoints only when meaning changes; do not store a
transcript. Stay in discussion until the user explicitly requests a handoff.
Do not treat an already-active discussion as a new automatic workflow entry;
topical acknowledgements and follow-ups continue this stage without requiring
the user to repeat `$spx-discussion`. A contextual confirmation such as `yes`,
`ok`, or `可以` authorizes handoff only when it directly answers a named handoff
action, and authorizes readiness only when it confirms the displayed digest.
Choose `recommended_consumer` from delivery intent, never task size:
canonical `sp-quick` for direct delivery of any size, and canonical `sp-specify`
only when the user explicitly selects a formal spec-first path; expose those as
`$spx-quick` and `$spx-specify` invocations after readiness. Include an
unconfirmed consumer choice in the protected digest review as a user-owned
decision.
Then build only one compact semantic contract input and submit it with
`{{specify-subcmd:specify-runtime discussion write-handoff <slug> --input-json '<semantic-json>' --json}}`.
The runtime expands the installed stable template, binds metadata and blocked
defaults, and computes the review digest. Never read or reproduce the template
and never create a draft JSON file; the discussion runtime alone materializes
the canonical handoff.
Run `{{specify-subcmd:specify-runtime discussion validate-handoff <slug> --mode draft --json}}`,
review its boundary against confirmed decisions, and ask the user to confirm
that exact revision. Then run
`{{specify-subcmd:specify-runtime discussion confirm-handoff <slug> --digest <review-digest> --json}}`
before `{{specify-subcmd:specify-runtime discussion mark-ready <slug> --json}}`. Before every
final response that names `$spx-quick` or `$spx-specify`, read canonical status
and `recommended_consumer`; withhold the downstream invocation unless status is
`handoff-ready` and the named workflow is the selected consumer.

Do not create feature state, a spec, plan, tasks, or production changes. A ready
handoff continues through its confirmed consumer: `$spx-quick` for direct
delivery of any size or `$spx-specify` for a user-selected formal spec-first
path. Mark it consumed only after that consumer writes evidence binding
`source_contract` and `review_digest` into its Quick or feature workspace. This
invocation authorizes only this workflow stage; do not invoke another workflow
in this run.
