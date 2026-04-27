---
name: "spec-kit-workflow-routing"
description: "Use when working inside a Spec Kit Plus repository and the user asks for feature work, planning, implementation, explanation, debugging, or code changes without explicitly naming the right sp-* workflow. Route the request to the correct active skill before proceeding."
origin: spec-kit-plus
---

# Spec Kit Workflow Routing

This repository's explicit `sp-*` workflow skills remain the primary execution surface.
This passive skill exists to route ambiguous requests into the right active workflow
instead of improvising a custom flow. Use it to route into the right active `sp-*` workflow
before any complementary gate or learning layer runs.

## Complementary Passive Skills

- `spec-kit-project-map-gate` is the hard brownfield context gate. Workflow routing
  handles route selection into the right active `sp-*` workflow, while the map gate
  decides whether an existing-code task can continue or must detour through
  `sp-map-codebase` first.
- `spec-kit-project-learning` is the shared memory layer that applies after routing.
  Once the active workflow is selected, that complementary skill defines the
  workflow-specific learning-start and learning-capture behavior instead of leaving
  those triggers implicit.

## Routing Rules

- Use `sp-fast` for trivial, local, low-risk fixes that touch at most 3 files and do
  not cross a shared surface.
- Use `sp-quick` for bounded work that is still small, but no longer trivial.
- Use `sp-test` when the repository needs a project-level unit testing bootstrap,
  refresh, or testing-contract pass instead of an ordinary feature workflow.
- Use `sp-specify` for new capability, behavior, or requirement changes that need an
  aligned spec package before implementation.
- Use `sp-clarify` when an existing spec package needs deeper analysis before
  planning can safely proceed.
- Use `sp-plan` only after a valid spec package exists.
- Use `sp-tasks` only after planning artifacts are ready.
- Use `sp-implement` only after tasks are ready and execution should begin.
- Use `sp-debug` for regressions, bugs, broken behavior, or incident-style recovery.
- Use `sp-map-codebase` before other workflow steps when handbook or project-map
  context for an existing codebase is missing, stale, or too broad.
- Use `sp-analyze` for drift, consistency, or readiness checks across existing
  spec/plan/tasks artifacts.
- Use `sp-explain` when the user needs a plain-language explanation of current
  artifacts or runtime state.

## Behavioral Rules

- Do not replace a matching `sp-*` workflow with ad hoc implementation.
- If multiple routes seem plausible, choose the smallest safe route and make the next
  escalation trigger explicit.
- Keep `sp-*` workflows as the visible daily surface. This passive skill should guide
  into them, not become a competing workflow.
- If the user is already invoking the correct `sp-*` skill, do not redirect.
