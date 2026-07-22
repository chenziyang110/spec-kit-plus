---
description: Use when a brownfield workflow needs a fresh graph-native cognition baseline and you must collect full project-internal evidence before graph reconstruction.
workflow_contract:
  when_to_use: A workflow needs reliable brownfield cognition and no graph-native baseline exists yet, or a full baseline rebuild is explicitly required.
  primary_objective: Enumerate the full project file universe cheaply, classify file value, deep-scan the highest-value project evidence, build provisional nodes and candidate edges, and publish the scan artifacts required for graph reconstruction.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, `.specify/project-cognition/coverage.json`, `.specify/project-cognition/workbench/repository-universe.json`, `.specify/project-cognition/workbench/scan-targets.json`, `.specify/project-cognition/workbench/coverage-ledger.*`, `.specify/project-cognition/workbench/scan-queue.json`, `.specify/project-cognition/workbench/handoff-ledger.json`, and `.specify/project-cognition/workbench/map-state.md`.'
  default_handoff: /sp-map-build after the evidence baseline is complete and the scan outputs are ready for graph reconstruction.
---

{{spec-kit-include: ../command-partials/map-scan/shell.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying shared semantic contracts.

- [semantic work contract](references/semantic-work-contract.md)

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, ask the Project Cognition CLI to budget and split
tasks, dispatch subagents from CLI-generated contracts, submit structured
handoffs through the CLI, verify runtime state, and continue until no work
remains. The leader does not author scheduler or acceptance state.

Before dispatch, every subagent lane needs the CLI-generated task contract with
objective, authoritative inputs, allowed read/write scope, forbidden paths,
acceptance checks, verification evidence, structured handoff format, and the
effective context budget for that attempt. Do not reconstruct this stable
contract from prose or chat memory.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Process

- Before repository inventory, run `{{specify-subcmd:specify-runtime cognition generate-ignore --format json}}`. If it creates `.specify/project-cognition/.cognitionignore`, ask the user to review the starter suggestions and wait for confirmation before continuing.
- After the ignore gate is clear, run `{{specify-subcmd:specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}` and use the returned file list as the candidate scan set. The agent may choose scan intent and concrete `--scope` values, but `specify-runtime cognition scan-set` decides the initial included file list through deterministic runtime rules; do not let the agent freely decide which files to omit.
- Run `{{specify-subcmd:specify-runtime cognition scan-prepare}}` against that scan set.
  It performs the cheap inventory/classification pass, estimates token cost,
  calculates each worker's effective context budget after instruction,
  inherited-context, reasoning, tool-output, checkpoint, result-output, and
  safety reserves, and deterministically renders bounded packets. Estimated
  token cost is the primary packing constraint; path count and byte limits are
  secondary guards.
- Build a value-weighted evidence baseline before any graph reconstruction work
  begins. The runtime classifies every non-excluded candidate path as `P0`,
  `P1`, `P2`, or `P3`, keeps related paths together when the budget permits, and
  creates an oversized single-path packet rather than silently truncating a
  file that cannot fit a normal packet.
- Drive dispatch from `{{specify-subcmd:specify-runtime cognition scan-status --format json}}`, which
  returns the compact pending/leased/accepted state and the next safe action.
  Bound each wave by the platform's currently available subagent slots and the
  selected models' effective capacities; never spawn one worker per pending
  packet merely because the queue is parallelizable.
  Use `{{specify-subcmd:specify-runtime cognition scan-lease --worker-id <worker-id> --format json}}` to claim one prepared
  packet and attempt, then give its CLI-generated self-contained task brief to
  one capable subagent with the minimum inherited conversation context the
  platform permits. Count any unavoidable inherited context against that
  worker's effective budget. An oversized packet is not dispatchable by
  default: select a worker whose effective capacity meets the returned
  estimate and lease it with `--worker-capacity-tokens <tokens>`, or stop and
  re-plan. Never knowingly assign more estimated work than the selected worker
  can consume.
- Require the worker to submit bounded packet-local progress through
  `{{specify-subcmd:specify-runtime cognition scan-checkpoint}}`. When it predicts that
  context, tool-output, or result-output capacity will run out, it checkpoints
  completed work and uses `{{specify-subcmd:specify-runtime cognition scan-yield}}`; it
  must not guess, omit paths, or claim the whole packet complete.
- Finish a complete attempt with
  `{{specify-subcmd:specify-runtime cognition scan-accept --packet-id <packet-id> --attempt-id <attempt-id> --format json}}`. The runtime validates the
  attempt, merges accepted packet-local data atomically, and computes the
  authoritative remaining set as assigned paths minus runtime-accepted terminal
  paths. A yield or partial result requeues only that remaining set; dispatch a
  new subagent for the remaining paths from the next `scan-lease` task brief.
  If a worker disconnects or stops before yielding, use the active packet and
  attempt identifiers returned by `scan-status` with `scan-requeue`; accepted
  checkpoints are retained and only the exact remainder becomes pending.
- Repeat status, lease, checkpoint/yield/accept until the runtime reports no
  pending, leased, yielded, or blocked high-value work. Wait for every
  dispatched lane's structured handoff before accepting scan coverage.
- If a safe scan lane cannot be packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Value-Weighted Repository Inventory

`sp-map-scan` must inventory all candidate paths from the runtime-resolved scan
set, but it must not deep-read all files by default. The first pass is a
path-level accounting pass, not a content scan.

`scan-prepare` materializes
`.specify/project-cognition/workbench/repository-universe.json` with one row per
candidate path from `.specify/project-cognition/tmp/scan-files.json`; the leader
must not hand-write it.
Runtime-excluded paths may be recorded only in boundary accounting when the
runtime exposes them through a debug/explain path; the default agent-facing
scan-set handoff intentionally contains only included files. Each included or
ambiguous row should record:

- `path`: repository-relative path
- `path_kind`: `source`, `test`, `config`, `script`, `doc`, `template`, `asset`, `generated`, `vendor`, `build_output`, `lockfile`, `unknown`
- `extension`
- `size_bytes`
- `directory_family`
- `git_tracked`
- `ignored_by_cognition`
- `matched_ignore_rule` when applicable
- `value_tier`: `P0`, `P1`, `P2`, or `P3`
- `scan_decision`: `scan`, `sample`, `inventory_only`, `exclude`, or `blocked`
- `disposition`: existing boundary disposition: `deep_read`, `sampled`, `inventory_only`, `excluded`, or `blocked`
- `criticality`: `critical`, `important`, or `low_risk`
- `classification_reasons`
- `decision_source`

Value tier rules:

- `P0`: application/runtime entrypoints, CLI commands, routes/controllers,
  public APIs, core services, state machines, data flow owners, protocol
  boundaries, security/auth/payment/destructive-operation surfaces, generated
  source templates that affect downstream behavior, and primary user workflows.
- `P1`: package/build/config manifests, CI/release scripts, migrations/schemas,
  adapter boundaries, feature gates, runtime wiring, verification entrypoints,
  and docs that define behavior or operator contracts.
- `P2`: tests, examples, secondary docs, story/demo files, and usage samples.
  Scan them when they prove behavior, expected contracts, or verification
  reachability; otherwise sample or inventory them.
- `P3`: vendored dependencies, generated bundles, cache/build/dist output,
  binary/static assets, lockfiles that do not define behavior beyond dependency
  identity, archived material, and large low-signal files. Keep these as
  `inventory_only` or `excluded` unless explicitly needed.

`scan-prepare` also materializes
`.specify/project-cognition/workbench/scan-targets.json` with the subset selected
for packet dispatch. It includes:

- `schema_version`
- `selection_policy: "value_weighted"`
- `selected_paths`
- `sampled_paths`
- `inventory_only_paths`
- `excluded_paths`
- `blocked_paths`
- per-path `value_tier`, `scan_decision`, `disposition`, `criticality`, and
  `classification_reasons`

High-value coverage is more important than raw path-count coverage. A scan can
validly leave many `P3` paths inventory-only, but it must not leave unexplained
`P0` or `P1` gaps.

## Machine-Readable Blocked State

Human workflow prose may say `subagent-blocked`, but persisted machine fields use
`subagent_blocked`.

If a substantive scan/build lane cannot dispatch or complete, use the runtime's
yield/block/requeue surface and verify through
`{{specify-subcmd:specify-runtime cognition scan-status}}`.
Only the runtime may persist:

- `.specify/project-cognition/status.json` with `baseline_state=blocked` and
  `subagent_blocked` in `stale_reasons` or `dirty_reasons`
- `.specify/project-cognition/workbench/map-state.md` with
  `readiness=blocked`, `blocking_reason=subagent_blocked`, blocked lane ids,
  blocked scope, and recovery condition
- `.specify/project-cognition/workbench/coverage-ledger.json.open_gaps[]` with
  `reason="subagent_blocked"`, `lane_id`, `packet_id`, `blocked_scope`,
  `criticality`, `owner`, `status="blocked"`, and `recovery_condition`

Do not edit these global state projections to manufacture or clear a blocker.

`unknown` blocks, `blocked`, `critical_open_gap`, and `subagent_blocked` block baseline
activation. `low_risk_open_gap` may pass only with owner, reason,
`evidence_expectation`, and `revisit_condition`.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

- Passive learning files are workflow guidance, not scan evidence.
- `.specify/**` must never enter the project cognition graph.
- `.specify/memory/**` must not appear in repository-universe, coverage-ledger, evidence rows, provisional nodes, provisional edges, observations, path_index, or alias_index.

## Hard Boundary

- `sp-map-scan` must not publish final cognition truth.
- `sp-map-scan` must not claim the baseline is graph-ready.
- `sp-map-scan` must produce evidence, provisional nodes, provisional edges, observations, and coverage diagnostics only.
- `sp-map-scan` may classify evidence and derive provisional structure, but `sp-map-build` owns schema v5 graph-store publication, confidence assignment, typed graph-claim lifecycle derivation, route validation, revision-bound claim-reconciliation basis support, and alias catalog readiness.

## Output Contract

The only canonical outputs for this command are the runtime-materialized
surfaces below. Workers produce packet-local submissions; only the runtime may
merge or update these global artifacts:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- optional `.specify/project-cognition/provisional/claims.json`
- `.specify/project-cognition/coverage.json`
- `.specify/project-cognition/workbench/map-scan.md`
- `.specify/project-cognition/workbench/coverage-ledger.md`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-queue.json`
- `.specify/project-cognition/workbench/handoff-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/<lane-id>.md`
- `.specify/project-cognition/workbench/worker-results/<packet-id>.json`
- `.specify/project-cognition/workbench/map-state.md`
- `.specify/project-cognition/workbench/repository-universe.json`
- `.specify/project-cognition/workbench/scan-targets.json`
- `.specify/project-cognition/workbench/capability-ledger.json`
- `.specify/project-cognition/workbench/control-ledger.json`
- refresh-workbench `coverage-ledger` artifacts that summarize scan coverage for follow-on build validation
- `map-state.md` as the scan-stage workbench state surface

Do not create handbook-first brownfield truth, alternate mapping trees, or canonical runtime documents during `sp-map-scan`.

## Runtime-Owned Machine-Readable Scan Artifact Schema

The CLI-generated result skeleton is the schema authority. Workers fill only
their designated packet-local skeleton and submit it with `scan-checkpoint`;
the leader must not copy this section into an improvised JSON contract. The
runtime accepts a few legacy aliases when validating old inputs, but new packet
results use the generated canonical shape so `sp-map-build` can reconstruct the
graph without manual repair.

`provisional/nodes.json` must contain a top-level `nodes` array. Each node row
uses:

- `id`: stable node identity. Do not write placeholder values such as `NO_ID`.
- `type`: node class such as `capability`, `module`, `file`, `page`, `command`, `test`, or `state`.
- `title`: human-readable node title.
- `paths`: concrete repository file paths owned or represented by this node. build-from-scan creates path_index rows only from nodes[].paths.
- `confidence`: `verified`, `high`, `medium`, `low`, or `provisional`.
- `evidence_ids`: evidence row IDs that justify the node.
- `attrs`: optional object for secondary metadata.

Emit alias-ready node material for schema v5. `nodes[].title`, `nodes[].type`,
`nodes[].paths`, and `nodes[].attrs.aliases`, `domain`, `owner`, `workflow`,
`route`, `route_hints`, and `verification_hints` feed the `alias_index` during
`sp-map-build`. This creates the alias catalog used to normalize user input
before query planning. Do not write raw observation summaries as aliases.
Observations may support bounded observation tags only when tied to graph
evidence. If validation reports schema v1 or rebuild-required readiness, run
sp-map-scan -> sp-map-build so build-from-scan can publish schema v5 alias
catalog rows.
When writing the recommendation in plain text, use: run sp-map-scan -> sp-map-build.

Compatibility aliases accepted by the runtime are `node_id` for `id`, `kind` for
`type`, `label` or `name` for `title`, and `attrs_json` for `attrs`. These are
fallbacks only; do not use them in newly generated scan artifacts.

`provisional/edges.json` must contain a top-level `edges` array. Each edge row
uses `id`, `type`, `source_id`, `target_id`, `confidence`, `evidence_ids`, and
optional `attrs`. `source_id` and `target_id` should reference node IDs. The
runtime can resolve a file path endpoint to a node only when exactly one node
lists that path in `nodes[].paths`. Compatibility aliases accepted by the
runtime are `source`, `target`, `source_node_id`, `target_node_id`, `kind`, and
`attrs_json`.

`provisional/observations.json` must contain a top-level `observations` array.
Each row uses `id`, `observation_type`, `summary`, `evidence_ids`, and optional
`attrs`. string observations are accepted only as compatibility input and are normalized as `observation_type: note`; new scan artifacts must write objects.

`provisional/claims.json` is optional so legacy-compatible scan packages remain
valid. When present, it must contain a top-level `claims` array. Each graph claim
row uses `id`, `node_id`, `graph_claim_type`, `summary`, optional
`requested_state`, `supporting_evidence_ids`, `contradicting_evidence_ids`,
`verifications`, optional `stale_reason`, and optional `attrs`. Each verification
uses `id`, `result`, optional `command`, `evidence_id`, `observed_at`, and
optional `attrs`. The Agent proposes candidates and evidence; it does not assign
the published lifecycle state. The deterministic compiler derives `candidate`,
`supported`, `verified_in_graph_generation`, `contradicted`, or `stale`, ignores
an unsupported self-promotion in `requested_state`, and blocks missing node or
evidence references. Do not use bare `claim_type` or workflow final claim types
such as `root_cause_claim`, `fixed_claim`, `completed_claim`, or `release_safe`
as graph claim lifecycle fields.

`coverage.json` must contain a top-level `rows` array with `path` values for
coverage accounting. Compatibility input may use a top-level `coverage` array,
but new scan artifacts must write `rows`; do not maintain separate `rows` and
`coverage` lists that can drift. coverage.json does not create path_index rows by itself; every queryable path must also appear in at least one node's `paths` array.

## Guardrails

- Do not publish final cognition truth from this command.
- Do not treat raw inventory notes or raw chat summaries as accepted scan results.
- Natural-language completion claims, worker-authored `pass` values, and leader
  summaries are not acceptance evidence. Only a successful runtime checkpoint
  or accept transition establishes durable progress.
- Workers write only the designated packet-local result/checkpoint surfaces and
  submit them through the CLI. The leader and workers must not hand-write the
  global queue, handoff, coverage, evidence, provisional, and status artifacts,
  or create/patch SQLite as a scan/build shortcut.
- Do not silently downgrade unknown or unclassified project-relevant surfaces.
- `.specify/**` workflow/runtime state is excluded from default source/runtime scan targets; do not put `.specify/**` paths into project graph evidence, nodes, observations, graph claims, path_index, or alias_index.
- Only read `.specify/**` for workflow operation, validation, migration, or when the requested scan is explicitly about generated workflow surfaces or spec-kit-plus itself; even then, classify it as workflow/reference support rather than source/runtime graph truth.
- Respect project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`. These files use gitignore-compatible syntax, including comments, directory patterns, globs, `**`, and `!` re-includes.
- `.cognitionignore` excludes project cognition scan/build/update targets only; it does not replace `.gitignore` or prove that ignored code is irrelevant to other tooling.
- If the required scan lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Project Cognition Workbench State Protocol

- `MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md`
- Treat `.specify/project-cognition/workbench/map-state.md` as the refresh-workbench state surface for scan progress, accepted packets, and unresolved gaps.
- `scan-queue.json`, `scan-targets.json`, and `handoff-ledger.json` are
  runtime-owned projections. Every generated packet has one queue row, every
  leased attempt has matching dispatch/return events, and only runtime commands
  may change them.
- Every scan packet draws concrete `assigned_paths` from the runtime-owned target
  set, not broad directory globs, unclassified path lists, or a leader-created
  manifest.
- The leader loop is: inspect compact `scan-status`, lease a packet, dispatch its
  CLI-generated task brief, let the worker submit packet-local checkpoints,
  accept or yield the attempt through the CLI, then use the updated runtime
  remaining set to dispatch the next bounded wave.
- `scan-prepare` sizes packets against the effective worker context budget.
  Estimated content plus analysis/result token cost is the primary bound; path
  count and bytes are secondary safety limits. Keep behaviorally related paths
  together only when the complete estimated task fits.
- An interrupted, explicitly requeued, yielded, or capacity-exhausted `P0`/`P1` attempt preserves
  runtime-accepted checkpoints and requeues every unaccepted remaining path.
  Only low-risk `P3` or justified `P2` paths may become accepted nonblocking
  inventory gaps.
- The CLI-generated pending result/checkpoint skeleton is authoritative. Workers
  may fill that packet-local shape but must not invent aliases, update global
  artifacts, or self-approve with a top-level outcome or acceptance claim.
- `accepted_nonblocking_gap_paths` contains only low-risk paths with owner, reason, evidence expectation, revisit condition, and `low_risk_open_gap` status.
- Scan packets are executable read instructions, not final truth documents.
- `MapScanPacket` is the required packet contract for each delegated scan lane.
- Each packet must declare `mode: read_only`, its effective context budget, and a `result_handoff_path`.
- Each `result_handoff_path` must point to `.specify/project-cognition/workbench/worker-results/<packet-id>.json`.
- Every `scan-packets/<lane-id>.md` file must have exactly one matching `worker-results/<lane-id>.json` handoff, and worker results without a matching scan packet are invalid.
- Runtime-validated worker checkpoints and result handoffs are the machine-checkable evidence surface for packet acceptance.
- Use `specify-runtime cognition scan-set` for inventory discovery before escalating to deeper reads. `rg --files` may support diagnostics, but it must not replace the runtime-resolved scan set.
- Treat Git-tracked file lists and user-provided scan hints as metadata or `scan-set --scope` inputs; they must not become scan targets until `specify-runtime cognition scan-set` returns them in `.specify/project-cognition/tmp/scan-files.json`.
- Raw inventory notes or raw chat summaries are not sufficient.
- Idle subagent output and natural-language completion claims are not accepted scan results.
- The leader must wait for every dispatched scan lane to return a structured handoff before closing the scan stage.
- Even when freshness is `fresh`, `sp-map-scan` still reasons from the git baseline diff before deciding whether the refresh workbench needs new coverage.
- Reference-only material is a live surface only for refresh-workbench validation; it must not become a scan target by default.

## Canonical Boundary Contract

- `.specify/project-cognition/workbench/repository-universe.json` is the canonical boundary artifact derived from the runtime-resolved scan set.
- It must include `schema_version`, `candidate_universe`, `included_paths`, `excluded_paths`, `ambiguous_paths`, `dispositions`, `criticality`, `value_tier`, `scan_decision`, `path_kind`, `classification_reasons`, and `decision_source`.
- Every candidate path must receive exactly one disposition: `deep_read`, `sampled`, `inventory_only`, `excluded`, or `blocked`.
- Disposition is separate from criticality; value tier adds another classification axis. Value tier remains `P0`, `P1`, `P2`, or `P3`; criticality remains `critical`, `important`, or `low_risk`.
- `scan_decision` is the execution intent derived from value tier and disposition. Use `scan` for deep-read packets, `sample` for sampled proof, `inventory_only` for accounted low-value surfaces, `exclude` for boundary exclusions, and `blocked` when no safe decision can be made.
- sampled and inventory_only are not free-form convenience labels; they must align with the recorded disposition and criticality in `repository-universe.json`.
- Critical entrypoints, shared state, configuration, tests, verification surfaces, generated-surface propagation chains, and any `P0`/`P1` path should not pass as `sampled` or `inventory_only` unless the boundary artifact already records an explicit accepted gap or an equally explicit lower-depth decision.
- `sampled` and `inventory_only` are acceptable only when the disposition and criticality together justify them, with value tier confirming the lower-depth decision.
- Excluded paths must not appear in graph-facing `coverage.json` rows, evidence rows, provisional nodes, provisional edges, observations, path indexes, route indexes, alias indexes, or `minimal_live_reads`.
- `MapScanPacket` must include bounded `assigned_paths`.
- `assigned_paths`, queue rows, worker path results, and worker coverage paths
  must be concrete repository file paths enumerated from
  `repository-universe.json`; globs such as `JZWinReNew/*.cpp`, directory
  patterns, absolute paths, and summary labels are invalid.
- Each packet carries a runtime-generated packet-local task ledger and result
  skeleton. The worker records concrete path outcomes and confidence only in
  that designated packet-local surface, then submits it through
  `scan-checkpoint`; do not reproduce a stable JSON schema in the prompt.
- Each runtime-accepted checkpoint identifies its packet and attempt and
  contains a non-empty set of concrete completed path results. `scan-accept`
  closes an attempt only after all assigned paths have an accepted terminal
  outcome; otherwise the worker must `scan-yield` and let the runtime requeue
  the remaining set.
- `paths_read: true`, summary-only read claims, and boolean read flags are invalid.
- `read` and `deep_read` outcomes must reference existing `evidence_ids`, and at least one referenced evidence row must have `source_path` equal to the covered path.
- Subagents checkpoint completed `read` or `deep_read` paths with evidence and
  report `blocked` paths explicitly. They do not need to guess a terminal result
  for untouched paths: the runtime computes the authoritative remaining set as
  assigned paths minus runtime-accepted terminal paths.
- A top-level `coverage.json` or `coverage-ledger.json` row is not proof that a
  path was scanned. Before closing the scan, the runtime computes
  `included_paths - assigned_paths - accepted_nonblocking_gap_paths` and checks
  every assigned path against accepted packet-local path results; any non-empty
  set blocks completion.
- If assigned paths no longer fit the effective context budget, the subagent
  checkpoints useful completed work and yields. The runtime preserves the
  accepted subset, splits/requeues the remaining paths, and the leader must
  dispatch a new subagent for the remaining paths before closing `P0`/`P1`
  coverage.
- Runtime acceptance has two gates: a coverage gate for assigned-path set
  reconciliation and a quality gate that rejects summary-only or inconsistent
  evidence. The runtime may classify packet failure as `fail_gap`,
  `fail_quality`, `fail_contract`, or `fail_systemic`.
- `fail_quality` must return a machine-checkable repack subset naming at least one of `paths[]`, `claim_ids[]`, `coverage_row_ids[]`, or `evidence_ids[]`; otherwise treat it as `fail_contract`.
- Any rejected or incomplete attempt blocks packet acceptance until the runtime
  repacks/requeues it or records an explicitly allowed unresolved gap.
- `fail_contract` and `fail_systemic` do not use local patch-only redispatch; repair the packet schema/boundary or repack the affected packet family.

## Scan Duties

`sp-map-scan` must:

- enumerate project-internal evidence comprehensively as value-weighted repository inventory, then scan evidence selectively by value
- generate a full project-relevant inventory from the runtime-resolved scan set across nested directories, then add Git tracking status and directory metadata during classification
- have `scan-prepare` materialize `.specify/project-cognition/workbench/repository-universe.json` with `included_paths` and any available `excluded_paths`; default `scan-set` output is intentionally minimal and does not require per-path exclusion details unless an explicit explain/debug mode was used
- have `scan-prepare` materialize `.specify/project-cognition/workbench/scan-targets.json` with the value-weighted execution target set
- classify project-relevant repository surfaces
- gather evidence first from high-value committed source, runtime entrypoints, tests that prove behavior, scripts, configs, docs that define behavior, templates, generated-surface sources, and `.git` history
- construct provisional nodes and candidate edges
- record uncertainty, blockers, and missing evidence explicitly
- stay graph-native from the start rather than staging a handbook-first atlas
- current-runtime native subagents are the default execution surface for scan lanes
- scan packets are executable read instructions and must still execute the packet reads before the leader accepts atlas evidence
- every project-relevant row is categorized with value tiers and coverage classes such as `P0`, `P1`, `P2`, `P3`, `inventory`, `sampled`, `deep-read`, `critical`, `important`, and `low-risk`
- `unknown` is a scan failure
- maintain `excluded_from_deep_read` reasoning for `vendor-cache-build-output` and similar excluded roots
- The runtime-resolved scan set is the primary inventory boundary; Git-tracked files and Git tracking status are classification metadata unless the scan explicitly records why untracked evidence matters.
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
- when UI exists: real UI entry points/navigation, token/theme/typography
  owners, reusable component owners, responsive/state patterns,
  Storybook/visual/accessibility tests, and design/reference assets
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

For UI evidence, make roles retrievable through node `type`, `title`, aliases,
domain, owner, route hints, and verification hints—not only opaque attrs. Use
role language such as `ui_entrypoint`, `design_token_owner`, `ui_component`,
`ui_pattern`, `visual_verification`, and `design_reference_asset` when live
evidence supports it.

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-scan", snapshot, workload_shape)` before broad work begins.
- Declare the selected worker/model capacity to the runtime when the integration
  exposes it; otherwise use the runtime's conservative profile. Never treat the
  advertised context window as entirely available for source input. Prefer
  `scan-prepare --context-window-tokens <window>` with explicit inherited,
  system/skill, reasoning, tool-output, and result-output reserves plus the
  safety margin; use `--worker-budget-tokens` only when that effective budget
  was already calculated outside the runtime.
- Dispatch each scan lane only from the validated `MapScanPacket` and
  self-contained task brief returned by `scan-lease`. Pair it with
  `.specify/templates/worker-prompts/map-scan-worker.md`; the runtime-generated
  task remains authoritative when generic prompt prose differs.
- Recommended scan lanes include source/symbol discovery, module boundaries, capability flows, state surfaces, build/test/runtime surfaces, and git evolution surfaces.
- Every lane checkpoints inspected paths, evidence harvested, confidence notes,
  provisional structure updates, typed graph-claim candidates, supporting or
  contradicting evidence references, and unresolved unknowns through the CLI.
  Workers may propose `requested_state`, but only the compiler derives the
  published lifecycle state.
- Must wait for every dispatched scan lane and consume its structured handoff before the scan closes.

## Layer 1 Route Material

- Generate layer 1 retrieval source material before the build phase begins.
- Produce task route candidates.
- Produce symptom route candidates.
- Produce shared-surface hotspot candidates.
- Produce verification route candidates.
- Produce propagation-risk route candidates.

## Concept Retrieval Signal Evidence

- Collect concept retrieval signals that let `specify-runtime cognition lexicon` surface
  useful `concept_candidates` instead of only path or symbol matches.
- Record colloquial user phrases, aliases, shorthand, command names, workflow
  names, symptoms, and domain vocabulary that maintainers naturally use when
  asking for work.
- Record these signals so downstream agent-owned semantic normalization can
  extract embedded project terms when raw lexicon ranking and
  `agent_normalization` are only bootstrap signals, all candidates are
  `score=0`, or user prompts are localized, mixed-language, CJK, colloquial,
  symptom-first, or mixed-language or CJK text. If
  `agent_normalization.required=true`, treat it as a non-intelligent CLI
  reminder to write `semantic_intake` from the alias catalog (action:
  write_semantic_intake_from_alias_catalog). If `agent_normalization` is
  omitted, treat it as `required=false`; omission does not make raw lexical
  ranking authoritative. CJK or mixed CJK/ASCII input still requires agent
  normalization even when positive raw lexical matches exist because embedded
  project tokens do not translate the surrounding user language. The agent still
  owns translation; `agent_normalization` is advisory guidance, not a route
  decision.
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
- run `{{specify-subcmd:specify-runtime cognition scan-status}}` and confirm that no
  pending, leased, yielded, or blocked high-value packet remains
- run `{{specify-subcmd:specify-runtime cognition validate-scan --format json}}` before handoff to `sp-map-build`
- `sp-map-scan` may report complete only after `validate-scan` returns `status=ok` and `readiness=scan_ready`
- for the runtime-owned v2 workbench, that successful validation writes
  `scan-receipt.json`, binding the generation, canonical scan set, current source-file bytes,
  boundary and target ledgers, accepted packet artifacts, evidence, coverage, and
  provisional graph inputs; any later canonical mutation makes the receipt
  stale and requires `validate-scan` again
- if `validate-scan` returns `status=blocked`, report the blocking errors and do not claim the scan package is build-ready
- confirm that the scan still has not published final cognition truth
- report any open uncertainty that `sp-map-build` must reconcile
