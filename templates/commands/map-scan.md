---
description: Use when a brownfield workflow needs a fresh graph-native cognition baseline and you must collect full project-internal evidence before graph reconstruction.
workflow_contract:
  when_to_use: A workflow needs reliable brownfield cognition and no graph-native baseline exists yet, or a full baseline rebuild is explicitly required.
  primary_objective: Enumerate all project-relevant in-repo evidence, build provisional nodes and candidate edges, and publish the scan artifacts required for graph reconstruction.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, and `.specify/project-cognition/coverage.json`.'
  default_handoff: /sp-map-build after the evidence baseline is complete and the scan outputs are ready for graph reconstruction.
---

{{spec-kit-include: ../command-partials/map-scan/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-scan --format json}}` when available so passive learning files exist and repeated cognition-runtime scan blind spots can be promoted at start.
- [AGENT] When scan friction appears, use the `signal-learning` helper surface: `{{specify-subcmd:hook signal-learning --command map-scan --route-changes <n> --artifact-rewrites <n> --false-start "<summary>"}}`.
- [AGENT] Before reporting completion or a blocked scan, use the `review-learning` helper surface: `{{specify-subcmd:hook review-learning --command map-scan --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`.

## Hard Boundary

- `sp-map-scan` must not publish final cognition truth.
- `sp-map-scan` must not claim the baseline is graph-ready.
- `sp-map-scan` must produce evidence, provisional nodes, provisional edges, observations, and coverage diagnostics only.
- `sp-map-scan` may classify evidence and derive provisional structure, but `sp-map-build` owns claim synthesis, conflict construction, confidence assignment, and slice publication.

## Output Contract

The only canonical outputs for this command are:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- `.specify/project-cognition/coverage.json`

Do not create handbook-first brownfield truth, alternate mapping trees, or canonical runtime documents during `sp-map-scan`.

## Scan Duties

`sp-map-scan` must:

- enumerate project-internal evidence comprehensively
- classify project-relevant repository surfaces
- gather evidence from committed source, tests, scripts, configs, docs, templates, generated-surface sources, and `.git` history
- construct provisional nodes and candidate edges
- record uncertainty, blockers, and missing evidence explicitly
- stay graph-native from the start rather than staging a handbook-first atlas

## Required Evidence Coverage

The scan must cover:

- source and symbol surfaces
- module and ownership surfaces
- capability and workflow surfaces
- state and handoff surfaces
- verification surfaces
- risk and fragility surfaces
- high-value `.git` evolution surfaces

If project-relevant evidence cannot be classified, the scan must remain blocked instead of silently downgrading the gap.

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-scan", snapshot, workload_shape)` before broad work begins.
- Recommended scan lanes include source/symbol discovery, module boundaries, capability flows, state surfaces, build/test/runtime surfaces, and git evolution surfaces.
- Every lane must return inspected paths, evidence harvested, confidence notes, and provisional structure updates.

## Completion Rule

Before reporting completion:

- confirm that the evidence baseline exists under `.specify/project-cognition/`
- confirm that provisional nodes and candidate edges were written
- confirm that the scan still has not published final cognition truth
- report any open uncertainty that `sp-map-build` must reconcile
