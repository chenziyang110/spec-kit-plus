# PRD Command Subagent Orchestration Design

Date: 2026-05-05
Scope: `templates/commands/prd-scan.md`, `templates/commands/prd-build.md`
Status: Approved for implementation planning

## Summary

This design upgrades the command-template contracts for `sp-prd-scan` and
`sp-prd-build` so they inherit the strongest orchestration qualities already
present in `sp-map-scan` and `sp-map-build` without mechanically copying
project-map-specific language.

The target outcome is command-level parity in orchestration quality:

- `sp-prd-scan` becomes a fully executable subagent-oriented scan contract
  rather than a template that only declares subagent use in principle.
- `sp-prd-build` gains explicit intake, packet validation, dispatch, join
  points, and refusal rules while preserving its strict build-only semantics.
- Both commands keep PRD-domain language centered on reconstruction evidence,
  capability truth, boundary contracts, and export synthesis rather than atlas
  construction.

This design changes only the `templates/commands/**` layer. It does not update
partials, passive skills, runtime code, docs, or tests in this pass.

## Problem Statement

`sp-prd-scan -> sp-prd-build` is already documented as the canonical heavy
reconstruction lane for existing repositories. However, the current command
templates are materially weaker than `sp-map-scan -> sp-map-build` in how they
describe actual execution.

Current gaps:

- `prd-scan` declares mandatory subagent execution but does not specify how the
  leader selects dispatch shape, validates packets before dispatch, waits at
  join points, rejects shallow worker results, or records blocked execution.
- `prd-build` requires scan-packet intake and worker-result validation, but it
  does not yet define a structured build-time orchestration contract comparable
  to `map-build`.
- The PRD lane therefore lacks the strong template-level protections already
  used elsewhere against ad hoc delegation, raw-summary handoffs, shallow
  evidence, and silent continuation under blocked conditions.

The result is an avoidable asymmetry: the repository already teaches one
high-quality orchestration pattern through `map-*`, but `prd-*` does not fully
benefit from it at the command-template layer.

## Goals

- Upgrade `prd-scan` to a command contract that is operationally explicit about
  subagent orchestration.
- Upgrade `prd-build` to a command contract that is operationally explicit
  about intake, synthesis-support delegation, and refusal conditions.
- Preserve the unique semantics of the PRD reconstruction lane:
  - `prd-scan` is the only phase allowed to broadly inspect live repository
    reality.
  - `prd-build` is a build-only compilation phase and must not become a second
    repository scan.
- Reuse the strongest generic orchestration patterns from `map-scan` and
  `map-build`:
  - fixed dispatch decision order
  - validated packet before dispatch
  - explicit `subagent-blocked` state
  - required join points
  - structured worker result contracts
  - leader-owned integration and refusal decisions

## Non-Goals

- No changes to `templates/command-partials/**`.
- No changes to passive skills, routing docs, runtime helpers, or hooks.
- No changes to tests in this design pass.
- No changes to the generated artifact schema outside what is described inside
  the command templates themselves.

## Design Principles

### Reuse Patterns, Not Domain Vocabulary

The migration should borrow orchestration discipline from `map-*` without
copying atlas-specific structures like Layer 1 routing, atlas targets, root
docs, or module docs. PRD templates should speak in terms of reconstruction
evidence, capability readiness, boundary contracts, export landing, and
traceability.

### Preserve Build-Only Semantics

`sp-prd-build` may use subagents, but only to process the completed scan bundle.
Those lanes are intake, validation, traceability, coverage, and export-landing
lanes. They are not live-repository explorer lanes.

### Refuse Guessing

Both commands should make it expensive to continue under ambiguity:

- no dispatch from raw prose
- no completion from chat summaries
- no silent filling of critical evidence gaps
- no masked unknowns
- no build completion without explicit traceability

### Leader Owns Truth Promotion

Subagents can gather evidence and propose updates, but the leader owns:

- acceptance or rejection of packet results
- readiness decisions
- state transitions
- handoff to the next command
- final synthesis into canonical outputs

## Command-by-Command Design

### `sp-prd-scan`

#### Desired Responsibility Boundary

`sp-prd-scan` becomes the sole broad repository-reading phase in the PRD lane.
It owns:

- freshness interpretation
- capability / artifact / boundary triage
- packet generation
- scan-lane dispatch
- worker result integration
- readiness for handoff to `sp-prd-build`

It must remain read-only with respect to final PRD exports.

#### New or Expanded Sections

The command should retain its current frontmatter and high-level sections, but
be expanded with additional operational sections and deeper process steps.

Recommended additions:

- `PRD Run State Protocol`
- expanded `Output Contract`
- expanded `Process`
- `Compile And Validate PrdScanPacket Inputs`
- `Execution Dispatch`
- `PrdScanPacket Dispatch`
- `Build Readiness Refusal Rules`
- `PrdScanPacket Template` or equivalent packet contract section
- `Worker Result Contract`
- `Report Completion`

#### State Protocol

`workflow-state.md` should be treated as the resumable execution surface for the
run. At minimum it should record:

- `active_command: sp-prd-scan`
- `status`
- `scan_status`
- `build_status`
- `freshness_mode`
- `classification`
- `selected_capabilities`
- `selected_boundaries`
- `selected_artifacts`
- `current_packet`
- `accepted_packet_results`
- `rejected_packet_results`
- `failed_readiness_checks`
- `next_action`
- `next_command`
- `handoff_reason`
- `open_gaps`

This gives `prd-scan` the same resumability and state discipline that makes
`map-scan` materially stronger than a prose-only workflow.

#### Dispatch Model

`prd-scan` should explicitly state the same decision skeleton used by `map-scan`
with PRD-domain wording:

- apply `choose_subagent_dispatch(command_name="prd-scan", snapshot, workload_shape)`
- persist:
  - `execution_model: subagent-mandatory`
  - `dispatch_shape: one-subagent | parallel-subagents`
  - `execution_surface: native-subagents`
- fixed decision order:
  - one safe validated scan lane -> `one-subagent`
  - two or more safe read-only scan lanes -> `parallel-subagents`
  - no safe lane, incomplete packet, or unavailable delegation ->
    `subagent-blocked`

This eliminates ambiguity around whether delegation is optional in practice.

#### Packet Contract

Every delegated scan lane should require a validated `PrdScanPacket` before
dispatch. Each packet should expose, at minimum:

- `lane_id`
- `mode: read_only`
- `scope`
- `capability_ids`
- `artifact_ids`
- `boundary_ids`
- `required_reads`
- `excluded_paths`
- `required_questions`
- `expected_outputs`
- `contract_targets`
- `forbidden_actions`
- `result_handoff_path`
- `join_points`
- `minimum_verification`
- `blocked_conditions`

The packet can remain Markdown, but the template must make these fields
non-optional at the contract level.

#### Worker Result Contract

Every lane result should be required to include:

- `lane_id`
- `reported_status: done | done_with_concerns | blocked | needs_context`
- `paths_read`
- `key_facts`
- `evidence_refs`
- `recommended_contract_updates`
- `confidence`
- `unknowns`
- `minimum_verification`
- `result_handoff_path`

Rejected result conditions should be explicit:

- missing `paths_read`
- prose-only summary without cited evidence
- omitted unknowns
- no recommendation for contract/checklist impact where one is expected
- idle or incomplete subagent output

#### Join Points

`prd-scan` should require waiting for every dispatched lane at least:

- before freezing ledgers and machine-readable contracts
- before declaring the package ready for `sp-prd-build`

That prevents the current weak path where subagent use is declared but not
structurally integrated into completion rules.

#### Refusal Rules

`prd-scan` should refuse handoff when:

- a critical capability lacks L4-level support
- a high capability remains path-only
- required packet results are missing
- worker results lack evidence structure
- unresolved critical unknowns are hidden or uncategorized
- key structures have not landed in the contract JSON files

The refusal must name the smallest safe repair rather than only saying the run
is incomplete.

### `sp-prd-build`

#### Desired Responsibility Boundary

`sp-prd-build` remains build-only. It may dispatch subagents, but those lanes
operate on the run bundle, not on the live repository.

Allowed build-lane purposes:

- packet evidence intake
- traceability validation
- export landing checks
- critical unknown verification
- cross-export coverage checks

Disallowed:

- rereading the repository for new facts
- broad source exploration
- treating the build step as a second scan

#### New or Expanded Sections

The build template should gain sections parallel in strength to `map-build`:

- `Mandatory Subagent Execution`
- `Required Inputs`
- `PRD Run State Protocol`
- `Validate Scan Inputs Before Execution`
- `Compile And Validate PrdBuildPacket Inputs`
- `Readiness Refusal Rules`
- `Execution Dispatch`
- `Build Packet Dispatch`
- `Output Contract` expansion
- `Reverse Coverage Validation`
- `Traceability Validation`
- `Report Completion`

#### Build-Time Dispatch Model

The build command should use the same orchestration contract framing:

- apply `choose_subagent_dispatch(command_name="prd-build", snapshot, workload_shape)`
- persist:
  - `execution_model: subagent-mandatory`
  - `dispatch_shape: one-subagent | parallel-subagents`
  - `execution_surface: native-subagents`

But the safe lanes are different from `map-build`:

- one safe validated intake or validation lane -> `one-subagent`
- two or more isolated bundle-processing lanes -> `parallel-subagents`
- any need for live repo reread, missing build packet, or unavailable delegation
  -> `subagent-blocked`

The template should make clear that `subagent-blocked` stops substantive build
work rather than implicitly permitting inline fallback scanning.

#### Build Packet Contract

`prd-build` should not dispatch directly from raw scan prose. It should compile
a validated build packet from the scan bundle. A `PrdBuildPacket` should include
at least:

- `lane_id`
- `mode: bundle_only`
- `packet_scope`
- `required_scan_inputs`
- `required_contract_files`
- `required_worker_results`
- `expected_exports`
- `traceability_targets`
- `forbidden_actions`
- `minimum_verification`
- `result_handoff_path`

This packet contract encodes the build-only constraint directly into the command
template.

#### Build Worker Result Contract

Every build-support lane should return structured output such as:

- `lane_id`
- `reported_status`
- `bundle_inputs_read`
- `traceability_findings`
- `export_landing_findings`
- `confidence`
- `unknowns`
- `recommended_repairs`
- `minimum_verification`
- `result_handoff_path`

Rejected result conditions should include:

- no concrete bundle inputs read
- claims that rely on new repository facts
- missing traceability findings for assigned targets
- omitted critical unknowns
- shallow summary with no actionable repair guidance

#### Required Join Points

`prd-build` should require waiting for every dispatched lane at least:

- before writing `master/master-pack.md`
- before writing or finalizing `exports/**`
- before reverse coverage / traceability validation

This preserves build integrity and prevents early synthesis from outrunning the
validated intake.

#### Refusal Rules

`prd-build` should refuse completion when:

- required scan artifacts are missing or malformed
- worker results are absent or structurally shallow
- critical reconstruction claims cannot be traced back to scan evidence
- export landing for critical artifacts is missing
- unresolved critical unknowns remain in the bundle
- the build would need new repository facts to complete honestly

The route back should explicitly point to `sp-prd-scan`.

## Shared Patterns To Migrate

The following `map-*` strengths should be consciously migrated into both PRD
commands:

- dispatch decision order is explicit, fixed, and persisted
- delegation starts only from validated packets
- `subagent-blocked` is a first-class state, not an informal comment
- the leader must wait at named join points
- idle subagent output is not accepted completion evidence
- accepted and rejected results are both recorded
- refusal conditions list the smallest safe repair

## Patterns Not To Copy Mechanically

The following `map-*` concepts should not be mirrored verbatim:

- atlas targets
- Layer 1 retrieval routing
- root/module documentation structure
- project-map-specific coverage row semantics where they do not fit PRD

The PRD lane should remain oriented around:

- capability reconstruction
- artifact and boundary contracts
- evidence labeling
- traceability into exported PRD deliverables

## Implementation Shape Inside `templates/commands`

The concrete implementation should follow this shape:

1. Expand `prd-scan.md` from a compact contract into a structurally executable
   orchestration template.
2. Expand `prd-build.md` from a compact synthesis contract into a structurally
   executable intake-and-build template.
3. Keep wording aligned with existing command style:
   - imperative, contractual, and refusal-oriented
   - explicit about allowed and forbidden surfaces
   - explicit about what leader vs subagent owns
4. Preserve current PRD-specific goals, outputs, and quality gates while adding
   orchestration rigor around them.

## Acceptance Criteria

This design is satisfied when the command templates meet all of the following:

- `prd-scan` contains explicit state, dispatch, packet, result, join-point, and
  refusal contracts comparable in quality to `map-scan`.
- `prd-build` contains explicit input-validation, build-packet, dispatch,
  result, join-point, traceability, and refusal contracts comparable in quality
  to `map-build`.
- `prd-build` still clearly forbids live-repository rereads and any drift into a
  second scan.
- both templates describe structured worker results rather than treating the
  presence of `worker-results/**` as sufficient.
- both templates make blocked execution and smallest-safe-repair routing
  explicit.

## Risks And Mitigations

### Risk: Mechanical Copying From `map-*`

Mitigation:

- migrate orchestration patterns only
- rewrite all domain nouns into PRD reconstruction language

### Risk: `prd-build` Becomes a Second Scan

Mitigation:

- enforce `bundle_only` packet semantics
- forbid live repo rereads in dispatch and refusal sections

### Risk: Longer Templates Without Stronger Guarantees

Mitigation:

- prioritize decision order, packet requirements, join points, result schema,
  and refusal rules over generic guidance prose

## Open Questions

None at the design level for the command-template-only pass. The implementation
pass can decide exact section titles and field names as long as it preserves the
semantics defined here.
