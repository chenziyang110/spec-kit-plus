# Simplify sp-specify Design

Date: 2026-05-22
Status: Design approved in conversation; pending written-spec review
Owner: Codex

## Goal

Rebuild `sp-specify` as a concise, user-confirmed specification workflow
modeled after the Superpowers brainstorming flow, while preserving only the
Spec Kit artifacts that downstream `sp-plan` needs.

The new rule is:

> `sp-specify` should help the user arrive at a reviewed spec. It should not
> run a private state machine whose complexity hides scope narrowing, semantic
> drift, or dropped intent.

This design intentionally reverses the recent direction that made
`sp-specify` depend on a heavy brainstorming kernel, append-only journal,
stage manifest, and multiple lock artifacts. Those mechanisms added recovery
structure, but they also made the workflow harder for users and agents to
understand, and they did not prevent the specific failure where ambiguous user
intent was silently narrowed before planning.

## Problem Statement

The current `sp-specify` workflow is too complex for its job. It mixes several
responsibilities:

- feature directory and branch setup
- project cognition intake
- a deterministic lock sequence
- JSON truth artifacts
- Markdown compilation
- discussion handoff validation
- consequence analysis
- release routing
- recovery after context compaction

The result is a long workflow contract that agents can follow mechanically
without preserving the user's meaning. In the observed discussion-to-specify
failure, upstream signals such as "real capabilities" and "optional model
fetch" were compiled into a narrower config-management feature. The later
artifacts were internally consistent, but they no longer represented the
original user intent.

The root issue is not that the workflow lacked more state. The issue is that
the workflow did not force a simple human-facing alignment loop before writing
planning-ready artifacts.

## Design Principles

### 1. User Meaning Before Workflow State

The workflow must first establish what the user means. Persisted state is
supporting evidence, not the primary product.

When a phrase has multiple plausible product meanings, especially around
capability, usability, realness, integrations, external systems, or acceptance
proof, `sp-specify` must ask the user to choose the intended meaning before it
can release to planning.

### 2. One Question At A Time

`sp-specify` should ask one high-impact question at a time. Grouped questions
are allowed only when all items are low-risk details inside an already
confirmed scope.

### 3. Alternatives Before Commitment

Before writing the final spec package, the workflow should present two or
three approaches with trade-offs and a recommendation. This gives the user a
clear chance to reject a narrower or different interpretation.

### 4. Design Review Before Plan

`sp-specify` must present the proposed spec shape in sections, get user
approval, write the artifacts, self-review them, then ask the user to review
the written files before recommending `/sp.plan`.

### 5. Minimal Durable State

Keep only state that downstream workflows or resume genuinely need:

- `spec.md`
- `alignment.md`
- `context.md`
- `references.md` when useful
- `workflow-state.md`
- `checklists/requirements.md`
- `brainstorming/handoff-to-specify.json` as a minimal compatibility artifact

The workflow should not require `brainstorming/journal.ndjson`,
`stage-manifest.json`, `facts.json`, `route.json`, `intent.json`,
`complexity.json`, or `domains.json` for normal `sp-specify` completion.

For the first implementation, `checklists/requirements.md` remains mandatory.
The checklist can be simplified, but it should not be made optional until a
separate change removes or rewrites every validator, template, integration
test, and downstream workflow assumption that still expects it.

`brainstorming/handoff-to-specify.json` also remains mandatory as a minimal
compatibility bridge. It should no longer encode the old lock kernel, but it
must keep enough fields for existing `sp-plan`, artifact validation, feature
scaffolding, and generated integration surfaces to continue working. Removing
that JSON file is a separate migration that must update all consumers in the
same change.

## Proposed Workflow

### Step 1: Explore Project Context

Read only enough local context to understand the request:

- the user's input
- existing `discussion` handoff files when supplied
- relevant repository files and documentation
- project rules, constitution, and learning memory when present
- project cognition results only as advisory navigation

The output of this step is a concise working understanding, not a JSON lock.

### Step 2: Clarify Purpose And Scope

Ask one question at a time when the answer can change scope, acceptance,
architecture, compatibility, security, data shape, external integration, or
downstream planning.

Low-risk defaults may be adopted silently, but they must be recorded in
`alignment.md` if they affect planning.

### Step 3: Decompose Ambiguous Terms

When user language includes high-value ambiguous terms, decompose the term into
concrete meanings and ask the user which meanings are in scope.

Trigger terms include:

- capability
- real
- usable
- works
- end-to-end
- full functionality
- ability
- fetch
- probe
- health
- test
- model
- endpoint
- integration
- auth
- available
- `能力`
- `真实`
- `可用`

Example question shape:

```text
When you say "provider capability", which meanings are in scope for this
version?

A. Configuration capability: read and write local CLI provider config.
B. Runtime config capability: enabled config is rediscovered and used next run.
C. Endpoint capability: provider endpoint, auth, and model can complete a real request.
D. Model catalog capability: fetch or list models from the provider endpoint.
```

The user's answer becomes the scope boundary. Meanings not selected are
deferred or out of scope only if the user confirms that disposition.

### Step 4: Present Approaches

Present two or three approaches with trade-offs and a recommendation before
committing to a spec shape.

The approaches should be product interpretations or delivery shapes, not
implementation details masquerading as scope decisions.

Recommended approach labels:

- user-intent-aligned path
- conservative compatibility path
- staged proof path

`sp-specify` must not treat smaller scope as the default. A smaller path is
valid only when the user asks for it, the input already defines it, or a named
constraint requires user confirmation.

### Step 5: Present Spec Sections For Approval

Before writing final artifacts, present the spec in sections scaled to the
feature:

- goal and user value
- confirmed scope
- capabilities
- semantic term decisions
- deferred or dropped intent
- out-of-scope items
- acceptance proof
- risks and open questions
- next workflow recommendation

Ask whether each section looks right before moving on when the section can
change product meaning.

### Step 6: Write The Artifact Package

Write the planning-ready package:

- `spec.md`: the user-facing requirement and acceptance surface
- `alignment.md`: confirmation state, ambiguity decisions, deferred or dropped
  intent, and readiness
- `context.md`: repository context, constraints, references, and planning notes
- `references.md`: source material when meaningful sources were used
- `workflow-state.md`: current command, current stage, open questions,
  next command, and review status
- `checklists/requirements.md`: first-release compatibility checklist
- `brainstorming/handoff-to-specify.json`: minimal compatibility handoff for
  downstream consumers

These files are the authoritative output of `sp-specify`.

The minimal compatibility handoff should contain only stable downstream fields:

- `version`
- `status`
- `entry_source`
- `source_handoff`
- `source_handoff_json`
- `source_files_read`
- `source_signal_disposition`
- `must_preserve`
- `coverage_status`
- `planning_gate_status`
- `hard_unknown_count`
- `open_conflict_count`
- `quality_gate`

It should not reintroduce `facts-lock`, `route-lock`, `intent-lock`,
`complexity-lock`, journal ranges, or stage-manifest semantics.

### Step 7: Self-Review

Review the written artifact package for:

- placeholders
- contradictions
- ambiguous requirements
- silent scope narrowing
- dropped upstream signals
- out-of-scope conflicts
- missing acceptance proof
- product minimization that the user did not confirm

Fix issues inline before asking for user review.

### Step 8: User Review Gate

Ask the user to review the written files.

Only after user review should `sp-specify` recommend exactly one next command:

- `/sp.plan` when the package is planning-ready
- `/sp.clarify` when planning-critical ambiguity remains
- `/sp.deep-research` when the requirements are clear but feasibility proof is
  still needed

## Discussion Handoff Behavior

`sp-discussion` handoffs are source material, not a bypass around user meaning.

When `sp-specify` starts from a discussion handoff, it must:

1. Read `handoff-to-specify.md` and its JSON companion when present.
2. Read the handoff-declared source files, not only the handoff summary.
3. At minimum, inspect `discussion-log.md`, `requirements.md`, and
   `open-questions.md` when those files exist in the discussion directory.
   Also inspect `technical-options.md` and `project-context.md` when the
   handoff names them or they exist and are relevant.
4. Extract upstream signals that can affect scope, acceptance, external
   integration, realness, usability, capability, tests, probes, models,
   endpoints, auth, or user-visible claims.
5. Ask the user to confirm any ambiguous or high-impact semantic terms.
6. Preserve each upstream signal as one of:
   - `preserved`
   - `in_scope`
   - `deferred`
   - `dropped`
   - `clarification_blocker`
7. Record the disposition in `alignment.md`.
8. Mirror the disposition rows into the minimal
   `brainstorming/handoff-to-specify.json` compatibility handoff.

No upstream capability-like signal may disappear between discussion and
specify.

This source-file sweep is mandatory because the discussion handoff itself can
be incomplete. `sp-specify` must not trust a ready handoff as proof that all
upstream intent was preserved. The handoff is a useful summary, but the
discussion source files are the audit surface for detecting signals that were
already dropped before handoff.

## Required Alignment Sections

`alignment.md` should become the main semantic traceability surface.

It must include these sections when relevant.

For discussion-originated features, every upstream capability-like signal found
in the source-file sweep must have exactly one disposition row. The workflow
must prove coverage by recording the source file and disposition, not by
recording only the signals that the handoff already mentioned.

Capability-like signals include wording about capability, realness, usability,
working behavior, end-to-end behavior, tests, probes, health checks, fetches,
models, endpoints, auth, external systems, and their Chinese equivalents such
as `能力`, `真实`, and `可用`.

### Semantic Term Decisions

| Term | Possible Meanings | Selected Meanings | Excluded Meanings | User Confirmation |
| --- | --- | --- | --- | --- |
| provider capability | config write; config rediscovery; endpoint request; model catalog fetch | config write; config rediscovery | endpoint request; model catalog fetch | user confirmed in specify |

### Upstream Intent Disposition

| Signal | Source | Disposition | Artifact Location | User Confirmed | Reopen Trigger |
| --- | --- | --- | --- | --- | --- |
| optional model fetch | `.specify/discussions/.../requirements.md:62` | deferred | `alignment.md#Deferred Or Dropped Intent` | yes | user asks whether provider really works |

### Out-Of-Scope Conflicts

| Upstream Signal | Source | Spec Disposition | Reason | User Confirmation | Reopen Trigger |
| --- | --- | --- | --- | --- | --- |
| model testing | discussion handoff | out of scope | v1 covers config management only | required | endpoint capability becomes in scope |

If an out-of-scope item conflicts with upstream wording and user confirmation
is missing, `sp-specify` must not recommend `/sp.plan`.

## Artifact Responsibilities

### `spec.md`

`spec.md` should contain the clean product requirement:

- feature goal
- user stories or usage scenarios
- functional requirements
- non-functional requirements when relevant
- explicit scope
- explicit out-of-scope items
- measurable success criteria
- acceptance proof expectations

It should not contain internal workflow machinery.

### `alignment.md`

`alignment.md` should contain how the workflow arrived at the spec:

- confirmed facts
- low-risk assumptions
- open questions
- semantic term decisions
- upstream intent disposition
- deferred or dropped intent
- out-of-scope conflicts
- user confirmations
- readiness decision

This file replaces the old need for multiple lock JSON files in normal
operation.

### `context.md`

`context.md` should contain planning context:

- relevant repository structure
- existing patterns
- project constraints
- integration boundaries
- references that planners should inspect
- risks that can change design or testing
- notes about project cognition advisory status when used

### `workflow-state.md`

`workflow-state.md` should be simple and resumable:

- active command
- status
- current stage
- last user-reviewed artifact state
- open questions
- blocker reason
- next command
- files written

It should not encode a full hidden state machine.

## Removed Or Downgraded Concepts

The following concepts should be removed from normal `sp-specify` guidance:

- mandatory `brainstorming/journal.ndjson`
- mandatory `stage-manifest.json`
- mandatory `facts-lock`
- mandatory `route-lock`
- mandatory `intent-lock`
- mandatory `complexity-lock`
- mandatory `domains.json`
- JSON-first recovery as the central spec truth
- multi-stage release-decision duplication
- Markdown/JSON mismatch gates as the normal path
- treating `handoff-to-specify.json` as the primary state source

Compatibility can remain for existing generated projects and existing tests
during migration, but new guidance should not teach these as the desired
workflow.

## Affected Surfaces

Expected implementation surfaces:

- `templates/commands/specify.md`
- `templates/command-partials/specify/shell.md`
- `templates/spec-template.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `templates/references-template.md`
- `templates/workflow-state-template.md`
- `templates/checklist-template.md`
- `templates/brainstorming-handoff-specify-template.json` for compatibility
  language only
- generated skill mirrors such as `.codex/skills/sp-specify/SKILL.md` through
  normal integration generation
- `README.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-handbook-template.md`
- template and integration tests that assert current `sp-specify` behavior

The implementation should avoid changing `sp-plan`, `sp-tasks`, and
`sp-implement` behavior. It may update downstream wording or intake references
only where required to keep the simplified `sp-specify` handoff compatible with
existing downstream consumers. This design is intentionally scoped to
`sp-specify`.

## Migration Strategy

### Phase 1: Replace The Workflow Contract

Rewrite `templates/commands/specify.md` around the simplified collaborative
flow. Remove duplicate and obsolete sections instead of patching around them.

Keep feature creation and existing artifact filenames stable.

Keep first-release compatibility outputs stable too:

- continue generating `checklists/requirements.md`
- continue generating a minimal `brainstorming/handoff-to-specify.json`
- keep feature scaffolding compatible with existing integration tests
- keep artifact validation compatible with the minimal handoff fields

If implementation chooses to stop generating any of these files, that same
implementation must update `sp-plan` intake, artifact validation, feature
scaffolding scripts, packaging, and generated integration tests in the same
pass. Partial removal is not allowed.

### Phase 2: Align The Shell Partial

Make `templates/command-partials/specify/shell.md` a concise summary of the
new workflow:

- context exploration
- one-question-at-a-time clarification
- semantic term decomposition
- approaches and recommendation
- section-by-section approval
- artifact writing
- self-review
- user review gate

### Phase 3: Adjust Artifact Templates

Add semantic traceability sections to `alignment.md` and scope/acceptance
sections to `spec.md` if the current templates do not already support them.

Keep `context.md` focused on planning context rather than workflow state.

### Phase 4: Update Tests And Docs

Replace tests that require the old lock kernel with tests that require:

- Superpowers-style clarification flow
- approach comparison before commitment
- user approval before artifact release
- semantic term decomposition
- upstream intent disposition
- no silent out-of-scope conflicts
- no default product minimization
- concise workflow-state guidance

Docs should describe `specify -> plan` as a reviewed spec handoff, not as a
JSON truth-lock pipeline.

## Testing Strategy

Tests should verify:

- `sp-specify` asks one high-impact question at a time.
- `sp-specify` requires 2-3 approaches before final spec commitment.
- `sp-specify` requires section-level user approval before writing or releasing
  artifacts.
- `sp-specify` records semantic term decisions for ambiguous capability-like
  language.
- `sp-specify` reads discussion source files, not only
  `handoff-to-specify.md/json`, before compiling a discussion-originated spec.
- `sp-specify` creates a disposition row for every capability-like upstream
  signal found in `discussion-log.md`, `requirements.md`, and
  `open-questions.md`.
- `alignment-template.md` contains `Semantic Term Decisions`.
- `alignment-template.md` contains `Upstream Intent Disposition`.
- `alignment-template.md` contains `Out-Of-Scope Conflicts`.
- `brainstorming-handoff-specify-template.json` supports the minimal
  compatibility handoff fields, including source files read and source signal
  disposition.
- `checklists/requirements.md` remains generated in the first simplified
  implementation.
- `specify.md` no longer requires the lock sequence as the normal workflow.
- `specify.md` does not teach `brainstorming/journal.ndjson` or
  `stage-manifest.json` as mandatory normal outputs.
- generated Codex, Claude, Gemini, Markdown, TOML, and skills-based surfaces
  receive the same simplified contract.
- README and handbook no longer describe the old lossless state model as the
  current mainline.

## Acceptance Criteria

The refactor is complete when:

- `sp-specify` reads like a concise collaborative specification workflow.
- The mainline user flow is context exploration, clarification, approaches,
  design approval, artifact writing, self-review, and user review.
- The workflow can no longer silently narrow ambiguous high-value terms without
  user confirmation.
- For discussion-originated features, `sp-specify` reads the discussion source
  files and records a disposition for every capability-like upstream signal,
  including signals missing from the handoff summary.
- Upstream discussion signals are preserved, deferred, dropped, or blocked
  explicitly in `alignment.md`.
- `checklists/requirements.md` and a minimal
  `brainstorming/handoff-to-specify.json` remain generated for first-release
  compatibility.
- Existing downstream artifact names remain stable enough for `sp-plan`.
- The old lock kernel and lossless journal concepts are absent from the normal
  generated `sp-specify` guidance.
- Tests and docs enforce the simplified behavior.

## Risks And Mitigations

### Risk: Losing Resume Robustness

Removing the journal and stage manifest reduces theoretical recovery detail.
The mitigation is to keep `workflow-state.md` simple, current, and human
readable, and to make written artifacts the reviewable source of truth.

### Risk: Breaking Existing Generated Projects

Existing generated projects may still contain old workflow assets. The
implementation should update generated templates and docs without requiring
existing feature directories to migrate old brainstorming files.

### Risk: Under-Specified Plans

Simplifying `sp-specify` must not make specs vague. The mitigation is stronger
human-facing gates: approach comparison, semantic decomposition, section
approval, self-review, and user review.

### Risk: Tests Preserve Obsolete Complexity

Many tests currently assert the old lock-kernel behavior. The implementation
must update tests to guard the new product contract rather than mechanically
preserve the obsolete workflow.

## Decision

Proceed with a full `sp-specify` simplification.

The new `sp-specify` should align with the Superpowers brainstorming model:
understand context, ask focused questions, compare approaches, present a
design, write the spec, self-review, and ask the user to review before
planning.

Spec Kit Plus should keep its necessary downstream artifacts, but the old
brainstorming kernel, lock sequence, journal, manifest, and JSON truth layer
should no longer be the normal `sp-specify` workflow.
