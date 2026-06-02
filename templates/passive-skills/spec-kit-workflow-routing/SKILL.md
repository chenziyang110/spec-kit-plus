---
name: "spec-kit-workflow-routing"
description: "Use when working inside a Spec Kit Plus repository and the user asks whether a structured sp-* workflow would help, or when a manually invoked sp-* workflow needs routing context."
origin: spec-kit-plus
---

# Spec Kit Workflow Routing

This repository's explicit `sp-*` workflow skills are structured entrypoints that
users normally invoke manually. This passive skill helps recommend a workflow or
interpret a manually invoked workflow; it should not auto-enter a workflow during
ordinary chat or coding. When giving a user an explicit next-step invocation, use
the projected invocation placeholder, such as `{{invoke:specify}}`, rather than
assuming one universal slash-style syntax.

## Workflow Recommendation Discipline

Do not auto-enter an `sp-*` workflow unless the user invokes it. For ordinary
natural-language tasks, answer or work in the current mode while using always-on
project cognition and project memory when they matter. You may recommend a
workflow when it would materially improve the outcome.

If the user already invoked an `sp-*` workflow, treat the routing check as
complete and proceed under that workflow's generated contract.

When there is even a 1% chance the current request is asking you to interpret,
continue, or recommend a structured workflow, complete route selection before any response or action,
including a clarifying question, file read, or shell command. The goal is to
route into the right active `sp-*` workflow when one is already invoked, or to
recommend the smallest safe workflow route without silently entering it when ordinary
chat or coding is enough. This command-routing rule does not authorize product-scope minimization.

## Command Surface Discipline

Treat the live `specify --help` output as the only authoritative CLI command
surface.

Before suggesting or running a `specify <subcommand>` invocation, verify that it
exists in `specify --help` or `specify <subcommand> --help`.

Do not invent, paraphrase, or "normalize" unsupported CLI names such as
`specify create-feature`.

Feature creation must stay on `{{invoke:specify}}` plus the generated
create-feature script at `.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`, not an imagined
standalone branch-creation command.

## Complementary Passive Skills

- `spec-kit-project-cognition-gate` is the brownfield advisory navigation layer.
  Workflow routing can recommend a route or explain a manually invoked `sp-*`
  workflow, while the cognition layer helps decide whether an existing-code task
  should treat map maintenance as follow-up or continue with live evidence.
- `spec-kit-project-learning` is the shared memory layer that applies after routing.
  Once the active workflow is selected, that complementary skill defines the
  workflow-specific learning-start and learning-capture behavior instead of leaving
  those triggers implicit.

## Recommendation Rules

- The default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement`. `sp-checklist` and `sp-analyze` remain visible optional diagnostics, but they are not default quality nets for clean workflow progress.
- Use `sp-fast` for trivial, local, low-risk fixes that touch at most 3 files and do
  not cross a shared surface.
- Use `sp-quick` for bounded work that is still small, but no longer trivial.
- `sp-quick` performs one Understanding Checkpoint before substantive execution:
  confirm the understood problem, intended outcome, scope boundary, execution
  approach, and validation evidence before code edits, broad repo analysis,
  delegation, or validation commands continue.
- Use `sp-auto` when repository state already records the recommended next step
  and the user wants to continue without naming the exact workflow manually.
- Use `sp-discussion` before `sp-specify` when the request is a rough idea, not-yet-ready requirement, unsettled product direction, or depends on unclear project boundaries. `sp-discussion` is the senior product-engineering advisor route: it performs a Truth Pass before project-specific technical advice, gives decision-ready judgment with evidence and risk, maintains a Discussion Compass for long conversations, and applies proactive implication mapping so adjacent implications are surfaced without one-point-at-a-time follow-up loops.
- `sp-discussion` must run the Context Boundary Gate before project-specific technical options, affected-file claims, or handoff generation.
- For cross-project or transfer requests, lock the target project root before technicalizing.
- Do not route to `sp-split`; broad directions either become one unified handoff with capability map, sequence, dependencies, deferred scope, and reopen conditions, or stay in `sp-discussion`.
- A valid explicit handoff from discussion is one pair: `handoff-to-specify.md` and `handoff-to-specify.json`, with self-review and user confirmation.
- Use `sp-specify` for new capability, behavior, or requirement changes that are
  ready for an aligned spec package before implementation.
- Use `sp-prd-scan -> sp-prd-build` when an existing repository needs a current-state PRD suite reverse-extracted from code, docs, tests, routes, UI/API surfaces, and project cognition evidence. Treat that pair as the canonical heavy reconstruction PRD lane, a peer workflow path to `sp-specify`, not as a pre-plan requirement, and do not automatically hand off to planning.
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
- Use `sp-implement` after `sp-tasks` produces a clean task package and records `/sp.implement`.
- Use `sp-debug` for regressions, bugs, broken behavior, or incident-style recovery.
- `sp-debug` is complexity-based: small focused investigations may stay
  leader-inline, while broad, independent, or parallel evidence lanes use
  subagent-assisted execution. If the next safe step is unavailable, unsafe, or
  cannot be packetized, record the blocked state instead of forcing delegation.
- Use `sp-map-update` before other workflow steps when project cognition runtime
  coverage is stale or too weak for a localized touched area and the user wants
  map maintenance first, including ordinary existing-baseline gaps.
- If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live requirements. Do not recommend map-scan -> map-build solely because the graph has no paths.
- Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build
  only for brownfield first/missing/unusable baseline, schema failure, zero active-generation
  path_index rows outside `greenfield_empty`, `explicit_rebuild_requested`, or
  `baseline_identity_invalid`.
- `sp-map-update` is for manual/external maintenance as the external/manual maintenance entrypoint for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. A source-changing `sp-*` workflow does not hand off its own verified changes to `sp-map-update`; it runs inline project cognition update during closeout from its workflow-owned changed paths, affected surfaces, and verification evidence. In shared routing summaries, sp-map-update is for manual/external maintenance.
- Inline update is map-update-equivalent for workflow-owned changes. Use `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json` when a delta session exists. Without a delta session, write `.specify/project-cognition/updates/<update-id>.json` and run `project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json`. Payload files accept `verification` plus the compatibility alias `verification_evidence`, and `generated_surfaces` plus the compatibility alias `generated_surface_notes`; failed verification evidence cannot produce a clean `ready` closeout. Clean closeout keys on `result_state`, not `update_id`, `last_update_id`, or freshness alone; `recorded` is legacy recorded-only partial/blocked output.
- Workflow-owned mutation closeout is not external map maintenance. Dirty state is fallback-only after inline update cannot complete.
- Use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state.
- Use `sp-explain` when the user needs a plain-language explanation of current
  artifacts or runtime state.
- For brownfield debug or extension work, the selected workflow must consume the
  project cognition runtime and capability truth layer when a capability or
  symptom route exists; do not jump straight to broad repository search.
- Use the direct `project-cognition` query planning flow required by the
  selected workflow contract to retrieve the task-local project cognition
  bundle. The agent must translate the raw user request into a `query_plan`
  using returned graph-backed project concept candidates, `concept_decisions`,
  and `lexicon_generation_id` before running
  `project-cognition query --query-plan`.
  Treat raw graph JSON artifacts as obsolete runtime surfaces.

## Consequence-Aware Routing

Recommend against `fast` when a request triggers the Senior Consequence Analysis Gate. Use `quick` only for bounded consequence work with durable `STATUS.md` fields. Recommend `discussion` or `specify` when lifecycle semantics, running work, destructive policy, shared state, downstream consumers, or acceptance criteria need product decisions. Recommend `debug` when the issue is a failure with unknown root cause.

## User Invocation Examples

Use canonical workflow names above when describing routing semantics, workflow
state, or artifact handoffs. Use projected invocation placeholders when telling a
user what to type:

- New capability alignment: `{{invoke:specify}}`
- Pre-spec discussion: `{{invoke:discussion}}`
- Existing-project PRD extraction: `{{invoke:prd-scan}} -> {{invoke:prd-build}}`
- Planning handoff: `{{invoke:plan}}`
- Task generation: `{{invoke:tasks}}`
- Implementation execution: `{{invoke:implement}}`
- Debugging route: `{{invoke:debug}}`
- Localized map refresh detour: `{{invoke:map-update}}`
- Full map rebuild detour: `{{invoke:map-scan}} -> {{invoke:map-build}}`

## Subagent Routing

- Use native subagents for bounded delegated work after the owning workflow
  selects or permits delegation.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- Record a fallback or blocked reason when a workflow-selected delegated lane
  cannot proceed because delegation is unavailable, unsafe, or not packetized.
- Do not use old strategy labels as routing choices.
- `sp-fast` is the main leader-inline route; use it only when the work is
  trivial, local, low risk, and does not benefit from delegated verification.
- For `sp-quick`, complete the one-time Understanding Checkpoint before
  substantive execution; after confirmation, use delegated lanes when they are
  safe and packetized.
- For `sp-debug`, choose leader-inline for small focused investigations and
  subagent-assisted execution for broad, independent, or parallel evidence
  lanes.
- For `sp-map-scan`, `sp-map-build`, and `sp-implement`, leader + subagents is
  the default execution shape for independent bounded lanes when the current
  runtime supports delegation.
- Use `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, or lifecycle control beyond one in-session subagent burst.

## Behavioral Rules

- Do not replace a user-invoked `sp-*` workflow with ad hoc implementation.
- If multiple workflow recommendations seem plausible, suggest the smallest safe workflow route and make the next escalation trigger explicit.
- Workflow-route minimization is only about choosing the command surface. Preserve the user's confirmed product scope; do not steer the product toward a smaller MVP, pilot, prototype, or first-story release unless the user asked for that shape or confirmed it after a named constraint/trade-off.
- If the user intent is effectively "continue with the recommended next step",
  prefer `sp-auto` over guessing which canonical workflow they meant from chat alone.
- Clean completed `sp-tasks` state with `/sp.implement` should route through `sp-auto` to `sp-implement`.
- Keep `sp-*` workflows as visible optional entrypoints. This passive skill should
  recommend them, not become a competing workflow.
- If the user is already invoking the correct `sp-*` skill, do not redirect.
- Do not skip from `sp-discussion` into `sp-specify` unless the user explicitly
  requests handoff.
- If a required next step is a user-invoked workflow entrypoint rather than an
  in-workflow action, stop the current flow and tell the user exactly what to run.
- Do not self-execute a different explicit `sp-*` workflow just because the current
  workflow discovered a stale gate or missing prerequisite. Hand off by telling the
  user to run the projected invocation, then wait.

## Red Flags

- You are about to auto-enter an `sp-*` workflow that the user did not invoke.
- You are presenting a workflow recommendation as mandatory when ordinary chat,
  coding, or review would satisfy the request.
- The user is exploring rough requirements, but you did not mention `sp-discussion`
  as an optional structured path.
- You are treating "small" as a reason to recommend `sp-fast` automatically instead
  of staying in the user's requested mode.
- You found independent lanes but have not considered `one-subagent` or
  `parallel-subagents` dispatch.
