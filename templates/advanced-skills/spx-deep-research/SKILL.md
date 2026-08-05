---
name: spx-deep-research
description: Focused pre-plan feasibility research for advanced coding models. Use when a planning-ready specification still lacks a credible implementation chain, external evidence, or a disposable proof.
---

# SPX Deep Research

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when evidence lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `research`,
`references/research-contract.md`, and `references/consequence-gate.md` only on
its triggers.

Before research, run `specify-runtime hook extension-plan --event
before_deep_research --format json`; after a successful or blocked research
closeout, run it for `after_deep_research`. Never inspect extension storage.
The runtime filters enabled/conditional hooks and renders integration-native
invocations. An actionable mandatory hook must finish before the stage
proceeds; offer optional hooks without auto-running them.

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

Create initial `workflow-state.md` through `artifact scaffold --kind workflow-state`; resume and mutate it only through targeted `artifact show` and leased `artifact patch` before
substantial work and read it before reconstructing intent from chat. Persist at least
`active_command: sp-deep-research`, `phase_mode: research-only`, the current
stage, accepted/rejected evidence, blockers, exit criteria, next action, and
next command. Set
`allowed_artifact_writes: deep-research.md, research-spikes/, alignment.md, context.md, references.md, workflow-state.md`.
Those feature-local artifacts are the complete CLI-owned artifact allowlist for this stage;
do not edit product source, tests, migrations, production configuration, or
build tooling.

Run independent evidence lanes in parallel only when their questions and CLI-owned
artifact sets are truly separate. Build a disposable spike under the feature's
`research-spikes/` only when documentation and source cannot prove the
integration chain. Create or modify every text/code spike through `artifact prepare`
plus inline `artifact submit` or leased `artifact patch`, and import binary proof
through `specify-runtime evidence import`; never write a spike directly. Keep spikes out of production paths and record environment,
commands, output, limitations, and the claim they establish.

Create an absent researched `deep-research.md` with `artifact scaffold --kind deep-research --path <feature-dir>/deep-research.md`; query an existing file with `artifact show` and update only targeted sections through fresh leased `artifact patch`
calls. Never submit or reconstruct the whole document. Patch concise findings, source attribution,
contradictions, confidence, rejected options, and a `Planning Handoff` that maps
each accepted result to architecture, task, verification, or risk implications.
Update referenced alignment/context evidence only through fresh artifact leases
when required by the existing feature package.

Structure the planning handoff deterministically: assign each planning-facing
item a `PH-###` ID, each accepted evidence record an `EVD-###` ID, and each
disposable spike a `SPK-###` ID. Persist each structured
`research-evidence/<EVD-###>.json` packet through `artifact prepare` plus inline
`artifact submit`, and refresh it only through leased JSON-pointer patches;
`evidence import` is reserved for external or binary proof in the content-addressed
evidence store and does not materialize a feature-local packet. Do not
hand-author either kind. Every
`PH-###` must cite its backing `EVD-###` and `SPK-###` refs when present so
`$spx-plan` can consume the handoff without reconstructing traceability.

If repository evidence already proves every planning-critical implementation
chain, create an absent lightweight `deep-research.md` with `artifact scaffold --kind deep-research-not-needed --path <feature-dir>/deep-research.md`, then patch only the exact marker
`**Status**: Not needed` plus `Feasibility Decision`, `Planning Handoff`,
and `## Next Command`; update durable state and do not invent research evidence
IDs. Before any plan handoff, run
reverse coverage: every planning-critical capability has a handoff decision
backed by repository/source/spike evidence, every accepted evidence item is
consumed or explicitly deferred, and every blocked item has a recovery action.
If any check fails, refuse the handoff, patch the failed checks and blocker into
`workflow-state.md` through a leased `specify-runtime artifact patch` call, and report the smallest recovery route.

Run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command deep-research --feature-dir <feature-dir> --format json}}`
before reporting readiness. Repair the research artifact or remain blocked on a
non-OK result; surface presence alone is not a valid handoff.

This invocation authorizes only this workflow stage. Do not implement production
behavior. Do not invoke `$spx-clarify`. Do not invoke `$spx-plan`. When
feasibility is proven or the remaining risk is explicitly accepted, report
`$spx-plan` as the next handoff. Report requirement gaps as a `$spx-clarify`
handoff; otherwise stop with the smallest unresolved blocker.
