# Project Handbook

**Last Updated:** 2026-05-02
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` is a Python-first CLI and asset-packaging repository for practical Spec-Driven Development workflows across local AI coding agents. The primary product surface is the `specify` command implemented in `src/specify_cli/__init__.py`; it initializes projects, installs agent-specific workflow files, manages project cognition freshness and compatibility exports, exposes testing/learning/hook/eval helper surfaces, and provides the Codex-only `sp-teams` runtime path.

The repository has three mapped runtime modules:

- `specify-cli-core`: Python CLI, integration registry, project cognition freshness and compatibility-export helpers, learning/testing/eval helpers, execution packet/result contracts, hooks, orchestration policy, and Codex team Python control plane.
- `templates-generated-surfaces`: workflow command templates, command partials, passive skills, project-map compatibility/export templates, scripts, and worker prompts that are copied or transformed into downstream projects.
- `agent-teams-engine`: bundled optional Node/TypeScript plus Rust runtime assets for Codex team coordination.

## System Boundaries

This repository owns the `specify` CLI, bundled templates/scripts, supported-agent integration adapters, project-map compatibility/export templates, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

## High-Value Capabilities

- **Project initialization and generated agent surfaces**: `specify init` resolves `--ai` or `--integration`, installs command/skill/workflow files, copies scripts/templates, and records integration manifests. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/**`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Generated-project repair and compatibility diagnostics**: `specify check` now surfaces broken project launchers and stale generated runtime assets, and `specify integration repair` refreshes shared/runtime-managed generated assets in place without overwriting user-edited workflow content. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Passive project learning memory**: generated projects use `.specify/memory/learnings/INDEX.md` as the thin first-read learning layer and may link each reusable lesson to one detail markdown document under `.specify/memory/learnings/`. `project-learnings.md` remains a compatibility summary; new captures write index/detail memory first, and workflow closeout applies the Learning Reflex before reusable lessons are left only in chat or workflow state.
- **Workflow contract generation**: `templates/commands/`, `templates/command-partials/`, and `templates/passive-skills/` define `sp-*` behavior for downstream agents. `sp-specify` is now a collaborative reviewed specification flow with an internal brainstorming kernel that locks brainstorming truth artifacts (`facts`, `route`, `intent`, `complexity`), asks one question at a time, decomposes semantic terms, compares approaches, writes and self-reviews artifacts, asks for user review, and then compiles the familiar spec package before routing to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`. Discussion-originated specs must read discussion source files and record capability-like upstream signals in `source_signal_disposition` instead of trusting only the handoff summary. `sp-auto` is the state-driven resume entrypoint; when the routed workflow would only ask a bounded question or confirmation with one safe recommended/default answer, it accepts that answer and continues, and when it cannot do so safely it reports a blocker plus a self-unblock recommendation instead of waiting silently. `sp-plan` and `sp-tasks` now use adaptive execution: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`. Light mode runs leader-inline for low-risk single-lane artifact work. Standard mode uses native-subagent dispatch when available, degrades leader-inline with `capability_degraded: true` only when native subagents are unavailable and no high-risk trigger is present, and blocks as `subagent-blocked` when there is no safe lane or the work cannot be packetized safely. Heavy or safety-critical work blocks when native subagents are unavailable or the work is unpacketizable. Managed-team fallback is not part of adaptive plan/tasks dispatch. `sp-quick` includes a one-time Understanding Checkpoint before substantive execution. `sp-debug` is complexity-based: leader-inline for small focused investigations, subagent-assisted for broad or independent evidence lanes, and blocked with `execution_surface: none` when the next safe step cannot proceed. Structured planning and task-generation handoffs remain required when delegated lanes are used. Read `templates/commands/**`, `templates/command-partials/**`, and `modules/templates-generated-surfaces/WORKFLOWS.md`.
- **Debug workflow confirmation**: `sp-debug` also performs one Debug Understanding Checkpoint before substantive investigation. Generated agents must present a Debug Checkpoint card with concrete symptom, expected behavior, investigation scope, first evidence action, and progress signal details before reproduction, logs, source/test reads, evidence collection, fixes, or validation.
- **sp-* compact quality standard**: Before adding, modifying, or compressing any `sp-*` workflow prompt, handoff shape, state artifact, task packet, or validation closeout contract, use `docs/workflow-quality/README.md`. A candidate optimization must show quality retention of at least 98% and whole-chain cost reduction; do not shorten prompts by moving ambiguity or interpretation burden downstream.
- **User-confirmed product scope**: Generated workflows preserve the user's confirmed product scope. Workflow routing may choose the lightest safe command surface, but it must not convert the user's product intent into a smaller MVP or first-story release. Scope reduction requires user confirmation, including when a named constraint forces a scope decision.
- **Command-surface minimization**: Command-surface minimization must not delete capability. When upstream discussion or specification text includes a new/create/scaffold/authoring operation, `sp-specify`, `sp-plan`, and `sp-tasks` must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral. Manual copy steps and template-only docs are support material, not a replacement for the confirmed operation unless the user selected that narrower entry point.
- **Semantic `sp-specify` traceability**: `sp-specify` preserves intent through `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and a minimal compatibility `brainstorming/handoff-to-specify.json`. `alignment.md` is the semantic traceability surface for `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts`; no upstream capability-like signal should disappear between discussion and spec.
- **Pre-spec discussion**: `sp-discussion` classifies each user turn, asks only for product judgment or genuine boundary/evidence conflicts, uses project cognition as advisory navigation, proves technical facts from live repository evidence, treats live evidence as the source of truth, appends compact ordinary-turn events, and refreshes structured discussion artifacts only at semantic checkpoints. It is a senior product-engineering advisor surface: before project-specific technical advice it performs a Truth Pass, separates verified facts from assumptions, reports advice confidence, gives owner-readable judgment with evidence and risk, maintains a Discussion Compass, uses recommendation-first decision progression, and proactively maps adjacent decisions instead of forcing narrow follow-up loops. It stores resumable product/technical discussions under `.specify/discussions/<slug>/`, runs a Context Boundary Gate before technical options or handoff generation, and drafts the unified handoff only after explicit user request and boundary lock; the handoff becomes ready only after self-review and user confirmation. `handoff-ready` remains resumable until `sp-specify` consumes it; after consumption, generated projects should run `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` so `handoff_consumption_status: consumed`, `consumed_by_feature_dir`, `status: completed`, and `next_command: none` remove stale handoffs from default `sp-auto` candidates. Generated projects can then archive it with `specify discussion archive <slug>`. Cross-project requests must lock the target project root (`target_project_root`); current project cognition cannot prove another project's implementation facts. The valid handoff is one unified handoff pair: `handoff-to-specify.md` plus `handoff-to-specify.json`, with `handoff_goal`, `context_boundary`, `implementation_target`, evidence provenance, `quality_gate`, Must-Preserve Ledger, coverage status, and planning gate status. Downstream workflows must preserve each protected item or block for a user decision.
- **Existing-project PRD extraction**: `sp-prd-scan -> sp-prd-build` is the canonical heavy reconstruction PRD lane for reverse-extracting repository-first current-state product documentation from code, docs, tests, routes, UI/API surfaces, and atlas evidence. Substantive scans are subagent-mandatory, critical claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. `sp-prd-build` compiles from the scan package into the expanded reconstruction archive; `exports/README.md` is the package navigation entry, `exports/prd.md` remains the primary reader-facing PRD, and `sp-prd-build` must not reread the repository. `sp-prd` is deprecated compatibility-only routing into that pair, which remains a peer workflow path to `sp-specify` with no automatic planning handoff.
- **Concurrent lane runtime**: `src/specify_cli/lanes/` adds lane-local durable state, reconcile-before-resume routing, and dedicated lane closeout primitives for independent feature execution.
- **Enriched task contract generation**: `sp-tasks` produces the minimum executable task contract in light mode and enriched subagent-ready task contracts in standard/heavy mode when downstream delegated implementation needs packets. UI/TUI/CLI/API/runtime-visible work must include User-Observable Path Coverage and packet fields such as `consumer_surfaces` plus `required_evidence: real_entrypoint_evidence` when synthetic-only proof would miss the real entrypoint.
- **Tasks/implement default contract**: `sp-tasks` must run an implementation-readiness self-audit before handoff. Clean completion writes `next_command: /sp.implement`, `gate_status: cleared`, and `highest_invalid_stage: none`; `sp-analyze` remains an optional diagnostic and legacy revalidation route only when explicitly invoked or recorded in existing state. If `analyze` is run, it should finish a complete blocker bundle before choosing the next command. repeated `tasks -> analyze -> tasks` loops are abnormal; only use `analyze` again when explicitly required by legacy or diagnostic state. Missing upstream truth routes directly to `plan`, `clarify`, or `deep-research`.
- **Embedded implement review**: `sp-implement` owns an embedded review-and-repair loop after a clean `sp-tasks` handoff. It runs a pre-implement review before source edits, drift review after join points and bounded sequential review windows, safe task-layer repairs for incomplete tasks/packets/handoff state/tracker state, and implementation-review audit records. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts are upstream truth and still route back to the owning workflow instead of being repaired inside implementation.
- **Spec quality gate (`spec-lint`)**: `tools/spec-lint/` is a zero-dependency Go binary that mechanically validates the current `sp-specify -> sp-plan` artifact contract plus tiered quality checks before `sp-plan`. Install scripts, CI cross-compilation, and the quality gate spec live alongside the tool. Read `templates/spec-quality-gate.md`.
- **Brownfield cognition lifecycle**: Generated projects use `.specify/project-cognition/status.json` plus `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the advisory project cognition index, default brownfield navigation intake, and advisory navigation inputs, while `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries. The compass packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`. Agents read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `before_fix_claim` checks to prove or reject the route from live repository evidence. These paths are first evidence, not final edit scope. When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`). The advanced CLI tool's `agent_normalization` field remains agent semantic guidance, not a route decision. Facet coverage gates advanced-path selection; top lexical or vector similarity alone is not route truth. Map points, code proves: navigation terms are route vocabulary, not evidence by themselves, and technical claims must be backed by live project evidence. If the map is stale, weak for localized coverage, blocked, or likely incomplete, ordinary workflows continue with live repository evidence and apply the map-update-first routing policy. Workflow-owned mutation closeout is not external map maintenance: source-changing `sp-*` workflows run inline project cognition update for their own changed paths and affected surfaces, while `sp-map-update` remains the external/manual entrypoint for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`; `build-from-scan` archives a v1 DB and rebuilds a clean schema v2 database. Map-specific workflows and validation commands still validate their own artifacts; recorded refresh and ready refresh are different outcomes, and `partial_refresh` means refresh data was recorded but readiness still failed. A first brownfield cognition baseline is map-maintenance complete only after `project-cognition validate-scan --format json` and `project-cognition validate-build --format json` pass. `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths` and `alias_index` rows from alias-ready node titles, types, paths, and bounded attrs; `coverage.json` is coverage accounting, not a path-index source. Coverage or coverage-ledger rows do not prove a path was scanned unless a concrete scan packet assigned the path and that packet's worker result reported packet-local coverage. After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`. Generated projects require `PROJECT_COGNITION_BIN` or `project-cognition` on PATH for direct project-cognition helpers; helper scripts prefer `PROJECT_COGNITION_BIN` when set and otherwise call `project-cognition` from PATH. Project cognition ignore rules live in root `.cognitionignore` or `.specify/project-cognition/.cognitionignore`; they are gitignore-compatible, apply to `map-scan`, `map-build`, and `map-update`, and excluded paths must not enter project cognition graph evidence, route indexes, or `minimal_live_reads`.
- **Inline cognition closeout result state**: Workflow-owned mutation closeout uses the same lower-level update engine as `sp-map-update`. Delta-session closeout calls `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; non-delta closeout writes `.specify/project-cognition/updates/<update-id>.json` and calls `project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json`. Payload files accept `verification` plus the compatibility alias `verification_evidence`, and `generated_surfaces` plus the compatibility alias `generated_surface_notes`. A clean closeout requires `result_state=ready` or `result_state=no_op`; `update_id`, `last_update_id`, freshness, legacy `recorded-only` output, and failed verification evidence are not enough.
- **Delegated execution contracts**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/orchestration/` define packet/result schemas, quality hooks, adaptive and mandatory dispatch selection, and state surfaces.
- **Codex team runtime**: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/`, and `extensions/agent-teams/engine/` provide optional Codex team orchestration, state, MCP facade, and bundled engine assets.
- **Testing and verification**: Python pytest layers, integration/template contract tests, Codex-team tests, and engine build checks protect generated behavior.

## How To Read This Project

- Start here for orientation.
- The runtime atlas now resolves to two workflow handbooks.
- Read `DEBUG-HANDBOOK.md` for `sp-debug` and `BUILD-HANDBOOK.md` for the major non-debug workflows.
- **First stop for any task**: use the project cognition routes described here. Repo-local `.specify/` state is not committed source-of-truth for this repository.
- For generated projects, read `.specify/project-cognition/status.json` plus the task-local `project-cognition compass` packet before broad brownfield work.
- Treat project cognition as an advisory navigation index. Code, tests, scripts, configuration, and authoritative docs are the evidence sources.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence.
- Empty projects initialized by `specify init` run `project-cognition init-empty` after pinning the binary. When there is no business code yet, this creates `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` with baseline kind `baseline_kind=greenfield_empty`; greenfield flows do not require map-scan -> map-build solely because the graph has no paths. Projects with existing code still use map-scan -> map-build when a full first brownfield cognition baseline is needed for a first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- When referencing another local directory, run `project-cognition discover --root <path> --format json` after checking for `.specify/`. Use that directory's cognition only when `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` exist, `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is true; otherwise fall back to minimal live reads. Do not treat legacy `.specify/project-map/**` outputs as current truth.
- Supporting project-map outputs are support-only or reference-only compatibility/export surfaces.
- The refresh workbench still contains `map-scan` / `map-build` scan packets and refresh workbench artifacts for rebuilding the handbooks.
- Legacy project-map artifacts may still exist in old projects, but there is no Python runtime alias and new workflows should not call or require `.specify/project-map/**`.
- Fall back to live code reads only when cognition coverage is missing, stale, too broad, or marked low confidence.
- If changed paths are missing from project cognition `path_index`, let `sp-map-update` classify the gap first when the user requested map maintenance or a separate map-maintenance pass is required. Source-changing `sp-*` workflows run inline project cognition update for their own changed paths and affected surfaces during closeout. Uncertain closure is recorded by inline update or `map-update` as partial/low-confidence facts when needed. Adoptable paths get provisional coverage, uncertain paths return `minimal_live_reads`, and ordinary existing-baseline gaps remain external/manual `sp-map-update` work.
- `sp-debug` should use `project-cognition compass --intent debug --query "$ARGUMENTS" --format json` as its default intake. `project-cognition query --query-plan` remains available for advanced precision escalation when compass coverage is missing, ambiguous, stale, or contradicted by evidence, and the deeper Stage 1A/1B observer-contract flow remains available for the same evidence conflicts.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.

## Project Cognition Routes

For generated projects, use project cognition first:

- `.specify/project-cognition/status.json` — freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` — canonical SQLite graph store
- `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` — default brownfield navigation intake returning readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; paths are first evidence, not final edit scope
- `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) — advanced path when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
- The advanced alias catalog path carries facet coverage details: `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `candidate_universe_version`, and `active_generation_id`.
- When shell quoting makes inline JSON brittle, use `project-cognition query --query-plan-file <path>` instead. The query plan accepts `path_hints`/`reason` as aliases for `paths`/`selection_reason`.

The cognition model should help answer:

- which workflow-specific cognition slice owns the current task
- which graph-backed concept candidates, alias interpretations, paths, and affected surfaces must be read before source work begins
- which propagation risks and verification routes matter before changing code
- what remains unknown and therefore needs live repository confirmation
- whether the factual freshness state is runtime staleness, support drift, or a partial refresh that still blocks readiness

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. `sp-map-build` and the project cognition runtime provide the evidence layer, but the Senior Consequence Analysis Gate turns those facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, and `implement`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.

## Shared Surfaces

- `src/specify_cli/__init__.py`: top-level Typer app, command registration, init flow, project-map/hook/learning/testing/eval/team helper commands.
- `src/specify_cli/launcher.py`: persisted project launcher binding, generated-project compatibility diagnostics, and runtime launcher helpers.
- `src/specify_cli/lanes/`: lane registry cache, lane-local durable state, lease helpers, reconcile logic, root-level lane resolution, and integrate closeout helpers.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/__init__.py`: integration registry, shared generation bases, template processing, passive skill installation, manifest behavior.
- `templates/`: command templates, command partials, passive skills, project-map/testing templates, worker prompts, constitution/spec/plan/tasks artifacts.
- `scripts/bash/` and `scripts/powershell/`: generated helper layer and freshness/context-update scripts.
- `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`: packet/result schemas, workflow hooks, adaptive plan/tasks dispatch plus mandatory-subagent dispatch/state/review helpers.
- `src/specify_cli/codex_team/` and `extensions/agent-teams/engine/`: optional Codex team runtime and bundled engine.
- `tools/spec-lint/`: spec quality gate binary, install scripts, CI cross-compilation workflow.
- `tools/project-cognition/`: standalone Go project cognition runtime binary, install scripts, and acceptance-gate validators.

## Risky Coordination Points

- Editing `src/specify_cli/__init__.py` can change CLI help, routing, init behavior, hook surfaces, and tests across many areas.
- Editing `templates/commands/`, `templates/command-partials/`, or `templates/passive-skills/` changes generated downstream behavior for multiple agents.
- Editing `src/specify_cli/integrations/base.py` affects most generated integrations.
- Editing `tools/project-cognition/`, `src/specify_cli/project_cognition_tool.py`, or freshness scripts affects brownfield workflow gating.
- Editing Codex team installer/runtime files can affect `.codex/config.toml`, `.specify/teams/*`, worker state, MCP behavior, and engine packaging.

## Change-Propagation Hotspots

- Agent registration metadata propagates into CLI help, integration generation tests, README guidance, generated file paths, and tool checks.
- Generated runtime compatibility rules propagate into `specify check`, integration install/switch/repair flows, generated `.specify/config.json`, generated hook/settings assets, and generated shared scripts.
- Template wording propagates into every generated agent surface and template assertion tests.
- Lane registry semantics and reconcile rules propagate into root-level routing, workflow templates, feature-creation scripts, hook diagnostics, and generated documentation.
- Adaptive and mandatory dispatch vocabulary propagates into orchestration tests, generated workflow tests, integration tests, README/quickstart guidance, context scripts, and project-map docs.
- Workflow-handbook guidance now propagates from `templates/project-handbook-template.md`, workflow command templates, packet context helpers, and handbook-validation rules into initialized projects, map refresh helpers, and tests.
- Packet/result schema changes propagate into execution helpers, hooks, Codex team runtime, generated workflow prompts, and contract tests.
- Project cognition freshness changes propagate into the Go runtime, Python external-tool bridge, Bash/PowerShell scripts, hook commands, and brownfield gates.
- Engine packaging changes propagate through `pyproject.toml` force-includes, `extensions/agent-teams/engine/`, Codex team installer/runtime tests, and release artifacts.

## Change Impact Guide

- Change CLI command wiring or init behavior: read `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, and `modules/specify-cli-core/OVERVIEW.md`.
- Change an integration adapter: read `root/INTEGRATIONS.md`, `root/CONVENTIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- Change workflow templates or passive skills: read `root/WORKFLOWS.md`, `modules/templates-generated-surfaces/WORKFLOWS.md`, and template tests. For `sp-prd-scan -> sp-prd-build`, preserve the heavy reconstruction contract: repository-first current-state PRD extraction, subagent-mandatory substantive scans, `L4 Reconstruction-Ready` critical claims, `config-contracts.json` in the contract surface, `sp-prd-build` as scan-package compilation rather than a second repository scan, `sp-prd` compatibility-only routing, and no automatic planning handoff.
- Change hooks, packets, orchestration, or Codex team runtime: read `root/ARCHITECTURE.md`, `root/OPERATIONS.md`, and relevant module docs.
- Change packaging, CI, devcontainer, extension, or preset surfaces: read `root/STRUCTURE.md`, `root/INTEGRATIONS.md`, and `root/OPERATIONS.md`.
- Change launcher binding, generated runtime compatibility, or generated-project repair flows: read `root/OPERATIONS.md`, `root/INTEGRATIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.

## Verification Entry Points

- Focused project cognition regression: `cd tools/project-cognition && go test ./... && cd ../.. && pytest tests/test_project_map_freshness_scripts.py tests/contract/test_hook_cli_surface.py -q`
- Full Python regression: `uv run --extra test pytest -q -n auto`
- Integration surface: `pytest tests/integrations -q`
- Hooks/execution/orchestration: `pytest tests/hooks tests/execution tests/orchestration -q`
- Codex team runtime: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- spec-lint: `cd tools/spec-lint && go vet ./... && go build -o /dev/null .`
- project-cognition: `cd tools/project-cognition && go vet ./... && go build -o /dev/null .`
- Packaging sanity: `uv build`
- Bundled engine sanity: `npm --prefix extensions/agent-teams/engine run build`

## Known Unknowns

- External agent CLIs can change behavior outside this repository; adapter claims should be verified against upstream docs when external surfaces change.
- The Rust crates under `extensions/agent-teams/engine/crates/` were sampled for this atlas; run a targeted Rust packet before changing Rust runtime semantics.
- The global `specify` executable on a developer machine may lag this checkout. Prefer `PYTHONPATH=src; python -m specify_cli ...` or an editable install when validating local source behavior.

## Low-Confidence Areas

- `agent-teams-engine` Rust internals: Inferred from manifests, representative source, and tests rather than exhaustive source tracing.
- Release packaging beyond GitHub release creation: sampled from workflow files and `pyproject.toml`, but publishing details should be rechecked before changing distribution automation.
- Historical `.planning/**` artifacts are useful context but not always current product truth; `.planning/STATE.md` is the current planning status source.

## Atlas Views

- `templates/project-map/index/atlas-index.json`: machine-readable atlas summary and next-read routes for generated projects.
- `templates/project-map/index/modules.json`: module registry, owned roots, and module doc paths for generated projects.
- `templates/project-map/index/relations.json`: cross-module dependencies and shared-surface expansion routes for generated projects.
- Generated-project `.specify/project-cognition/status.json` plus the `project-cognition compass` task-local packet: freshness, module coverage, stale paths, and refresh metadata.
- `root/ARCHITECTURE.md`: cross-module architecture, contracts, dependency graph, capability cards.
- `root/STRUCTURE.md`: directory ownership, critical file families, placement rules.
- `root/CONVENTIONS.md`: naming, generated-surface, state, compatibility, and review conventions.
- `root/INTEGRATIONS.md`: supported agent adapters, external tool boundaries, MCP/runtime seams, security boundaries.
- `root/WORKFLOWS.md`: user and maintainer flows, state transitions, map/test/implement/debug behavior.
- `root/TESTING.md`: test layers, verification matrix, command selection.
- `root/OPERATIONS.md`: build, install, freshness, runtime state, recovery, troubleshooting.

## Where To Read Next

- Add or change workflow behavior: `root/WORKFLOWS.md`, then `modules/templates-generated-surfaces/WORKFLOWS.md`.
- Add or change an agent integration: `root/INTEGRATIONS.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change CLI internals: `modules/specify-cli-core/OVERVIEW.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change Codex team runtime or bundled engine: `modules/agent-teams-engine/OVERVIEW.md`, then `root/OPERATIONS.md`.
- Diagnose test failures: `root/TESTING.md`, then the module `TESTING.md` for the affected area.

## Topic Map

- `.specify/project-cognition/status.json` - default generated-project runtime status, freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` - canonical generated-project SQLite graph store
- `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` bundle - default generated-project route to readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; agents use those paths as first evidence, not final edit scope
- `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan` (`lexicon -> semantic_intake -> query`) - advanced route when compass needs explicit concept decisions or coverage escalation
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- `templates/project-map/**` is retained only for legacy compatibility review and must not be installed or required by new generated projects.

## Update Triggers

- CLI command registration, generated workflow names, integration directories, packet/result schemas, hook events, testing workflow state, project-map compatibility/export rules, extension/preset schemas, packaging force-includes, or Codex team runtime installation assumptions change.

## Recent Structural Changes

- The runtime atlas is being rewritten around `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, default `project-cognition compass` navigation packets, and advanced agent-planned `project-cognition lexicon --mode catalog` -> `semantic_intake` -> `project-cognition query --query-plan` task-local bundles.
- Ordinary `sp-*` workflows should treat project cognition consumption as advisory navigation before source-level work.
- Supporting handbook artifacts remain available as compatibility/export surfaces, but are no longer the primary evidence path.
