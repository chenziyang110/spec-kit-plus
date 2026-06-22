# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Compatibility/export navigation view for this repository.

## System Summary

[What this project is, its primary runtime shape, its major layers or runtime
units, and the main capability surfaces that planners or implementers must keep
in view.]

[Cover the project type, primary technology stack, build/dependency tooling, and deployment shape. Name the major capability surfaces, runtime units, and architectural boundaries that downstream readers must understand first.]

## System Boundaries

[State what this repository deliberately owns, what it coordinates but does not own,
and what sits clearly outside the system boundary.]

## High-Value Capabilities

- [List the highest-value capabilities a newcomer should understand first.]
- [For each capability, state why it matters and which topical file should be
  read next.]
- **Semantic `sp-specify` traceability**: `sp-specify` uses a collaborative
  reviewed specification flow: explore project context, ask one question at a
  time, decompose semantic terms, compare approaches, write artifacts,
  self-review them, and ask for user review before planning. Discussion-originated
  specs read discussion source files and record capability-like upstream signals
  in `source_signal_disposition` instead of trusting only the handoff summary.
  `alignment.md` records `Semantic Term Decisions`, `Upstream Intent Disposition`,
  and `Out-Of-Scope Conflicts`.
- **User-confirmed product scope**: Generated workflows preserve the user's confirmed product scope. Workflow routing may choose the lightest safe command
  surface, but it must not convert the user's product intent into a smaller MVP
  or first-story release. Scope reduction requires user confirmation, including
  when a named constraint forces a scope decision.
- **`sp-auto` nonblocking resume**: `sp-auto` resumes the safe next workflow from
  recorded state. When the routed workflow would only ask a bounded question or
  confirmation with one safe recommended/default answer, it accepts that answer
  and continues; when it cannot do so safely, it reports the blocker and a
  self-unblock recommendation instead of waiting silently.
- **Command-surface minimization**: Command-surface minimization must not delete capability. When upstream discussion or specification text includes a new/create/scaffold/authoring operation, downstream workflows must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral. Manual copy steps and template-only docs are support material, not a replacement for the confirmed operation unless the user selected that narrower entry point.
- **Pre-spec discussion**: `sp-discussion` classifies each user turn, asks only for product judgment or genuine boundary/evidence conflicts, uses project cognition as advisory navigation, proves technical facts from live repository evidence, treats live evidence as the source of truth, appends compact ordinary-turn events, and refreshes structured discussion artifacts only at semantic checkpoints. It is a senior product-engineering advisor surface: before project-specific technical advice it performs a Truth Pass, separates verified facts from assumptions, reports advice confidence, gives owner-readable judgment with evidence and risk, maintains a Discussion Compass, uses recommendation-first decision progression, and proactively maps adjacent decisions instead of forcing narrow follow-up loops. It stores resumable product/technical discussions under `.specify/discussions/<slug>/`, runs a Context Boundary Gate before technical options or handoff generation, and drafts the unified handoff only after explicit user request and boundary lock; the handoff becomes ready only after self-review and user confirmation. `handoff-ready` remains resumable until `sp-specify` consumes it; `sp-specify` accepts the handoff path, JSON path, slug, or the single unconsumed ready discussion, validates the ready/user-confirmed contract before feature creation, and derives the feature description from `handoff_goal`. After consumption, generated projects should run `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` so `handoff_consumption_status: consumed`, `consumed_by_feature_dir`, `status: completed`, and `next_command: none` remove stale handoffs from default `sp-auto` candidates. Generated projects can then archive it with `specify discussion archive <slug>`. Cross-project requests must lock the target project root (`target_project_root`); current project cognition cannot prove another project's implementation facts. The valid handoff is one unified handoff pair: `handoff-to-specify.md` plus `handoff-to-specify.json`, with `handoff_goal`, `context_boundary`, `implementation_target`, evidence provenance, `quality_gate`, a human-facing `Handoff Reviewer Guide`, Must-Preserve Ledger, coverage status, and planning gate status. Downstream workflows must preserve each protected item or block for a user decision.
- **Embedded implement review**: `sp-implement` owns an embedded review-and-repair loop after a clean `sp-tasks` handoff. It runs a pre-implement review before source edits, drift review after join points and bounded sequential review windows, safe task-layer repairs for incomplete tasks/packets/handoff state/tracker state, and implementation-review audit records. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts are upstream truth and still route back to the owning workflow instead of being repaired inside implementation.

## How To Read This Project

- Start here for compatibility/export orientation.
- **Advisory project cognition index**:
  - `.specify/project-cognition/status.json` for freshness, coverage, stale paths, and refresh metadata
  - `.specify/project-cognition/project-cognition.db` as the canonical graph store
  - `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` for default brownfield navigation intake, readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; these paths are first evidence, not final edit scope
  - `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) for advanced escalation when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
  - `project-cognition changes --format json` - Git-native change plan for `sp-map-update`; reports included, ignored, known, unknown, and recommended next action before incremental update recording
  - advanced alias catalog payload fields such as `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `candidate_universe_version`, and `active_generation_id`
- **Cross-project cognition reference**: use the project cognition runtime as
  explicit-only, supplemental-only, fresh-only context with a minimal read before
  broader source inspection. When another local directory is used as a
  reference, check for `.specify/` first, run
  `project-cognition discover --root <path> --format json`, and use that project's
  cognition only when `.specify/project-cognition/status.json` and
  `.specify/project-cognition/project-cognition.db` exist,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true. If the reference is stale, blocked, or incomplete, do not treat legacy
  `.specify/project-map/**` outputs as current truth; fall back to minimal live
  reads or refresh the reference project.
- Generated workflows use `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default brownfield navigation intake and advisory navigation inputs. The packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`.
- Agents read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `before_fix_claim` checks to prove or reject the route from live repository evidence. These paths are first evidence, not final edit scope.
- When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan`. In short: `lexicon -> semantic_intake -> query`. The alias catalog path carries facet coverage through `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `candidate_universe_version`, and `active_generation_id`. Facet coverage gates advanced-path selection; top lexical or vector similarity alone is not route truth. CJK or mixed CJK/ASCII prompts still require agent-owned translation when using the advanced path. The advanced CLI tool's `agent_normalization` field remains agent semantic guidance, not a route decision.
- Generated projects require `PROJECT_COGNITION_BIN` or `project-cognition` on PATH before direct project cognition helpers run.
- Read this handbook only when a user or workflow explicitly asks for the compatibility/export view; it is not the default runtime truth path or evidence path.
- Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is not external map maintenance: normal `sp-*` workflows that change project-related source, runtime, templates, config, tests, generated assets, state contracts, or behavior-bearing docs must run inline project cognition update from their changed paths and affected surfaces. sp-map-update is for manual/external maintenance after user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Workflow-owned mutation closeout uses the same lower-level update engine as `sp-map-update`. Delta-session closeout calls `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; non-delta closeout writes `.specify/project-cognition/updates/<update-id>.json` and calls `project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json`. Payload files accept `verification` plus the compatibility alias `verification_evidence`, and `generated_surfaces` plus the compatibility alias `generated_surface_notes`. A clean closeout requires `result_state=ready` or `result_state=no_op`; `update_id`, `last_update_id`, freshness, legacy `recorded-only` output, and failed verification evidence are not enough.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Stateful first-baseline scans also require `.specify/project-cognition/workbench/scan-queue.json` and `handoff-ledger.json`; build readiness requires sparse `path_index` gates to pass before `status.json` can be query-ready. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths`; `coverage.json` is coverage accounting, not a path-index source.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`.
- Recorded refresh and ready refresh are different outcomes: `partial_refresh` means refresh data was recorded but readiness still failed.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`.
- Support drift is not runtime-truth staleness; resolve support-surface drift without reflexively routing to `map-update`.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.
- Use `Where To Read Next` for task-oriented routing.
- Map points, code proves: use live code, tests, scripts, configuration, or authoritative docs as evidence whenever making technical claims.

## Compatibility Export Model

Describe the handbook export model explicitly:

- **Debug export**: `DEBUG-HANDBOOK.md` — compatibility view of symptom routing, likely truth owners, failure propagation, investigation playbooks, and verification exit rules
- **Build/change export**: `BUILD-HANDBOOK.md` — compatibility view of product capability map, workflow sequences, change entrypoints, collaboration routes, propagation risks, implementation playbooks, and verification routes
- **Legacy project-map artifacts**: old projects may still carry project-map compatibility/export artifacts, but there is no Python runtime alias and new workflows should not call or require `.specify/project-map/**`
- **Runtime truth**: `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, the task-local `project-cognition compass` packet, and conditional advanced project cognition query bundles

The export model should help the reader distinguish compatibility views from
the graph-native cognition runtime used before broader code reads begin.

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. The map points to likely evidence, but the Senior Consequence Analysis Gate turns live project facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, and `implement`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.

## Shared Surfaces

- [Registries, routing files, template directories, config schemas, exported
  contracts, or other shared surfaces whose changes propagate into multiple
  areas]

## Risky Coordination Points

- [Files, modules, or runtime surfaces that can silently affect multiple
  workflows or capability surfaces]

## Change-Propagation Hotspots

- [Where a change is likely to fan out across consumers, integrations, config,
  scripts, docs, operators, or tests]

## Change Impact Guide

- [Provide the fastest route from a proposed code change to the affected cognition slices and compatibility/export views.]
- [For each major hotspot, say which topical document explains the blast radius,
  hidden dependencies, lifecycle risks, and minimum verification route.]
- [For existing capabilities, route readers through the capability flow and lifecycle truth layer before broader source inspection.]

## Verification Entry Points

- [Fastest trustworthy checks, scripts, suites, or manual proofs for the major
  capability surfaces]

## Known Unknowns

- [Stale areas, unresolved ownership, weak observability, or evidence gaps that
  downstream workflows should treat carefully]

## Low-Confidence Areas

- [Call out current stale, inferred, or weakly evidenced areas so readers know
  where extra live-code verification is needed.]
- [Tie low-confidence areas back to specific capabilities, workflows, or boundaries whenever possible.]

## Atlas Views

- [Summarize which cognition status and slices answer debugging, requirement shaping, implementation planning, testing, and verification questions.]
- [Call out where compatibility/export handbooks still help continuity without becoming the primary runtime truth path.]

## Where To Read Next

- [If you need to add or extend a capability, point to the topical file most
  likely to contain ownership, placement, and verification guidance.]
- [If you need to debug or extend an existing capability, route first through `By Symptom` or `By Capability`, then the matching deep workflow page.]
- [If you need API or protocol details, route to the relevant integration or
  workflow sections.]

## Topic Map

- `.specify/project-cognition/status.json` - default runtime status, freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` - canonical SQLite graph store
- `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` bundle - default route to readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; agents use those paths as first evidence, not final edit scope
- `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) - advanced route when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
- `project-cognition changes --format json` - Git-native change plan for `sp-map-update`; reports included, ignored, known, unknown, and recommended next action before incremental update recording
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- Legacy project-map artifacts - historical compatibility/export artifacts for existing projects, not the new runtime truth path

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
