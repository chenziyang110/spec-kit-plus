{{spec-kit-include: ../common/user-input.md}}

## Objective

Produce a planning-ready research packet before implementation planning starts:
prove or retire planning-critical feasibility questions, synthesize external and
repository evidence, validate uncertain links with disposable demo spikes when
needed, and hand `/sp.plan` the constraints and recommended implementation
direction it must preserve.

## Context

- Primary inputs: the current spec package, unresolved feasibility risks,
  external references, repository evidence, research-agent findings, and any
  disposable prototype evidence created in this command.
- The active working set is `spec.md`, `alignment.md`, `context.md`,
  `references.md`, `deep-research.md`, `research-spikes/`, and
  `workflow-state.md` inside the current `FEATURE_DIR`.
- This command is research-only. It is not permission to implement production
  behavior.

## Process

- Decide whether a feasibility and research handoff gate is actually needed.
- Decompose unknown implementation chains by capability and independent
  research track.
- Dispatch subagents when independent research tracks can run in parallel and
  produce evidence packets without conflicting writes.
- Research external APIs, libraries, algorithms, platform constraints, and
  repository patterns only where those facts change planning.
- Build the smallest disposable demo or spike when research alone cannot prove
  the chain.
- Synthesize research-agent findings and spike results into planning decisions,
  rejected options, risks, and a concrete `/sp.plan` handoff.

## Output Contract

- Write or update `deep-research.md`.
- Optionally write isolated scratch assets under `research-spikes/`.
- Update `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`
  when feasibility evidence changes planning readiness.
- If this gate is not needed, still write a lightweight `deep-research.md`
  with `**Status**: Not needed`, `Feasibility Decision`, `Planning Handoff`,
  and `Next Command`; do not invent `CAP/TRK/EVD/PH` IDs for already-proven
  work.
- Include a `Planning Handoff` section that `/sp.plan` can consume directly for
  recommended approach, module boundaries, API/library choices, demo artifacts,
  constraints, rejected options, and residual risks.
- Use stable traceability IDs (`CAP-###`, `TRK-###`, `EVD-###`, `SPK-###`,
  `PH-###`) plus an evidence quality rubric so `/sp.plan` can cite exactly which
  research finding or spike supports each design decision.
- Use `.specify/templates/examples/deep-research/` as the output-shape
  reference when available: `not-needed.md`, `docs-only-evidence.md`, and
  `spike-required.md`.
- Report which capabilities are proven, constrained, blocked, or no longer worth
  planning.

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
