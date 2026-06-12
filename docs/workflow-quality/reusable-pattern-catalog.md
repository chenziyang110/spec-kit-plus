# Reusable sp-* Workflow Pattern Catalog

Use this catalog when adding or modifying `sp-*` workflows. Reuse the smallest applicable pattern contract instead of copying long prompt blocks.

## Pattern Record Format

Each pattern records:

- Pattern name
- When to use
- Behavior it enforces
- Minimal prompt contract
- Required artifacts
- Handoff fields
- Validation signals
- Failure modes prevented
- Anti-patterns
- Reusable location
- Example workflows

## State Management Pattern

**When to use:** A workflow must resume, survive context compaction, track blockers, or preserve current phase.

**Behavior it enforces:** The agent can reconstruct the current stage, authority, blocker state, and next action without guessing.

**Minimal prompt contract:** Create or resume workflow state before substantive work. Keep state compact and current at phase transitions. Record status, current stage, blockers, next action, allowed writes, forbidden actions, authoritative files, and terminal state. Do not continue from stale or contradictory state without resolving it.

**Required artifacts:** `discussion-state.md`, `workflow-state.md`, quick `STATUS.md`, debug state, implement tracker, or equivalent.

**Handoff fields:** status, stage, blockers, next action, allowed writes, forbidden actions, authoritative files, terminal state.

**Validation signals:** Resume behavior is deterministic; next action, blockers, and terminal states are explicit; stale state is updated or rejected.

**Failure modes prevented:** Lost context, duplicate sessions, stale state, skipped blockers, phase jumps.

**Anti-patterns:** Long transcripts as state; state files without owners; terminal state mixed with next-action state.

**Reusable location:** Workflow state sections, command partials, and worker result envelopes.

**Example workflows:** `sp-discussion`, `sp-quick`, `sp-debug`, `sp-plan`, `sp-tasks`, `sp-implement`.

## Handoff Contract Pattern

**When to use:** A workflow transfers decisions, obligations, or execution contracts to another workflow.

**Behavior it enforces:** Downstream workflows receive bounded, reviewable, and consumable instructions instead of raw context.

**Minimal prompt contract:** Write handoff only when the handoff gate is satisfied. Include goal, boundary, source evidence, blockers, preserved decisions, downstream instructions, quality gate, and reopen conditions. Use Markdown for human review and JSON only when downstream automation consumes it. Do not mark ready until self-review and required user confirmation are recorded.

**Required artifacts:** `handoff-to-specify.md/json`, `plan-contract.json`, `handoff-to-tasks.json`, task packets, or worker result envelopes.

**Handoff fields:** goal, boundary, evidence, blockers, preserved decisions, downstream instructions, quality gate, reopen conditions, confirmation state.

**Validation signals:** Downstream artifacts preserve key decisions; Markdown and JSON agree on shared identifiers; hard blockers do not disappear.

**Failure modes prevented:** Context dumping, JSON/Markdown drift, unconfirmed handoff, lost MP/CA obligations, downstream guessing.

**Anti-patterns:** Dumping full chat history; using JSON when no automation consumes it; marking ready with unresolved hard blockers.

**Reusable location:** Handoff templates, plan/task contracts, and worker result schemas.

**Example workflows:** `sp-discussion` to `sp-specify`, `sp-plan` to `sp-tasks`, `sp-tasks` to `sp-implement`.

## Evidence Gate Pattern

**When to use:** A workflow makes claims about current project behavior, affected files, APIs, tests, runtime state, or external documentation.

**Behavior it enforces:** Project-specific claims are grounded in bounded live evidence.

**Minimal prompt contract:** Before project-specific claims, inspect bounded live evidence. Record verified facts, assumptions, evidence checked, and confidence. Use project cognition as navigation, not proof. Ask the user only when evidence cannot answer the question or judgment is required.

**Required artifacts:** Evidence notes, command output summaries, cited files, docs links, or user-confirmed assumptions.

**Handoff fields:** verified facts, evidence checked, assumptions, confidence, unresolved unknowns, owner or resolve phase.

**Validation signals:** Claims cite files, commands, tests, docs, or user-confirmed assumptions; unknowns have owners and resolve phases.

**Failure modes prevented:** Hallucinated repo behavior, stale documentation claims, unsupported scope decisions, false confidence.

**Anti-patterns:** Treating project maps as proof; broad claims from a single search result; asking the user before checking local evidence.

**Reusable location:** Exploration gates, research summaries, handoffs, and closeout reports.

**Example workflows:** `sp-discussion`, `sp-specify`, `sp-plan`, `sp-debug`, `sp-quick`, `sp-implement`.

## Boundary Gate Pattern

**When to use:** The active repository, target repository, reference source, external system, or implementation path is ambiguous.

**Behavior it enforces:** Work stops before claims or edits cross an unclear ownership boundary.

**Minimal prompt contract:** If target, reference, current repository role, external system, or target path is ambiguous, stop technical claims and ask one boundary question. Record current project roles, target project roles, reference sources, external systems, path status, boundary confidence, and boundary unknowns.

**Required artifacts:** Boundary note, state entry, handoff field, or task packet constraint.

**Handoff fields:** current project role, target project role, reference source, external systems, path status, confidence, unknowns.

**Validation signals:** The target path and source of truth are explicit before edits; references are not treated as implementation targets.

**Failure modes prevented:** Wrong repository, wrong evidence source, treating examples as implementation targets.

**Anti-patterns:** Editing the nearest matching path; using examples as source of truth; bundling multiple boundary questions.

**Reusable location:** Workflow preflight, task packet scope, and escalation records.

**Example workflows:** `sp-discussion`, `sp-specify`, `sp-plan`, `sp-implement`.

## Must-Preserve Pattern

**When to use:** Goals, non-goals, decisions, references, trade-offs, or unresolved questions would cause drift if lost.

**Behavior it enforces:** Drift-causing decisions remain visible until mapped, resolved, or explicitly deferred.

**Minimal prompt contract:** Record only drift-causing decisions as MP items. Each item has id, type, claim, source, downstream requirement, blocking level, owner, latest resolve phase, status, and reopen condition when needed. Map MP items into spec, plan, tasks, validation, or explicit deferral.

**Required artifacts:** MP table, alignment section, plan contract, task packet, validation closeout, or handoff entry.

**Handoff fields:** id, type, claim, source, downstream requirement, blocking level, owner, latest resolve phase, status, reopen condition.

**Validation signals:** MP items appear in the next consumer artifact or are explicitly deferred with owner and phase.

**Failure modes prevented:** Scope drift, lost non-goals, accidental reversal of user decisions, downstream reinterpretation.

**Anti-patterns:** Recording every note as MP; omitting source; resolving by silence; duplicating MP items without stable ids.

**Reusable location:** Alignment artifacts, handoffs, plan contracts, and task packets.

**Example workflows:** `sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`.

## Consequence Analysis Pattern

**When to use:** Changes affect lifecycle operations, running state, destructive behavior, shared state, compatibility, security-sensitive behavior, downstream consumers, or multiple plausible product behaviors.

**Behavior it enforces:** Risky consequences become explicit obligations with owners, validation, and stop conditions.

**Minimal prompt contract:** When consequence risk triggers, record affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and CA obligations. Each CA item has claim, affected objects, owner workflow, latest resolve phase, status, and stop-and-reopen condition. Do not mark ready while triggered obligations are unmapped or unsupported by validation.

**Required artifacts:** CA table, risk section, plan contract, task packet, test plan, or validation closeout.

**Handoff fields:** claim, affected objects, lifecycle state, dependency impact, owner workflow, latest resolve phase, validation need, status, stop-and-reopen condition.

**Validation signals:** Triggered risks have tests, checks, or explicit residual risk; ready state excludes unmapped CA obligations.

**Failure modes prevented:** Unsafe lifecycle changes, destructive side effects, compatibility breaks, hidden downstream consumer impact.

**Anti-patterns:** Treating risk as narrative only; marking ready without validation; burying stop conditions in prose.

**Reusable location:** Specification risk gates, plan validation gates, task packets, and closeout reports.

**Example workflows:** `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`.

## Subagent Dispatch Pattern

**When to use:** Work can be split into bounded independent lanes or needs parallel verification confidence.

**Behavior it enforces:** Parallel work has explicit read/write boundaries, acceptance criteria, and join conditions.

**Minimal prompt contract:** Choose dispatch shape from workload and safety. Each lane has purpose, read scope, write scope, forbidden scope, acceptance, verification, result format, and join condition. Do not dispatch if the work cannot be packetized safely. At join, consume structured results before declaring completion.

**Required artifacts:** Lane packet, task packet, worker prompt, result envelope, or join summary.

**Handoff fields:** purpose, read scope, write scope, forbidden scope, acceptance, verification, result format, join condition.

**Validation signals:** Lane outputs are independently checkable; no lane writes outside scope; join summary reconciles conflicts and residual risks.

**Failure modes prevented:** Overlapping edits, unreviewed agent output, missing verification, incompatible parallel results.

**Anti-patterns:** Dispatching tightly coupled work; giving broad write access; accepting worker completion without checking evidence.

**Reusable location:** Worker prompts, team execution plans, task packets, and join summaries.

**Example workflows:** `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`.

## Task Packet Pattern

**When to use:** A task needs to be executable by a worker or resumed independently.

**Behavior it enforces:** Each task is a bounded work order with enough context to execute and verify without expanding scope.

**Minimal prompt contract:** Each task packet includes task id, objective, dependencies, read scope, write scope, forbidden scope, acceptance criteria, verification commands, preserved MP/CA items, result envelope, and escalation path. Use batch defaults for repeated fields and per-task deltas for differences.

**Required artifacts:** Task packet Markdown/JSON, worker prompt, implementation plan task, or queue item.

**Handoff fields:** task id, objective, dependencies, read scope, write scope, forbidden scope, acceptance criteria, verification commands, MP/CA items, result envelope, escalation path.

**Validation signals:** A worker can execute the packet without asking for missing scope; verification commands are concrete; forbidden scope is enforceable.

**Failure modes prevented:** Ambiguous tasks, cross-task edits, missing dependencies, unverified worker results.

**Anti-patterns:** Repeating large shared context in every task; omitting forbidden scope; using vague acceptance criteria.

**Reusable location:** Task generation templates, worker prompts, and execution queues.

**Example workflows:** `sp-tasks`, `sp-implement`, `sp-plan`.

## Validation Closeout Pattern

**When to use:** A workflow claims completion, readiness, resolution, or handoff-ready status.

**Behavior it enforces:** Completion language is separated from evidence, gaps, and residual risk.

**Minimal prompt contract:** Record validation commands, results, acceptance coverage, unmapped obligations, residual risks, external validation gaps, dirty-state assumptions, and next action. Do not merge residual risk into completion language.

**Required artifacts:** Closeout section, validation report, handoff readiness note, worker result envelope, or final task status.

**Handoff fields:** commands, results, acceptance coverage, unmapped obligations, residual risks, external gaps, dirty-state assumptions, next action.

**Validation signals:** Fresh command output or explicit non-run rationale is present; residual risks are named separately from completed work.

**Failure modes prevented:** False completion, hidden test gaps, ignored dirty state, lost residual risk.

**Anti-patterns:** Claiming success before verification; saying tests pass without output; burying not-tested gaps in summary prose.

**Reusable location:** Final responses, handoffs, worker envelopes, and readiness gates.

**Example workflows:** `sp-quick`, `sp-debug`, `sp-plan`, `sp-tasks`, `sp-implement`.

## Escalation Pattern

**When to use:** Scope growth, missing evidence, root-cause uncertainty, unsafe consequence obligations, or impossible handoff prevents safe continuation.

**Behavior it enforces:** Hard blockers remain visible and are routed to the right owner or workflow.

**Minimal prompt contract:** When the current workflow cannot safely continue, record blocker, owner, latest safe resolve phase, stop condition, and recommended next workflow. Do not downgrade hard blockers to soft unknowns. Do not escalate when a bounded local resolution exists.

**Required artifacts:** Escalation note, blocker table, state update, handoff reopen condition, or final status.

**Handoff fields:** blocker, owner, latest safe resolve phase, stop condition, recommended next workflow, attempted local resolution.

**Validation signals:** The blocker is concrete; local resolution was considered; the next owner and reopen condition are explicit.

**Failure modes prevented:** Silent scope growth, unsafe continuation, unresolved root cause, impossible handoff, blocker laundering.

**Anti-patterns:** Escalating avoidable local work; vague blocker statements; softening hard blockers to keep moving.

**Reusable location:** State files, handoffs, closeout reports, and workflow routing gates.

**Example workflows:** `sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`.
