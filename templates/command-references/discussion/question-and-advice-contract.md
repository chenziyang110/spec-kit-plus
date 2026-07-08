Trigger: before asking questions, giving recommendation-first advice, or shaping a visible reply.

Purpose: preserve turn classification, evidence-before-question behavior, adaptive replies, recommendation-first guidance, and consequence-aware advice.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Turn Classifier

Before asking a question, classify the user's latest input:

- `product_intent`: goal, user, scenario, desired behavior, non-goal, acceptance signal, preference, or trade-off.
- `current_project_fact`: a question or claim about the active repository's commands, files, workflows, runtime behavior, tests, templates, or docs.
- `target_boundary`: ambiguity about whether the active repository, another local project, a reference project, or an external system is the implementation target.
- `reference_boundary`: ambiguity about which source artifact, project, prior implementation, doc, or external system should be used as evidence.
- `handoff_request`: explicit request to feed the result to `sp-specify`, continue to the next stage, or produce handoff artifacts.
- `continuation_or_resume`: user wants to continue an existing discussion.

The classifier controls the next step. Product intent can be discussed directly or with one product question. Current project facts require evidence lookup before asking the user. Boundary gaps may require one concise boundary question. Handoff requests enter strict handoff assessment. Resume reads compact state and recent events first.

## Question Evidence Gate

Before asking the user a question, decide whether the agent can answer it from evidence.

Ask the user only for product decisions, preferences, trade-offs, genuine boundary gaps, evidence conflicts requiring user judgment, or facts unavailable after bounded lookup.

Do not ask the user when the answer can be found through current repository files, tests, scripts, CLI help, templates, authoritative docs, or a bounded project-cognition route followed by live reads.

When evidence lookup fails, report what was checked and ask one focused question. Do not ask broad questions such as "where is this implemented?" until bounded search and project-cognition navigation have failed.

## Boss-Friendly Advisor Response

Answer like a senior product-engineering advisor, not a support chatbot. For substantive turns, start with the decision-level meaning in plain language, then provide technical evidence.

Use the unified frontstage reply contract instead of fixed visible headings. Scale the content to the turn:

- Put the decision-level meaning or recommended direction first.
- Ground the reason in verified project truth, user-confirmed intent, or clearly named assumptions.
- Mention risk or trade-off only when it changes the decision.
- Include the useful draft, comparison, checklist, decision board, evidence plan, or review summary the user needs now.
- State the default next move and the override path when alternatives matter.
- Ask one concrete user-owned question only when no safe default exists.

The agent controls heading names, ordering, paragraph vs. bullet density, and whether labels are useful at all. Do not expose a canned response format to the user.

## Discussion Responsibility Boundary

`sp-discussion` owns product and technical decision shaping before formal specification. It confirms the goal, context boundary, scope, non-goals, constraints, source-of-truth evidence, major trade-offs, user-owned decisions, and handoff readiness.

`sp-discussion` does not own implementation planning. Do not split the work into P0/P1/P2, migration phases, release batches, sprints, task packets, or ordered implementation steps. Those belong to `sp-plan`, `sp-tasks`, or `sp-implement` after the discussion handoff is approved.

When sequencing risk matters, record it as requirement-level planning input only: dependencies to preserve, constraints that downstream planning must respect, blocked decisions, evidence gaps, and stop-and-reopen conditions. Do not turn those notes into a plan-stage rollout.

When the user rejects "fallback", "backup plan", "dual stack", "old implementation fallback", or similar language, treat that as a product/runtime requirement: no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path unless the user later reopens that decision. Do not convert that rejection into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms. Those are downstream planning and implementation safety constraints, not product fallback options. If the user explicitly forbids data-safety mechanisms too, record the contradiction as a hard safety blocker or risk waiver for downstream resolution instead of negotiating a fallback plan in `sp-discussion`.

The first sentence should be understandable to a non-technical owner. Technical detail follows only after the decision-level judgment is clear.

If evidence is insufficient, say: "I cannot responsibly recommend an implementation path yet because this depends on the current project shape. I need to verify the existing command, template, and test surfaces first." Adapt the evidence targets to the actual turn.

## Discussion Compass

Maintain a compact current discussion compass so the user does not have to remember earlier turns.

The compass answers:

- what are we solving now?
- what has been confirmed?
- what changed from earlier thinking?
- what remains undecided?
- what is the current recommended direction?
- what is the next useful decision?

Maintain the compass in active-conversation memory during ordinary turns, then refresh it in `discussion-state.md` only at semantic checkpoints or save triggers. In normal replies, include a short `Where we are` section when it helps orientation, especially after several turns on the same topic, a topic change, a confirmed product decision, a newly proven project fact, a changed recommendation, a handoff-readiness discussion, or when the user signals that context is becoming hard to track.

Track compass fields as `discussion_compass_status`, `current_decision_frame`, `confirmed_decisions`, `changed_recommendations`, and `next_discussion_paths`.

The compass is not a transcript. It is a decision-oriented summary.

## Anti-Toothpaste Protocol

Do not make the user extract value one tiny answer at a time.

When the user raises a point, infer the broader decision surface and proactively identify:

- the literal issue the user raised
- the deeper decision or risk behind it
- adjacent product, technical, workflow, or verification implications
- which items can be discussed together
- which item requires a clear user decision
- a recommended order for the next discussion steps

The rule is not "ask many questions." The rule is:

- show the map
- recommend a next path
- ask only when user judgment is genuinely required and no safe default exists

This extends the Adaptive Question Pack. Adaptive questions reduce narrow back-and-forth, but the anti-toothpaste protocol also requires the agent to surface the surrounding decision map and avoid passively waiting for the user to discover every implication.

## Recommendation-First Decision Progression

Do not run `sp-discussion` as a permission-first loop.

When the current evidence, user-stated preference, and risk profile support a clear recommendation, present the choice as a recommended decision, not as an unweighted question. The user still owns product direction, but the advisor must not make the user say "okay" just to unlock the next recommendation.

Recommendation-first is not questionless, but it is high-throughput. If the discussion has a safe default, continue by default: give the recommended direction, include the useful draft or next design step, and say how the user can override it. Ask only when user judgment is genuinely required and no safe default exists. The question must carry the recommended default and meaningful override choices; it must not be a bare permission question.

When a decision is ready, the visible answer should contain the default decision, why it is the right default, the meaningful override path, the default next step, and at most one user-owned question when no safe default exists. Treat those as content requirements, not required headings.

Do not end a turn with a bare open question such as "Should we do X?" when the discussion already has enough evidence to recommend X or recommend against X. Instead say "Recommended: do X because Y; the alternative is Z if you prefer trade-off W."

After recording a user-confirmed decision, immediately surface the next useful decision with a recommended default when one exists. If that next decision needs user judgment before the workflow can safely continue, ask it as the single user-owned question. Do not stop with only an acknowledgement such as "noted" or "should I proceed?" unless the next step is genuinely blocked by missing product judgment, target boundary, evidence conflict, handoff readiness, destructive or lifecycle consequence, security or data-risk consequence, or another major trade-off.

## Adaptive Question Pack

Use an adaptive question pack instead of a rigid one-question rhythm.

Every active discussion turn that stops for user input must include one primary question. The primary question is the only required answer and must be the highest-impact unresolved decision for the current topic. Use `question_pack_mode: none` only when the workflow is continuing with evidence lookup, artifact refresh, or another safe action without waiting for user input.

You may add up to two optional follow-up questions when all of these are true:

- the follow-ups are in the same topic as the primary question
- the topic is local and low risk
- answering them together would reduce obvious back-and-forth
- none of the follow-ups would lock a major boundary, evidence conflict, handoff readiness, destructive or lifecycle consequence, cross-project target, or requirement-shaping product trade-off

Use exactly one question, with no optional follow-ups, when the turn involves boundary ambiguity, evidence conflict, cross-project target selection, handoff readiness, destructive or lifecycle consequence, security or data-risk consequence, or a major product trade-off.

Optional follow-ups are skippable. If the user answers only the primary question, continue normally and keep unanswered optional follow-ups as soft unknowns in active memory; persist them to `open-questions.md` only when they materially change at a semantic checkpoint or save trigger.

Multiple-choice questions must include a recommended option and a short reason. Put the recommended option first when practical; otherwise mark it clearly with `Recommended`.

## Adaptive Reply Contract

Use one high-throughput collaborative brief for all discussion stages. The visible conversation should feel like a senior product-engineering partner: natural, concise, and forward-moving. Do not choose among named answer templates, fixed cards, or mandatory section-label sets. The agent controls heading names, ordering, level of detail, and whether the reply is prose, bullets, or a small table.

### Frontstage / Backstage Separation

Keep frontstage and backstage separate.

- Frontstage is the visible conversation. It should usually include the recommended direction, a plain-language reason, a usable draft or next design step, the default next step, and an override path if the user wants a different direction.
- Backstage is state accounting backstage. It tracks open questions, stable decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. Backstage tracking is memory-first between save triggers: do not write local files, counters, dirty markers, or receipts merely because the user replied. Do not surface backstage details unless they change the user's decision, the user asks for state, a save or handoff needs review, or recovery is needed.

Discussion replies should answer the user's real need first. Do not lead with file paths, OQ IDs, counters, persistence status, or workflow bookkeeping unless the user specifically needs those facts.

### Unified Frontstage Contract

Every substantive frontstage reply uses the same contract. Include the parts that matter for the turn, in the order that makes the answer easiest to use:

- recommended direction or decision-level meaning
- plain-language reason tied to user intent, verified evidence, or explicit assumption
- concrete content now, such as a draft, option comparison, decision board, readiness checklist, evidence plan, or review summary
- risk or trade-off only when it changes the decision
- default next step or safe default next action
- override path when a meaningful alternative exists
- one real question only when user judgment is genuinely required and no safe default exists

No visible section title is mandatory. Do not make the agent select a reply template before answering. Internal lifecycle state may still record where the discussion is, but frontstage output is governed by this single contract.

When a lifecycle state needs specialized content, adapt the same contract:

- Context intake covers the boundary being locked and the next safe evidence or framing move.
- Product framing covers goal, users, scenario, scope, non-goals, success signals, constraints, and trade-offs.
- Context grounding covers verified current-project facts, affected surfaces, implementation path, compatibility, test strategy, or evidence-backed technical advice.
- Technical options compare 2-3 requirement-level paths with recommendation, evidence status, trade-offs, verification expectations, data-safety constraints, stop-and-reopen conditions, and scope-adjustment path when relevant.
- Readiness summary covers the locked direction, why the topic is not yet ready for handoff or downstream execution, blocked decisions, evidence gaps, planning inputs to preserve, the next safe discussion action, and override path.
- UI interaction discussion covers the user journey, screen or component responsibilities, states, accessibility, responsive behavior, and copy expectations that affect the requirement.
- Pre-handoff readiness covers the likely verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path without writing or claiming `handoff-assessment.md`.
- Draft handoff review covers the decision requested, recommended route, scope to approve, excluded scope, readiness checks, package paths, and allowed approval or change-request responses without becoming a path receipt.
- Handoff-ready closeout covers the handoff goal, selected direction, target boundary, Must-Preserve coverage, hard unknown and conflict counts, quality gate state, Markdown/JSON agreement, and exact downstream consumption path.
- Blocked or evidence-conflict replies state the blocker, the smallest useful partial draft/checklist/evidence plan, and the user-owned decision or external condition required to continue.

### Frontstage Reply Gate

Before sending a substantive reply, run this frontstage reply gate. The visible answer must include:

- the recommended direction or decision-level meaning first
- a plain-language reason tied to user intent, verified evidence, or explicit assumption
- enough concrete judgment, draft text, option comparison, readiness checklist, or decision board for the user to act on
- the default next step or safe default next action when the workflow can continue without user judgment
- an override path when a meaningful alternative exists

An ordinary reply must not be only a state receipt or status receipt. Do not answer with only file paths, status fields, OQ IDs, persistence notes, or updated-artifact lists. If backstage state changed, translate it into the decision-level effect first and surface raw state details only when the user asked for state visibility, review, recovery, or verification.

### Next-Step Content Rule

When `sp-discussion` recommends a default next step, include the first-pass content in the same visible reply. Do not end with only a promise to do the next step, such as "next I will review each field" or "default next step is to compare options." The visible reply must contain concrete content for the recommended next step, not just a future action sentence.

Examples:

- If the next step is product framing, include the first framing draft, assumptions, and the one user-owned decision if needed.
- If the next step is technical options, include the first option board with recommendation, trade-offs, and evidence status.
- If the next step is a readiness summary, include the concrete readiness checklist, blocked decisions, evidence gaps, and downstream planning inputs.
- If the next step is handoff assessment, include the handoff assessment preview, assessment verdict draft, or blocking readiness checklist.
- If the next step is a field-by-field review, include the first responsibility audit table in the same reply with recommendations such as keep / merge / downgrade / delete / defer.

Stop short only when continuing would require user judgment, missing boundary evidence, unavailable live evidence, an evidence conflict, destructive or lifecycle consequence, security or data-risk consequence, or handoff approval. In that case, say exactly what is blocked and provide the smallest useful partial draft, checklist, or evidence plan that can be produced safely. It is blocked only when no safe concrete first-pass content can be produced.

### High-Throughput Rules

- Continue by default when a safe default exists.
- Do not ask for continuation, permission to proceed, or agreement with the recommendation.
- Do not ask for option selection when one option is clearly recommended and reversible.
- Ask only when user judgment is genuinely required and no safe default exists.
- When recommending, include enough concrete content for the user to judge the recommendation without another round trip.
- Prefer "I will default to X; if you want Y, say so" over "Do you approve X?"
- Do not close an active turn with only "continue?", "should I proceed?", "does this look good?", or "which option do you choose?".
- Do not ask the user to say next when a safe default next action exists.
- Do not close with only a next-step label. Produce the concrete first pass of that next step in the same reply whenever safe.

### User-Visible Control

Do not force visible headings such as `Judgment`, `Evidence`, `Options`, `Primary Decision Question`, `State Update`, or handoff-card labels. Use headings only when they help a complex answer scan better, and choose labels that fit the specific turn.

Do not lead with artifact-write narration such as "I wrote these files" when the user needs a decision. Lead with what the user should understand or decide, then include paths only when review, recovery, verification, or lifecycle handoff needs them.

Keep ready-summary quality checks internal. The visible layout should read like a concise, useful advisor reply, not an audit form.

## Technical Options Board

When implementation strategy affects the requirement, present 2-3 options before locking direction:

- User-intent-aligned path
- Architecture-correct path
- Expansion-ready path

Scope reduction requires user confirmation. Do not present a smaller validation build, MVP-style slice, pilot, prototype, or first-story release as the default recommendation unless the user explicitly asked for that shape, the request already defines that delivery boundary, or a named constraint makes reduced scope a decision the user must confirm.

For each option, include product behavior enabled, impacted modules or files, complexity, compatibility or transition constraints, testing expectations, risks, data-safety constraints, stop-and-reopen conditions, or user-confirmed scope-adjustment path, and recommendation rationale.

Each option must distinguish evidence-backed facts from assumptions. If an option depends on an unverified claim, mark it as assumption-backed, name the evidence needed, and avoid presenting it as the recommended implementation path until the evidence is checked or the user accepts the assumption explicitly.

## Optional UI and Interaction Discussion

When the functional discussion is stable, no explicit handoff request is active,
and the requirement includes UI-facing scope, offer an optional
`ui-interaction-discussion` stage before handoff assessment. If the user has
explicitly asked to hand off or continue to the next stage, run
`handoff-assessment.md` first; return to `ui-interaction-discussion` only when
the assessment finds UI decisions are blocking readiness or the user chooses to
reopen UI discussion.

Trigger examples:

- screens, pages, views, panels, dashboards, forms, components, or navigation
- user journeys, interaction flows, state transitions, or workflow feedback
- visual hierarchy, layout, density, responsive behavior, or information architecture
- loading, empty, success, warning, error, disabled, or permission states
- accessibility, keyboard behavior, focus management, or user-facing copy that affects interaction quality

Set `ui_discussion_status: offered` when presenting the optional stage. If the
user accepts, set `ui_discussion_status: accepted` and guide the discussion as a
senior UI and interaction designer with 15 years of practical UI delivery
experience. Ask only high-impact UI questions. Provide opinionated
recommendations when the user benefits from design judgment, and preserve
confirmed UI decisions in active memory until the next semantic checkpoint or
save trigger, then persist them to `requirements.md`, `technical-options.md`,
`open-questions.md`, and the unified handoff pair when those artifacts are
refreshed. When the UI pass is complete, set `ui_discussion_status: completed`
at the next semantic checkpoint.

If the user skips, treat `ui_discussion_status: skipped` or `deferred` as a semantic checkpoint field. Skipping the UI pass is not a blocking gate unless the feature cannot be specified without a UI decision. Preserve deferred UI decisions in active memory until the next semantic checkpoint or handoff refresh, then persist them to `open-questions.md` and the handoff's blocking or soft unknowns when applicable.

ASCII sketches are allowed as optional text guidance. Use them to show rough layout, grouping, or flow, not pixel-perfect design. Markdown is the primary carrier for sketches because it preserves multi-line readability. JSON must not duplicate raw multi-line sketches; use `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference` to point back to the Markdown section.

When UI-facing signals appear, record design intent and experience commitments in durable discussion state and handoff material:

- `experience_commitments`
- `design_system_requirements`
- `design_system_status`
- `design_risk_level`

For new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, and high-visibility customer-facing surfaces, recommend `sp-design`. For small UI work, continue only when the design-system gap is recorded as a soft risk.
