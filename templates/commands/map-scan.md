---
description: Use when a brownfield workflow needs a fresh graph-native cognition baseline and you must collect full project-internal evidence before graph reconstruction.
workflow_contract:
  when_to_use: A workflow needs reliable brownfield cognition and no graph-native baseline exists yet, or a full baseline rebuild is explicitly required.
  primary_objective: Enumerate all project-relevant in-repo evidence, build provisional nodes and candidate edges, and publish the scan artifacts required for graph reconstruction.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, `.specify/project-cognition/coverage.json`, `.specify/project-cognition/workbench/coverage-ledger.*`, and `.specify/project-cognition/workbench/map-state.md`.'
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

## Process

- Build the evidence baseline before any graph reconstruction work begins.
- Dispatch each bounded scan lane only from a validated `MapScanPacket`.
- Wait for every dispatched lane's structured handoff before accepting scan coverage.
- If a safe scan lane cannot be packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-scan --format json}}` when available so passive learning files exist and repeated cognition-runtime scan blind spots can be promoted at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader scan context.
- Passive learning files are workflow guidance, not scan evidence.
- `.specify/**` must never enter the project cognition graph.
- `.specify/memory/**` must not appear in repository-universe, coverage-ledger, evidence rows, provisional nodes, provisional edges, observations, path_index, alias_index, or graph claims.
- Open only learning detail docs linked from map-scan-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When scan friction exposes route changes, artifact rewrites, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `map-state.md` captures that durable context.
- [AGENT] When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.

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
- `.specify/project-cognition/workbench/map-scan.md`
- `.specify/project-cognition/workbench/coverage-ledger.md`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/<lane-id>.md`
- `.specify/project-cognition/workbench/map-state.md`
- `.specify/project-cognition/workbench/repository-universe.json`
- `.specify/project-cognition/workbench/capability-ledger.json`
- `.specify/project-cognition/workbench/control-ledger.json`
- refresh-workbench `coverage-ledger` artifacts that summarize scan coverage for follow-on build validation
- `map-state.md` as the scan-stage workbench state surface

Do not create handbook-first brownfield truth, alternate mapping trees, or canonical runtime documents during `sp-map-scan`.

## Guardrails

- Do not publish final cognition truth from this command.
- Do not treat raw inventory notes or raw chat summaries as accepted scan results.
- Do not silently downgrade unknown or unclassified project-relevant surfaces.
- `.specify/**` workflow/runtime state is excluded from default source/runtime scan targets; do not put `.specify/**` paths into project graph evidence.
- Only read `.specify/**` for workflow operation, validation, migration, or when the requested scan is explicitly about generated workflow surfaces or spec-kit-plus itself; even then, classify it as workflow/reference support rather than source/runtime graph truth.
- If the required scan lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Project Cognition Workbench State Protocol

- `MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md`
- Treat `.specify/project-cognition/workbench/map-state.md` as the refresh-workbench state surface for scan progress, accepted packets, and unresolved gaps.
- Scan packets are executable read instructions, not final truth documents.
- `MapScanPacket` is the required packet contract for each delegated scan lane.
- Each packet must declare `mode: read_only` and a `result_handoff_path`.
- Prefer `rg --files` for inventory discovery before escalating to deeper reads.
- Raw inventory notes or raw chat summaries are not sufficient.
- Idle subagent output is not an accepted scan result.
- The leader must wait for every dispatched scan lane to return a structured handoff before closing the scan stage.
- Even when freshness is `fresh`, `sp-map-scan` still reasons from the git baseline diff before deciding whether the refresh workbench needs new coverage.
- Reference-only material is a live surface only for refresh-workbench validation; it must not become a scan target by default.

## Scan Duties

`sp-map-scan` must:

- enumerate project-internal evidence comprehensively
- generate a full project-relevant inventory across nested directories and Git-tracked files
- classify project-relevant repository surfaces
- gather evidence from committed source, tests, scripts, configs, docs, templates, generated-surface sources, and `.git` history
- construct provisional nodes and candidate edges
- record uncertainty, blockers, and missing evidence explicitly
- stay graph-native from the start rather than staging a handbook-first atlas
- current-runtime native subagents are the default execution surface for scan lanes
- scan packets are executable read instructions and must still execute the packet reads before the leader accepts atlas evidence
- every project-relevant row is categorized with coverage classes such as `inventory`, `sampled`, `deep-read`, `critical`, `important`, and `low-risk`
- `unknown` is a scan failure
- maintain `excluded_from_deep_read` reasoning for `vendor-cache-build-output` and similar excluded roots
- Git-tracked files remain the primary inventory boundary unless the scan explicitly records why untracked evidence matters.

## Coverage Classification

- Coverage classification must explain why each surface is `inventory`, `sampled`, `deep-read`, `critical`, `important`, or `low-risk`.
- Every project-relevant row is categorized before the scan can report completion.

## Criticality Scoring

- Criticality scoring must explain why a surface escalates toward `critical` or can stay `low-risk`.
- Atlas evidence should prioritize owner, consumer, change propagation, and verification reachability for higher-criticality rows.

## Required Evidence Coverage

The scan must cover:

- project shape and stack
- architecture overview
- directory ownership
- module dependency graph
- core code elements
- entry and api surfaces
- data and state flows
- user and maintainer workflows
- integrations and protocol boundaries
- build, release, and runtime
- testing and verification
- risk, security, observability, and evolution
- template and generated-surface propagation
- coverage reverse index
- layer 1 retrieval inputs
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
- Dispatch each scan lane from a validated `MapScanPacket`.
- Recommended scan lanes include source/symbol discovery, module boundaries, capability flows, state surfaces, build/test/runtime surfaces, and git evolution surfaces.
- Every lane must return inspected paths, evidence harvested, confidence notes, and provisional structure updates.
- Must wait for every dispatched scan lane and consume its structured handoff before the scan closes.

## Layer 1 Route Material

- Generate layer 1 retrieval source material before the build phase begins.
- Produce task route candidates.
- Produce symptom route candidates.
- Produce shared-surface hotspot candidates.
- Produce verification route candidates.
- Produce propagation-risk route candidates.

## Truth Layer Ledgers

- Maintain file, entrypoint, branch, and control-node coverage.
- Summarize ledger coverage by capability.
- Summarize ledger coverage by symptom.

## Completion Rule

Before reporting completion:

- confirm that the evidence baseline exists under `.specify/project-cognition/`
- confirm that provisional nodes and candidate edges were written
- run `{{specify-subcmd:project-cognition validate-scan --format json}}` before handoff to `sp-map-build`
- `sp-map-scan` may report complete only after `validate-scan` returns `status=ok` and `readiness=scan_ready`
- if `validate-scan` returns `status=blocked`, report the blocking errors and do not claim the scan package is build-ready
- confirm that the scan still has not published final cognition truth
- report any open uncertainty that `sp-map-build` must reconcile
