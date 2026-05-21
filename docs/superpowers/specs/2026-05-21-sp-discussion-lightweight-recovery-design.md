# sp-discussion Lightweight Recovery And Evidence-First Design

## Summary

Refine `sp-discussion` so it behaves like a capable senior product and technical discussion partner while preserving durable recovery and downstream handoff quality.

The governing rule is:

```text
Code facts are self-checked, product judgment is asked, project cognition navigates, state is checkpointed by stage, and handoff remains strict.
```

The workflow should stop treating ordinary discussion turns like full artifact-maintenance passes. Normal turns write only a small durable event. Structured files are refreshed at semantic checkpoints. `project-cognition` is used only when existing-project facts matter, and only as advisory navigation toward minimal live reads. Current repository files, tests, scripts, configuration, or authoritative docs remain the evidence source for technical claims.

Strict handoff behavior stays intact. When the user explicitly asks to hand off to `sp-specify`, `sp-discussion` still writes the unified Markdown and JSON handoff pair, runs self-review, requires user confirmation, and preserves Must-Preserve and consequence obligations.

## Problem

`sp-discussion` currently over-optimizes for resumability and handoff fidelity during every normal conversation turn. The result is a workflow that can feel less intelligent than the user expects:

- It tends to read and refresh many discussion artifacts on ordinary turns.
- It may ask the user questions whose answers are discoverable in the current project.
- It can treat context boundary caution as a reason to ask the user instead of first checking available project evidence.
- It risks treating `project-cognition` output as runtime truth instead of a map toward live evidence.
- It protects against context compaction, but with too much per-turn ceremony.

The desired behavior is not pure chat memory. Long discussions still need to survive context compression, session restarts, and downstream workflow handoff. The design therefore changes the granularity of persistence rather than removing persistence.

## Goals

- Make ordinary `sp-discussion` turns feel like a senior product and technical discussion, not an audit routine.
- Prevent questions that can be answered from current repository evidence.
- Use `project-cognition` efficiently as an advisory navigation layer, not as an authoritative fact source.
- Preserve context-compaction resilience through low-cost event logging and semantic checkpoints.
- Reduce routine reads and writes of `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md`.
- Keep strict handoff fidelity for `handoff-to-specify.md` and `handoff-to-specify.json`.
- Preserve Context Boundary Gate, Must-Preserve Ledger, quality gate, Senior Consequence Analysis, and downstream rejection of bad handoffs.
- Keep the first implementation template-testable and integration-neutral.

## Non-Goals

- Do not make `sp-discussion` chat-only or memory-only.
- Do not remove existing discussion artifacts.
- Do not remove the unified handoff pair or JSON companion.
- Do not weaken `sp-specify` handoff integrity checks.
- Do not make `project-cognition` authoritative for source behavior.
- Do not block ordinary discussion solely because project cognition is stale, missing, or incomplete.
- Do not add a new Python runtime state machine in the first increment.
- Do not make the behavior Codex-only.
- Do not automatically invoke `sp-specify`.
- Do not edit source code or tests from `sp-discussion`.

## Reference Shape

The design borrows the useful shape from Superpowers skills:

- inspect context before detailed questions
- ask one high-impact question at a time
- explore alternatives before locking design
- save durable artifacts at stage boundaries
- self-review before transition
- keep strict execution and verification gates out of the discussion loop until the workflow reaches those stages

For `sp-discussion`, this becomes:

- classify each user turn before deciding whether to ask, inspect, or checkpoint
- use evidence before asking fact questions
- append compact events for compaction resilience
- checkpoint semantic state only when discussion meaning changes
- preserve strict audit structure only for explicit handoff

## Core Model

`sp-discussion` uses five cooperating layers:

1. **Turn Classifier**: classify the user's latest input before any question is asked.
2. **Question Evidence Gate**: decide whether the next question can be answered from evidence.
3. **Cognition Advisory, Code Authority**: use project cognition only to choose minimal live reads; prove facts from live files.
4. **Lightweight Recovery Log**: append a small event for ordinary turns.
5. **Semantic Checkpoint And Strict Handoff**: refresh structured files at stage boundaries and enforce full handoff quality on explicit handoff.

This model keeps the workflow fast during conversation and rigorous when the discussion becomes a downstream contract.

## Turn Classifier

Before responding, `sp-discussion` classifies the user input into one or more categories:

- `product_intent`: goal, user, scenario, desired behavior, non-goal, acceptance signal, preference, or trade-off.
- `current_project_fact`: a question or claim about the active repository's commands, files, workflows, runtime behavior, tests, templates, or docs.
- `target_boundary`: ambiguity about whether the active repository, another local project, a reference project, or an external system is the implementation target.
- `reference_boundary`: ambiguity about which source artifact, project, prior implementation, doc, or external system should be used as evidence.
- `handoff_request`: explicit request to feed the result to `sp-specify`, continue to the next stage, or produce handoff artifacts.
- `continuation_or_resume`: user wants to continue an existing discussion.

The classifier controls the next step:

- Product intent can be discussed directly or with a product question.
- Current project facts require evidence lookup before asking the user.
- Target and reference boundary gaps may require one concise boundary question.
- Handoff request enters strict handoff assessment.
- Resume reads only the compact state and recent events first.

## Question Evidence Gate

Before asking the user a question, `sp-discussion` must decide whether the question is actually answerable by the agent.

Ask the user only when the question is one of these:

- Product decision: the user must choose behavior, priority, scope, non-goal, or success criteria.
- Preference or trade-off: multiple valid options exist and repository evidence cannot choose.
- Boundary gap: target root, current repository role, reference source, or external system is genuinely unclear.
- Evidence conflict: live evidence, docs, project rules, or user claims disagree and the user must decide.
- Unavailable fact: the relevant source cannot be accessed or located after bounded evidence lookup.

Do not ask the user when the answer can be found through:

- current repository files
- current repository tests
- scripts and CLI help
- templates and generated workflow surfaces
- authoritative project docs
- a bounded project-cognition route followed by live reads

When evidence lookup fails, report what was checked and ask one focused question. Do not ask broad questions such as "where is this implemented?" until bounded search and project-cognition navigation have failed.

## Project Cognition Policy

Project cognition is advisory navigation and coverage metadata. It is not authoritative evidence for current behavior.

The workflow should use `project-cognition` only when the discussion needs current-project grounding. It should not run cognition on every turn.

When current-project facts matter, use the discussion intent:

```text
project-cognition lexicon --intent discussion --query "$ARGUMENTS" --format json
project-cognition query --intent discussion --query-plan "<query_plan_json>" --format json
```

Using `intent=discussion` matters because discussion can continue through review and uncertain path coverage with live evidence, while planning or implementation intents may route too aggressively toward map maintenance.

The agent must translate lexicon output into a bounded query plan:

- `selected_concepts`: relevant concept IDs chosen by the agent.
- `rejected_concepts`: plausible but irrelevant candidates.
- `expanded_queries`: aliases or domain phrases that improve recall.
- `paths`: explicit path hints from the user or conversation.
- `selection_reason`: why these concepts were selected or rejected.

Then use the query result as follows:

- `readiness=ready`: read `minimal_live_reads`, then make claims only from live evidence.
- `readiness=review`: read `minimal_live_reads`, carry confidence labels, and ask only if live reads still leave the fact unresolved.
- `readiness=ambiguous`: present the likely candidates and ask the user to choose the intended target.
- `readiness=needs_update`: treat as map-quality advisory for ordinary discussion; use live reads and record the cognition gap. Recommend `sp-map-update` only when map maintenance becomes relevant or before a handoff needs stronger coverage.
- `readiness=needs_rebuild`: continue product framing if possible, but do not make project-specific technical claims until live evidence proves them or the user accepts an explicit assumption.
- `readiness=blocked`: report project cognition as unavailable or degraded for this discussion, continue with product framing or bounded live evidence when safe, and recommend map repair only when the user asks for map maintenance or handoff needs evidence that live reads cannot provide.

If these distinctions become machine-readable JSON contract fields, the implementation must update the JSON handoff template, downstream artifact validation, and related hook tests. If the first implementation keeps them inside `source_evidence` as prose or structured entries, the workflow guidance must say so explicitly and avoid implying a new top-level JSON schema.

The handoff evidence model must distinguish:

- `project_cognition_route`: what cognition suggested
- `live_code_evidence`: files, tests, scripts, configs, or docs actually read
- `evidence_status`: `proven`, `inferred`, `stale-advisory`, `missing`, or `conflict`
- `needs_refresh`: whether map maintenance is recommended

## Live Evidence Rule

`sp-discussion` may use project cognition to find likely owners, entrypoints, state surfaces, consumers, tests, and docs. It must not treat those results as proof.

Technical claims require live evidence from one or more of:

- source code
- tests
- scripts
- configuration
- command help output
- authoritative repository docs
- explicit user confirmation

If cognition and live evidence disagree, live evidence wins for the current discussion. The disagreement is recorded as a map maintenance note, not as a reason to ask the user to repeat facts that the code already proves.

## Lightweight Recovery Log

Ordinary turns append a compact event to `discussion-log.md`. The event is not a transcript. It records only durable meaning:

```markdown
## Event: 2026-05-21T12:00:00Z

- kind: product_decision | evidence_lookup | open_question | checkpoint | handoff_request | correction
- user_input_summary: User confirmed ordinary discussion should avoid refreshing every artifact.
- agent_conclusion: Use lightweight event logging on ordinary turns and refresh structured artifacts only at semantic checkpoints.
- evidence_used: docs/superpowers/specs/2026-05-19-project-cognition-advisory-map-design.md
- open_questions_delta: none
- checkpoint_required: true | false
```

The first implementation should use `discussion-log.md` event blocks rather than introducing a new `journal.ndjson` file. A later runtime-oriented increment may add `journal.ndjson` if machine recovery needs become stronger.

The event log exists to survive context compaction. It should be small enough that normal turns do not require reading or rewriting all discussion artifacts.

## Semantic Checkpoints

Structured files are refreshed only at semantic checkpoints.

Checkpoint triggers:

- user confirms a goal, non-goal, scope boundary, or important product decision
- discussion stage changes, such as product framing to technical options
- project evidence materially changes the understanding of the request
- a code fact was proven and must survive compaction
- evidence conflict is found
- the user asks for handoff or next-stage continuation
- context compaction risk is high
- an old discussion is resumed and the compact state is missing or stale

Checkpoint refresh targets:

- `discussion-state.md`: short current summary, stage, confirmed decisions, open questions, boundary status, latest evidence route, and next question.
- `requirements.md`: only when product requirements have changed enough to matter.
- `technical-options.md`: only when options are introduced, revised, selected, or rejected.
- `project-context.md`: only when source-grounding evidence or cognition coverage changes.
- `open-questions.md`: only when blocking or soft unknowns materially change.

Normal turns should not refresh all files just because a user answered one question.

## Recovery Flow

When resuming a discussion, `sp-discussion` uses a gradient:

1. Read `discussion-state.md`.
2. Read recent `discussion-log.md` events since the last checkpoint, or the last bounded event window when no checkpoint marker exists.
3. Read `requirements.md`, `technical-options.md`, `project-context.md`, or `open-questions.md` only when the state summary references them, is stale, is missing, or conflicts with recent events.
4. Reconstruct a short working summary in the response.
5. Continue with one evidence-backed answer or one genuinely necessary question.

This keeps recovery robust under context compression without making every turn pay the cost of full artifact reload.

## Strict Handoff Mode

Strict handoff mode starts only when the user explicitly asks to hand off, feed the result to `sp-specify`, continue to the next stage, or produce handoff artifacts.

In strict mode, existing safeguards remain:

- write or refresh `handoff-assessment.md`
- refresh the required discussion artifacts needed by the handoff
- after explicit handoff request and boundary lock, write `handoff-to-specify.md` and `handoff-to-specify.json` together as a draft pair
- require Markdown and JSON agreement on shared fields before asking the user to review the handoff
- include context boundary, implementation target, source evidence, blocking unknowns, downstream instructions, quality gate, and Must-Preserve Ledger
- preserve Senior Consequence Analysis obligations when triggered
- run handoff self-review and keep `quality_gate.status: draft` or equivalent until the review passes
- require user confirmation before marking the discussion `handoff-ready` or recommending `sp-specify`
- do not invoke `sp-specify` automatically

Strict mode is where the workflow acts like an audit package. Ordinary discussion turns should not.

## Artifact Behavior

The artifact set remains compatible with the current contract:

- `discussion-state.md`
- `discussion-log.md`
- `requirements.md`
- `technical-options.md`
- `project-context.md`
- `open-questions.md`
- `handoff-assessment.md` after explicit handoff request
- `handoff-to-specify.md` as a draft after explicit handoff request and boundary lock; mark it ready only after self-review and user confirmation
- `handoff-to-specify.json` as a draft companion after explicit handoff request and boundary lock; mark it ready only after self-review and user confirmation

The behavioral change is write cadence and evidence discipline, not artifact removal.

## Prompt Contract Changes

The `sp-discussion` command guidance should say:

- Start with turn classification.
- Ask product and boundary questions only after checking whether evidence can answer them.
- Use project cognition only when current-project facts matter.
- Use `intent=discussion` for cognition.
- Treat cognition as advisory navigation and code as authority.
- Read `minimal_live_reads` before making project-specific claims.
- Append compact events on ordinary turns.
- Refresh structured files only at checkpoint triggers.
- Enter strict handoff mode only on explicit user request.

Existing wording that calls project cognition "runtime truth" should be replaced with advisory wording:

```text
Treat project cognition as advisory navigation and coverage metadata. Use it to choose minimal live reads. Do not treat it as authoritative evidence for current behavior; prove project facts from live repository files before asking the user or making technical claims.
```

## Implementation Surfaces

The first implementation should sweep these surfaces:

- `templates/commands/discussion.md`
- `templates/command-partials/discussion/shell.md`
- `templates/discussion-state-template.md`
- `templates/brainstorming-handoff-specify-template.json` if evidence distinctions become JSON contract fields or structured `source_evidence` entries
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- generated integration guidance in `src/specify_cli/integrations/base.py`
- `src/specify_cli/hooks/artifact_validation.py` if JSON handoff validation must recognize the evidence distinctions
- README and `PROJECT-HANDBOOK.md`
- template, integration, and hook tests that assert discussion, cognition, handoff, and JSON validation contracts

If shared project-cognition guidance is updated, keep the change consistent with the advisory-map policy: map points, code proves.

## Testing Strategy

Update or add tests that assert:

- `sp-discussion` uses `project-cognition lexicon --intent discussion` and `project-cognition query --intent discussion`.
- Generated discussion guidance says cognition is advisory navigation, not runtime truth.
- Discussion guidance defines `readiness=blocked` as degraded advisory state, not an automatic hard stop for ordinary product discussion.
- Discussion guidance requires live repository evidence before project-specific technical claims.
- Guidance includes the Question Evidence Gate.
- Guidance includes lightweight event logging and semantic checkpoints.
- Normal turns are not instructed to refresh every discussion artifact.
- Handoff guidance permits a draft Markdown and JSON pair after explicit request and boundary lock, then permits `handoff-ready` only after self-review and user confirmation.
- If evidence distinctions become JSON fields, the JSON handoff template and artifact validation tests cover them.
- Strict handoff still requires the Markdown and JSON pair, Must-Preserve Ledger, self-review, and user confirmation.
- Existing integration renderers preserve the updated discussion contract across Markdown, TOML, and skills-based agents.

Runtime project-cognition query tests already cover `intent="discussion"` behavior for uncertain path gaps. The implementation should preserve those tests and add template-level coverage so the generated workflow actually uses the discussion intent.

## Acceptance Criteria

- A generated `sp-discussion` prompt tells the agent to classify each turn before asking questions.
- The prompt tells the agent not to ask user questions that can be answered from repository evidence.
- The prompt uses `project-cognition lexicon --intent discussion` and `project-cognition query --intent discussion`.
- The prompt states that project cognition is advisory and live code/docs/tests are authoritative for current behavior.
- The prompt treats `blocked` cognition readiness as degraded map guidance and continues only with product framing or live evidence that can be proved.
- The prompt defines checkpoint triggers and ordinary-turn lightweight event logging.
- Resume guidance reads compact state and recent events before full artifact reload.
- Handoff draft and ready states are separate: draft pair after explicit handoff request and boundary lock; `handoff-ready` only after self-review and user confirmation.
- Handoff guidance remains strict and compatible with existing downstream `sp-specify` integrity checks.
- Docs describe the same policy: code facts self-check, product judgment ask, cognition navigate, checkpoint by stage, strict handoff.
