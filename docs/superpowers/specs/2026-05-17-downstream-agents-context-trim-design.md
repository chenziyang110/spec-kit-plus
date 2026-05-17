# Downstream Agent Context Trim Design

**Date:** 2026-05-17  
**Status:** Approved direction; written for user review  
**Scope:** Generated downstream agent context files, especially `AGENTS.md` and equivalent integration-specific context surfaces  

## Problem Statement

Generated downstream `AGENTS.md` content has grown from startup guidance into a
workflow handbook. It now explains many `sp-*` workflow choices, durable artifact
details, project cognition commands, recovery rules, and map maintenance
procedures in the always-read context file.

That creates two product problems:

1. The most important rules are diluted by workflow catalog detail.
2. The file implies agents should auto-route ordinary chat or coding work into
   `sp-*` workflows, even though those workflows are primarily user-triggered.

The downstream context file should instead make ordinary agent sessions better
by exposing always-on project cognition and project memory. `sp-*` workflows
should remain structured entrypoints that users invoke manually, with agents
allowed to recommend them when helpful.

## Design Goals

1. Make downstream `AGENTS.md` a compact startup behavior layer, not a workflow
   manual.
2. Preserve the benefit of project cognition and project memory even when no
   `sp-*` command is active.
3. Replace mandatory workflow auto-routing with advisory workflow
   recommendations.
4. Remove duplicate command-surface and recovery guidance across the base
   template and managed Spec Kit block.
5. Keep specific workflow procedures inside workflow commands, passive skills,
   project cognition tooling, or human docs.
6. Target a much smaller managed block: enough to steer behavior, not enough to
   teach the whole product.

## Non-Goals

- Do not remove `sp-*` workflows or change their command contracts.
- Do not prevent an agent from recommending a workflow when it clearly fits.
- Do not move project cognition or project memory behind a workflow-only gate.
- Do not turn `AGENTS.md` into a complete project cognition handbook.
- Do not require ordinary natural-language tasks to auto-enter `sp-*`.

## Target Behavior

For ordinary chat, review, planning, coding, debugging, or discussion, the agent
should stay in the user's requested mode unless the user explicitly invokes an
`sp-*` workflow. It should still use generated project support surfaces:

- query project cognition before broad source inspection when existing-system
  truth matters
- read relevant project memory before decisions that depend on stable local
  conventions, constraints, or past lessons
- use project cognition results to narrow live reads
- carry useful cognition and memory facts into answers, plans, edits, or
  verification notes

For workflow recommendations, the agent may suggest a workflow without taking
over the session:

- recommend `sp-discussion` when the user is still exploring requirements
- recommend `sp-specify` when scope, behavior, constraints, or acceptance
  criteria need formal alignment
- recommend `sp-deep-research` when requirements are clear but feasibility or
  the implementation chain is uncertain
- recommend `sp-debug` when diagnosis is needed before a fix path is trustworthy
- follow the workflow's generated command or skill contract only after the user
  invokes it

## Proposed Managed Block Shape

The managed Spec Kit block should be short and organized around behavior that
must be true in normal sessions. A representative target shape:

```markdown
<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.

## Always-On Context

- Project cognition and project memory are always available, even without an
  active `sp-*` workflow.
- When existing-system truth matters, use project cognition before broad source
  inspection and use its results to narrow live reads.
- Read relevant project memory before decisions that depend on local
  conventions, constraints, or past lessons.

## Workflow Recommendations

- Do not auto-enter an `sp-*` workflow unless the user invokes it.
- Recommend `sp-discussion` for open-ended requirement exploration,
  `sp-specify` for formal alignment, `sp-deep-research` for feasibility proof,
  and `sp-debug` for root-cause diagnosis.
- If the user invokes an `sp-*` workflow, follow that workflow's own contract.

## Command Surface Rules

- Treat live `specify --help` output as the authoritative CLI surface.
- Do not invent unsupported CLI names such as `specify create-feature`.

## Durable State

- When resuming generated work, prefer durable workflow state and explicit
  feature paths over branch name or chat memory.
- Keep project cognition freshness truthful after changes to architecture,
  ownership, workflow names, integration contracts, or verification entry
  points.
- Store reusable lessons in project memory, not only in chat or task artifacts.

- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
```

This shape intentionally removes the full workflow catalog, long artifact
inventory, duplicated project cognition command recipe, and mandatory
one-percent workflow activation language.

## Content To Remove Or Compress

Remove from downstream always-read guidance:

- `Workflow Activation Discipline`, especially mandatory routing before any
  response or inspection
- the complete `Workflow Routing` catalog
- duplicated `Command Surface Rules` between the base template and managed block
- long `Artifact Priority` file listings
- detailed project cognition command and field inventory
- map refresh command procedure details better owned by map workflows

Compress into shorter principles:

- `Brownfield Context Gate` and `Project Cognition Usage` become
  `Always-On Context`
- `Project Memory` becomes a short memory-use and lesson-capture rule
- `Workflow Recovery Rules` become `Durable State`
- `Map Maintenance` becomes a freshness responsibility rule

## Source Surfaces For Implementation

When this design moves to implementation, update all managed block emitters and
tests together:

- `templates/agent-file-template.md`
- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`
- `src/specify_cli/__init__.py`
- managed-block tests under `tests/`
- integration tests that assert generated context file content
- README or handbook text only where user-facing workflow guidance needs the
  same distinction between recommendations and manual workflow invocation

## Verification Strategy

Implementation should verify:

- Bash, PowerShell, and Python managed block renderers stay semantically aligned.
- Generated downstream context files contain the compact managed block.
- The block no longer contains mandatory one-percent workflow routing.
- The block still teaches project cognition and memory as always-on support
  surfaces.
- The block permits workflow recommendations without auto-entering workflows.
- Existing content outside managed blocks remains preserved.

## Open Decision

The exact line budget can be finalized during implementation. The recommended
target is a managed block around 25-40 lines and a full generated `AGENTS.md`
around 60-90 lines after project-specific sections are populated.
