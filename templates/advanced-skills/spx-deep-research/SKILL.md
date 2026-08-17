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
repository evidence first and current primary external sources through
vendor-neutral search or documentation tooling when the answer depends on an
API, platform, standard, dependency, or recent behavior.

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
`allowed_artifact_writes: deep-research.md, research-spikes/, research/state.json, research/track-manifest.json, research/handoffs/, research/synthesis.json, research/audit-request.json, research/audit.json, research/handoff-to-plan.json, research-evidence/, alignment.md, context.md, references.md, workflow-state.md`.
Those feature-local artifacts are the complete CLI-owned artifact allowlist for this stage;
do not edit product source, tests, migrations, production configuration, or
build tooling.

Treat the runtime lifecycle as authoritative for structured research work:
initialize or resume the research session, read status before acting, prepare
tracks before any worker lease, lease one track at a time, submit bounded track
results, accept or reject them explicitly, yield unresolved leased work before
stopping, synthesize only from accepted packets, prepare and accept the final
audit, validate the structured package, publish the planning handoff, verify
the handoff before recommending `$spx-plan`, and use the dedicated not-needed
path when repository evidence already proves the implementation chain. Never
simulate these lifecycle transitions by patching a Markdown summary alone.

Use the concrete runtime surface, preserving the `--expected-revision` returned
by each mutation:

```text
specify-runtime deep-research init
specify-runtime deep-research status
specify-runtime deep-research track-prepare
specify-runtime deep-research track-lease
specify-runtime deep-research track-submit
specify-runtime deep-research track-accept
specify-runtime deep-research track-yield
specify-runtime deep-research synthesize
specify-runtime deep-research audit-prepare
specify-runtime deep-research audit-accept
specify-runtime deep-research validate
specify-runtime deep-research publish
specify-runtime deep-research verify-handoff
specify-runtime deep-research not-needed
```

Run independent evidence lanes in parallel only when their questions and CLI-owned
artifact sets are truly separate. Build a disposable spike under the feature's
`research-spikes/` only when documentation and source cannot prove the
integration chain. Create or modify every text/code spike through `artifact prepare`
plus inline `artifact submit` or leased `artifact patch`, and import binary proof
through `specify-runtime evidence import`; never write a spike directly. Keep spikes out of production paths and record environment,
commands, output, limitations, and the claim they establish.

Pass concise findings, source attribution, contradictions, confidence, rejected
options, and planning handoffs into `deep-research synthesize`. The runtime
materializes `research/synthesis.json` and derives `deep-research.md`; query the
projection with `artifact show`, but never scaffold, submit, or patch it.
Update referenced alignment/context evidence only through fresh artifact leases
when required by the existing feature package.

Structure the planning handoff deterministically: assign each planning-facing
item a `PH-###` ID, each accepted evidence record an `EVD-###` ID, and each
disposable spike a `SPK-###` ID. Include structured evidence in the bounded
`deep-research track-submit` result; the runtime validates and materializes
`research-evidence/<EVD-###>.json`. `evidence import` is reserved for external
or binary proof in the content-addressed evidence store. Do not hand-author or
patch runtime-owned research packets. Every
`PH-###` must cite its backing `EVD-###` and `SPK-###` refs when present so
`$spx-plan` can consume the handoff without reconstructing traceability.

Structured research artifacts produced by the runtime are the canonical source
of truth for track status, accepted evidence, audit state, handoff metadata,
claim status, source hashes, and revision-bound publish state. Treat
`deep-research.md` as the derived human-readable projection of that structured
package: query it for explanation and review, but do not treat it as the sole
source of truth when canonical structured state exists, and never hand-author a
Markdown-only result to bypass canonical packets, audits, or handoff
verification.

If repository evidence already proves every planning-critical implementation
chain, invoke `specify-runtime deep-research not-needed` with one evidence-backed
disposition per selected capability. The runtime publishes the exact
`**Status**: Not needed` projection; do not invent research or handoff IDs.
Before any plan handoff, run
reverse coverage: every planning-critical capability has a handoff decision
backed by repository/source/spike evidence, every accepted evidence item is
consumed or explicitly deferred, and every blocked item has a recovery action.
If any check fails, refuse the handoff, patch the failed checks and blocker into
`workflow-state.md` through a leased `specify-runtime artifact patch` call, and report the smallest recovery route.

Run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command deep-research --feature-dir <feature-dir> --format json}}`
before reporting readiness. Repair the research artifact or remain blocked on a
non-OK result; surface presence alone is not a valid handoff.

Before a clean handoff claim, verify that the published research handoff binds
the current source revision, current structured research claim status, exact
accepted `PH-*` / `EVD-*` / `SPK-*` IDs, and any runtime-produced source hash or
handoff digest. If the publish or verify step reports stale, tampered, foreign,
or partial state, stop and repair the canonical structured package instead of
rephrasing the derived Markdown.

This invocation authorizes only this workflow stage. Do not implement production
behavior. Do not invoke `$spx-clarify`. Do not invoke `$spx-plan`. When
feasibility is proven or the remaining risk is explicitly accepted, report
`$spx-plan` as the next handoff. Report requirement gaps as a `$spx-clarify`
handoff; otherwise stop with the smallest unresolved blocker.
