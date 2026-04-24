---
description: "Use when working inside a Spec Kit Plus repository and the user asks for feature work, planning, implementation, explanation, debugging, or code changes without explicitly naming the right sp-* workflow. Route the request to the correct active skill before proceeding."
---

# Spec Kit Workflow Routing

This repository's explicit `sp-*` workflow skills remain the primary execution surface.
This passive skill exists to route ambiguous requests into the right active workflow
instead of improvising a custom flow.

## Routing Rules

- Use `sp-fast` for trivial, local, low-risk fixes that touch at most 3 files and do
  not cross a shared surface.
- Use `sp-quick` for bounded work that is still small, but no longer trivial.
- Use `sp-specify` for new capability, behavior, or requirement changes that need an
  aligned spec package before implementation.
- Use `sp-spec-extend` when an existing spec package needs deeper analysis before
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
