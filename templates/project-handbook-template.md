# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Compatibility/export navigation view for this repository.

## System Summary

[What this project is, its primary runtime shape, its major layers or runtime
units, and the main capability surfaces that planners or implementers must keep
in view.]

[Cover the project type, primary technology stack, build/dependency tooling, and deployment shape. Name the major capability surfaces, runtime units, and architectural boundaries that downstream readers must understand first.]

Project cognition compass, query, and expansion responses carry an `epistemic_contract` with `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. This contract cannot authorize source changes and cannot prove current behavior; agents must carry it into downstream state, withhold unverified claims, and let contradictory live evidence override the route candidate.

Graph claims are indexed assertions. Their lifecycle is `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale`; even `verified_in_graph_generation` is scoped to the active graph generation and is not current repository truth. Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; bounded live evidence, matching workflow verification, and explicit final-claim authorization remain separate requirements.

Schema v5 adds revision-bound, expiring reconciliation to the auditable live feedback loop and current evidence basis while preserving superseded claim evidence as history. Decisive claim-specific bounded reads provide semantic intent to `project-cognition claim-reconcile prepare --input <intent.json> --format json`; the runtime owns every integrity field and returns a prepared packet path plus structured `apply_argv`. Execute that argv through `project-cognition claim-reconcile apply --input <prepared_packet_path> --format json`, then rerun Compass once on ready. This remains route-candidate evidence and cannot authorize a workflow final claim. Schema v5 does not migrate schema v4 or older databases.

## System Boundaries

[State what this repository deliberately owns, what it coordinates but does not own,
and what sits clearly outside the system boundary.]

## High-Value Capabilities

- [List the highest-value capabilities a newcomer should understand first.]
- [For each capability, state why it matters and which topical file should be
  read next.]
- **Project Learning lifecycle**: Agents consume reusable project Learning only through read-only CLI progressive disclosure: `specify learning start --command <workflow> --format json`, filtered/paginated `learning list`, then one selected `learning show --ref <ref>`. Production is separate: `capture` / `capture-auto` create or merge candidates and explicit `promote` changes lifecycle state. Classic commands use the shared Learning partial/passive skill; Advanced skills use `references/project-learning.md`; storage files are runtime implementation details rather than normal agent read surfaces.
- **Project Learning Agent contract**: Summary cards expose identity, imperative action, applicability, trigger signals, lifecycle strength, and executable `show_argv`; full records group guidance, evidence, provenance, and lifecycle detail. Owned workflow state records explicit `kind: compact evidence` entries under `## Learning Triggers`, which `capture-auto` maps deterministically into typed candidates.
- **Semantic `sp-specify` traceability**: `sp-specify` uses a collaborative
  specification flow: explore project context, decompose semantic terms, compare
  approaches when a decision is still open, write artifacts, and self-review them.
  Discussion-originated work uses compile mode: consume the confirmed
  `handoff-to-specify.json`, preserve its decision digest by reference, and reopen
  source evidence only when a named reference is stale, missing, or contradictory.
  `spec-contract.json` is the agent-facing authority; user review is required only
  for a non-empty semantic delta or a real unresolved decision. Project-facing
  Markdown remains available when it has independent human value.
- **UI design system**: Generated projects include a root `DESIGN.md` design-system bootstrap seed. It is structurally valid but not approved product direction until `sp-design` or `$spx-design` replaces generic starter choices, records approval/provenance, and passes `specify design lint --level ready`; `specify design lint --level structural` checks shape only. Use `specify design export --format json|tailwind` for approved implementation tokens (`--allow-unapproved` is a temporary legacy migration escape hatch) and `specify design import SOURCE_REFERENCE` for synthesis input. Substantive UI work creates `ui-brief.md` even without an external reference. UI reference inputs such as screenshots, mockups, code references, design exports, URLs, existing pages, or "make it like this" language additionally use Classic's writable `ui-reference-artifact` lane, which writes `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`, and defaults fidelity to `approximate`. Plan/tasks/implement preserve the brief in the single current structured UI contract; old UI version fields, duplicate fidelity payloads, untyped lifecycle refs, and evidence-kind aliases are not accepted and stale artifacts must be regenerated. Completion requires real-entrypoint viewport/state evidence and a capture/inspect/repair/recapture loop; unavailable comparison remains `pending-human-review`.
- **User-confirmed product scope**: Generated workflows preserve the user's complete user-confirmed scope. Workflow routing may choose the lightest safe command surface, but `sp-plan` and `sp-tasks` must not convert the user's product intent into a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`. Scope reduction requires user confirmation, including when a named constraint forces a scope decision. Complexity alone is not a valid reason to shrink scope, defer ordinary work, or block; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
- **`sp-auto` nonblocking resume**: `sp-auto` resumes the safe next workflow from
  recorded state. When the routed workflow would only ask a bounded question or
  confirmation with one safe recommended/default answer, it accepts that answer
  and continues; when it cannot do so safely, it reports the blocker and a
  self-unblock recommendation instead of waiting silently.
- **Command-surface minimization**: Command-surface minimization must not delete capability. When upstream discussion or specification text includes a new/create/scaffold/authoring operation, downstream workflows must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact. Manual copy steps and template-only docs are support material, not a replacement for the confirmed operation unless the user selected that narrower entry point.
- **Agent-facing CLI runtime**: Negotiate stable capabilities with `specify api handshake --format json`; list the optimized API with `specify api list`, or discover every current Typer operation progressively with `specify api commands` followed by `specify api command <id>`. Feature stages use `specify workflow transition --to <stage>` with the current revision. The runtime validates the completed source-stage artifacts, refuses skips/stale writes without mutation, and uses exit code `10` for a detailed resumable blocker. Do not make agents rebuild command parameters, workflow state, or human recovery tutorials from prompt prose.
- **Evidence-backed project Q&A**: Use `sp-ask` for read-only project questions before choosing an action workflow. It can use project cognition to navigate, but it answers from live evidence and does not create state, handoffs, tests, builds, or source edits. Same-topic follow-ups reuse the prior evidence set when it still applies; localized, mixed-language, CJK, colloquial, or project-slang terms are normalized into project vocabulary; complex answers separate proven facts from evidence-derived inferences and unknowns. It is independent from `sp-discussion`, does not create `.specify/ask/`, does not run package managers or project CLI commands by default, and has no `specify ask` Typer helper in v1.
- **Pre-spec discussion**: Use `discussion` before `specify` or `quick` when product direction, trade-offs, or context boundaries are not yet stable. Human-visible replies remain human-first and adaptive; compact typed state stays backstage. After explicit handoff request, boundary lock, self-review, and confirmation, `sp-discussion` writes exactly one Agent-only `handoff-to-specify.json` requirement contract. It has no Markdown companion or reviewer-guide artifact. The contract preserves target need, scope, constraints, success criteria, design direction, evidence refs, target boundary, decision digest, Must-Preserve/Consequence refs, consumer eligibility, and recovery. Supporting discussion files are read downstream only through a named stale, missing, or contradictory evidence ref.
- **Discussion cadence**: Continue by default, do not ask for continuation, and ask only when user judgment is genuinely required and no safe default exists.
- **Discussion persistence**: Ordinary turns use frontstage-only deferred in-conversation persistence rather than file writes, including for counters, receipts, status summaries, and dirty markers. Native hooks are not a per-user-reply or per-tool-use persistence loop; durable writes occur only at save triggers, semantic checkpoints, and lifecycle transitions.
- **Agent-native phase pipeline**: `handoff-to-specify.json` -> `spec-contract.json` -> `plan-contract.json` -> `task-index.json` -> per-task lifecycle records -> `human-acceptance.json`. Generate project-facing Markdown and research/design/lane artifacts only when triggered. Compile delegated WorkerTaskPackets just in time, review implementation on evidence-triggered events, then use `sp-accept` to restore a contextless human's understanding and guide explicit product acceptance one real step at a time.
- **Adaptive planning dispatch**: `sp-plan` and `sp-tasks` use `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`; delegation must save more critical-path work than it costs.
- **Agent-native discussion state**: Human frontstage replies are written from the human's point of view with adaptive headings; agent backstage uses a compact typed `DiscussionTurnPacket`. Canonical state is `discussion-state.json`, Markdown is a derived compatibility view, and `discussion-log.jsonl` contains semantic checkpoints. Lifecycle is `explore -> ground -> decide -> prepare -> review -> ready -> consumed|closed`; UI, blockers, evidence, persistence mode, and confirmation are orthogonal. The handoff itself is JSON-only, and confirmation/consumption bind to `review_digest`.
- **Discussion-to-specify continuation**: A confirmed discussion contract enters compile mode. `sp-specify` reuses its decisions and evidence, computes `semantic_delta`, and does not repeat approach selection or user review when the delta is empty.
- **Discussion unified frontstage replies**: All `sp-discussion` visible replies use the same flexible contract. For readiness summary, include locked direction, reason, blocked decisions, evidence gaps, downstream planning inputs to preserve, default discussion action, and override path; do not split the work into P0/P1/P2, migration phases, release batches, task packets, or ordered implementation steps because those belong to `sp-plan`, `sp-tasks`, or `sp-implement`. For pre-handoff readiness, include likely verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path without writing or claiming `handoff-assessment.md`. For draft handoff review, include recommended route, scope to approve, excluded scope, readiness checks, package paths, and allowed review decisions. Do not require fixed headings, fixed cards, or a template ID selection step.
- **Discussion fallback language**: When the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, `sp-discussion` records that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. It must not turn that into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.
- **Discussion handoff repair ownership**: Repair canonical JSON in `sp-discussion`, recompute the digest, and confirm the current revision. Do not render or compare a Markdown handoff.
- **Discussion next-step content**: When `sp-discussion` recommends a default next step, the same reply should include the first-pass content for that step, such as a draft, option board, readiness checklist, handoff assessment checklist, evidence plan, or field-by-field responsibility audit table. Do not make the user ask for "next" just to see the content already recommended.
- **Discussion decision digest**: When `sp-specify` consumes a discussion handoff, it builds a `Discussion Decision Digest` so selected direction, rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and must-not-dilute constraints become explicit spec/alignment/context inputs instead of disappearing into prose. When `sp-quick` consumes the same handoff, it carries the digest, Must-Preserve items, and reopen conditions into `STATUS.md` before the Quick Checkpoint.
- **Quick workflow confirmation**: Raw quick requests use one Understanding Checkpoint for user-owned outcome, visible result, scope, recommended approach, assumptions/risks, completion evidence, and reconfirmation triggers. Applicable UI work adds an independent implementation-proposal card and one reply confirms both; technical execution remains agent-owned. A confirmed discussion contract with no quick-stage semantic delta reuses its `review_digest` and does not repeat that confirmation.
- **Debug workflow confirmation**: `sp-debug` presents one plain-text Debug Checkpoint before substantive investigation for reporter-owned problem facts, expected behavior, occurrence conditions, investigation boundary, fix authority, assumptions to correct, and reconfirmation triggers. Agent hypotheses and evidence sequencing stay outside the approval table. Applicable UI symptoms add an independent target-baseline card, with one reply for both and no speculative repair approval. Checkpoint cards must not use HTML tags or inline line-break markup in terminal output.
- **Event-triggered implement review**: `sp-implement` validates the task-graph revision at entry and reviews only on drift, parallel joins, write-scope change, validation failure, worker concern, obligation conflict, real-entrypoint gaps, or review-window limits. One task lifecycle record carries result, validation, review verdict, blockers, and recovery. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts remain upstream truth.
- **Post-implementation human acceptance**: Technical closeout prepares fingerprinted `human-acceptance.json` and hands off to `sp-accept`; it does not claim a human PASS. Acceptance assumes the human has no prior context, explains outcome/value/exclusions/prerequisites/entrypoint, guides one observable step at a time, persists the cursor and evidence, and routes defects or requirement gaps without editing source. Changed implementation evidence makes the guide stale and invalidates old acceptance.

## How To Read This Project

- Start here for compatibility/export orientation.
- **Advisory project cognition index**:
  - `.specify/project-cognition/status.json` for freshness, coverage, stale paths, and refresh metadata
  - `.specify/project-cognition/project-cognition.db` as the canonical graph store
  - `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` for default brownfield navigation intake, readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` and compact `claim_refs`, `coverage_diagnostics`, and `expansion_ref`; `route_confidence` is scoped by `confidence_scope=route_candidate`, advanced query `claim_signals` and `expand --section claim_evidence` expose bounded `source_path`/`span` refs, and every graph claim still requires live verification because it cannot prove current repository truth
  - Compass claim-aware ranking is a bounded rerank only after `match_score` establishes repository-backed candidate eligibility. `claim_ranking.adjustment` is capped at `+1` for fresh supported or graph-generation-verified claims, `-1` for stale, and `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. A selected `stale_claim_signal` or `contradicted_claim_signal` keeps the packet `usable_with_review` and returns `reconcile_claims_with_minimal_live_reads` plus a lane-specific live repository action.
  - `project-cognition semantic-intake --input <work-contract-input.json> --format json` as the WorkContract v1 unified semantic candidate entrypoint for colloquial, localized, symptom-first, or mixed-language requests; semantic-intake alone cannot authorize source changes, root-cause claims, fixed claims, complete claims, or release-safe claims
  - `project-cognition semantic-audit --input <semantic-audit-input.json> --format json`, when available, as the optional v1.1 audit artifact builder for replayable WorkContract artifact records: semantic-intake input/output snapshot, selected/rejected basis, permission upgrade/downgrade reason, and action log; the audit artifact does not authorize source changes or replace live-evidence verification
  - `project-cognition semantic-audit-resume --input <resume-validation.json> --format json`, when available, as the optional persisted audit-state comparator. It does not authorize source changes or final claims, and does not grant P3/P4. Multiple `authorized_claims` require a single `active_claim_type`, and failed, blocked, skipped, or inconclusive verification results keep claim readiness blocked with `verification_result_failed`, `verification_result_blocked`, or `verification_result_inconclusive` until a newer matching passed rerun supersedes them.
  - `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) for advanced escalation when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
  - Current query contracts are `claim_retrieval_contract_version=2` and `candidate_universe_version=2`; carry the latter from lexicon into every explicit query plan. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed.
  - Schema v5 is current-only. The current runtime does not migrate schema v4 or older databases and does not archive or replace them. Remove the incompatible project-cognition.db explicitly, then run `sp-map-scan -> sp-map-build` with the current binary.
  - `project-cognition changes --format json` - Git-native change plan for `sp-map-update`; reports `summary.included`, `summary.ignored`, `summary.known`, `summary.unknown`, `ignored_paths`, `unknown_paths`, top-level `next_action`, and per-change `recommended_action` before incremental update recording
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
- Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is not external map maintenance: normal `sp-*` workflows that change project-related source, runtime, templates, config, tests, generated assets, state contracts, or behavior-bearing docs must run planner-first project cognition update from their changed paths and affected surfaces. sp-map-update is for manual/external maintenance after user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Workflow-owned mutation closeout is planner-first: source-changing `sp-*` workflows run `project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json`, passing `--delta-session "$DELTA_SESSION_ID"` when a delta session exists. The planner returns `update_mode=delta_session` or `update_mode=payload_file`, `required_agent_fields`, `unknown_path_dispositions`, display-only command templates, and structured execution fields. Agents execute via `update_argv` after writing a completed payload, or by completing `delta_append_draft.argv_prefix` with agent-owned evidence placeholders before running `update_argv`. Verified `adoptable` unknown paths can be recorded without becoming blocking `known_unknowns`; only `blocking_known_unknown` dispositions become payload or delta known unknowns. `agent_disposition=adoptable` is accounting, not proof that runtime indexing succeeded; final routing uses `result_state`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`. Payload files accept `verification` plus the compatibility alias `verification_evidence`, and `generated_surfaces` plus the compatibility alias `generated_surface_notes`. Clean closeout gates on `result_state=ready` or `result_state=no_op`, not `status=ok`, `update_id`, `last_update_id`, freshness, display-only command templates, legacy `recorded-only` output, or failed verification evidence. A `partial_refresh` caused by `missing_passing_verification_result` must be repaired in the payload or delta evidence before final closeout; do not route that to `sp-map-update`, and never run `complete-refresh` or `clear-dirty` after partial/blocked outcomes.
- Closeout agents should use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If unrelated dirty or untracked working-tree paths were excluded by explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as blocking `known_unknowns`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. Before SQLite publication, `build-from-scan` adapts the accepted legacy-compatible scan package into a versioned proposal and runs the deterministic cognition proposal compiler; conflicts block before any graph-store mutation, and compiled graph material remains advisory route candidates rather than repository facts. The pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Stateful first-baseline scans also require `.specify/project-cognition/workbench/scan-queue.json` and `handoff-ledger.json`; build readiness requires sparse `path_index` gates to pass before `status.json` can be query-ready. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths`; `coverage.json` is coverage accounting, not a path-index source.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`.
- Recorded refresh and ready refresh are different outcomes: `partial_refresh` means refresh data was recorded but readiness still failed.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`. `sp-map-scan` runs `project-cognition generate-ignore --format json` before inventory; when it creates `.specify/project-cognition/.cognitionignore`, review the commented starter suggestions before continuing.
- After the ignore gate is clear, scan workflows resolve their temporary agent-facing file list with `project-cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json`. Default stdout contains only the file-list path and count, and the handoff file contains only `files`; do not replace this with broad ad hoc repository enumeration.
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
- `project-cognition changes --format json` - Git-native change plan for `sp-map-update`; reports `summary.included`, `summary.ignored`, `summary.known`, `summary.unknown`, `ignored_paths`, `unknown_paths`, top-level `next_action`, and per-change `recommended_action` before incremental update recording
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- Legacy project-map artifacts - historical compatibility/export artifacts for existing projects, not the new runtime truth path

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
