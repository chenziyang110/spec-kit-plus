Trigger: before project-specific technical advice, repository fact claims, or handoff boundary decisions.

Purpose: preserve boundary locking, truth-pass, project-cognition advisory, and live-evidence authority rules outside the main hot path.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Truth Pass

When the user asks for advice that depends on current project reality, complete a bounded truth pass before giving project-specific technical options, affected-surface claims, testing strategy claims, or implementation-path recommendations.

The truth pass is required when the turn involves current project behavior, command/template/script/test/documentation surfaces, implementation path or affected surface claims, existing capability reuse, cross-CLI propagation, compatibility, lifecycle, state, security, or downstream workflow risk.

The truth pass records:

- `verified_project_facts`: facts proven from live files, command output, tests, docs, or explicitly cited evidence
- `open_assumptions`: claims still unproven after bounded lookup
- `evidence_checked`: project cognition route, returned `minimal_live_reads`, repository files, commands, tests, docs, or user-provided references inspected
- `advice_confidence`: `high`, `medium`, `low`, or `blocked`

Project cognition remains advisory navigation. It helps select minimal live reads, but live repository evidence proves current project behavior.

Before the truth pass completes, `sp-discussion` may discuss product intent and decision shape, but must not name affected files, modules, APIs, tests, or implementation paths as facts. If evidence is insufficient, say so directly and explain what must be checked next instead of packaging an assumption as a recommendation.

Do not recommend implementation work before the relevant Truth Pass is complete.

## Context Boundary Gate

The Context Boundary Gate triggers semantically when the user request implies an unclear boundary involving:

- execution target project or target root
- current repository role
- reference project or source artifact
- external system or service boundary
- existing module, package, adapter, generated artifact, or workflow surface
- path where work must land
- source of truth for existing behavior
- evidence source needed before making technical claims

When the gate triggers and the relevant boundary is not locked, `sp-discussion` may continue only with boundary clarification and product framing. It must not provide project-specific technical recommendations, name affected files, modules, APIs, or tests as facts, claim a target implementation path, write handoff files, mark the discussion `handoff-ready`, or tell the user to proceed to `sp-specify`.

For cross-project transfer requests, lock the target project root immediately. If the target root is unknown, continue only with goal, scope, non-goals, and success signals. The handoff must say whether the active repository is the implementation target, a reference source, both, or unrelated. Current project's cognition cannot prove another project's implementation facts.

## Staged Project Cognition Gate

Product framing may begin before project cognition is available.

Allowed before the cognition gate:

- session creation or resume
- user goal framing
- audience and scenario clarification
- scope, non-goal, and success-signal questions
- recording unknowns and assumptions

Forbidden before the cognition gate:

- project-specific technical recommendations
- affected module, file, API, or test claims
- implementation path recommendations
- testing strategy claims tied to existing code
- confident advice that hides open assumptions

Bounded source-code reads are allowed during the Truth Pass when they are needed to prove current project facts.

Before `context-grounding`, `technical-options`, affected-surface analysis, or source-grounded recommendations, use project cognition only when current-project facts matter:

1. Read `.specify/project-cognition/status.json` for advisory freshness and runtime metadata when present.
2. Run the `project-cognition compass --intent discussion` route through `{{specify-subcmd:project-cognition compass --intent discussion --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `coverage_diagnostics`. Preserve the advanced `lexicon -> semantic_intake -> query` flow as a conditional escalation for explicit concept decisions.
3. Run the advanced path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, write `semantic_intake` from the alias catalog with `normalized_query`, `intent_facets`, `negative_constraints`, and `alias_interpretations`; select from the returned graph-backed project concept candidates by facet coverage and create a bounded `query_plan` with `semantic_intake`, `selected_concepts`, `rejected_concepts`, `concept_decisions` containing `covered_facets`, `missing_facets`, and `match_sources`, `lexicon_generation_id`, `expanded_queries`, `repository_search_terms`, justified `paths`, and `selection_reason`. Agent-owned semantic normalization is mandatory: raw lexicon ranking and `agent_normalization` are only bootstrap signals, not route decisions. If `agent_normalization.required=true`, every raw candidate is `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, or symptom-first, extract embedded project terms and write `semantic_intake` from the alias catalog before selecting or rejecting concepts. If `agent_normalization` is omitted, treat it as `required=false`; CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. This includes mixed-language or CJK text. (raw lexicon ranking is only a bootstrap; action: write_semantic_intake_from_alias_catalog) Derive project-language search terms from the alias catalog before source search. Do not search only the raw user words; include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched_terms, colloquial_matches, returned paths, `normalized_query`, and `expanded_queries`. Use these project-language search terms before broad repository search. Do not trust top similarity alone.
4. In that escalation, run `project-cognition query --query-plan "<query_plan_json>"` and use the returned readiness, route_pack, subgraph, missing coverage, and `minimal_live_reads` only as advisory navigation.
5. Read the returned `minimal_live_reads` before making project-specific technical claims.

### Cognition Advisory, Code Authority

Treat project cognition as advisory navigation and coverage metadata. Use it to choose minimal live reads. Do not treat it as authoritative evidence for current behavior; prove project facts from live repository files before asking the user or making technical claims.

Readiness handling:

- `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
- `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for documented brownfield rebuild triggers.
- `readiness=blocked`: report project cognition as unavailable or degraded, continue with product framing or bounded live evidence when safe, and recommend a map maintenance workflow only when the user asks for map maintenance or handoff needs evidence that live reads cannot provide.

If the idea is clearly greenfield or does not depend on existing project structure, keep the stand-down reason as pending project context and persist it to `project-context.md` only at the next semantic checkpoint; avoid existing-code placement claims.

## Lightweight Recovery Log

Ordinary turns do not write local files by default. Use deferred persistence: keep a compact pending context summary in the active conversation and flush one semantic event to `discussion-log.jsonl` only when a save trigger fires. Treat an existing discussion package as a recovery surface, not a reason to write more often.

Classify the persistence mode before any write-capable action:

- `frontstage-only`: default for ordinary discussion replies, acknowledgements, low-risk preference answers, small clarifications, and follow-up thinking. This mode behaves like `sp-ask`: answer in the visible conversation, keep backstage state in active memory, and do not write files, counters, dirty markers, receipts, or status summaries.
- `durable-checkpoint`: use only when a semantic checkpoint, user-triggered checkpoint/save, high compaction risk, or resume-relevant stop requires a compact durable summary. Write the smallest useful state update.
- `evidence-handoff`: use only when delegated or source-grounded evidence must be consumed by later synthesis. Persist the evidence packet or source reference required for that later consumer; do not turn the whole discussion into a transcript.
- `lifecycle-transition`: use for handoff assessment, draft handoff creation, handoff-ready confirmation, consume/repair/archive transitions, or resume repair.

Keep the classification backstage. If the mode is `frontstage-only`, do not call filesystem write tools for `.specify/discussions/<slug>/` artifacts during that turn.

Before any local write in an ordinary discussion turn, run the persistence gate:

- If no save trigger has fired, do not write `discussion-state.json`, `discussion-state.md`, `discussion-log.jsonl`, optional structured files, hidden counters, dirty-artifact markers, or state receipts just to record that turn.
- Keep pending decisions, pending open-question deltas, and compaction-preserve notes in active-conversation memory until the next save trigger.
- Update persisted counters and pending summaries only inside the batched save event or semantic-checkpoint refresh.
- A user reply is not itself a save trigger. A reply becomes durable only when it changes a checkpoint-level decision, boundary, evidence status, recommendation, handoff readiness, or the configured cadence/compaction/lifecycle trigger fires. Plain confirmations such as "yes", "ok", "continue", or localized equivalents remain `frontstage-only` unless they approve a named checkpoint, save, handoff, or lifecycle transition.
- Native hooks may remind the agent about resume or compaction at session start/stop, but must not create per-user-reply or per-tool-use discussion writes. Do not use `UserPromptSubmit`, `PostToolUse`, or similar hook events as a hidden persistence loop for `sp-discussion`.

Save triggers are:

- semantic checkpoint
- user-triggered checkpoint/save, such as "checkpoint", "checkpoint, continue", "save this point", "record the current discussion", or "this is decided"
- evidence-handoff: delegated or source-grounded evidence must be consumed by later synthesis
- context compaction risk is high
- handoff assessment, handoff drafting, resume repair, or another durable lifecycle transition needs the pending summary

When a save trigger fires, append one compact JSON object to `discussion-log.jsonl`. The event is not a transcript and records only durable meaning: event kind, summary, confirmed decisions, evidence used, open-question delta, save trigger, and resulting lifecycle phase.

At a natural pause or when compaction would risk losing important decisions, optionally suggest `checkpoint, continue` to save progress and keep going. Do not expose or maintain a turn counter merely to trigger this suggestion.

When the user says `checkpoint, continue` or an equivalent checkpoint-plus-continue phrase, flush the batched compact event first, refresh only semantically changed structured files, reset persisted unsaved counts inside that flush, and then continue with the next useful discussion content in the same visible reply instead of stopping at a file-write receipt.

Do not refresh all structured files on ordinary turns. The batched event log exists to survive context compaction while keeping normal discussion lightweight.

Use checkpoint persistence: do not persist every turn. Ordinary replies should keep state accounting backstage and continue the visible conversation without a visible save receipt. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.

When there is active meaning to preserve, keep a pending backstage Compaction Preserve note for user thinking, decisions, confirmed requirement points, confirmed feature points, constraints, trade-offs, and reopen conditions that must not be dropped, flattened, or reinterpreted during context compression. Surface that preserve note only at a save trigger, handoff/recovery checkpoint, compaction-risk moment, or when the user asks for state.
