{{spec-kit-include: ../common/user-input.md}}

## Objective

Produce a planning-ready research packet before implementation planning starts:
prove or retire planning-critical feasibility questions, synthesize external and
repository evidence, validate uncertain links with disposable demo spikes when
needed, and hand `/sp.plan` the constraints and recommended implementation
direction it must preserve.

Deep Research uses a runtime-owned lifecycle. `deep-research.md` is the
compatible human-readable projection, not the canonical mutable state surface.

## Context

- Primary inputs: the current spec package, unresolved feasibility risks,
  external references, repository evidence, research-agent findings, and any
  disposable prototype evidence created in this command.
- The active working set is `spec.md`, `alignment.md`, `context.md`,
  `references.md`, `deep-research.md`, `research-spikes/`,
  `research/state.json`, `research/track-manifest.json`,
  `research/handoffs/`, `research/rejections/`, `research/synthesis.json`,
  `research/audit-request.json`, `research/audit.json`,
  `research/handoff-to-plan.json`, `research-evidence/`, and `workflow-state.md`
  inside the current `FEATURE_DIR`.
- This command is research-only. It is not permission to implement production
  behavior.

## Process

- Decide whether a feasibility and research handoff gate is actually needed.
- Drive the runtime lifecycle in order: `init -> status -> track-prepare ->
  track-lease -> (track-submit -> track-accept | track-reject; or track-yield) -> synthesize ->
  audit-prepare -> audit-accept -> validate -> publish -> verify-handoff`, or
  `not-needed` for the lightweight path.
- Decompose unknown implementation chains by capability and independent
  research track.
- Dispatch every substantive track to a bounded subagent. Use one-subagent for
  a single or write-overlapping lane and parallel-subagents only for independent
  tracks with disjoint write scopes.
- Research external APIs, libraries, algorithms, platform constraints, and
  repository patterns only where those facts change planning.
- Build the smallest disposable demo or spike when research alone cannot prove
  the chain.
- Synthesize research-agent findings and spike results into planning decisions,
  rejected options, risks, and a concrete `/sp.plan` handoff.
- Run reverse coverage validation before handoff: every CAP → PH → Evidence chain must close.
- Run readiness refusal checks; refuse handoff with a gap report when checks fail.
- Run the Planning Handoff Readiness Checklist; do not recommend `/sp.plan` until all items pass.

## Output Contract

- Canonical Deep Research outputs are runtime-owned:
  `research/state.json`, `research/track-manifest.json`,
  `research/handoffs/*.json`, `research/rejections/*.json`, `research/synthesis.json`,
  `research/audit-request.json`, `research/audit.json`,
  `research/handoff-to-plan.json`, and `research-evidence/*.json`.
- `deep-research.md` is the compatible projection for human review and legacy
  readers. Query it with `artifact show`, but never patch it: the runtime alone
  derives it from canonical synthesis. Never treat it as a mutable ledger.
- Optionally submit isolated text/code scratch assets under `research-spikes/` through the artifact CLI; import binary proof through the evidence CLI.
- Mutate `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` only through their registered artifact owner; prefer leased section/JSON-pointer patches
  when feasibility evidence changes planning readiness.
- If this gate is not needed, let the runtime publish the lightweight
  `not-needed` path, preserve the exact `**Status**: Not needed` compatibility
  marker, and do not invent `CAP/TRK/EVD/PH` IDs for already-proven work.
- Publish the canonical `research/handoff-to-plan.json`; the runtime keeps the
  compatible `Planning Handoff` projection synchronized for human review.
- Use stable traceability IDs (`CAP-###`, `TRK-###`, `EVD-###`, `SPK-###`,
  `PH-###`) plus an evidence quality rubric so `/sp.plan` can cite exactly which
  research finding or spike supports each design decision.
- Use `.specify/templates/examples/deep-research/` as the output-shape
  reference when available: `not-needed.md`, `docs-only-evidence.md`, and
  `spike-required.md`.
- Report which capabilities are proven, constrained, blocked, or no longer worth
  planning.
- Submit accepted evidence objects inside the matching `deep-research track-submit`
  payload. The runtime validates and materializes
  `FEATURE_DIR/research-evidence/<EVD-###>.json`; never author or patch those
  canonical packets directly.
- The leader accepts submitted packets with `deep-research track-accept` or
  rejects them with `deep-research track-reject`. Rejection snapshots and the
  single retry transition are runtime-owned under `research/rejections/`.

## Guardrails

- Do not edit production source files, tests, migrations, release config, or
  implementation artifacts from `sp-deep-research`.
- Keep demos disposable and isolated under `FEATURE_DIR/research-spikes/` unless
  the user explicitly asks to preserve a prototype elsewhere in a later
  implementation workflow.
- Skip this command when the change is a minor adjustment to an existing,
  already-proven capability.
- Do not let research subagents edit production files; they must either
  return evidence packets or write only to their assigned disposable spike
  directory.
- A research pass without runnable evidence (spike result or repo path trace) is a failed pass.
- Coordinator-only execution without subagent dispatch justification and recorded `subagent-blocked` reason is a failed pass.
- Feasibility claims based only on documentation citations without live repository path reads are not sufficient for planning.
- Subagent evidence packets without `paths_read` must be rejected; do not accept or synthesize them.
- A structural-only refresh (reformatting findings without new evidence) is a failed pass.
- External tools may collect or verify sources, but provider choice is not part
  of the binding contract. Keep source acquisition provider-neutral.
- Treat `context.md` Locked Decisions as immutable constraints during research.
  Do not research alternatives that contradict a locked decision unless the
  research explicitly proves the locked decision is infeasible, in which case
  mark the affected CAP as `blocked` and escalate; do not silently replace the
  locked decision.
