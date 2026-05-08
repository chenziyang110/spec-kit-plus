---
name: spec-kit-project-map-gate
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Require `DEBUG-HANDBOOK.md` or `BUILD-HANDBOOK.md` first, or route to `sp-map-scan -> sp-map-build` when that runtime handbook coverage is missing or stale."
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

- Read `DEBUG-HANDBOOK.md` for `sp-debug`.
- Read `BUILD-HANDBOOK.md` for other ordinary brownfield workflows.
- Read the fixed chapter IDs required by the active workflow contract before broader repository evidence gathering.
- Do not use `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, or `.specify/project-map/modules/**` as the primary runtime read path.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`
  when they exist.

## Command Surface Discipline

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation while satisfying this gate, verify that it exists in `specify --help` or `specify <subcommand> --help`.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation remains `{{invoke:specify}}` plus the generated create-feature script at `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`, not a separate branch-creation command.

## Missing Or Stale Context

- If the required runtime handbook is missing, stale, or too weak for the touched area, route through the canonical `sp-map-scan -> sp-map-build`
  workflow detour before continuing. When giving the user an explicit command to
  type, write `{{invoke:map-scan}} -> {{invoke:map-build}}`.
- Treat that detour as a user-invoked workflow handoff. Do not silently switch into
  `sp-map-scan` or `sp-map-build` yourself from another workflow; stop and tell the
  user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- Do not rely on generic framework instinct, chat memory, or prior sessions when the
  runtime handbook should be the source of truth.

## Scope Guard

- This gate applies even if the user asks for a direct code change without mentioning
  Spec Kit workflows.
- Stand down only when the task is clearly greenfield and does not depend on any
  existing project structure, conventions, or runtime surface.
