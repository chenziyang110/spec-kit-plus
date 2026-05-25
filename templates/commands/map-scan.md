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

## Machine-Readable Blocked State

Human workflow prose may say `subagent-blocked`, but persisted machine fields use
`subagent_blocked`.

If a substantive scan/build lane cannot dispatch or complete, write:

- `.specify/project-cognition/status.json` with `baseline_state=blocked` and
  `subagent_blocked` in `stale_reasons` or `dirty_reasons`
- `.specify/project-cognition/workbench/map-state.md` with
  `readiness=blocked`, `blocking_reason=subagent_blocked`, blocked lane ids,
  blocked scope, and recovery condition
- `.specify/project-cognition/workbench/coverage-ledger.json.open_gaps[]` with
  `reason="subagent_blocked"`, `lane_id`, `packet_id`, `blocked_scope`,
  `criticality`, `owner`, `status="blocked"`, and `recovery_condition`

`unknown` blocks, `blocked`, `critical_open_gap`, and `subagent_blocked` block baseline
activation. `low_risk_open_gap` may pass only with owner, reason,
`evidence_expectation`, and `revisit_condition`.

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
- `.specify/project-cognition/workbench/worker-results/<packet-id>.json`
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
- Respect project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`. These files use gitignore-compatible syntax, including comments, directory patterns, globs, `**`, and `!` re-includes.
- `.cognitionignore` excludes project cognition scan/build/update targets only; it does not replace `.gitignore` or prove that ignored code is irrelevant to other tooling.
- If the required scan lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Project Cognition Workbench State Protocol

- `MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md`
- Treat `.specify/project-cognition/workbench/map-state.md` as the refresh-workbench state surface for scan progress, accepted packets, and unresolved gaps.
- Scan packets are executable read instructions, not final truth documents.
- `MapScanPacket` is the required packet contract for each delegated scan lane.
- Each packet must declare `mode: read_only` and a `result_handoff_path`.
- Each `result_handoff_path` must point to `.specify/project-cognition/workbench/worker-results/<packet-id>.json`.
- Every `scan-packets/<lane-id>.md` file must have exactly one matching `worker-results/<lane-id>.json` handoff, and worker results without a matching scan packet are invalid.
- Worker result handoffs are the machine-checkable evidence surface for packet acceptance.
- Prefer `rg --files` for inventory discovery before escalating to deeper reads.
- Filter `rg --files`, Git-tracked file lists, and any user-provided scan hints through `.cognitionignore` before writing `.specify/project-cognition/workbench/repository-universe.json`.
- Raw inventory notes or raw chat summaries are not sufficient.
- Idle subagent output is not an accepted scan result.
- The leader must wait for every dispatched scan lane to return a structured handoff before closing the scan stage.
- Even when freshness is `fresh`, `sp-map-scan` still reasons from the git baseline diff before deciding whether the refresh workbench needs new coverage.
- Reference-only material is a live surface only for refresh-workbench validation; it must not become a scan target by default.

## Canonical Boundary Contract

- `.specify/project-cognition/workbench/repository-universe.json` is the canonical boundary artifact.
- It must include `schema_version`, `candidate_universe`, `included_paths`, `excluded_paths`, `ambiguous_paths`, `dispositions`, `criticality`, `classification_reasons`, and `decision_source`.
- Every candidate path must receive exactly one disposition: `deep_read`, `sampled`, `inventory_only`, `excluded`, or `blocked`.
- Disposition is separate from criticality. Criticality remains `critical`, `important`, or `low_risk`.
- sampled and inventory_only are not free-form convenience labels; they must align with the recorded disposition and criticality in `repository-universe.json`.
- Critical entrypoints, shared state, configuration, tests, verification surfaces, and generated-surface propagation chains should not pass as `sampled` unless the boundary artifact already records an explicit accepted gap or an equally explicit lower-depth decision.
- `sampled` and `inventory_only` are acceptable only when the disposition and criticality together justify them.
- Excluded paths must not appear in graph-facing `coverage.json` rows, evidence rows, provisional nodes, provisional edges, observations, path indexes, route indexes, or `minimal_live_reads`.
- `MapScanPacket` must include bounded `assigned_paths`.
- Each packet carries a packet-local task ledger with `todo`, `doing`, `done`, `blocked`, and `overflow`.
- Each accepted worker result must repeat `assigned_paths`, include `paths_read` as a non-empty array of concrete repository paths, include packet-local `coverage` rows for the final outcome of each assigned path, and include confidence.
- `paths_read: true`, summary-only read claims, and boolean read flags are invalid.
- `read` and `deep_read` outcomes must reference existing `evidence_ids`, and at least one referenced evidence row must have `source_path` equal to the covered path.
- Subagents must account for every assigned path with evidence, `sampled`, `inventory_only`, `excluded`, `blocked`, or `overflow`.
- If assigned paths do not fit in context, the subagent must return `overflow` or `blocked`; the leader must split and redispatch or record an open gap.
- Leader acceptance has two gates: a coverage gate that requires every assigned path to have a declared outcome, and a quality gate that rejects summary-only or inconsistent evidence.
- The leader may classify packet failure as `fail_gap`, `fail_quality`, `fail_contract`, or `fail_systemic`.
- `fail_quality` must return a machine-checkable repack subset naming at least one of `paths[]`, `claim_ids[]`, `coverage_row_ids[]`, or `evidence_ids[]`; otherwise treat it as `fail_contract`.
- Any acceptance value other than `pass` blocks scan acceptance until the leader repacks, repairs, or explicitly records the unresolved gap.
- `fail_contract` and `fail_systemic` do not use local patch-only redispatch; repair the packet schema/boundary or repack the affected packet family.

## Scan Duties

`sp-map-scan` must:

- enumerate project-internal evidence comprehensively
- generate a full project-relevant inventory across nested directories and Git-tracked files
- write `.specify/project-cognition/workbench/repository-universe.json` with `included_paths` and `excluded_paths`; every `.cognitionignore` match belongs in `excluded_paths` with the matched rule or a human-readable reason
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
- `.cognitionignore`-excluded paths must not appear in coverage rows, evidence rows, provisional nodes, provisional edges, observations, or scan packets unless a later `!` rule re-includes the path.

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

## Consequence Substrate Evidence

During the first baseline scan and rare full rebuilds, scan packets must collect the evidence that lets later workflows reason like a long-term project maintainer:

- ownership evidence for files, modules, commands, APIs, generated assets, and workflow state
- upstream and downstream consumers, including generated-surface propagation and adjacent workflow dependencies
- lifecycle and state surfaces, including active/running actors, queues, sessions, locks, caches, persisted state, and cleanup paths
- shared mutable state and destructive-operation surfaces where close/delete/archive/rename/migrate behavior can affect other work
- compatibility, migration, rollback, retry, idempotency, and observability evidence
- verification routes that prove affected owners, consumers, state transitions, and recovery paths
- confidence notes, conflicts, known unknowns, and minimal live reads needed when later `sp-map-update` cannot fully prove an edge from existing evidence

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

## Concept Retrieval Signal Evidence

- Collect concept retrieval signals that let `project-cognition lexicon` surface
  useful `concept_candidates` instead of only path or symbol matches.
- Record colloquial user phrases, aliases, shorthand, command names, workflow
  names, symptoms, and domain vocabulary that maintainers naturally use when
  asking for work.
- Attach domain ownership evidence to each retrieval signal, including owning
  paths, modules, generated surfaces, workflow artifacts, tests, and supporting
  evidence rows.
- Preserve conflicts, weak ownership, and unknown mappings as scan evidence for
  `sp-map-build` rather than flattening them into accepted keywords.

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
