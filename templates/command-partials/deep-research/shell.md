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
- Use native multi-agent/subagent delegation when independent research tracks can
  run in parallel and produce evidence packets without conflicting writes.
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
- Include a `Planning Handoff` section that `/sp.plan` can consume directly for
  recommended approach, module boundaries, API/library choices, demo artifacts,
  constraints, rejected options, and residual risks.
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
- Do not let child research agents edit production files; they must either
  return evidence packets or write only to their assigned disposable spike
  directory.
