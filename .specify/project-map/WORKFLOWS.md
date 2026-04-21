# Workflows

**Last Updated:** 2026-04-20
**Coverage Scope:** repository-wide user and maintainer workflow paths
**Primary Evidence:** templates/commands/, docs, tests
**Update When:** entry commands, handoffs, or neighboring workflow risks change

## Core User Flows

- Mainline: `specify -> plan`, then `tasks -> implement`.
- Brownfield navigation refresh: `map-codebase` before `specify`, `plan`,
  `tasks`, or `implement` when handbook/project-map coverage is missing or
  stale.
- Optional enhancement: `spec-extend` when an existing spec needs deeper
  analysis before planning.
- Lightweight lanes: `fast` for trivial local changes, `quick` for bounded
  non-trivial work, escalation back to `specify` when scope expands.
- Codex runtime lane: `specify team` for runtime-heavy coordinated execution in
  Codex-initialized projects.

## Core Maintainer Flows

- Add or update shared command templates in `templates/commands/` and keep
  generated surfaces aligned.
- Maintain docs and tests together when workflow guidance changes.
- Validate changes using focused pytest subsets before wider runs.

## Adjacent Workflow Risks

- Changing workflow wording in one location but not others (README, quickstart,
  templates, generated surfaces, tests) causes drift and false operator
  assumptions.
- Fast/quick/specify boundaries are sensitive; inconsistent thresholds lead to
  wrong execution path selection.
- Brownfield navigation drift can invalidate downstream workflow assumptions if
  `sp-map-codebase` is skipped when handbook/project-map coverage is stale.
- Codex-only runtime messaging must remain isolated from non-Codex flows.

## Entry Commands and Handoffs

- User entrypoints are CLI commands (`specify init`, `specify check`, workflow
  command templates in generated projects).
- Handoffs happen through generated artifacts in `.specify/`, `specs/`, and
  task/plan docs.
- The handbook system (`PROJECT-HANDBOOK.md` + `.specify/project-map/`) is the
  required navigation handoff surface for repository understanding.
- `sp-map-codebase` is the explicit generation and refresh surface for that
  navigation handoff.
