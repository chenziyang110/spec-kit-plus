# Learning Command-Surface Safety Design

**Date:** 2026-05-05  
**Status:** Approved for implementation planning  
**Scope:** Learning runtime hooks, learning-oriented workflow templates, passive learning skill guidance, quickstart docs, and contract tests that govern the learning command surface  
**Primary goal:** Prevent Spec Kit Plus from emitting learning-related command advice that looks executable but cannot actually be run

## Problem

The passive learning layer currently mixes three different kinds of text under
one command-shaped presentation:

- real CLI commands that are complete and executable
- command-shape examples that still require operator substitution
- runtime recovery advice that omits required arguments but still looks like a
  shell-ready command

This causes a real product failure.

When a workflow hits the learning gate, runtime hook output can tell an agent to
run a command such as:

- `specify hook capture-learning --command <name> ...`

That string is not directly executable because the real CLI surface requires
additional options such as `--type`, `--summary`, and `--evidence`.

The result is predictable:

- agents copy the suggested command
- the CLI returns a `Usage:` error
- the user sees a failure caused by our own guidance instead of their work

This is not just a documentation clarity issue. It is a contract problem across
runtime hooks, templates, docs, and tests.

## Goals

- Ensure learning runtime output never tells an agent to run a command that is
  not executable as written
- Separate executable command advice from descriptive command-surface guidance
- Keep the learning command surface accurate across runtime hooks, templates,
  passive skills, and docs
- Remove self-contradictory learning guidance from `sp-fast` and `sp-quick`
- Add regression coverage so placeholder-style fake commands cannot re-enter the
  learning runtime contract

## Non-Goals

- A full repository-wide cleanup of every placeholder command outside the
  learning surfaces
- Redesigning the actual `specify learning` or `specify hook` CLI option model
- Adding a new workflow for learning management
- Rewriting unrelated documentation tone or structure outside the learning
  surfaces touched by this fix
- Expanding this pass into non-learning runtime messaging unless it is required
  for shared enforcement primitives

## Verified Current-State Findings

The following facts were verified in the current repository state before this
design was written:

- the real `specify hook review-learning` surface requires `--command` and
  `--terminal-status`
- the real `specify hook capture-learning` surface requires `--command`,
  `--type`, `--summary`, and `--evidence`
- runtime hook recovery actions currently emit placeholder-style commands such
  as `specify hook capture-learning --command {command_name} ...`
- workflow templates and docs widely use command-shaped learning examples with
  `...` and `<...>` placeholders
- `sp-fast` currently says to skip all learning hooks and capture, but later in
  the same template also instructs a learning capture closeout
- `sp-quick` is documented as a light-tier auto-capture flow with no review or
  signal, but nearby tests still tolerate or preserve a review-learning shape

These findings show that the problem is systemic inside the learning product
surface, not isolated to one doc string.

## Design Summary

This design introduces one hard rule:

**Runtime-facing learning advice must never output a non-executable command
string.**

To enforce that rule, the learning surface is split into two explicit classes:

1. **Executable advice**
   - A runtime hook may emit a command only when all required arguments are
     known and the command is runnable as written.

2. **Command-surface guidance**
   - When required fields are still unknown, the product must describe the
     command surface as a shape or requirement list instead of pretending to
     provide a ready-to-run command.

This rule is then propagated consistently across runtime hooks, workflow
templates, passive skill guidance, public docs, and contract tests.

## Formal Contract

### 1. Runtime Executability Contract

Any learning-related runtime hook output shown to an agent through `actions`,
`warnings`, `systemMessage`, or `additionalContext` must satisfy one of the
following:

- it is a complete executable command with all required options present
- it is not presented as a runnable command and is clearly labeled as guidance,
  missing fields, or command shape

Runtime output must not contain shell-ready strings with:

- `...`
- `<placeholder>` tokens
- omitted required options that the agent cannot infer safely

### 2. Command-Shape Labeling Contract

Templates, passive skills, and docs may still explain the learning helper
surface, but they must label non-runnable forms explicitly.

Allowed patterns include labels such as:

- `Command shape:`
- `Required options:`
- `Supply --type, --summary, and --evidence when capturing manually`

Disallowed patterns include:

- prose that says `run` followed by a command containing `...`
- prose that visually imitates a copy-paste-ready command while still using
  `<workflow>`, `<status>`, or similar placeholders

### 3. Fast-Tier Learning Contract

`sp-fast` is a trivial tier and must not participate in manual learning capture
as part of the workflow contract.

That means the template must be self-consistent:

- if the command says all learning hooks and capture are skipped, it must not
  later require `learning capture`

This design chooses the stricter interpretation:

- `sp-fast` remains outside the learning capture path

### 4. Quick-Tier Learning Contract

`sp-quick` is a light tier.

Its learning behavior must remain:

- auto-capture on resolution when durable quick-task state already contains the
  relevant evidence
- no `signal-learning`
- no `review-learning` terminal gate

Tests and docs must align to that contract instead of preserving review-shaped
historical wording.

### 5. Test Enforcement Contract

Contract tests must stop protecting placeholder command output as acceptable
behavior.

For learning surfaces, tests must instead verify:

- runtime hook outputs do not emit non-executable command strings
- learning templates and docs use explicit command-shape labeling when examples
  are incomplete
- `sp-fast` and `sp-quick` learning contracts are internally consistent

## Implementation Layers

### Layer 1: Runtime Hook Advice Cleanup

Primary surface:

- `src/specify_cli/hooks/learning.py`

Required changes:

- keep executable `review-learning` suggestions only where all required fields
  are known
- replace placeholder `capture-learning` recovery commands with non-command
  guidance such as required-field instructions
- ensure runtime hook actions no longer contain `...` or `<...>` command text

### Layer 2: Workflow Template Contract Cleanup

Primary surfaces:

- `templates/commands/*.md`
- `templates/command-partials/common/learning-layer.md`

Required changes:

- rewrite learning command examples so incomplete forms are presented as command
  shape guidance rather than runnable commands
- remove the contradictory `sp-fast` learning capture instruction
- ensure `sp-quick` reflects a light-tier auto-capture-only contract

### Layer 3: Passive Skill and Doc Surface Cleanup

Primary surfaces:

- `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- `docs/quickstart.md`

Required changes:

- preserve the documented helper surface
- clearly distinguish example syntax from executable commands
- remove wording that encourages direct execution of placeholder command forms

### Layer 4: Regression and Contract Coverage

Primary surfaces:

- `tests/hooks/**`
- `tests/integrations/**`
- `tests/test_alignment_templates.py`
- `tests/test_command_surface_semantics.py`
- any focused learning-surface guidance tests

Required changes:

- add assertions that runtime learning actions do not contain placeholder-style
  fake commands
- update template tests so they no longer require `...` command forms
- add consistency checks for `sp-fast` and `sp-quick`
- preserve the existing stale `--origin-artifact` detection while extending
  coverage to the newer placeholder-command failure mode where appropriate

## Success Criteria

This design is successful when all of the following are true:

1. Learning runtime output no longer suggests non-executable commands.
2. Manual capture guidance still tells the operator what fields are required.
3. Learning templates and docs no longer disguise incomplete command shapes as
   runnable commands.
4. `sp-fast` and `sp-quick` learning behavior is internally consistent across
   templates and tests.
5. Regression coverage fails if placeholder-style learning command advice is
   reintroduced into runtime or learning contract surfaces.

## Risks and Mitigations

### Risk: Guidance becomes too vague after removing placeholder commands

Mitigation:

- replace fake commands with explicit required-field guidance instead of
  dropping the recovery advice entirely

### Risk: Template churn spills into unrelated workflow messaging

Mitigation:

- limit this pass to learning surfaces only
- treat non-learning placeholder cleanup as follow-up work, not implicit scope

### Risk: Tests continue locking in historical placeholder behavior

Mitigation:

- update the assertions themselves, not just the source strings
- ensure at least one runtime-facing test checks for the absence of fake command
  forms

## Follow-Up Boundary

This design intentionally stops at the learning surfaces.

If implementation reveals the same placeholder-command failure mode in other
runtime hook families, that should become a separate repository-wide command
surface safety follow-up. The learning fix should also leave behind the first
testable enforcement pattern for that broader cleanup.
