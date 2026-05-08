# Agent-First Project Cognition Runtime

## Summary

This design replaces the current runtime-handbook-centered brownfield mapping model with an agent-first project cognition runtime.

The target is not a better `BUILD-HANDBOOK.md` or `DEBUG-HANDBOOK.md`.
The target is a continuously maintained internal project understanding system that pushes ordinary brownfield agent work as close as possible to the decision quality of a deeply embedded senior engineer.

The system is project-internal only. It uses all project-relevant in-repo evidence, including committed source, configs, scripts, tests, docs, templates, generated surfaces, and `.git` history. Project-external knowledge is intentionally excluded and must live in a separate knowledge surface.

Cold start uses `map-scan -> map-build`.
After that baseline exists, daily maintenance moves to `map-update`.

## Goal

Create an agent-first cognition runtime that becomes the mandatory first read surface for ordinary brownfield workflows and can:

- identify the true change surface for a requested modification
- identify likely impact closure and risky propagation paths
- identify the smallest trustworthy verification route
- identify the most likely debug investigation route for a symptom
- preserve both implementation reality and operational reality when they conflict
- continuously absorb repository changes and user corrections without falling back to full cold reconstruction

## Non-Goals

- Reconstruct project-external knowledge such as Slack, ticketing systems, production telemetry, or oral history outside the repository
- Preserve compatibility with the current handbook-first runtime atlas as a primary truth layer
- Optimize first for human-readable brownfield documentation
- Guarantee perfect equivalence to a senior engineer's three-year embedded understanding in all edge cases

The system should aim at that benchmark, but it must remain explicit about uncertainty, conflict, and evidence limits instead of pretending full knowledge.

## Product Position

This is not a document generator.
This is not a static code map.
This is not a one-shot repository summarizer.

This is a continuously updated project cognition runtime with:

- an evidence layer
- a typed cognition graph
- explicit truth layers
- explicit conflict modeling
- confidence-aware claim synthesis
- agent-oriented consumption slices
- incremental update mechanics
- task-simulation-based quality gates

Generated views are outputs, not the core system.

## Design Principles

1. Graph first, not handbook first
2. Agent first, not reader first
3. Evidence traceability before synthesis
4. Multiple truth layers may coexist
5. Unknowns must stay explicit
6. Incremental maintenance is the normal state
7. Full rebuild is an exception, not the daily path
8. All ordinary brownfield workflows must consume the cognition runtime before large-scale source reading

## Scope Of Evidence

The allowed evidence surface is project-internal only.

Included:

- source code
- tests and fixtures
- scripts and automation
- templates and generated-surface sources
- project configuration
- committed documentation
- project state surfaces committed in-repo
- packaging and release metadata
- integration adapters
- `.git` history and commit evolution

Excluded:

- chat systems
- ticketing systems outside the repository
- external runbooks
- production systems not stored in the repository
- institutional memory with no project-internal evidence or user-supplied correction

## Target Consumer

The first-class consumer is the agent.

Human-readable outputs are allowed and useful, but they are secondary projections from the cognition runtime. The core product requirement is not "can a person read this nicely"; it is "can an agent make materially better brownfield decisions with lower blind-read cost and lower overconfidence risk."

## System Boundary

The runtime has three major layers:

1. Evidence layer
2. Cognition layer
3. Consumption layer

### Evidence Layer

This layer stores traceable raw project evidence and extracted structured observations.
It never claims final truth by itself.

Each evidence record should minimally carry:

- `evidence_id`
- `source_kind`
- `source_path`
- `commit_sha` or `commit_range`
- `span`
- `extractor`
- `captured_at`
- `content_hash`
- `project_internal: true`

Valid `source_kind` examples:

- `file`
- `git_commit`
- `git_diff`
- `config`
- `script`
- `test`
- `template`
- `doc`

### Cognition Layer

This layer stores typed nodes, typed edges, synthesized claims, conflicts, confidence, and update history.

The cognition layer is the actual truth runtime.

### Consumption Layer

This layer exposes graph slices and task-oriented projections to workflows.
It is not allowed to become the canonical truth store.

## Core Object Model

The cognition system should use two distinct object families:

- evidence-family objects
- cognition-family objects

### Evidence-Family Objects

#### Evidence

Traceable raw or extracted repository evidence.

#### Observation

Structured extraction from evidence without full synthesis.
Examples:

- "this file exports command X"
- "this test invokes script Y"
- "this config key gates feature Z"

### Cognition-Family Objects

#### Node

All major understanding units are first-class nodes.

Required node classes:

- `FileNode`
- `SymbolNode`
- `ModuleNode`
- `CapabilityNode`
- `FlowNode`
- `EntrypointNode`
- `StateNode`
- `VerificationNode`
- `RiskNode`
- `DecisionNode`
- `ConflictNode`

#### Edge

Edges must be typed and directionally meaningful.

Required baseline edge types:

- `owns`
- `defines`
- `contains`
- `calls`
- `depends_on`
- `implements`
- `triggers`
- `reads_state`
- `writes_state`
- `verifies`
- `risks`
- `conflicts_with`
- `supersedes`
- `derived_from`
- `feeds`
- `consumed_by`

#### Claim

A claim is a synthesized project understanding statement backed by evidence and attached to a subject node or relationship.

Required fields:

- `claim_id`
- `subject_ref`
- `predicate`
- `object_ref` or `object_value`
- `backing_evidence_ids`
- `truth_layer`
- `confidence`
- `falsification_reads`
- `last_validated_at`

#### UpdateEvent

Represents one cognition update action.

Required fields:

- `update_id`
- `kind`
- `trigger`
- `changed_paths`
- `affected_nodes`
- `affected_claims`
- `created_conflicts`
- `invalidated_claims`
- `rebuild_scope`
- `completed_at`

## Truth Model

The system must support dual truth instead of forcing one winner.

Required truth layers:

- `implementation_reality`
- `operational_reality`
- `inferred_synthesis`

### Implementation Reality

Facts grounded in committed code, configs, tests, scripts, docs, or git history.

### Operational Reality

Facts supplied by the user about how the project is actually operated, maintained, or interpreted inside the team, even when that differs from the committed implementation.

### Inferred Synthesis

Agent-derived conclusions drawn from multiple evidence points when no direct single-source statement exists.

## Conflict Model

Conflicts must be explicit first-class objects, not hidden merge behavior.

A conflict exists when:

- implementation and operational claims disagree
- two operational claims disagree
- an inferred claim is contradicted by new evidence
- a historical interpretation remains plausible but current implementation appears to have drifted

Each `ConflictNode` must minimally carry:

- `conflict_id`
- `subject_ref`
- `competing_claim_ids`
- `conflict_type`
- `impact_scope`
- `agent_behavior_rule`
- `resolution_status`

`agent_behavior_rule` examples:

- `do_not_auto_decide`
- `prefer_implementation_for_code_change`
- `prefer_operational_for_runbook_guidance`
- `require_map_update_before_task_execution`

## Confidence Model

Confidence must be conservative and typed.

Suggested confidence levels:

- `grounded`
- `strong`
- `partial`
- `weak`
- `stale`
- `conflicted`

Confidence must be computed from evidence class, evidence multiplicity, freshness, and contradiction state.

High-value claims must not jump to high confidence from a single shallow read.

## Multi-Axis Node Design

The system must not center files as the only meaningful objects.

All of the following must be first-class and cross-linked:

- files
- modules
- capabilities
- flows
- entrypoints
- state surfaces
- verification surfaces
- risk surfaces
- long-lived decisions

Example:

An "online reinstall" capability is not a paragraph inside a file summary.
It is a `CapabilityNode` linked to:

- triggering UI or CLI entrypoints
- implementing modules
- state objects exchanged across processes
- risk nodes that disrupt the path
- verification nodes that best validate the path
- git evolution that shows major historical drift

## Command Model

The runtime uses three commands.

### `map-scan`

Cold-start full-project evidence collection.

Responsibilities:

- enumerate all project-relevant in-repo surfaces
- classify project-relevant evidence
- extract provisional observations
- construct preliminary nodes and candidate edges
- find missing coverage and uncertainty
- identify high-value historical drift in `.git`
- avoid publishing final cognition truth

Normal output class:

- evidence bundles
- observation sets
- provisional nodes
- candidate edges
- uncertainty map
- scan coverage diagnostics

### `map-build`

First cognition reconstruction from a full scan baseline.

Responsibilities:

- merge scan outputs into a coherent cognition graph
- deduplicate nodes
- type relationships
- synthesize claims
- create explicit conflicts
- compute confidence
- validate reachability and coverage
- publish the baseline cognition runtime

Normal output class:

- graph store
- claim store
- conflict index
- confidence index
- agent consumption slices
- optional human-readable projections

### `map-update`

Daily maintenance command after baseline exists.

Responsibilities:

- accept changed paths or commit ranges
- accept user corrections or additional project-internal knowledge
- calculate impact closure
- perform targeted evidence refresh
- invalidate stale claims
- add or update conflicts
- rebuild only affected subgraphs and views
- produce a cognition delta report

After initial baseline, this should become the ordinary maintenance entrypoint.

## Lifecycle

### Initial Baseline

`map-scan -> map-build`

### Ongoing Maintenance

`map-update`

### Full Rebuild Triggers

The system may fall back to full rebuild only when:

- the graph store is corrupted
- repository restructuring destroys incremental path mapping
- confidence degradation reaches a defined failure threshold
- the user explicitly requests a new baseline

## Subagent Strategy

Subagents remain mandatory, but lane design must change from directory-oriented packeting to cognition-oriented packeting.

Required scan lane families:

- file and symbol discovery
- module boundary recovery
- capability and flow recovery
- state and handoff recovery
- build, test, package, and runtime recovery
- risk and fragility recovery
- git evolution and long-lived constraint recovery

Required update lane families:

- diff impact analysis
- affected-node refresh
- claim invalidation and revalidation
- user-supplement normalization
- conflict reconciliation

## User Supplement Model

User supplementation is required as a first-class mechanism because cold reconstruction cannot recover every operational reality detail.

The system should support both:

- freeform supplement intake
- structured supplement intake

Freeform input examples:

- "this config key exists but nobody should touch it"
- "this workflow is dead even though the files still exist"
- "this build path looks valid but is broken in practice"

Structured supplement examples:

- attach a new operational owner to a capability
- mark a risk node as forbidden extension surface
- add an operational conflict against an implementation claim

All supplements must be normalized into:

- evidence-backed operational claims
- conflict nodes
- pending verification tasks
- node/edge enrichments

## Agent Consumption Model

Ordinary brownfield workflows must consume task-oriented cognition slices instead of broad source reading.

Required baseline slice types:

- `change_slice`
- `debug_slice`
- `capability_slice`
- `module_slice`
- `verification_slice`

Each slice must minimally include:

- relevant nodes
- relevant edges
- key claims
- active conflicts
- confidence distribution
- must-verify-live items
- minimal source read set

### Consumption Rule

Graph first.
Live source reads second.

Agent behavior should be:

1. request cognition slice
2. inspect conflicts and confidence
3. perform only the minimum targeted live reads needed
4. proceed or require `map-update`

The agent must not silently fall back to broad repository rereads unless the graph slice explicitly fails quality thresholds.

## Workflow Integration Rule

For ordinary brownfield workflows, the cognition runtime becomes the mandatory first entrypoint.

Expected flow:

1. workflow requests slice
2. slice returns `green`, `yellow`, or `red`
3. `green`: proceed with graph-backed execution
4. `yellow`: do minimal targeted live verification reads
5. `red`: route to `map-update`

This makes graph insufficiency explicit and operational.

## Quality Gates

The new runtime must not be validated by artifact shape alone.
It must be validated by capability quality.

### 1. Coverage Gates

Validate at least:

- project-relevant file coverage
- entrypoint coverage
- key state object coverage
- capability coverage
- flow coverage
- verification surface coverage
- risk surface coverage
- high-value git evolution coverage

### 2. Claim Integrity Gates

Every high-value claim must show:

- backing evidence
- truth layer
- confidence
- conflict state
- falsification path

### 3. Agent Task Simulation Gates

The runtime must be tested on task simulations such as:

- change-surface prediction
- impact-closure prediction
- minimal verification recommendation
- first-pass debug route quality
- false-coverage detection
- implementation-versus-operational conflict handling

### 4. Self-Honesty Gates

The runtime must prove:

- uncertainty remains visible
- conflicts remain visible
- weak confidence blocks over-automation
- stale claims degrade correctly
- oversized diffs trigger `map-update` instead of silent guesswork

## North Star Metrics

The system should be judged primarily by brownfield execution quality, not by output prettiness.

Primary north star metrics:

- change decision correctness rate
- first-pass debug routing hit rate
- overconfident wrong-answer rate

Secondary metrics:

- broad-source-read reduction
- graph slice usefulness rate
- supplement-to-claim normalization quality
- stale-claim invalidation precision

## Storage Model Recommendation

This design does not require a specific database implementation, but it does require graph-native storage behavior.

Required persistence capabilities:

- stable node and edge identifiers
- efficient reverse lookup from claim to evidence
- explicit conflict indexing
- time-aware update history
- slice materialization
- selective subgraph rebuild

It is acceptable to start with file-backed structured graph artifacts if they behave as a graph runtime, but the storage contract must remain graph-native, not markdown-native.

## Recommended Implementation Path

Choose a fresh graph runtime instead of extending the current handbook-first artifact system.

Recommended product direction:

- replace handbook-first truth with graph-native truth
- rewrite `map-scan`
- rewrite `map-build`
- add `map-update` as the normal maintenance entrypoint
- make downstream workflows graph-first
- keep human-readable outputs as projections, not the core

## Open Risks

- graph complexity could exceed the current workflow tooling ergonomics
- confidence scoring can become noisy if evidence extraction stays shallow
- user supplements may create operational truth bloat unless normalized strictly
- graph-first workflow enforcement will require broad downstream command updates
- migration from existing map artifacts may not be worth preserving

## Recommended Acceptance Standard

This design should be considered successful only when ordinary brownfield agent tasks stop depending on broad repository rereads and start depending primarily on cognition slices with targeted live verification.

That is the practical threshold for approaching "deeply embedded senior engineer" behavior rather than producing a better documentation set.
