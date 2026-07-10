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
- **UI design system**: Generated projects include a root `DESIGN.md` as the design-system contract. UI-facing workflows read it before specification, planning, task generation, and implementation. Use `sp-design` to create, synthesize, refine, or audit the design system; use `specify design lint` to check structural readiness; use `specify design export --format json|tailwind` when implementation needs token exports; use `specify design import SOURCE_REFERENCE` to create reference summaries for synthesis without overwriting `DESIGN.md`. Feature-specific UI references are owned by `sp-specify`, not `sp-design`: screenshots, HTML/CSS mockups, UI framework snippets, design exports, URLs, existing pages, or "make it like this" language route through the writable `ui-reference-artifact` lane. That lane writes `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`; downstream plan/tasks/implement stages treat `ui-brief.md` as the worker-facing UI contract and record `pending-human-review` when visual fidelity cannot be proven by agent verification. `sp-specify` asks for a UI reference fidelity mode and defaults to `approximate`.
- **User-confirmed product scope**: Generated workflows preserve the user's complete user-confirmed scope. Workflow routing may choose the lightest safe command surface, but `sp-plan` and `sp-tasks` must not convert the user's product intent into a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`. Scope reduction requires user confirmation, including when a named constraint forces a scope decision. Complexity alone is not a valid reason to shrink scope, defer ordinary work, or block; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
- **`sp-auto` nonblocking resume**: `sp-auto` resumes the safe next workflow from
  recorded state. When the routed workflow would only ask a bounded question or
  confirmation with one safe recommended/default answer, it accepts that answer
  and continues; when it cannot do so safely, it reports the blocker and a
  self-unblock recommendation instead of waiting silently.
- **Command-surface minimization**: Command-surface minimization must not delete capability. When upstream discussion or specification text includes a new/create/scaffold/authoring operation, downstream workflows must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact. Manual copy steps and template-only docs are support material, not a replacement for the confirmed operation unless the user selected that narrower entry point.
- **Evidence-backed project Q&A**: Use `sp-ask` for read-only project questions before choosing an action workflow. It can use project cognition to navigate, but it answers from live evidence and does not create state, handoffs, tests, builds, or source edits. Same-topic follow-ups reuse the prior evidence set when it still applies; localized, mixed-language, CJK, colloquial, or project-slang terms are normalized into project vocabulary; complex answers separate proven facts from evidence-derived inferences and unknowns. It is independent from `sp-discussion`, does not create `.specify/ask/`, does not run package managers or project CLI commands by default, and has no `specify ask` Typer helper in v1.
- **Pre-spec discussion**: `sp-discussion` classifies each user turn and works as a high-throughput senior product-engineering advisor before formal specification or bounded quick execution. It keeps frontstage / backstage separation: the visible conversation uses one unified frontstage contract with the recommended direction, plain-language reason, usable draft or next design step, default next step, and override path when relevant; the agent controls headings, order, and detail level instead of choosing named answer templates or fixed cards. State accounting backstage tracks decisions, open questions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. It uses checkpoint persistence: do not persist every turn; ordinary replies, acknowledgements, low-risk preferences, and small clarifications default to frontstage-only deferred in-conversation persistence rather than file writes, including for counters, receipts, status summaries, and dirty markers; flush batched compact events at semantic checkpoints, user-triggered checkpoints/saves, compaction risk, or durable lifecycle transitions; after several unsaved turns, a reply may mention the unsaved turn count and suggest `checkpoint, continue`, but that suggestion is not a file write; and surface file paths and state updates only when the user needs review, recovery, verification, or state visibility. Native hooks may surface resume or compaction reminders, but they are not a per-user-reply or per-tool-use persistence loop for discussion files. The behavior is: continue by default, do not ask for continuation, and ask only when user judgment is genuinely required and no safe default exists. It uses project cognition as advisory navigation, proves technical facts from live evidence, treats live repository evidence as the source of truth, performs a Truth Pass before project-specific technical advice, separates verified facts from assumptions, reports advice confidence, and maintains a Discussion Compass. It stores durable product/technical discussion artifacts under `.specify/discussions/<slug>/` only at save triggers, semantic checkpoints, and lifecycle transitions, runs a Context Boundary Gate before technical options or handoff generation, and drafts one unified `discussion_requirement_contract` handoff only after explicit user request and boundary lock; the handoff becomes ready only after self-review and user confirmation. Until that ready pair exists, `sp-discussion` must keep the visible next step inside handoff assessment, draft review, or repair and must not tell the user to run `sp-specify`; `specification-input.md` is not a substitute handoff. The compatibility filenames remain `handoff-to-specify.md` plus `handoff-to-specify.json`, but the pair is not specify-only: it carries an agent-facing requirement contract, `consumer_eligibility` for `sp-specify` and `sp-quick`, `recommended_consumer`, and `quick_task_candidate`. `handoff-ready` remains resumable until an eligible consumer consumes it; `sp-specify` validates the ready/user-confirmed contract before feature creation and derives the feature description from `handoff_goal`, while `sp-quick` validates `consumer_eligibility.sp-quick`, seeds quick `STATUS.md`, and still requires the Quick Checkpoint before execution. After consumption, generated projects should run `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` so `handoff_consumption_status: consumed`, `consumed_by_feature_dir`, `status: completed`, and `next_command: none` remove stale handoffs from default `sp-auto` candidates. Generated projects can then archive it with `specify discussion archive <slug>`. Cross-project requests must lock the target project root (`target_project_root`); current project cognition cannot prove another project's implementation facts. The valid handoff is one unified handoff pair with `handoff_goal`, `context_boundary`, `implementation_target`, evidence provenance, `quality_gate`, a human-facing `Handoff Reviewer Guide`, Must-Preserve Ledger, coverage status, planning gate status, and quick-task boundedness status. Skills-based projects include `spec-kit-discussion-handoff-review` to standardize review verdicts and apply ready-summary quality checks without requiring fixed visible labels or cards. Downstream workflows must preserve each protected item or block for a user decision.
- **Agent-native discussion state**: Human frontstage replies are written from the human's point of view with adaptive headings; agent backstage uses a compact typed `DiscussionTurnPacket`. Canonical state is `discussion-state.json`, Markdown is a derived compatibility view, and `discussion-log.jsonl` contains semantic checkpoints. Lifecycle is `explore -> ground -> decide -> prepare -> review -> ready -> consumed|closed`; UI, blockers, evidence, persistence mode, and confirmation are orthogonal. Checkpoints are meaning-driven rather than turn-count-driven. Canonical handoff JSON renders Markdown deterministically, and user confirmation plus downstream consumption bind to a stable `review_digest`.
- **Discussion-to-specify continuation**: When `sp-specify` consumes a user-confirmed `sp-discussion` handoff and there is one safe recommended approach or section shape that preserves the confirmed scope, it should record that choice and write the draft spec package instead of asking the user to approve the recommendation again. The mandatory user review happens after the draft artifacts exist. Runtime/tool availability details such as structured-question fallback or execution mode stay backstage.
- **Discussion unified frontstage replies**: All `sp-discussion` visible replies use the same flexible contract. For readiness summary, include locked direction, reason, blocked decisions, evidence gaps, downstream planning inputs to preserve, default discussion action, and override path; do not split the work into P0/P1/P2, migration phases, release batches, task packets, or ordered implementation steps because those belong to `sp-plan`, `sp-tasks`, or `sp-implement`. For pre-handoff readiness, include likely verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path without writing or claiming `handoff-assessment.md`. For draft handoff review, include recommended route, scope to approve, excluded scope, readiness checks, package paths, and allowed review decisions. Do not require fixed headings, fixed cards, or a template ID selection step.
- **Discussion fallback language**: When the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, `sp-discussion` records that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. It must not turn that into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.
- **Discussion handoff repair ownership**: When review returns `request-changes` or a consumer reports `blocked_by_handoff_integrity`, the fix belongs in `sp-discussion`. Update canonical JSON, render Markdown from the same payload, preserve `entry_source`, source paths, `review_digest`, planning/coverage gates, unknown/conflict counts, and quality-gate evidence, rerun self-review, and ask for approval of the current digest. Consumers block instead of reconstructing or patching the pair.
- **Discussion next-step content**: When `sp-discussion` recommends a default next step, the same reply should include the first-pass content for that step, such as a draft, option board, readiness checklist, handoff assessment checklist, evidence plan, or field-by-field responsibility audit table. Do not make the user ask for "next" just to see the content already recommended.
- **Discussion decision digest**: When `sp-specify` consumes a discussion handoff, it builds a `Discussion Decision Digest` so selected direction, rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and must-not-dilute constraints become explicit spec/alignment/context inputs instead of disappearing into prose. When `sp-quick` consumes the same handoff, it carries the digest, Must-Preserve items, and reopen conditions into `STATUS.md` before the Quick Checkpoint.
- **Quick workflow confirmation**: `sp-quick` presents a plain-text Quick Checkpoint before substantive execution. The card records issue, target outcome, boundaries, known facts/assumptions, affected surfaces, concrete implementation plan, next action, validation evidence, and stop condition, then waits for confirmation before implementation, delegation, broad repository analysis, or validation commands. Checkpoint cards must not use HTML tags or inline line-break markup in terminal output.
- **Debug workflow confirmation**: `sp-debug` presents a plain-text Debug Checkpoint before substantive investigation. The card records symptom, expected behavior, reproduction or failing signal, known evidence, investigation boundary, candidate focus, ordered investigation plan, first evidence action, fix gate, and progress signal, then waits for confirmation before reproduction, logs, source/test reads, evidence collection, fixes, or validation. Checkpoint cards must not use HTML tags or inline line-break markup in terminal output.
- **Embedded implement review**: `sp-implement` owns an embedded review-and-repair loop after a clean `sp-tasks` handoff. It runs a pre-implement review before source edits, drift review after join points and bounded sequential review windows, safe task-layer repairs for incomplete tasks/packets/handoff state/tracker state, and implementation-review audit records. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts are upstream truth and still route back to the owning workflow instead of being repaired inside implementation.

## How To Read This Project

- Start here for compatibility/export orientation.
- **Advisory project cognition index**:
  - `.specify/project-cognition/status.json` for freshness, coverage, stale paths, and refresh metadata
  - `.specify/project-cognition/project-cognition.db` as the canonical graph store
  - `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` for default brownfield navigation intake, readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; these paths are first evidence, not final edit scope
  - `project-cognition semantic-intake --input <work-contract-input.json> --format json` as the WorkContract v1 unified semantic candidate entrypoint for colloquial, localized, symptom-first, or mixed-language requests; semantic-intake alone cannot authorize source changes, root-cause claims, fixed claims, complete claims, or release-safe claims
  - `project-cognition semantic-audit --input <semantic-audit-input.json> --format json`, when available, as the optional v1.1 audit artifact builder for replayable WorkContract artifact records: semantic-intake input/output snapshot, selected/rejected basis, permission upgrade/downgrade reason, and action log; the audit artifact does not authorize source changes or replace live-evidence verification
  - `project-cognition semantic-audit-resume --input <resume-validation.json> --format json`, when available, as the optional persisted audit-state comparator. It does not authorize source changes or final claims, and does not grant P3/P4. Multiple `authorized_claims` require a single `active_claim_type`, and failed, blocked, skipped, or inconclusive verification results keep claim readiness blocked with `verification_result_failed`, `verification_result_blocked`, or `verification_result_inconclusive` until a newer matching passed rerun supersedes them.
  - `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) for advanced escalation when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
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
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Stateful first-baseline scans also require `.specify/project-cognition/workbench/scan-queue.json` and `handoff-ledger.json`; build readiness requires sparse `path_index` gates to pass before `status.json` can be query-ready. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
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
