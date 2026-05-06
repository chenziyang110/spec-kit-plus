# sp-specify Fixed Heavy Discovery Design

**Date:** 2026-05-06
**Status:** Proposed
**Owner:** Codex

## Summary

This design replaces `sp-specify`'s internal dynamic strategy model with a
fixed heavy discovery lifecycle.

The workflow keeps the same top-level artifact set and the same possible final
handoff commands, but it no longer changes its internal requirement-discovery
depth based on task classification, scenario profile, coverage mode, or other
adaptive routing surfaces.

The approved direction is:

- always treat short user descriptions as potentially incomplete, high-risk
  requirement inputs
- always run the same six-stage discovery lifecycle
- always use the same three bounded subagent roles
- always walk the same six requirement domains in the same order
- always run batch-level adversarial challenge and a final completeness audit
- only decide `/sp-plan`, `/sp-clarify`, or `/sp-deep-research` after the full
  fixed lifecycle completes

The goal is not to preserve the user's original wording. The goal is to
converge on the most complete useful requirement shape the current product can
support without silently omitting critical capability, boundary, or dependency
information.

## Problem Statement

`sp-specify` currently contains multiple dynamic decision surfaces that can
improve efficiency on some requests but also create a recurring failure mode on
short or underspecified inputs:

- the workflow can scale its rigor up or down depending on inferred task shape
- the workflow can switch coverage depth based on dynamic triggers
- the workflow can vary its collaboration structure and question strategy
- the workflow can treat requirement discovery as "good enough" before the
  feature has been expanded into a complete usable shape

That is specifically dangerous when the user's request is short, because short
requests are often the highest-risk requirement inputs:

- a one-line request can hide multiple affected surfaces
- the user may describe the desired outcome but omit the operational shape
- the request may sound narrow while actually requiring front-end, back-end,
  data, lifecycle, permission, and downstream behavior decisions
- the workflow can accidentally preserve only what the user said explicitly,
  instead of what the resulting feature must include to be genuinely usable

The product problem is therefore not "the workflow asked too few questions" in
the abstract. The deeper problem is:

- requirement discovery can stop before the feature reaches a complete useful
  form
- critical gaps can survive because dynamic depth controls decide they are not
  worth probing yet
- downstream planning inherits artifacts that look structured but still omit
  indispensable requirement content

## Goals

- Make `sp-specify` default to a fixed heavy discovery posture.
- Treat every incoming request as potentially incomplete regardless of how short
  or polished the user's initial description is.
- Force requirement discovery toward the user's likely ideal complete feature
  shape rather than only the text they happened to provide.
- Keep discovery bounded by current project and product scope.
- Preserve the existing command surface and artifact filenames.
- Preserve the existing final handoff set:
  - `/sp-plan`
  - `/sp-clarify`
  - `/sp-deep-research`

## Non-Goals

- Do not remove `sp-clarify` or `sp-deep-research` as explicit commands.
- Do not redesign `sp-debug` in this change.
- Do not change `sp-specify` into an implementation workflow.
- Do not require full-repository deep scans before initial requirement analysis.
- Do not preserve legacy dynamic routing fields in user-facing `sp-specify`
  artifacts just for continuity.

## Design Principles

### 1. Short Input Is Not Low Risk

A short feature request should be treated as a compressed statement of intent,
not as proof that the underlying work is simple.

### 2. Discovery Must Seek Completeness, Not Parity With User Wording

The workflow should not aim to capture only what the user explicitly said. It
should aim to discover the complete useful shape of what the user is actually
trying to achieve.

### 3. Completeness Is Bounded

The completeness target is shaped by two limits:

- the current project's product boundary
- the domain's normal completeness expectations for that type of capability

The workflow should use domain expectations to find omissions, but it must not
invent a different product.

### 4. Fixed Lifecycle Beats Adaptive Rigor

For `sp-specify`, correctness and completeness matter more than adapting the
workflow to look lighter or more efficient on easier requests.

### 5. Challenge Must Be Continuous

It is not enough to ask all questions first and critique later. Discovery must
run in a loop:

- ask a bounded batch
- record the result
- challenge the result
- reopen if needed

### 6. Planning Readiness Is a Consequence, Not the Primary Aim

`sp-specify` does not exist merely to exit into `/sp-plan` quickly. It exists to
produce a requirement package that deserves to be planned.

## Approved Direction

### Fixed Six-Stage Lifecycle

`sp-specify` should always execute these six internal stages in order:

1. `intent-analysis`
2. `intent-confirmation`
3. `question-batch`
4. `batch-adversarial-review`
5. `completeness-audit`
6. `final-handoff-decision`

The workflow must not dynamically switch into alternate internal lifecycles
based on inferred request shape.

### Fixed Subagent Roles

`sp-specify` should use only three fixed subagent roles:

- `intent-analyst`
- `adversarial-reviewer`
- `completeness-auditor`

The workflow should not create ad hoc analysis roles for this command family.

### Fixed Requirement Domains

The workflow should always process these six domains in this exact order:

1. `goal-and-users`
2. `triggers-and-primary-flow`
3. `boundaries-and-non-goals`
4. `failure-paths-exceptions-and-permissions`
5. `dependencies-constraints-and-upstream-downstream-impact`
6. `acceptance-and-completeness-gap-closure`

The workflow may skip asking a user question for a domain only when that domain
is already closed by strong existing evidence. It may not skip the domain
itself.

## Lifecycle Semantics

### Stage 1: `intent-analysis`

Purpose:

- expand the user's initial statement into an initial feature-shape hypothesis
- identify likely affected surfaces without overcommitting to implementation

Behavior:

- first read the user request plus `PROJECT-HANDBOOK.md` and relevant
  project-map context
- use minimal targeted code scanning only when handbook and map evidence cannot
  establish a plausible impact surface
- do not default to a full repository deep scan

Output expectations:

- what the user is probably trying to achieve
- what a complete usable version of that capability probably includes
- which product surfaces, modules, or boundaries are likely involved
- which areas are still ambiguous enough to require structured questioning

### Stage 2: `intent-confirmation`

Purpose:

- cheaply correct the biggest misunderstanding before deeper questioning begins

Behavior:

- the leader gives the user a short current-understanding summary
- the summary should name the likely intended outcome and the major affected
  surfaces
- this is a lightweight correction gate, not a full approval ceremony

### Stage 3: `question-batch`

Purpose:

- drive the feature toward a complete useful shape domain by domain

Behavior:

- each batch may ask at most three questions
- each batch covers one active domain only
- the workflow must not mix multiple domains in the same batch
- the next domain does not open until the current domain is closed

Question strategy:

- use the fixed domain order
- ask only questions that materially reduce completeness risk
- if a domain is already sufficiently known from user input or repository
  evidence, mark it `closed-by-existing-evidence`

### Stage 4: `batch-adversarial-review`

Purpose:

- challenge each completed question batch before the workflow moves on

Behavior:

- this stage runs after every answered question batch
- it must test whether the batch introduced contradiction, hidden dependency,
  project-boundary conflict, or a completeness-threatening omission
- it is not optional and must not be deferred until the end

If a critical problem is found:

- the current domain becomes `reopen-required`
- the next batch stays in the same domain
- the workflow must not proceed to the next domain while a critical gap remains

### Stage 5: `completeness-audit`

Purpose:

- decide whether the requirement package has reached a complete enough shape to
  end discovery

Behavior:

- run only after all fixed domains have been processed
- evaluate the whole feature, not only the most recent domain
- explicitly test for missing capability, missing boundaries, missing adjacent
  effects, and domain-normal omissions that would make the final feature
  unusable

If the audit fails:

- discovery reopens
- the workflow returns to `question-batch` on the relevant domain
- the workflow cannot move to final handoff

### Stage 6: `final-handoff-decision`

Purpose:

- choose the downstream workflow after the full fixed lifecycle has completed

This stage is the only place where `sp-specify` may choose between:

- `/sp-plan`
- `/sp-clarify`
- `/sp-deep-research`

The fixed mapping is:

- `/sp-plan`
  - all domains are closed
  - completeness audit passed
  - no planning-critical requirement gaps remain
  - no key implementation-chain feasibility gap remains
- `/sp-clarify`
  - one or more domains still contain requirement-level critical gaps,
    contradictions, or `force-carried-with-risk`
- `/sp-deep-research`
  - requirement discovery is complete enough, but a key implementation chain,
    external dependency, or feasibility proof is still missing

`sp-specify` must not jump to `/sp-clarify` or `/sp-deep-research` early.
Those remain valid downstream commands, but only after the full internal
lifecycle has run.

## Domain Closure Rules

Each fixed domain must end in exactly one of these states:

- `confirmed-by-user`
- `closed-by-existing-evidence`
- `force-carried-with-risk`
- `reopen-required`

`force-carried-with-risk` is not planning-ready closure.

If any domain remains `force-carried-with-risk` at the end of discovery:

- the workflow must not hand off to `/sp-plan`
- the final handoff must become either `/sp-clarify` or `/sp-deep-research`
  depending on whether the remaining problem is requirement incompleteness or
  feasibility incompleteness

## Artifact Responsibilities

The file set remains:

- `spec.md`
- `alignment.md`
- `context.md`
- `references.md`
- `workflow-state.md`
- `specify-draft.md`

The responsibilities change.

### `spec.md`

`spec.md` becomes the final requirement artifact with a fixed dual-layer model:

1. `Ideal Complete Requirement Shape`
2. `Current Delivery Boundary`

The first layer captures the complete useful feature form the workflow believes
the user actually wants within project and product limits.

The second layer captures what this repository should currently plan and
deliver.

This split prevents two failure modes:

- underspecifying the user's actual need because the original input was short
- overcommitting planning to the entire ideal shape when the current project
  boundary or release scope is narrower

### `alignment.md`

`alignment.md` becomes the completeness convergence report.

It should record:

- initial intent-analysis conclusions
- domain-by-domain closure outcomes
- batch-level adversarial findings and dispositions
- critical gaps that blocked closure and how they were resolved
- the final completeness-audit result and the reason the workflow may or may not
  exit discovery

It should no longer act as a dynamic routing report driven by task
classification, scenario profile, coverage mode, or observer-gate overlays.

### `context.md`

`context.md` becomes the impact-and-constraint map.

It should record:

- affected modules and surfaces
- upstream and downstream dependencies
- product-boundary constraints that limit the feature shape
- existing capabilities that change what "complete" means in this repository
- domain-normal considerations the user did not name directly
- critical adjacent effects that would make the feature unusable if omitted

### `references.md`

`references.md` remains mandatory.

It should record all evidence sources used to support:

- completeness judgments
- boundary judgments
- compatibility judgments
- impact-surface judgments

Sources may include:

- project docs
- project-map entries
- existing repository features
- user-provided examples
- external references

### `specify-draft.md`

`specify-draft.md` becomes the content ledger for the whole discovery run.

It should carry:

- stage-local findings
- current active domain
- question batches and answer summaries
- adversarial-review findings
- domain statuses
- reopen reasons
- unresolved completeness gaps
- final audit inputs

This is the primary running content ledger for `sp-specify`.

### `workflow-state.md`

`workflow-state.md` becomes a minimal fixed-state tracker.

It should carry only:

- current lifecycle stage
- current active domain
- next action
- blocker or reopen reason
- final downstream handoff decision when reached

It should not continue to expose old dynamic strategy fields such as:

- task classification
- active profile
- coverage mode
- observer gate

## Template Changes

### `templates/commands/specify.md`

Update the command contract so it:

- teaches the fixed six-stage lifecycle
- teaches the three fixed subagent roles
- teaches the six fixed domains in fixed order
- removes internal dynamic routing semantics for this command
- preserves only the final handoff mapping

### `templates/spec-template.md`

Update the spec template so it explicitly supports:

- `Ideal Complete Requirement Shape`
- `Current Delivery Boundary`

### `templates/alignment-template.md`

Replace dynamic-routing-oriented sections with convergence-oriented sections,
including:

- initial intent analysis
- domain closure log
- batch adversarial review summary
- critical gap handling
- completeness audit outcome

### `templates/context-template.md`

Strengthen context toward:

- impact surface mapping
- dependency and boundary mapping
- completeness-sensitive adjacent effects
- project constraints that shape completeness

### `templates/specify-draft-template.md`

Promote the draft from a loose clarification ledger into a batch-and-challenge
ledger that matches the fixed lifecycle.

### `templates/workflow-state-template.md`

Reduce the state template to the fixed six-stage model and remove dynamic
strategy fields from the primary `sp-specify` state surface.

### `templates/references-template.md`

Keep the template but add mapping expectations for which sources justified which
completeness or boundary conclusions.

## Shared Product Surface Impact

This is a shared workflow change, not a Codex-only tweak.

At minimum the implementation pass should review:

- shared `sp-specify` command template
- `sp-specify` artifact templates
- shared partials used by `sp-specify`
- integration addenda that currently inject old dynamic `sp-specify` language
- README and handbook guidance that still teach dynamic `sp-specify` behavior
- tests that currently assert old `sp-specify` routing semantics

## Compatibility Position

This design preserves:

- the existence of `sp-specify`
- the artifact filenames
- the downstream command set

This design intentionally does not preserve:

- user-facing dynamic `sp-specify` strategy fields
- internal adaptive rigor semantics as the primary workflow model

## Risks

- The fixed heavy lifecycle will be slower than the current adaptive version on
  genuinely simple requests.
- Artifact templates will need coordinated updates to avoid preserving old
  semantics under new names.
- Documentation and tests may initially drift if the implementation updates only
  the command template and not the artifact templates.

These costs are accepted because the design prioritizes completeness and
consistency over adaptive lightness.

## Acceptance Criteria

This design is satisfied when:

- `sp-specify` always runs the same six internal stages
- `sp-specify` always uses the same three subagent role types
- all six fixed domains are always processed in fixed order
- each batch is limited to one domain and at most three questions
- batch-level adversarial review is mandatory
- final completeness audit is mandatory
- `/sp-plan`, `/sp-clarify`, and `/sp-deep-research` remain valid final
  outcomes, but only after the fixed lifecycle completes
- the primary `sp-specify` artifacts no longer expose old dynamic strategy
  surfaces as first-class workflow semantics

## Next Step

After spec review, create an implementation plan that updates:

- `templates/commands/specify.md`
- `templates/spec-template.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `templates/specify-draft-template.md`
- `templates/workflow-state-template.md`
- `templates/references-template.md`
- shared partials or integration addenda that still inject old `sp-specify`
  dynamic strategy language
- affected docs and tests
