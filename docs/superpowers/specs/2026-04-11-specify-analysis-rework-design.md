# Specify Analysis Rework Design

**Date:** 2026-04-11
**Status:** Implemented
**Owner:** Codex

## Summary

This design replaces the current front-end workflow shape of `specify -> clarify -> plan -> tasks -> implement` with a stronger analysis-first workflow where `specify` becomes the single pre-planning entry point.

The current problem is not just naming. In practice, `specify` often records surface-level intent without fully decomposing the requirement, does not reliably absorb supplied reference material, and leaves too much hidden ambiguity for later phases. `clarify` then acts as a second pass, which splits responsibility across commands and makes requirement understanding feel optional instead of foundational.

The proposed system turns `specify` into a requirement-analysis orchestrator that:

- performs top-down analysis of the feature
- decomposes the feature into capabilities
- records supplied reference material without bloating the main spec
- distinguishes confirmed facts from inferred assumptions and open gaps
- triggers parallel sub-agent research only when the shape of the work justifies it

`clarify` exits the mainline workflow. Its successor is a new command, `spec-extend`, which revisits an existing spec, runs gap-finding plus optional multi-agent research, and writes targeted improvements back into the spec artifacts.

The design also adds a new stage explanation command, `explain`, that explains the current artifact in plain language with a richer TUI presentation.

## Problem Statement

The current workflow has four linked issues:

1. `specify` often captures what the user said without deeply unpacking it.
2. Requirement analysis is split across `specify` and `clarify`, so the main path does not force alignment early enough.
3. Reference material such as URLs, repos, and external documents is not treated as durable planning input.
4. Parallel agent work exists in some execution surfaces, but it is not treated as a stage-level policy that can trigger automatically when the task shape calls for it.

This creates a downstream failure pattern:

- `plan` receives an incomplete or shallow spec
- `tasks` decomposes around gaps instead of decisions
- `implement` either guesses or stalls
- user-provided references are forgotten or only partially absorbed

## Goals

- Make `specify` the only required pre-planning requirement entry point.
- Upgrade `specify` from recorder to analyst.
- Ensure a feature is analyzed top-down before planning starts.
- Preserve external references in a durable, compact form.
- Keep the main spec readable while retaining source traceability.
- Add a `spec-extend` command for post-spec enhancement.
- Add a stage explanation command with a polished TUI output.
- Introduce passive parallelism that triggers from stage conditions, not manual user choice.
- Update command guidance, templates, and tests so the new workflow is coherent end-to-end.

## Non-Goals

- Do not redesign the entire Spec Kit lifecycle outside the requirement-analysis problem.
- Do not turn every stage into always-on multi-agent execution.
- Do not replace implementation-time dispatching already handled by the Codex team runtime where that logic already fits.
- Do not store large raw source documents inside `spec.md`.

## User Intent

The desired behavior is not "make specs shorter." The desired behavior is "make requirements fully clear."

The user explicitly wants:

- top-down requirement analysis
- capability-by-capability decomposition
- scenario-aware thinking
- implementation-oriented understanding before planning
- explicit treatment of preconditions and dependencies
- durable memory of supplied references
- a single main entry point instead of `specify` plus a second alignment phase

The user does not want shallow summaries or compressed output that loses needed detail.

## Proposed Workflow

### New Mainline

```text
specify -> plan -> tasks -> implement
```

### Repositioned Commands

- `specify`: primary analysis and alignment entry point
- `spec-extend`: post-spec enhancement and gap-filling command
- `explain`: stage explanation command for current artifacts

### Legacy Command Treatment

- `clarify` exits the mainline flow
- `clarify` remains temporarily as a compatibility alias or shim
- `clarify` should route users toward `spec-extend` and explain that the old split workflow is deprecated

## Core Design

### 1. `specify` Becomes an Analysis Orchestrator

`specify` should no longer stop at a narrative feature statement. It must produce a requirement-analysis package.

Its default analysis shape is two-layered:

1. Feature-level analysis
2. Capability-level decomposition

This reflects the approved direction:

- first analyze the whole feature
- then decompose into capabilities
- then reconnect those capabilities to execution needs

### 2. `specify` Completion Standard

A `specify` run is complete only when it has produced enough information for `plan` to proceed without reopening the feature definition from scratch.

The minimum completion contract is:

- clear description of the feature goal
- target scenarios and expected behavior
- capability decomposition
- implementation-oriented analysis of each capability
- required preconditions and dependencies
- explicit statement of known risks and uncertainty
- classification of confirmed facts vs inferences vs open items
- retained reference mapping for user-supplied sources

This should be treated as "all necessary things," not a shortest-possible output.

### 3. Artifact Structure

The design uses a layered output model rather than forcing everything into one file.

#### `spec.md`

The main artifact consumed by later phases. It should remain readable and actionable.

Suggested structure:

1. Overview
   - what the feature is
   - why it exists
   - who it serves
   - what success looks like

2. Scenarios and usage paths
   - typical triggering situations
   - expected outcomes
   - notable edge cases

3. Capability decomposition
   - capability list
   - relationships between capabilities
   - sequencing or dependency notes

4. Implementation-oriented analysis
   - likely solution paths
   - critical preconditions
   - system or process dependencies
   - points that materially affect planning

5. Alignment state
   - confirmed
   - inferred
   - unresolved

6. Risks and gaps
   - conflicts
   - missing information
   - assumptions that could cause rework

#### `references.md`

Stores compact source memory.

For each reference:

- source identifier or URL
- what the source is
- why it matters
- what can be reused or learned from it
- where it influenced the spec

This preserves references without bloating the main spec.

#### Optional supporting analysis artifact

Depending on the existing Spec Kit conventions, a supporting file may also capture heavier reasoning or structured analysis. This can remain separate from `spec.md` if needed.

The important contract is:

- `spec.md` contains absorbed conclusions and execution-facing analysis
- references remain durable and discoverable
- later phases can revisit sources as needed

## New Command: `spec-extend`

### Purpose

`spec-extend` replaces the old role of `clarify`, but with broader responsibility.

It is not just a question-asking command. It is a post-spec enhancement command that:

- scans an existing spec for weak spots
- identifies misalignment, missing decomposition, shallow areas, or underused references
- optionally dispatches multiple agents to research or reason in parallel
- writes improvements back into the spec artifacts

### Typical Use Cases

- "This spec still feels shallow."
- "The spec is missing scenario detail."
- "The references were not absorbed properly."
- "I want the system to challenge the spec before planning."
- "There are unresolved assumptions and I want them investigated."

### Expected Behavior

`spec-extend` should:

1. read current spec artifacts
2. identify dissatisfaction or alignment gaps
3. classify issues by severity
4. decide whether single-session analysis is enough or whether multi-agent work is justified
5. update `spec.md` and related support artifacts

### Relationship to `specify`

- `specify` is the main path
- `spec-extend` is the enhancement path
- `plan` should be able to consume either a freshly completed `specify` output or a spec that was improved through `spec-extend`

## New Command: `explain`

### Purpose

`explain` translates the current stage artifact into plain language.

The output is not merely a summary. It should interpret the artifact in human terms:

- what this stage currently says
- what is already decided
- what remains open
- what the next stage will do with it

### Stage-Specific Behavior

When run against:

- `specify`: explain the current requirement package in plain language
- `plan`: explain the implementation direction in non-technical or mixed language
- `tasks`: explain what work is about to happen and how it is grouped
- `implement`: explain current progress, completed scope, and active risks

### TUI Expectations

The command should produce a polished terminal presentation, not a raw markdown dump.

Suggested presentation model:

- stage banner
- artifact status card
- primary narrative section
- open issues / risks panel
- next-step panel
- stage-specific visual adjustments

The TUI should feel intentionally designed rather than just boxed text.

## Passive Parallelism

### Principle

Parallel agent work should be system-triggered, not manually selected every time.

The user should not have to decide "now use multiple agents." The workflow should decide based on the structure of the task.

### Parallelism Types

#### Research Parallelism

Used in `specify` and `spec-extend`.

Trigger examples:

- multiple references must be processed
- the feature spans multiple problem domains
- external examples and internal repo state both need review
- uncertainty can be reduced through focused investigation

Possible split:

- one agent reviews external references
- one agent reviews local repo context
- one agent analyzes gaps, contradictions, or risks
- controller agent synthesizes and writes

#### Planning Parallelism

Used in `plan` and parts of `tasks`.

Trigger examples:

- spec contains multiple semi-independent capabilities
- capability-level analysis can happen separately
- cross-cutting validation is needed in parallel

Possible split:

- per-capability planning agents
- one cross-cutting validation agent
- controller agent synthesizes phases and sequencing

#### Implementation Parallelism

Used in `implement` when tasks are independently writable.

Trigger examples:

- disjoint write scopes
- low task coupling
- clear file ownership
- available runtime support

This should integrate with existing Codex team runtime capabilities rather than duplicating them.

### Do Not Auto-Trigger Parallelism When

- requirements are still fundamentally unclear
- the task is too coupled to split safely
- the available information is too sparse
- write scopes overlap heavily
- the stage primarily needs a user answer, not research

### Decision Inputs

A passive parallelism policy should consider:

- number of source materials
- number of capabilities
- independence of subproblems
- dependency coupling
- write-scope overlap
- stage-specific parallelism limits

## Migration Strategy

### Command Surface

- keep `specify`
- add `spec-extend`
- add `explain`
- keep `clarify` temporarily as deprecated compatibility entry point

### User Guidance Changes

Help text, onboarding flows, and success messages should stop teaching:

`specify -> clarify -> plan`

and instead teach:

`specify -> plan`

with `spec-extend` as optional enhancement after `specify`.

### Template Changes

The following files will need coordinated updates:

- `templates/commands/specify.md`
- `templates/commands/clarify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/spec-template.md`

Additional template files may be needed for:

- `references.md`
- `spec-extend`
- `explain`

### CLI and Registry Changes

User-facing command descriptions in `src/specify_cli/__init__.py` should be updated to reflect the new workflow.

The command catalog should clearly express:

- `specify` is analysis-first and complete enough for planning
- `clarify` is deprecated or rerouted
- `spec-extend` is the enhancement command
- `explain` is the stage interpretation command

### Runtime / Dispatch Changes

Passive parallelism should begin at the command/skill logic layer first.

Where existing runtime support already exists, especially under the Codex team runtime, it should be reused rather than replaced.

Relevant existing runtime surfaces include:

- `src/specify_cli/codex_team/auto_dispatch.py`
- `src/specify_cli/codex_team/runtime_bridge.py`

## Testing Impact

At minimum, the redesign requires:

- template tests for the new `specify` behavior
- compatibility tests for `clarify`
- tests for the new command surfaces
- tests for updated guidance and command descriptions
- tests for passive parallelism trigger rules
- tests for reference retention behavior
- tests for stage explanation output structure

Existing files likely affected include:

- `tests/test_alignment_templates.py`
- `tests/test_clarify_template.py`
- `tests/integrations/test_cli.py`
- `tests/codex_team/test_auto_dispatch.py`

New tests will likely be needed for:

- `spec-extend` integration behavior
- `explain` integration behavior
- reference artifact generation and reuse

## Risks

### Scope Risk

This is a deep workflow redesign, not a prompt tweak. It touches templates, user guidance, command descriptions, and potentially runtime dispatch behavior.

### Compatibility Risk

Existing users may still expect `clarify` to be part of the standard path. Migration messaging must be explicit and gradual.

### Overreach Risk

If `specify` is made "more powerful" without strong structure, it may simply become longer rather than better. The redesign must enforce layered analysis, not just more prose.

### Parallelism Risk

If passive parallelism is too eager, it will introduce cost and noise. Trigger conditions must be conservative.

## Recommended Delivery Sequence

1. Redesign templates and command guidance for the new workflow.
2. Introduce `spec-extend` and compatibility behavior for `clarify`.
3. Introduce the `explain` command and TUI presentation.
4. Add passive parallelism for `specify` and `spec-extend`.
5. Expand passive parallelism policies in `plan` and `implement` using existing runtime support where appropriate.

## Implementation Resolution

The implementation resolved the main naming and scope questions as follows:

- the stage explanation command shipped as `explain`
- the reference-memory artifact shipped as `references.md`
- stage explanation shipped as a single command with stage-aware behavior
- passive parallelism shipped first as conservative Python-side policy helpers that preserve existing runtime semantics
- `clarify` shipped as a compatibility bridge that redirects users toward `spec-extend`

## Decision

Proceed with the deep architecture option:

- `specify` becomes the sole pre-planning requirement-analysis entry point
- `clarify` exits the mainline flow
- `spec-extend` becomes the post-spec enhancement command
- a new explanation command provides stage-aware plain-language TUI output
- passive parallelism becomes a stage policy rather than a manual choice
