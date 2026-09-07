# Discussion contract

The durable state is a decision model, not a transcript. Preserve the problem,
actors, outcomes, scope boundaries, repository facts, confirmed decisions,
rejected options with reasons, assumptions, open decisions, and current next
question.

Session identity comes from `specify-runtime discussion resolve --intent continue
[--slug <slug>] --format json`. Multiple candidates are a blocker until the
user chooses a slug; do not guess and do not select latest. The resolver's
`state_sha256` is the compare-and-swap input for checkpoint and write-handoff.

## Optional checkpoint prefix

Show one short reminder in the user's language only on active discussion turns
whose next user message may continue ordinary discussion, including
acknowledgements and replies that already saved progress while the discussion
remains active. For Chinese:
"需要保存讨论进度时，可在下一条回复前加 `checkpoint`。"
This advertises an optional leading `checkpoint` prefix on the next user message;
no `continue` keyword or extra confirmation is required. Do not ask whether to
save, wait for an answer, or maintain a turn counter. The prompt does not write
files by itself. Ordinary turns remain memory-first; existing semantic,
evidence, compaction-risk, handoff, and lifecycle save gates still apply.

Suppress the reminder during handoff assessment or consumer-route selection,
draft handoff review or exact digest confirmation, handoff confirmation or
mark-ready, and `handoff-ready` closeout or downstream invocation. Those replies
already request one dedicated handoff action and must not append an unrelated
discussion-save prompt.

Separate the prefix from the discussion body; it is a user-triggered save
modifier. After resolving the session,
save prior pending progress first with `discussion checkpoint` and the current
`--expected-state-sha256`, then answer the body normally in the same visible
reply. Whitespace or punctuation can separate an explicit prefix from prose.
Quoted text, code, or a question about checkpoint is not a save request; honor
an explicit request not to save. Preserve standalone `checkpoint`,
`save checkpoint`, `checkpoint, continue`, and clear localized save requests.

| User message | Save action | Discussion action |
| --- | --- | --- |
| `这个方案的成本怎么算？` | No explicit save request | Answer the cost question normally |
| `checkpoint，这个方案的成本怎么算？` | Save prior pending progress first | Answer the same cost question normally |
| `checkpoint` | Save prior pending progress | Briefly acknowledge the actual result; keep discussion available |
| `这里的 checkpoint 是什么意思？` | No explicit save request | Explain the term normally |

The prefix checkpoint excludes the new body until that body is processed.
For a later write in the same turn, obtain a fresh resolver hash rather than
reusing the pre-checkpoint hash; do not repeat the prefix save at reply closeout.
Apply topic ownership, decision classification, and any handoff approval gates
to the body independently; the prefix grants none of those permissions.

Save through the exact rendered command
`{{specify-subcmd:specify-runtime discussion checkpoint <slug> --expected-state-sha256 <state_sha256> --input-json - --format json}}`.
Use the exact rendered project-local runtime launcher at the start of that
command. Never prepend or synthesize a drive letter, rebuild the launcher from
the current directory, or substitute an agent-guessed absolute path. Run it
from the project root. On Windows PowerShell, keep the JSON in memory and pipe
it to stdin with `--input-json -`; do not place a PowerShell here-string directly
after `--input-json`. Before the first payload in a session, or whenever its
shape is uncertain, inspect
`{{specify-subcmd:specify-runtime api schema discussion-checkpoint-input --format json}}`
and obey the live field types rather than inventing objects.

If checkpointing fails, no durable checkpoint exists. Do not dismiss the
failure as harmless or cross a semantic, handoff, or lifecycle boundary that
depends on it. Keep progress pending and perform one typed recovery: retry the
exact rendered launcher from the project root for a path or executable lookup
failure; use returned `show_argv`/the live schema for invalid input; use the
slug-bound `next_argv`/resolve action for stale state. Retry once with the
corrected contract. If that retry still fails, report the exact pending blocker.
A standalone `checkpoint` has no discussion body to continue, so stop there.
For a prefixed ordinary body, only safe discussion independent of the missing
durable transition may continue, with the checkpoint visibly pending. Ambiguous
session identity still blocks durable writes.

## Discussion ownership and handoff

Topic ownership is explicit. Classify each turn with `route: continue_current`,
`branch_new`, `link_existing`, or `defer`. Only `route: continue_current` may change
this discussion's owned scope or handoff. Branch/link/defer side topics stay as
references with `target_slug`/`source_digest` when available; do not copy those
decisions into the current requirement contract.

Before a handoff, preserve the locked target root, `verified_project_facts`,
evidence checked, open assumptions, and advice confidence. Carry triggered
consequence obligations with affected objects and stop/reopen conditions. For UI
work, keep every original UI reference, confirmed direction and interaction
decision, and deferred UI unknown with its downstream owner. Run Design
Discovery when UI is involved and persist durable `design_context` (feeling/tone,
dials, density, motion, references, anti-slop lean, `sp_design_required`) into
Design Carry-Forward and handoff `discussion_decision_digest.design_context`—
not chat-only prose.

User-provided source material is first-class state, not incidental context.
Apply `source-material-consumption.md` before using its claims: import full
source text, deliver every exact runtime unit, extract atomic
`requirements_snapshot.source_requirements`, and perform semantic reverse
review. Evidence links and inspected labels alone cannot prove full coverage.
Snapshot/delivery writes are necessary evidence-handoff events; ordinary
replies retain deferred persistence. Runtime owns reading progress and inspected
status; checkpoint only semantic unit/requirement dispositions.
Documents, screenshots, recordings, pasted notes, links, and other supplied
materials must be checkpointed in `source_materials` before their claims are
used downstream. Use stable `MAT-###` IDs with `material_type`, `locator`,
`summary`, `inspection_status` (`pending`, `inspected`, `partial`,
`unavailable`, `stale`, `conflict`), `claims[]`, `coverage_gaps[]`,
`sensitivity` (`safe`, `sanitized`, `restricted`), and optional
`content_sha256`/`version_ref`. Restricted material stores only a safe reference
or sanitized summary. `source_evidence[].material_id` must point to existing
materials, and every material must have full runtime-unit delivery and
unit/requirement coverage before handoff; partial or uncovered material remains
blocked. Retain routed-topic materials/REQ IDs with explicit scope dispositions
for accounting, without treating them as owned delivery scope.

Use deterministic discussion helpers for lifecycle changes. A handoff is
eligible only when its evidence exists, product boundaries are explicit,
blocking contradictions are resolved or retained, and every material decision
can become a requirement or constraint. Validation success is necessary but
does not replace agent self-review or user confirmation.

The latest semantic checkpoint is mandatory before `write-handoff`.
`latest_checkpoint.snapshot_sha256` must match the current canonical discussion
snapshot. If no such checkpoint exists, `write-handoff` blocks with
`missing_semantic_checkpoint`; if the state changed afterward, it blocks as
stale. Handoff v5 does not copy the full state snapshot and does not accept
state truth from ad hoc input: the runtime derives `agent_requirement_contract`
from state `requirements_snapshot`, carries the state-owned semantic fields, and
binds them with `discussion_snapshot_digest`; counts, material digests, coverage,
and planning status are runtime-derived.

At handoff routing, show both consumers with their eligibility, explain any
blocker, and recommend one eligible consumer from delivery complexity and
consequence profile rather than raw size alone. The user makes the final choice.
If no explicit choice exists, ask one route-choice question, remain in
`spx-discussion`, and do not call `discussion write-handoff`. Keep the route
unresolved until that choice is explicit, then store the selected consumer in
`recommended_consumer`; the protected digest reconfirms it with the rest of the
handoff meaning.

Human review must show material coverage alongside the decision package: covered
`MAT-###` IDs, any uninspected or partially inspected materials, coverage gaps,
unknowns/conflicts, and what would return the discussion from handoff review to
ordinary clarification.

If the conversation changes after a handoff draft, invalidate the draft rather
than editing around its protected revision. Closing and archiving are separate
explicit actions; neither proves the handoff was consumed.
