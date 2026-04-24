---
name: spec-kit-project-map-gate
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Require PROJECT-HANDBOOK.md and relevant .specify/project-map context first, or route to sp-map-codebase when that context is missing or stale."
origin: spec-kit-plus
---

# Spec Kit Project Map Gate

This passive skill is the brownfield hard gate, not the route selection layer.

## Complementary Passive Skills

- `spec-kit-workflow-routing` owns route selection into the correct `sp-*` workflow
  before implementation, planning, or debugging proceeds.
- `spec-kit-project-learning` owns the shared memory capture layer after context is
  loaded. Once this gate is satisfied, follow that skill's learning-start and
  learning-capture expectations for the active workflow.

## Hard Gate

Before code edits, investigation, planning against existing code, or architectural
judgment in an established Spec Kit Plus repository:

- Read `PROJECT-HANDBOOK.md`.
- Read the relevant `.specify/project-map/*.md` files for the touched subsystem,
  workflow, or boundary.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`
  when they exist.

## Missing Or Stale Context

- If the handbook or project-map documents do not exist, are stale, or are too broad
  for the touched area, use `sp-map-codebase` before continuing.
- Do not rely on generic framework instinct, chat memory, or prior sessions when the
  repository map should be the source of truth.

## Scope Guard

- This gate applies even if the user asks for a direct code change without mentioning
  Spec Kit workflows.
- Stand down only when the task is clearly greenfield and does not depend on any
  existing project structure, conventions, or runtime surface.
