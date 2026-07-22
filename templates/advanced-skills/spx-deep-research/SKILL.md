---
name: spx-deep-research
description: Focused pre-plan feasibility research for advanced coding models. Use when a planning-ready specification still lacks a credible implementation chain, external evidence, or a disposable proof.
---

# SPX Deep Research

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `research`,
`references/research-contract.md`, and `references/consequence-gate.md` only on
its triggers.

Before research, run the installed extension-hook gate for
`before_deep_research`; after a successful or blocked research closeout, run it
for `after_deep_research`. Use `HookExecutor` when available so enabled state,
conditions, optionality, and integration-specific invocation stay
runtime-owned. An enabled unconditional mandatory hook must finish before the
stage proceeds; offer optional hooks without auto-running them. If only the
project config is available, inspect `.specify/extensions.yml` for those two
events, leave non-empty conditions to `HookExecutor`, and preserve the same
mandatory/optional stop semantics.

Resolve the existing feature in paths-only mode. Start from the spec contract
and name the planning decision each research question must unlock. Use live
repository evidence first and current primary external sources when the answer
depends on an API, platform, standard, dependency, or recent behavior.

Before any write, run
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`.
`FEATURE_DIR/workflow.json` is CLI-owned; this auxiliary skill must not write
it, and its expected required-stage owner is `specify`. On missing, corrupt,
different, or completed runtime state, stop with the returned blocker or a
typed owner handoff containing the observed stage, expected owner, affected
files, exact next action, unblock criteria, and resume argv. Never overwrite
either state surface to force entry.

Create or resume the feature's rich workflow-owned `workflow-state.md` before
substantial work and read it before reconstructing intent from chat. Persist at least
`active_command: sp-deep-research`, `phase_mode: research-only`, the current
stage, accepted/rejected evidence, blockers, exit criteria, next action, and
next command. Set
`allowed_artifact_writes: deep-research.md, research-spikes/, alignment.md, context.md, references.md, workflow-state.md`.
Those feature-local artifacts are the complete write allowlist for this stage;
do not edit product source, tests, migrations, production configuration, or
build tooling.

Run independent evidence lanes in parallel only when their questions and write
sets are truly separate. Build a disposable spike under the feature's
`research-spikes/` only when documentation and source cannot prove the
integration chain. Keep spikes out of production paths and record environment,
commands, output, limitations, and the claim they establish.

Write or update `deep-research.md` with concise findings, source attribution,
contradictions, confidence, rejected options, and a `Planning Handoff` that maps
each accepted result to architecture, task, verification, or risk implications.
Update referenced alignment/context evidence when required by the existing
feature package.

If repository evidence already proves every planning-critical implementation
chain, still write a lightweight `deep-research.md` with the exact marker
`**Status**: Not needed` plus `## Feasibility Decision`, `## Planning Handoff`,
and `## Next Command`; update durable state and do not invent research evidence
IDs. Before any plan handoff, run
reverse coverage: every planning-critical capability has a handoff decision
backed by repository/source/spike evidence, every accepted evidence item is
consumed or explicitly deferred, and every blocked item has a recovery action.
If any check fails, refuse the handoff, persist the failed checks and blocker in
`workflow-state.md`, and report the smallest recovery route.

Run
`{{specify-subcmd:hook validate-artifacts --command deep-research --feature-dir <feature-dir> --format json}}`
before reporting readiness. Repair the research artifact or remain blocked on a
non-OK result; surface presence alone is not a valid handoff.

This invocation authorizes only this workflow stage. Do not implement production
behavior. Do not invoke `$spx-clarify`. Do not invoke `$spx-plan`. When
feasibility is proven or the remaining risk is explicitly accepted, report
`$spx-plan` as the next handoff. Report requirement gaps as a `$spx-clarify`
handoff; otherwise stop with the smallest unresolved blocker.
