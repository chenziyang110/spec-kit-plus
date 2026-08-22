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
`{{specify-subcmd:specify-runtime discussion resolve --intent continue --json}}`
and `{{specify-subcmd:specify-runtime discussion init <slug> --json}}` helpers. Resume existing
state with `{{specify-subcmd:specify-runtime discussion resume <slug> --json}}` instead of
reconstructing it from chat memory. Append `--slug <slug>` to resolve when the
user supplied an exact slug. If resolve returns multiple candidates,
ask for an explicit slug; never guess, never select latest, and never infer an
unstated slug from a name, title, topic, or keyword similarity.

Use the live repository only to ground product boundaries, current behavior,
technical options, and constraints. Keep the visible conversation natural:
surface one decision cluster at a time, explain meaningful tradeoffs, and
distinguish confirmed decisions, working assumptions, rejected options, and
unresolved user choices.

Run a Truth Pass before source-grounded technical advice or affected-surface,
implementation-path, or verification claims. For cross-project work, lock
`target_project_root` before technicalizing and verify facts in that target.

Persist compact semantic checkpoints only when meaning changes; do not store a
transcript. A summary-only checkpoint is valid only for an explicit savepoint
with no semantic change. When meaning changed since the last durable state,
submit every changed semantic field needed to preserve current truth,
especially confirmed decisions, the context boundary, the current
recommendation, topic ownership, and open assumptions. Use the resolver-returned
`state_sha256` as `--expected-state-sha256` on checkpoint and write-handoff
writes. Do not report checkpoint success while leaving newly confirmed decisions
only in chat memory. Stay in discussion until the user explicitly requests a
handoff.
Run a Topic Ownership Gate each turn with exactly one `route`:
`continue_current`, `branch_new`, `link_existing`, or `defer`. Only
`route: continue_current` may mutate this discussion's owned scope or handoff.
`branch_new`, `link_existing`, and `defer` stay out of the current
`owned_scope`, requirement contract, and decision digest; record only routed
topic pointers such as `target_slug` and `source_digest` when available.
Do not treat an already-active discussion as a new automatic workflow entry;
topical acknowledgements and follow-ups continue this stage without requiring
the user to repeat `$spx-discussion`. A contextual confirmation such as `yes`,
`ok`, or `可以` authorizes handoff only when it directly answers a named handoff
action, and authorizes readiness only when it confirms the displayed digest.
Converging requirements, design, or validation gates changes the next
in-discussion action to handoff assessment and consumer selection; it never
authorizes the agent to declare implementation as the next stage or ask the
user to "start implementation".
At the handoff routing gate, present both routes and their eligibility: canonical
`sp-quick` for direct execution with task-local planning and canonical
`sp-specify` for the formal specification-first pipeline; explain any blocker
and expose the selected route later as `$spx-quick` or `$spx-specify`. Give a
complexity-informed recommendation among eligible routes by whether a formal
durable specification chain is needed, not by raw size or capability count:
favor Quick when the outcome is clear enough for confirmed direct
delivery—even multi-capability, architecture, migration, compatibility,
rollout, or acceptance-heavy work—because Quick owns a multi-Q Decision
Checkpoint, Delivery Map, and acceptance DAG; favor Specify when requirements
remain ambiguous, key decisions are unlocked, interacting systems need formal
traceability, or the user wants a durable specification-first chain. Complexity
alone is not a reason to leave Quick. The user owns the final consumer choice
and may choose either eligible route against the recommendation. Do not write the
handoff until the user has selected an eligible consumer. If no explicit choice
exists, ask one route-choice question and stay in this discussion. A contextual
`yes`, `ok`, or `可以` selects the recommendation only when it directly answers
that named route-choice question; it does not approve the later digest.
Then set `recommended_consumer` to record that confirmed selection, build only
one compact semantic contract input, and submit it with
`{{specify-subcmd:specify-runtime discussion write-handoff <slug> --expected-state-sha256 <state_sha256> --input-json '<semantic-json>' --json}}`.
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
handoff continues only through its user-selected consumer, regardless of which
route the agent recommended. Mark it consumed only after that consumer writes evidence binding
`source_contract` and `review_digest` into its Quick or feature workspace. This
invocation authorizes only this workflow stage; do not invoke another workflow
in this run.
