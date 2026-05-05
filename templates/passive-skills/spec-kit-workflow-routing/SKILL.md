---
name: "spec-kit-workflow-routing"
description: "Use when working inside a Spec Kit Plus repository and the user asks for feature work, planning, implementation, explanation, debugging, or code changes without explicitly naming the right sp-* workflow. Route the request to the correct active skill before proceeding."
origin: spec-kit-plus
---

# Spec Kit Workflow Routing

This repository's explicit `sp-*` workflow skills remain the primary execution surface.
This passive skill exists to route ambiguous requests into the right active workflow
instead of improvising a custom flow. Use it to route into the right active `sp-*` workflow
before any complementary gate or learning layer runs. When giving a user an explicit
next-step invocation, use the projected invocation placeholder, such as
`{{invoke:specify}}`, rather than assuming one universal slash-style syntax.

## Workflow Activation Discipline

If there is even a 1% chance that a user request belongs to an `sp-*` workflow,
route to the right workflow before any response or action. "Action" includes a
clarifying question, file read, shell command, repository inspection, code edit,
test run, or design summary.

Do not first "take a quick look" outside the workflow. Repository inspection is
part of the selected workflow, not a pre-routing exception. State the selected
workflow or passive skill in one concise line, then continue under that contract.
If the user already invoked the correct `sp-*` skill, treat this routing check as
complete and proceed.

## Command Surface Discipline

Treat the live `specify --help` output as the only authoritative CLI command
surface.

Before suggesting or running a `specify <subcommand>` invocation, verify that it
exists in `specify --help` or `specify <subcommand> --help`.

Do not invent, paraphrase, or "normalize" unsupported CLI names such as
`specify create-feature`.

Feature creation must stay on `{{invoke:specify}}` plus the generated
create-feature script, not an imagined standalone branch-creation command.

## Complementary Passive Skills

- `spec-kit-project-map-gate` is the hard brownfield context gate. Workflow routing
  handles route selection into the right active `sp-*` workflow, while the map gate
  decides whether an existing-code task can continue or must detour through
  `sp-map-scan -> sp-map-build` first.
- `spec-kit-project-learning` is the shared memory layer that applies after routing.
  Once the active workflow is selected, that complementary skill defines the
  workflow-specific learning-start and learning-capture behavior instead of leaving
  those triggers implicit.

## Routing Rules

- Use `sp-fast` for trivial, local, low-risk fixes that touch at most 3 files and do
  not cross a shared surface.
- Use `sp-quick` for bounded work that is still small, but no longer trivial.
- Use `sp-test-scan` when the repository needs read-only testing-system evidence,
  module risk tiers, coverage-gap analysis, or build-ready test lanes.
- Use `sp-test-build` when `TEST_SCAN.md` and `TEST_BUILD_PLAN.md/json` exist and
  scan-approved lanes should construct or refresh the unit testing system.
- Use `sp-auto` when repository state already records the recommended next step
  and the user wants to continue without naming the exact workflow manually.
- Use `sp-specify` for new capability, behavior, or requirement changes that need an
  aligned spec package before implementation.
- Use `sp-prd-scan -> sp-prd-build` when an existing repository needs a current-state PRD suite reverse-extracted from code, docs, tests, routes, UI/API surfaces, and project-map evidence. Treat that pair as the canonical heavy reconstruction PRD lane, a peer workflow path to `sp-specify`, not as a pre-plan requirement, and do not automatically hand off to planning.
- Require the PRD lane to follow `subagent-mandatory` scan semantics for
  substantive runs, carry contract artifacts such as `config-contracts.json`,
  and keep critical claims blocked until `L4 Reconstruction-Ready`.
- Treat `sp-prd-build` as a build-only compilation step: it must not reread the repository, and it must block completion when critical evidence gaps remain.
- Treat `sp-prd` as a deprecated compatibility alias that must route into the
  canonical `sp-prd-scan -> sp-prd-build` flow instead of acting as the primary
  reverse-PRD lane.
- Use `sp-clarify` when an existing spec package needs deeper analysis before
  planning can safely proceed.
- Use `sp-deep-research` when the requirements are clear but feasibility, external
  evidence, optional multi-agent research, or a disposable demo is needed to prove
  the implementation chain before planning. It must write a Planning Handoff for
  `sp-plan`; skip it for minor changes to already-proven project behavior.
- Treat `sp-research` as a compatibility alias for `sp-deep-research`. It must
  route into the canonical feasibility gate and must not create separate
  `sp-research` artifacts or workflow state.
- Use `sp-plan` only after a valid spec package exists.
- Use `sp-tasks` only after planning artifacts are ready.
- Use `sp-implement` only after tasks are ready and execution should begin.
- Use `sp-debug` for regressions, bugs, broken behavior, or incident-style recovery.
- Use `sp-map-scan -> sp-map-build` before other workflow steps when handbook or project-map
  context for an existing codebase is missing, stale, or too broad.
- Use `sp-analyze` for drift, consistency, or readiness checks across existing
  spec/plan/tasks artifacts.
- Use `sp-explain` when the user needs a plain-language explanation of current
  artifacts or runtime state.

## User Invocation Examples

Use canonical workflow names above when describing routing semantics, workflow
state, or artifact handoffs. Use projected invocation placeholders when telling a
user what to type:

- New capability alignment: `{{invoke:specify}}`
- Existing-project PRD extraction: `{{invoke:prd-scan}} -> {{invoke:prd-build}}`
- Planning handoff: `{{invoke:plan}}`
- Task generation: `{{invoke:tasks}}`
- Implementation execution: `{{invoke:implement}}`
- Debugging route: `{{invoke:debug}}`
- Map refresh detour: `{{invoke:map-scan}} -> {{invoke:map-build}}`

## Subagent Routing

- Use subagents-first execution for bounded delegated work.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- Use `leader-inline-fallback` only after recording why delegation is
  unavailable, unsafe, or not packetized.
- Do not use old strategy labels as routing choices.
- `sp-fast` is the main leader-inline route; use it only when the work is
  trivial, local, low risk, and does not benefit from delegated verification.
- For `sp-quick`, `sp-debug`, `sp-test-build`, `sp-map-scan`, `sp-map-build`, and
  `sp-implement`, leader + subagents is the default execution shape for
  independent bounded lanes when the current runtime supports delegation.
- Use `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, or lifecycle control beyond one in-session subagent burst.

## Behavioral Rules

- Do not replace a matching `sp-*` workflow with ad hoc implementation.
- If multiple routes seem plausible, choose the smallest safe route and make the next
  escalation trigger explicit.
- If the user intent is effectively "continue with the recommended next step",
  prefer `sp-auto` over guessing which canonical workflow they meant from chat alone.
- Keep `sp-*` workflows as the visible daily surface. This passive skill should guide
  into them, not become a competing workflow.
- If the user is already invoking the correct `sp-*` skill, do not redirect.
- If a required next step is a user-invoked workflow entrypoint rather than an
  in-workflow action, stop the current flow and tell the user exactly what to run.
- Do not self-execute a different explicit `sp-*` workflow just because the current
  workflow discovered a stale gate or missing prerequisite. Hand off by telling the
  user to run the projected invocation, then wait.

## Red Flags

- You are about to ask a clarifying question before selecting a workflow.
- You are about to run a file read, search, or shell command before selecting a workflow.
- The request mentions planning, debugging, implementation, tests, or code changes,
  but no `sp-*` workflow has been named yet.
- You are treating "small" as a reason to skip routing instead of checking `sp-fast`
  or `sp-quick`.
- You found independent lanes but have not considered `one-subagent` or
  `parallel-subagents` dispatch.
