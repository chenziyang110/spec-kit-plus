# sp-* Workflow Compact Quality Standard Design

## Purpose

SuperSpec's `sp-*` workflows already produce useful implementation artifacts and validated downstream work. The next optimization target is not merely "shorter prompts." The target is compactness without meaningful quality loss:

```text
maximize prompt and intermediate-artifact cost reduction
subject to quality retention >= 98%
```

This design defines a reusable standard for evaluating, adding, modifying, and compressing `sp-*` workflow prompts and their produced artifacts. It applies to command prompts, shared partials, passive workflow skills, handoff documents, workflow state files, specification packages, plans, tasks, task packets, implementation closeout artifacts, quick task state, and debug outputs.

The standard should prevent regressions where a prompt is made shorter but the workflow becomes less reliable, less recoverable, or harder for downstream agents to consume.

## Goals

- Identify prompt text that genuinely improves workflow behavior.
- Identify correct but low-value prompt text that can be deleted, merged, or moved.
- Reduce prompt, handoff, and intermediate artifact size while preserving current workflow quality.
- Build a reusable pattern catalog for common workflow behaviors such as state management, handoff contracts, subagent dispatch, task packets, evidence gates, and validation closeout.
- Give agents a repeatable self-review rubric before changing any `sp-*` workflow.
- Make future `sp-*` additions reuse proven patterns instead of copying long prompt blocks.

## Non-Goals

- Do not rewrite any existing `sp-*` workflow as part of this design.
- Do not define a one-size-fits-all artifact schema for every workflow.
- Do not optimize for shortest possible prompts at the expense of quality.
- Do not replace existing workflow tests, skill-flow maps, or artifact validators.
- Do not treat successful output alone as proof that a prompt is optimal.

## Core Principle

A high-quality compact workflow uses the least necessary information to reliably trigger correct behavior and produce downstream artifacts that require less guessing, less rework, and less repeated validation.

```text
workflow value = behavior contribution + downstream consumability + failure prevention
workflow cost = prompt length + artifact length + cognitive load + duplicated maintenance surface
optimization win = quality retention >= 98% and workflow cost decreases materially
```

Correctness alone is not enough. A sentence can be true and still be low value if deleting or merging it does not reduce behavior quality. Conversely, a long section can be worth keeping if it prevents a high-cost failure and no cheaper mechanism exists yet.

## Evaluation Scope

The standard evaluates four layers together.

| Layer | Examples | Evaluation Question |
| --- | --- | --- |
| Prompt layer | `templates/commands/**`, command partials, passive skills | Does this text reliably change agent behavior? |
| Handoff layer | `handoff-to-specify.md/json`, `plan-contract.json`, `handoff-to-tasks.json` | Can the next workflow consume this quickly and safely? |
| Planning artifact layer | `spec.md`, `alignment.md`, `context.md`, `plan.md`, `tasks.md`, task packets | Did upstream intent become executable and verifiable work? |
| Execution evidence layer | worker results, quick `STATUS.md`, debug state, implementation validation | Did the workflow prove the intended behavior and record residual risk clearly? |

The standard evaluates a chain, not an isolated prompt. A prompt is high value only when its intended behavior can be observed in downstream artifacts or in avoided failure modes.

## Calibration Samples

Initial calibration should use real downstream workflow outputs from `F:\AI_WORK\jx-skills`.

| Sample | Use |
| --- | --- |
| `.specify/features/006-tui-interaction-redesign` | Main success sample because it reaches `sp-implement` completed with validation evidence. |
| `.specify/discussions/tui-interaction-redesign` | Discussion-to-specify handoff quality and UI decision preservation. |
| `.specify/features/005-gitlab-source-install` | Complex handoff, MP/CA carry-forward, task generation, task packet, and validation-route sample. |
| `.planning/quick/*` | Lightweight quick state compactness, resume behavior, and validation closeout samples. |
| Future `sp-debug` samples | Diagnostic workflow compactness and root-cause evidence samples. |

The first standard pass should not assume any sample is perfect. Successful outputs can still contain waste, duplicated fields, or prompt effects that are masked by model capability, manual correction, or tests.

## Quality Score

Each baseline and candidate workflow chain receives a 100-point quality score.

| Dimension | Points | What To Check |
| --- | ---: | --- |
| Behavior correctness | 20 | The agent follows the intended workflow, does not skip stages, does not overreach, and does not ask avoidable questions. |
| Intent preservation | 15 | Goals, scope, non-goals, user decisions, MP items, and CA obligations survive across handoff and downstream artifacts. |
| Evidence quality | 15 | Project facts use live evidence or named authoritative evidence; assumptions and unknowns are explicit. |
| Handoff consumability | 15 | The next workflow can quickly identify goal, boundary, blockers, key decisions, and reopen conditions. |
| Downstream executability | 15 | Spec, plan, tasks, and packets can drive implementation without reinterpreting upstream intent. |
| Validation closure | 15 | Validation proves acceptance and critical obligations, not merely that some tests ran. |
| Residual risk handling | 5 | External validation gaps, dirty state, manual checks, and residual risks are explicit and not hidden in completion language. |

Acceptance rule:

```text
candidate_quality_score / baseline_quality_score >= 0.98
```

A candidate that drops below the threshold is rejected even when it is much shorter. A candidate that improves quality and reduces cost should become a reusable pattern.

## Efficiency Metrics

Efficiency is measured across the chain.

| Cost | Measurement |
| --- | --- |
| Prompt cost | Lines, words, estimated tokens, repeated rules, number of sections, number of authority surfaces. |
| Handoff cost | Lines, field count, MP/CA count, duplicate sections, hard-vs-soft blocker clarity, estimated downstream read time. |
| Artifact cost | Spec/plan/tasks/task packet total size, repeated metadata, fields with no consumer, redundant evidence copies. |
| Cognitive cost | Time for a human or agent to find goal, boundary, blockers, validation, and next action. |
| Maintenance cost | Number of places a rule must be changed to update behavior safely. |

Useful derived metrics:

```text
prompt_reduction = 1 - candidate_prompt_cost / baseline_prompt_cost
artifact_reduction = 1 - candidate_artifact_cost / baseline_artifact_cost
quality_retention = candidate_quality_score / baseline_quality_score
```

Cost reduction is not valid if it only moves the burden downstream. For example, a shorter handoff that forces `sp-plan` to reread a full discussion log and infer decisions again is not compact.

## Behavior-Artifact Backtrace

Every evaluated prompt unit should be traced through behavior and artifacts.

| Field | Meaning |
| --- | --- |
| `unit_id` | Stable evaluation id, such as `discussion.truth-pass.01`. |
| `source_location` | File and section where the unit appears. |
| `unit_text_summary` | Short summary of the prompt or artifact section. |
| `intended_behavior` | The concrete behavior it tries to cause. |
| `artifact_trace` | Where the behavior appears downstream. |
| `failure_mode_prevented` | Specific failure the unit prevents. |
| `cost_level` | `low`, `medium`, or `high`. |
| `duplication_status` | `unique`, `partial_duplicate`, or `full_duplicate`. |
| `verification_surface` | Test, schema, workflow state, field, human review, or sample evidence. |
| `score` | `0` to `3` local value score. |
| `decision` | `keep`, `merge`, `move`, `tighten`, or `delete`. |
| `rationale` | One concise reason. |

Local value score:

| Score | Meaning |
| ---: | --- |
| 3 | Clear behavior constraint, downstream trace, important failure prevention, and reasonable cost. |
| 2 | Valuable but duplicated, too long, or in the wrong authority location. |
| 1 | Correct principle, but better as a shared pattern, template, test, or checklist. |
| 0 | No traceable behavior contribution and no meaningful failure prevention. |

Decision rules:

| Condition | Decision |
| --- | --- |
| Score 3 and unique | Keep. |
| Score 3 but duplicated | Merge to one authority location. |
| Score 2 | Tighten or merge. |
| Score 1 | Move to shared pattern, template, test, schema, or reviewer checklist. |
| Score 0 | Delete. |
| High failure prevention but high cost | Keep the intent and rewrite shorter. |
| Multi-workflow behavior | Move to the reusable pattern catalog or shared partial. |
| Workflow-specific exception | Keep near the workflow that owns the exception. |

## Reusable Workflow Pattern Catalog

The standard should extract proven patterns from current `sp-*` workflows. New workflows should reuse these patterns instead of copying long prompt text.

Each pattern uses this structure:

```text
Pattern name:
When to use:
Behavior it enforces:
Minimal prompt contract:
Required artifacts:
Handoff fields:
Validation signals:
Failure modes prevented:
Anti-patterns:
Reusable location:
Example workflows:
```

### State Management Pattern

When to use:
Any workflow that must resume, survive context compaction, track blockers, or preserve a current phase.

Behavior it enforces:
Maintain a compact source of truth for current state, terminal status, blockers, allowed writes, forbidden actions, next action, and recovery path.

Minimal prompt contract:

```text
Create or resume the workflow state before substantive work.
Keep it compact and current at phase transitions.
Record status, current stage, blockers, next action, allowed writes, forbidden actions, authoritative files, and terminal state.
Do not continue from stale or contradictory state without resolving it.
```

Required artifacts:
Workflow-specific state such as `discussion-state.md`, `workflow-state.md`, quick `STATUS.md`, debug state, or implement tracker.

Validation signals:
Resume behavior is deterministic; next action is clear; blockers and terminal states are explicit.

Failure modes prevented:
Lost context, duplicate sessions, acting on stale state, skipping a blocker, and accidental phase jumps.

Example workflows:
`sp-discussion`, `sp-quick`, `sp-debug`, `sp-plan`, `sp-tasks`, `sp-implement`.

### Handoff Contract Pattern

When to use:
A workflow transfers decisions, obligations, or execution contracts to another workflow.

Behavior it enforces:
Create a compact, reviewable contract that downstream can consume without reinterpreting upstream context.

Minimal prompt contract:

```text
Write handoff only when the handoff gate is satisfied.
Include goal, boundary, source evidence, blockers, preserved decisions, downstream instructions, quality gate, and reopen conditions.
Use Markdown for human review and JSON only when downstream automation consumes it.
Do not mark ready until self-review and required user confirmation are recorded.
```

Required artifacts:
Depends on the workflow: `handoff-to-specify.md/json`, `plan-contract.json`, `handoff-to-tasks.json`, task packets, worker result envelopes.

Validation signals:
Downstream artifacts preserve key decisions; Markdown and JSON agree on shared identifiers; hard blockers do not disappear.

Failure modes prevented:
Context dumping, JSON/Markdown drift, unconfirmed handoff, lost MP/CA obligations, and downstream guessing.

Example workflows:
`sp-discussion -> sp-specify`, `sp-plan -> sp-tasks`, `sp-tasks -> sp-implement`, delegated worker handoffs.

### Evidence Gate Pattern

When to use:
A workflow makes claims about current project behavior, affected files, APIs, tests, runtime state, or external documentation.

Behavior it enforces:
Separate verified facts from assumptions and use live evidence for current project claims.

Minimal prompt contract:

```text
Before project-specific claims, inspect bounded live evidence.
Record verified facts, assumptions, evidence checked, and confidence.
Use project cognition as navigation, not proof.
Ask the user only when evidence cannot answer the question or judgment is required.
```

Required artifacts:
Evidence fields in project context, workflow state, references, debug reports, validation closeout, or implementation summaries.

Validation signals:
Claims cite files, commands, tests, docs, or user-confirmed assumptions; unknowns have owners and resolve phases.

Failure modes prevented:
Confident hallucinated implementation paths, avoidable user questions, and stale project cognition treated as authority.

Example workflows:
`sp-discussion`, `sp-specify`, `sp-plan`, `sp-debug`, `sp-quick`, `sp-implement`.

### Boundary Gate Pattern

When to use:
The active repository, target repository, reference source, external system, or implementation path is ambiguous.

Behavior it enforces:
Lock the target and evidence boundary before technicalizing.

Minimal prompt contract:

```text
If target, reference, current repository role, external system, or target path is ambiguous, stop technical claims and ask one boundary question.
Record current project roles, target project roles, reference sources, external systems, path status, boundary confidence, and boundary unknowns.
```

Required artifacts:
Boundary fields in discussion state, handoff, specify context, plan, or workflow state.

Validation signals:
Downstream knows whether the current repository is target, reference, both, or unrelated.

Failure modes prevented:
Applying evidence from the wrong project, changing the wrong repository, or treating examples as implementation targets.

Example workflows:
`sp-discussion`, `sp-specify`, `sp-deep-research`, cross-project reference flows.

### Must-Preserve Pattern

When to use:
User decisions, goals, non-goals, references, trade-offs, or unresolved questions would cause drift if lost.

Behavior it enforces:
Preserve only semantic units that must survive downstream transformation.

Minimal prompt contract:

```text
Record only drift-causing decisions as MP items.
Each item has id, type, claim, source, downstream requirement, blocking level, owner, latest resolve phase, status, and reopen condition when needed.
Map MP items into spec, plan, tasks, validation, or explicit deferral.
```

Required artifacts:
Must-Preserve ledger in handoff and carry-forward sections in downstream artifacts.

Validation signals:
Each important upstream decision has a disposition; no key decision silently disappears.

Failure modes prevented:
Scope drift, lost non-goals, accidental reversal of user choices, and downstream reinterpretation.

Example workflows:
`sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`.

### Consequence Analysis Pattern

When to use:
Changes affect lifecycle operations, running state, destructive behavior, shared state, compatibility, security-sensitive behavior, downstream consumers, or multiple plausible product behaviors.

Behavior it enforces:
Turn consequence risk into explicit obligations and validation requirements.

Minimal prompt contract:

```text
When consequence risk triggers, record affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and CA obligations.
Each CA item has a claim, affected objects, owner workflow, latest resolve phase, status, and stop-and-reopen condition.
Do not mark ready while triggered obligations are unmapped or unsupported by validation.
```

Required artifacts:
CA obligations in spec/context/plan/tasks/handoff/validation as appropriate.

Validation signals:
Risky lifecycle and shared-state behavior has tests, recovery, or stop-and-reopen coverage.

Failure modes prevented:
Surface-only fixes, unsafe mutation semantics, destructive ambiguity, and downstream compatibility breakage.

Example workflows:
`sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`, `sp-quick`, `sp-debug`, `sp-implement`.

### Subagent Dispatch Pattern

When to use:
The workflow can be split into bounded independent lanes or needs parallel verification confidence.

Behavior it enforces:
Dispatch only when lanes are safe, bounded, and have structured result contracts.

Minimal prompt contract:

```text
Choose dispatch shape from workload and safety.
Each lane has purpose, read scope, write scope, forbidden scope, acceptance, verification, result format, and join condition.
Do not dispatch if the work cannot be packetized safely.
At join, consume structured results before declaring completion.
```

Required artifacts:
Lane handoffs, worker result envelopes, task packets, evidence indexes, checkpoints, or workflow state.

Validation signals:
No write-set conflicts; join points are explicit; worker results are accepted or rejected with reasons.

Failure modes prevented:
Parallel agents editing the same files blindly, lost handoffs, incomplete joins, and leader closing before consuming results.

Example workflows:
`sp-plan`, `sp-tasks`, `sp-quick`, `sp-implement`, heavy research lanes.

### Task Packet Pattern

When to use:
A task needs to be executable by a worker or resumed independently.

Behavior it enforces:
Make task execution self-contained without copying the full plan into every packet.

Minimal prompt contract:

```text
Each task packet includes task id, objective, dependencies, read scope, write scope, forbidden scope, acceptance criteria, verification commands, preserved MP/CA items, result envelope, and escalation path.
Use batch defaults for repeated fields and per-task deltas for differences.
```

Required artifacts:
`tasks.md`, `task-index.json`, `task-packets/*.json`, worker results.

Validation signals:
Packets parse, match task index, preserve obligations, and define safe execution boundaries.

Failure modes prevented:
Worker ambiguity, scope overreach, missing verification, and task graph drift.

Example workflows:
`sp-tasks`, `sp-implement`, `sp-quick`.

### Validation Closeout Pattern

When to use:
A workflow claims completion, readiness, resolution, or handoff-ready status.

Behavior it enforces:
Completion is evidence-backed and residual risk is explicit.

Minimal prompt contract:

```text
Record validation commands, results, acceptance coverage, unmapped obligations, residual risks, external validation gaps, dirty-state assumptions, and next action.
Do not merge residual risk into completion language.
```

Required artifacts:
Implementation validation, debug closeout, quick summary, workflow state, or worker result.

Validation signals:
The closeout maps tests and evidence to acceptance criteria and preserved obligations.

Failure modes prevented:
False completion, unverified acceptance, hidden external risk, and missing follow-up action.

Example workflows:
`sp-quick`, `sp-debug`, `sp-implement`, `sp-tasks`.

### Escalation Pattern

When to use:
The workflow discovers scope growth, missing evidence, root-cause uncertainty, unsafe consequence obligations, or an impossible handoff.

Behavior it enforces:
Route to the right workflow or block with a concrete reason instead of forcing progress.

Minimal prompt contract:

```text
When the current workflow cannot safely continue, record blocker, owner, latest safe resolve phase, stop condition, and recommended next workflow.
Do not downgrade hard blockers to soft unknowns.
Do not escalate when a bounded local resolution exists.
```

Required artifacts:
Workflow state, open questions, handoff blockers, debug findings, or quick status.

Validation signals:
The next command is unambiguous and the reason is tied to a concrete limit.

Failure modes prevented:
Wrong workflow route, overbuilt quick tasks, underspecified plans, and endless clarification loops.

Example workflows:
All `sp-*` workflows.

## Compactness Rules By Layer

### Prompt Layer

High-value prompt text:

- Specifies behavior, trigger, stop condition, artifact, or validation.
- Prevents a named failure mode.
- Has a downstream trace.
- Lives in the smallest useful authority location.
- Uses examples sparingly and only when they prevent ambiguity.

Low-value prompt text:

- Says "be clear", "be careful", or "ensure quality" without behavior.
- Explains why at length when the agent only needs what/when/stop.
- Repeats an existing rule without adding trigger, exception, or consequence.
- Defines a field that no downstream workflow consumes.
- Is copied across workflows instead of becoming a shared pattern.

### Handoff Layer

A compact handoff:

- Lets the next workflow identify goal, boundary, blockers, preserved decisions, and next action quickly.
- Contains only semantic units that can cause drift or execution failure if lost.
- Separates human review and machine consumption.
- Uses hard/soft unknowns accurately.
- Has clear reopen conditions.

A noisy handoff:

- Dumps discussion history instead of decisions.
- Treats every detail as an obligation.
- Has many fields but no priority.
- Requires downstream to infer what is hard, soft, deferred, or obsolete.
- Allows Markdown and JSON to drift.

### Spec/Plan/Tasks Layer

Compact downstream artifacts:

- Carry forward upstream decisions without restating the whole handoff.
- Explain trade-offs where they affect implementation.
- Use shared defaults and per-item deltas.
- Keep tasks independently executable.
- Keep validation tied to acceptance and preserved obligations.

Noisy downstream artifacts:

- Repeat the same MP/CA text in every section without mapping value.
- List files without explaining ownership, dependencies, or validation.
- Create task packets that are longer than needed because every common field is repeated.
- Treat test output as proof without saying what behavior it proves.

## Required Change Protocol

Every `sp-*` prompt or artifact-format optimization must include this record before implementation:

```text
workflow:
target_layer:
optimization_goal:
protected_quality:
baseline_prompt_cost:
baseline_artifact_cost:
baseline_quality_score:
candidate_prompt_cost:
candidate_artifact_cost:
candidate_quality_score:
quality_retention:
expected_cost_reduction:
compression_candidates:
replacement_protection:
validation_plan:
decision:
```

Required validation:

- Static contract: relevant tests and skill-flow maps still pass.
- Artifact contract: sample outputs preserve core MP/CA, boundary, evidence, and next-action semantics.
- Efficiency contract: prompt/artifact/cognitive cost decreases without moving cost downstream.

## Rollout Strategy

1. Build the inventory of all `sp-*` prompts, partials, passive skills, and generated workflow artifacts.
2. Measure prompt and artifact baseline costs.
3. Score the calibration samples.
4. Run Behavior-Artifact Backtrace for high-impact workflow patterns.
5. Extract the reusable pattern catalog.
6. Use the standard to evaluate one workflow as a pilot.
7. Apply the pilot only after the candidate demonstrates `quality_retention >= 0.98`.
8. Record accepted and rejected optimizations as future examples.

The first pilot should be selected after the standard is reviewed. Good candidates are `sp-discussion` for prompt/handoff compression or `sp-tasks` for task-packet and repeated metadata compression.

## Open Decisions

- Whether quality scoring should be manual first or assisted by a script that collects line/word/token and artifact-size metrics.
- Whether accepted patterns should live in this standard document, a separate pattern catalog, or shared prompt partials.
- Whether compression evaluation records should live under `docs/superpowers/specs/`, `docs/superpowers/evaluations/`, or workflow-local notes.
- How many real samples are required before a pattern graduates from "candidate" to "standard."

## Acceptance Criteria

- The standard can evaluate prompt text, handoff documents, downstream planning artifacts, and implementation validation as one chain.
- The standard makes compactness subordinate to quality retention.
- The standard defines a 100-point Quality Score and measurable cost metrics.
- The standard includes reusable patterns for state management, handoff contracts, evidence gates, boundary gates, Must-Preserve carry-forward, consequence analysis, subagent dispatch, task packets, validation closeout, and escalation.
- The standard provides a required change protocol for future `sp-*` modifications.
- The standard does not require changing any existing workflow before it has been used to evaluate a candidate.

## Self-Review Notes

- No implementation edits are specified in this design.
- The design is intentionally workflow-wide, not `sp-discussion`-specific.
- The design treats current successful outputs as calibration evidence, not as proof that every current prompt is optimal.
- The design defines compactness as whole-chain cost reduction, not prompt length alone.
