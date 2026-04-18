# Workflows

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide user and maintainer workflow paths
**Primary Evidence:** templates/commands/, .agents/skills/, docs, tests
**Update When:** entry commands, handoffs, or neighboring workflow risks change

## Core User Flows

- Mainline: `specify -> plan`, then `tasks -> implement`.
- Optional enhancement: `spec-extend` when an existing spec needs deeper
  analysis before planning.
- Lightweight lanes: `fast` for trivial local changes, `quick` for bounded
  non-trivial work, escalation back to `specify` when scope expands.
- Codex runtime lane: `specify team` for runtime-heavy coordinated execution in
  Codex-initialized projects.

## Core Maintainer Flows

- Add/update templates in `templates/` and keep `.agents/skills/` mirrors
  aligned.
- Maintain docs and tests together when workflow guidance changes.
- Validate changes using focused pytest subsets before wider runs.

## Adjacent Workflow Risks

- Changing workflow wording in one location but not others (README, quickstart,
  templates, mirrors, tests) causes drift and false operator assumptions.
- Fast/quick/specify boundaries are sensitive; inconsistent thresholds lead to
  wrong execution path selection.
- Codex-only runtime messaging must remain isolated from non-Codex flows.

## Entry Commands and Handoffs

- User entrypoints are CLI commands (`specify init`, `specify check`, workflow
  command templates in generated projects).
- Handoffs happen through generated artifacts in `.specify/`, `specs/`, and
  task/plan docs.
- The handbook system (`PROJECT-HANDBOOK.md` + `.specify/project-map/`) is the
  required navigation handoff surface for repository understanding.
