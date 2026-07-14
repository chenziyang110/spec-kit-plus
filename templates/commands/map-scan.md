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

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Process

- Before repository inventory, run `project-cognition generate-ignore --format json`. If it creates `.specify/project-cognition/.cognitionignore`, ask the user to review the starter suggestions and wait for confirmation before continuing.
- After the ignore gate is clear, run `project-cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json` and use the returned file list as the candidate scan set. The agent may choose scan intent and concrete `--scope` values, but `project-cognition scan-set` decides the initial included file list through deterministic runtime rules; do not let the agent freely decide which files to omit.
- Build a value-weighted evidence baseline before any graph reconstruction work begins.
- First spread out the resolved scan set as a cheap inventory pass: enumerate paths, metadata, runtime exclusion status, Git tracking status, size, extension, directory family, and likely generated/vendor/test/doc/config/source classification without deep-reading file contents.
- Classify every non-excluded candidate path by value tier before dispatch: `P0` core behavior and entry surfaces, `P1` supporting contracts and runtime/config surfaces, `P2` selective tests/docs/examples, and `P3` low-signal generated/vendor/assets/cache/static output.
- Deep-scan `P0` and `P1` first. Use `P2` selectively when it proves behavior, verification, or public contracts. Keep `P3` as inventory-only or excluded unless the user explicitly asks for that surface or it is the only evidence for a critical behavior.
- Write `.specify/project-cognition/workbench/scan-targets.json` after classification and before dispatch. It is the leader-owned execution target list derived from `repository-universe.json`.
- Dispatch each bounded scan lane only from a validated `MapScanPacket`.
- Wait for every dispatched lane's structured handoff before accepting scan coverage.
- If a safe scan lane cannot be packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Value-Weighted Repository Inventory

`sp-map-scan` must inventory all candidate paths from the runtime-resolved scan
set, but it must not deep-read all files by default. The first pass is a
path-level accounting pass, not a content scan.

Write `.specify/project-cognition/workbench/repository-universe.json` with one
row per candidate path from `.specify/project-cognition/tmp/scan-files.json`.
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

Write `.specify/project-cognition/workbench/scan-targets.json` with the subset
selected for packet dispatch. It must include:

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
- `.specify/memory/**` must not appear in repository-universe, coverage-ledger, evidence rows, provisional nodes, provisional edges, observations, path_index, or alias_index.
- Open only learning detail docs linked from map-scan-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When scan friction exposes route changes, artifact rewrites, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `map-state.md` captures that durable context.
- [AGENT] When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.

## Hard Boundary

- `sp-map-scan` must not publish final cognition truth.
- `sp-map-scan` must not claim the baseline is graph-ready.
- `sp-map-scan` must produce evidence, provisional nodes, provisional edges, observations, and coverage diagnostics only.
- `sp-map-scan` may classify evidence and derive provisional structure, but `sp-map-build` owns schema v5 graph-store publication, confidence assignment, typed graph-claim lifecycle derivation, route validation, revision-bound claim-reconciliation basis support, and alias catalog readiness.

## Output Contract

The only canonical outputs for this command are:

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

## Machine-Readable Scan Artifact Schema

Write canonical JSON fields, not agent-local aliases. The runtime accepts a few
legacy aliases for compatibility, but new scan packets must emit the canonical
shape below so `sp-map-build` can reconstruct the graph without manual repair.

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
- Do not silently downgrade unknown or unclassified project-relevant surfaces.
- `.specify/**` workflow/runtime state is excluded from default source/runtime scan targets; do not put `.specify/**` paths into project graph evidence, nodes, observations, graph claims, path_index, or alias_index.
- Only read `.specify/**` for workflow operation, validation, migration, or when the requested scan is explicitly about generated workflow surfaces or spec-kit-plus itself; even then, classify it as workflow/reference support rather than source/runtime graph truth.
- Respect project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`. These files use gitignore-compatible syntax, including comments, directory patterns, globs, `**`, and `!` re-includes.
- `.cognitionignore` excludes project cognition scan/build/update targets only; it does not replace `.gitignore` or prove that ignored code is irrelevant to other tooling.
- If the required scan lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Project Cognition Workbench State Protocol

- `MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md`
- Treat `.specify/project-cognition/workbench/map-state.md` as the refresh-workbench state surface for scan progress, accepted packets, and unresolved gaps.
- `scan-queue.json` is the leader-owned scheduler queue. Every `scan-packets/<packet-id>.md` file must have exactly one queue row.
- `scan-targets.json` is the leader-owned value-weighted target set. Every scan packet must draw concrete `assigned_paths` from `scan-targets.json`, not from broad directory globs or unclassified path lists.
- `handoff-ledger.json` records every dispatch and return event. Every `worker-results/<packet-id>.json` file must have a matching queue row and return event.
- The leader loop is: leader receives worker result, leader reads durable scan state, leader validates handoff quality, leader updates queue, coverage, and handoff ledgers, leader plans next packets, and leader dispatches the next bounded wave.
- Worker packet acceptance is separate from path coverage outcome. If a packet exceeds budget, the worker returns `acceptance=fail_gap`, marks affected paths as `coverage[].outcome="overflow"`, and includes split recommendations.
- Do not create huge mixed-value packets. Target packet size should be small enough for the worker to read and account for every path concretely. Prefer 25-75 paths for `P0`/`P1` code lanes, use a hard cap of 150 paths for any one packet, and split large directories by behavior owner, entrypoint family, or dependency boundary.
- A timed-out or overflowed `P0`/`P1` packet must be split and retried before it can become an accepted gap. Only low-risk `P3` or justified `P2` paths may become accepted nonblocking inventory gaps.
- New worker results must write top-level `acceptance`. Top-level `outcome` is a legacy alias only and must not appear in generated worker prompt examples.
- `worker-results/<packet-id>.json` must write the packet-local ledger as top-level `ledger`, not `packet_local_ledger`, `packet-local-ledger`, scan-packet Markdown sections, or inline JSON inside `scan-packets/*.md`.
- `accepted_nonblocking_gap_paths` contains only low-risk paths with owner, reason, evidence expectation, revisit condition, and `low_risk_open_gap` status.
- Scan packets are executable read instructions, not final truth documents.
- `MapScanPacket` is the required packet contract for each delegated scan lane.
- Each packet must declare `mode: read_only` and a `result_handoff_path`.
- Each `result_handoff_path` must point to `.specify/project-cognition/workbench/worker-results/<packet-id>.json`.
- Every `scan-packets/<lane-id>.md` file must have exactly one matching `worker-results/<lane-id>.json` handoff, and worker results without a matching scan packet are invalid.
- Worker result handoffs are the machine-checkable evidence surface for packet acceptance.
- Use `project-cognition scan-set` for inventory discovery before escalating to deeper reads. `rg --files` may support diagnostics, but it must not replace the runtime-resolved scan set.
- Treat Git-tracked file lists and user-provided scan hints as metadata or `scan-set --scope` inputs; they must not become scan targets until `project-cognition scan-set` returns them in `.specify/project-cognition/tmp/scan-files.json`.
- Raw inventory notes or raw chat summaries are not sufficient.
- Idle subagent output is not an accepted scan result.
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
- `assigned_paths`, queue rows, worker `paths_read`, and worker coverage paths must be concrete repository file paths enumerated from `repository-universe.json`; globs such as `JZWinReNew/*.cpp`, directory patterns, absolute paths, and summary labels are invalid.
- Each packet carries a packet-local task ledger in the worker result JSON top-level `ledger` object with `todo`, `doing`, `done`, `blocked`, and `overflow`.
- Each accepted worker result must repeat `assigned_paths`, include `paths_read` as a non-empty array of concrete repository paths, include packet-local `coverage` rows for the final outcome of each assigned path, and include confidence.
- Minimal accepted worker result JSON shape:
  `{"packet_id":"lane-1","family_id":"app","assigned_paths":["src/app.go"],"paths_read":["src/app.go"],"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],"confidence":"high","acceptance":"pass"}`
- `paths_read: true`, summary-only read claims, and boolean read flags are invalid.
- `read` and `deep_read` outcomes must reference existing `evidence_ids`, and at least one referenced evidence row must have `source_path` equal to the covered path.
- Subagents must account for every assigned path with evidence, `sampled`, `inventory_only`, `excluded`, `blocked`, or `overflow`.
- A top-level `coverage.json` or `coverage-ledger.json` row is not proof that a path was scanned. Before accepting a packet or closing the scan, compute `included_paths - assigned_paths - accepted_nonblocking_gap_paths`; any non-empty set blocks completion. For accepted packets, every assigned path must also have a packet-local worker `coverage[]` outcome.
- If assigned paths do not fit in context, the subagent must return `acceptance=fail_gap`, mark path-level `coverage[].outcome="overflow"` or `coverage[].outcome="blocked"`, and include split or recovery recommendations; the leader records queue state `overflow` or `blocked`.
- For `P0`/`P1` overflow, the leader must split and redispatch a smaller packet before closing the scan. Do not mark a high-value overflow as accepted nonblocking coverage.
- Leader acceptance has two gates: a coverage gate that requires every assigned path to have a declared outcome, and a quality gate that rejects summary-only or inconsistent evidence.
- The leader may classify packet failure as `fail_gap`, `fail_quality`, `fail_contract`, or `fail_systemic`.
- `fail_quality` must return a machine-checkable repack subset naming at least one of `paths[]`, `claim_ids[]`, `coverage_row_ids[]`, or `evidence_ids[]`; otherwise treat it as `fail_contract`.
- Any acceptance value other than `pass` blocks scan acceptance until the leader repacks, repairs, or explicitly records the unresolved gap.
- `fail_contract` and `fail_systemic` do not use local patch-only redispatch; repair the packet schema/boundary or repack the affected packet family.

## Scan Duties

`sp-map-scan` must:

- enumerate project-internal evidence comprehensively as value-weighted repository inventory, then scan evidence selectively by value
- generate a full project-relevant inventory from the runtime-resolved scan set across nested directories, then add Git tracking status and directory metadata during classification
- write `.specify/project-cognition/workbench/repository-universe.json` with `included_paths` and any available `excluded_paths`; default `scan-set` output is intentionally minimal and does not require per-path exclusion details unless an explicit explain/debug mode was used
- write `.specify/project-cognition/workbench/scan-targets.json` with the value-weighted execution target set
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
- Dispatch each scan lane from a validated `MapScanPacket`.
- Recommended scan lanes include source/symbol discovery, module boundaries, capability flows, state surfaces, build/test/runtime surfaces, and git evolution surfaces.
- Every lane must return inspected paths, evidence harvested, confidence notes, provisional structure updates, typed graph-claim candidates, supporting or contradicting evidence references, and unresolved unknowns. Workers may propose `requested_state`, but only the compiler derives the published lifecycle state.
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
- run `{{specify-subcmd:project-cognition validate-scan --format json}}` before handoff to `sp-map-build`
- `sp-map-scan` may report complete only after `validate-scan` returns `status=ok` and `readiness=scan_ready`
- if `validate-scan` returns `status=blocked`, report the blocking errors and do not claim the scan package is build-ready
- confirm that the scan still has not published final cognition truth
- report any open uncertainty that `sp-map-build` must reconcile
