---
description: Use when a user invokes `sp-research` but the intended Spec Kit workflow is the pre-plan `sp-deep-research` feasibility gate.
workflow_contract:
  when_to_use: Compatibility alias for /sp.deep-research.
  primary_objective: Route immediately into /sp.deep-research with the same user request.
  primary_outputs: No separate `sp-research` artifacts; the canonical command writes `FEATURE_DIR/deep-research.md`, optional `research-spikes/`, and `workflow-state.md`.
  default_handoff: /sp-deep-research
handoffs:
  - label: Run Deep Research
    agent: sp.deep-research
    prompt: Continue with the canonical deep-research workflow using the same arguments.
    send: true
---

# `/sp.research` Compatibility Alias

## Workflow Contract Summary

{{spec-kit-include: ../command-partials/common/execution-note.md}}

## Objective

[AGENT] Treat `sp-research` as a compatibility alias for `sp-deep-research`.
Route immediately to the canonical deep-research workflow without creating a separate workflow lane or artifact set.

## Context

- `sp-research` exists only for compatibility with users who name research as a Spec Kit command.
- The canonical workflow is `sp-deep-research`.
- Canonical outputs belong to `sp-deep-research`: `FEATURE_DIR/deep-research.md`, optional `FEATURE_DIR/research-spikes/`, and `workflow-state.md`.

## Process

- Preserve the user's original request and arguments: `$ARGUMENTS`.
- Immediately continue with `/sp.deep-research` / `sp-deep-research`.
- Do not create or persist a separate `sp-research` workflow state.

## Output Contract

- Do not write separate `sp-research` artifacts.
- If a workflow state is written, it must use `active_command: sp-deep-research`.
- If deep research is not needed, let the canonical `sp-deep-research` command write its lightweight not-needed handoff.

## Guardrails

- If this command was invoked for generic web research rather than a planning-ready spec feasibility gate, route to the passive external/web research skill instead of writing Spec Kit feature artifacts.
- Do not treat `sp-research` as a replacement for `sp-plan`, `sp-test-scan`, or any implementation workflow.
