# Workflow and Runtime Maintenance

Read before changing workflow behavior, state/artifact ownership, runtime or
cognition contracts, hooks, install/launcher behavior, or release distribution.
Use the matching sections after reading the shared change rules. Code paths
below are relative to the repository root. This guide maintains the product;
it does not activate a generated workflow or authorize a release.

## Workflow Change Surface Index

Keep repository maintenance guidance here or in the unmanaged portion of
`AGENTS.md`. The shared Bash and PowerShell context renderers own the managed
`<!-- SPEC-KIT:BEGIN -->` block.

### Non-Negotiable Rule

- Never change only `templates/commands/<workflow>.md` and assume the workflow is done.
- In this repository, generated `sp-*` workflows are usually the thing being built and tested, not the workflow contract that governs editing this source tree.
- For every `sp-*` or `spx-*` workflow change, sweep `templates/`, `src/`, `scripts/`, `tests/`, `README.md`, `PROJECT-HANDBOOK.md`, `pyproject.toml`, and `.github/workflows/`.
- Minimum repo search before editing: `rg -n "sp-<name>|spx-<name>|<name>" templates src scripts tests README.md PROJECT-HANDBOOK.md .github pyproject.toml`.
- If a workflow reads or writes state artifacts, update the artifact templates, runtime helpers, hook checks, and tests in the same pass.
- If a change affects wording or behavior across generated projects, treat it as a `specify init` surface change, not as a local template-only edit.

### Shared Surfaces That Commonly Propagate Across All `sp-*` Workflows

- Command templates: `templates/commands/*.md`
- Shared command partials and shared hook insertion points: `templates/command-partials/**`, especially `templates/command-partials/common/**`
- Passive support-skill mirrors: `templates/passive-skills/**`, especially `spec-kit-project-cognition-gate`, `subagent-driven-development`, `test-driven-development`, `tdd-workflow`, `verification-before-completion`, and `dispatching-parallel-agents`
- Worker prompts used by delegated execution lanes: `templates/worker-prompts/*.md`
- CLI registration, aliases, state routing, and generated-command help: `src/specify_cli/__init__.py`, `src/specify_cli/agents.py`, `src/specify_cli/workflow_markers.py`, `src/specify_cli/launcher.py`
- Integration rendering and generated asset installation: `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/**`
- Hook runtime and shared hook shims: `src/specify_cli/hooks/**`, `src/specify_cli/shared_hooks/specify-hook*`, `src/specify_cli/integrations/claude/hooks/**`, and `src/specify_cli/integrations/gemini/hooks/**`
- Shared generated scripts: `scripts/bash/*.sh` and `scripts/powershell/*.ps1`
- Packaged init assets: `pyproject.toml` force-includes for `templates/commands`, `templates/command-partials`, `templates/passive-skills`, `templates/worker-prompts`, and related `.specify/templates/**` content
- User/operator docs: `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`
- Core regression families: `tests/test_alignment_templates.py`, `tests/integrations/**`, `tests/contract/**`, and `tests/hooks/**`

### Install, Generated Asset, Hook, and CLI Surfaces

- `specify init` and integration install behavior lives in `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`, `src/specify_cli/integrations/**`, `src/specify_cli/agents.py`, and `src/specify_cli/launcher.py`.
- Shared generated assets copied into downstream projects come from `templates/commands/**`, `templates/command-partials/**`, `templates/passive-skills/**`, `templates/worker-prompts/**`, `templates/project-map/**`, `scripts/bash/**`, `scripts/powershell/**`, and `templates/vscode-settings.json`.
- Hook-aware integrations must keep their dispatch maps in sync with workflow names and aliases, especially `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py` and `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`.
- Thin integration wrappers under `src/specify_cli/integrations/*/scripts/update-context.*` delegate to the shared `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1`; if guidance or agent coverage changes, update both layers.
- If AGENTS-level guidance changes should ship into generated projects, update the managed block renderers inside `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1`. Keep custom repository-only maintenance notes in this unmanaged section.
- Release/install/documentation surfaces that can drift from workflow reality are `README.md`, `.github/workflows/release.yml`, `.github/workflows/release-trigger.yml`, and `.github/workflows/release-specify-runtime.yml`.

### Specify Runtime Distribution

- `tools/specify-runtime/` is the standalone Go runtime used by every generated Classic `sp-*`, Advanced `spx-*`, and worker surface for fixed workflow artifact access, deterministic `plan-contract`/`quick-status` scaffolds, tiered spec validation, workflow state, and project cognition. It is a user-facing binary, not a Python `specify` subcommand.
- The primary `.github/workflows/release.yml` flow cross-compiles and publishes runtime assets to the separate public distribution repository through `scripts/publish-runtime-release.py`; `.github/workflows/release-specify-runtime.yml` is only a fallback for externally created source-repository releases. Follow the public release checklist below.
- Any specify-runtime update that changes user-visible behavior, command names, flags, output contracts, install/runtime compatibility checks, or generated-workflow expectations must ship with a new GitHub release before it is considered distributed. Do not leave these changes only on `main`: trigger the release flow, publish fresh `specify-runtime-*` assets, and verify the latest release binary reports the new version and exposes the expected commands/flags.
- `tools/specify-runtime/install.sh` and `tools/specify-runtime/install.ps1` must download the matching prebuilt release binary by default, verify `api handshake`, and smoke-test the namespaced cognition command surface.
- `specify init` must best-effort auto-download/cache the prebuilt binary, then persist the resolved executable in `.specify/config.json` under `runtime_launcher` so generated command templates invoke the pinned binary path instead of relying only on PATH.
- If init cannot download the binary, it must not fail project initialization; print a clear install warning. Generated commands retain the stable project-local launcher path. `SPECIFY_RUNTIME_BIN` is a bootstrap override, not a generated-command fallback; preserve the installer and launcher recovery contract.
- Project-cognition outputs intended for agent consumption should default to minimal stdout and compact temporary files that contain only the next-step data needed, such as a file list path and count or the file list itself. Detailed exclusion reasons, scan explanations, and audit metadata belong behind explicit explain/debug modes.
- `specify-runtime cognition scan-set` is the runtime-owned scan-set resolution contract for agent-facing file-list handoffs; do not replace it with prompt-only guidance that asks agents to freely decide which files to skip.
- When changing project-cognition command names, flags, binary names, release assets, or install behavior, update `src/specify_cli/specify_runtime.py`, `src/specify_cli/launcher.py`, the install scripts, release workflows, README/docs, and the init/launcher regression tests in the same pass, then publish and verify the release assets in the same workstream.

#### Public Runtime Release Checklist

Before any runtime release, read
[Runtime Release Distribution](../runtime-release-distribution.md).
These are repository maintenance instructions, not generated-project rules;
keep them outside the managed `<!-- SPEC-KIT:BEGIN -->` block.

- **Separate source and distribution.** Keep `chenziyang110/spec-kit-plus`
  private. Publish binaries to
  [chenziyang110/spec-kit-plus-releases](https://github.com/chenziyang110/spec-kit-plus-releases/releases).
  Never make the source repository public, push its Git history to the public
  repository, or upload source archives, private commit messages, logs, or
  credentials. The public repository's landing document comes from
  `templates/runtime-distribution/README.md`; retain the existing LICENSE.
- **Publish exactly six assets:** `specify-runtime-linux-amd64`,
  `specify-runtime-linux-arm64`, `specify-runtime-darwin-amd64`,
  `specify-runtime-darwin-arm64`, `specify-runtime-windows-amd64.exe`, and
  `SHA256SUMS`. Do not upload an entire build directory with an unchecked glob.
- **Bind the version to source.** Use a new concrete release tag, the matching
  CLI version in `pyproject.toml`, and a clean snapshot of that source tag's
  commit. The binary must report that version and source revision, the current
  protocol, every required capability, and `dirty=false`. The source revision
  is the private source tag's commit, not the public README repository's commit.
  Never move an existing tag or replace it with a different source revision.
- **Check automation prerequisites first.** The private workflows require
  `PUBLIC_RELEASES_TOKEN`, a fine-grained token with Contents read/write access
  to only `spec-kit-plus-releases`. Store it in the private repository's Actions
  secrets; never put its value in chat, argv, files, or Git. The built-in
  `GITHUB_TOKEN` cannot publish across repositories. Source checkout must remain
  `contents: read` with `persist-credentials: false`. Do not persist a broad
  personal CLI login token as the publishing secret.
- **Use the owning workflow and helper.** `release-trigger.yml` owns the private
  source tag/version sequence; `release.yml` owns the normal build/publication.
  Both publication workflows use `scripts/publish-runtime-release.py` with
  `--target-repo chenziyang110/spec-kit-plus-releases`, `--tag`,
  `--source-revision`, `--assets-dir`, and `--token-env PUBLIC_RELEASES_TOKEN`.
  Run `--mode check` before `--mode ensure-release`. The helper generates
  SHA256SUMS and fixed public notes, verifies existing assets, uploads a draft,
  and publishes only after verification. Do not use automatic notes derived
  from private Git history.
- **Recover without weakening publication checks.** If cloud Actions cannot
  start because of billing, spending limits, or missing credentials, report
  that exact blocker. An authorized local publication may use a clean source
  snapshot, the same build identity and helper, and credentials only in memory.
  Do not rely on previous session scripts or binaries under `dist/`. For an
  interrupted upload, inspect the existing draft and rerun the helper with the
  same tag/source revision only when its checks permit recovery. Never expose
  a partial draft or bypass an extra-asset, checksum, or revision rejection.
- **Verify the public consumer path.** Check the public release is no longer a
  draft and has exactly the six assets. Download the Windows binary and
  SHA256SUMS without authentication, compare the checksum, and run `version`
  and `api handshake`. Run `specify init` in an isolated project with an empty
  runtime cache and no runtime override or download token; require the public
  URL, successful project-local pinning, and no source-build fallback. Keep
  Python/PowerShell/Bash download defaults pointed at the public repository.
  CLI installation from the private Git source still requires source access.
- **Keep completion claims separate.** Local tests, cross-platform builds,
  native execution checks, cloud CI, public publication, and anonymous init
  verification are distinct evidence. Never claim cloud automation works just
  because a one-off local release succeeded.

Historical setup checkpoint: on 2026-08-31, `v0.6.24` was publicly published and
anonymous empty-cache initialization passed. At that time, GitHub Actions jobs
were blocked by account billing/spending limits and `PUBLIC_RELEASES_TOKEN` was
not configured. Recheck both conditions before the next release; do not treat
this historical note as a permanent or current status assertion.

### Project Cognition Schema v5 Maintenance

- Cognition closeout must reject malformed or failed verification before writing
  a pending intent. Recover older invalid verification through runtime-owned
  `cognition closeout inspect` and its exact digest-bound repair/replay argv;
  never edit/delete pending intent JSON, fabricate passing evidence, or rebuild
  a usable map merely to bypass a bad input. A verification repair is not graph
  readiness, and already committed intents must not be resubmitted after a
  graph generation changes.

- Schema v5 runtime readiness is graph, alias, and revision-bound typed graph-claim reconciliation first. The active runtime tables are `metadata`, `generations`, `evidence`, `nodes`, `node_evidence`, `edges`, `edge_evidence`, `observations`, `observation_evidence`, `path_index`, `alias_index`, `claims`, `claim_evidence`, `claim_verifications`, `claim_transitions`, `claim_reconciliations`, and `updates`.
- Schema v5 adds claim revisions to the auditable reconciliation record and current/superseded claim-evidence basis. Agents supply semantic reconciliation intent only; the runtime owns contract versions, generation/state/revision preconditions, time bounds, source kinds, hashes, repository snapshots, IDs, prepared packet paths, and `apply_argv`. Do not reintroduce old broad-schema tables such as `conflicts`, `conflict_claims`, `symbol_index`, `entrypoint_index`, `test_index`, `slice_members`, FTS tables, or `query_examples` as readiness requirements unless a deliberate design, runtime implementation, prompt update, and regression suite add them back together.
- Graph claims are indexed assertions, use `graph_claim_type`, and have compiler-derived `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale` states. They never authorize source changes or set workflow `claim_ready=true`.
- `alias_index` is the route vocabulary. `specify-runtime cognition lexicon --mode catalog` lists alias-backed candidates; the agent must normalize the user's prompt into project vocabulary, record `semantic_intake`, carry `lexicon_generation_id`, and call `specify-runtime cognition query --query-plan`. Top lexical or vector similarity alone is not route truth; live repository evidence still proves technical claims.
- Schema v5 is current-only. v1 through v4 and old broad-schema DBs are diagnostic/inspect-only for normal workflows; `lexicon`, `query`, `claim-reconcile`, and `build-from-scan` require the complete current schema. The current runtime does not migrate schema v4 or older databases. Never move, remove, archive, or replace `project-cognition.db` directly. Run `specify-runtime cognition archive-incompatible-store --inspect --format json`, execute its hash-guarded `archive_argv`, then run `sp-map-scan -> sp-map-build` with the current binary.
- Alias derivation should stay bounded: titles, types, paths, and bounded attrs/tags are valid sources; raw observation summaries should not become unbounded aliases.

### Workflow Family Map

The Python `specify` CLI owns bootstrap/operator compatibility; the Go
`specify-runtime` owns generated workflow artifact/state mutation and cognition.
Python paths below include installation, compatibility, rendering, and hook
consumers; their presence does not authorize Python workflow-mutation commands.
Use live runtime capabilities and current source evidence to confirm ownership.

- `sp-specify`, `sp-deep-research`, `sp-plan`, `sp-tasks`, `sp-analyze`
  - Templates: `templates/commands/{specify,deep-research,plan,tasks,analyze}.md`, `templates/command-partials/{specify,deep-research,plan,tasks,analyze}/shell.md`, and `templates/workflow-state-template.md`
  - Feature artifacts: `workflow-state.md`, `alignment.md`, `context.md`, runtime-owned `research/{state,track-manifest,handoffs,rejections,synthesis,audit-request,audit,handoff-to-plan}.json`, runtime-owned `research-evidence/`, derived `deep-research.md`, `research-spikes/`, `plan.md`, and `tasks.md`
  - Runtime/code: `tools/specify-runtime/deep_research_workflow.go`, `tools/specify-runtime/artifact_registry.go`, `tools/specify-runtime/result.go`, `src/specify_cli/__init__.py`, `src/specify_cli/agents.py`, `src/specify_cli/learnings.py`, and `src/specify_cli/hooks/artifact_validation.py`
  - Tests/docs: `tools/specify-runtime/deep_research_workflow_test.go`, `tests/test_deep_research_runtime_contract.py`, `tests/test_alignment_templates.py`, `tests/test_plan_research_contract.py`, `tests/test_specify_guidance_docs.py`, `tests/test_tasks_reporting_guidance.py`, `README.md`, and `PROJECT-HANDBOOK.md`

- `sp-fast`, `sp-quick`, `sp-implement`, `sp-debug`
  - Templates: `templates/commands/{fast,quick,implement,debug}.md` and `templates/command-partials/{fast,quick,implement,debug}/shell.md`
  - Delegation prompts: `templates/worker-prompts/{quick-worker,implementer,debug-investigator,debug-thinker,code-quality-reviewer,spec-reviewer}.md`
  - Runtime/code: `src/specify_cli/__init__.py`, `src/specify_cli/debug/**`, `src/specify_cli/execution/**`, `src/specify_cli/orchestration/**`, and `src/specify_cli/hooks/{delegation,checkpoint,learning,project_map,workflow_policy}.py`
  - State/scripts: `scripts/bash/{quick-state,check-prerequisites}.sh`, `scripts/powershell/{quick-state,check-prerequisites}.ps1`, and normalized result handoff logic in `src/specify_cli/execution/`
  - Tests/docs: `tests/test_quick_*`, `tests/test_fast_template_guidance.py`, `tests/test_debug_*`, `tests/execution/test_result_handoff.py`, `tests/orchestration/test_policy.py`, `tests/orchestration/test_task_contract_validation.py`, and `README.md`

- `sp-map-scan`, `sp-map-build`
  - Templates: `templates/commands/{map-scan,map-build}.md`, `templates/command-partials/{map-scan,map-build}/shell.md`, `templates/project-handbook-template.md`, `templates/project-map/**`, `templates/project-map/index/*.json`, `templates/project-map/root/*.md`, `templates/project-map/modules/**/*.md`, and `templates/project-map/map-state-template.md`
  - Runtime/code: `tools/specify-runtime/**`, `src/specify_cli/specify_runtime.py`, `src/specify_cli/project_map_status.py`, project-cognition preflight/commands inside `src/specify_cli/__init__.py`, `src/specify_cli/launcher.py`, and `src/specify_cli/hooks/project_map.py`
  - Shared scripts: `scripts/bash/project-cognition-freshness.sh` and `scripts/powershell/project-cognition-freshness.ps1`
  - Tests/docs: `tests/test_map_scan_build_template_guidance.py`, `tests/test_map_runtime_template_guidance.py`, `tests/test_project_cognition_runtime_install.py`, `tests/test_runtime_handbook_contract.py`, `tests/test_project_map_*`, `tests/hooks/test_project_map_hooks.py`, `tests/test_project_handbook_templates.py`, `PROJECT-HANDBOOK.md`, and `templates/project-map/QUICK-NAV.md`

- `sp-prd-scan`, `sp-prd-build`, `sp-constitution`, `sp-checklist`, and `sp-auto`
  - Templates: `templates/commands/{prd-scan,prd-build,constitution,checklist,auto}.md`, matching `templates/command-partials/**`, and `templates/workflow-state-template.md`
  - Runtime/code: `scripts/bash/prd-state.sh`, `scripts/powershell/prd-state.ps1`, `src/specify_cli/__init__.py` auto entrypoints, and launcher/learning helpers when state routing changes
  - Tests/docs: `tests/test_prd_hook_contract.py`, `tests/contract/test_hook_cli_surface.py`, `tests/test_launcher.py`, `tests/test_alignment_templates.py`, and `README.md`

- Cross-workflow Work Board and execution ownership
  - Runtime/code: `tools/specify-runtime/work_board.go`, `tools/specify-runtime/execution_control.go`, and `tools/specify-runtime/internal/runcontrol/**`
  - Contract: Work Board + execution is the default current-worktree path. Fast/Debug/Implement/Quick use one Work/Activity, packet-integrity announce when applicable, selected checkpoint, fresh overview, atomic guard, and completion only after fresh validation plus terminal workflow state. Packet announce derives the full planned union of unchanged product scope and exact compiler-owned bookkeeping scope; guard that returned set and serialize overlapping metadata ownership. Completion audits the product and canonical workflow Git delta, including declared workflow-state artifact paths. Only narrowly identified private runtime receipt/transaction cache bytes may be excluded; canonical feature/design/memory and `.planning` artifacts remain audited, Work recovery inspections remain unchanged, and no agent-authored file bypass is allowed. Other modifying workflows retain precise Work scope and artifact/state-owner guards; do not invent Activity workflow values. Feature bootstrap is dry-run -> board reconcile/show -> one board feature-bootstrap -> real script with the same id and returned branch policy. Native agent tools own manual workers; no automatic branch, merge, or publish occurs. Preserve Review -> human Accept and existing external-mutation approval gates.
  - Retirement: Run is removed from active workflow routing; its records are inert preserved history only. Existing worktrees, branches, and edits remain preserved. Live/recovery-held Work stays active until reconciliation or explicit resolution. Safe additive metadata schema evolution is allowed; never delete or rewrite historical records or automatically clean up worktrees.
  - Tests/docs: `tools/specify-runtime/internal/runcontrol/**/*_test.go`, `tests/test_run_control_workflow_routing.py`, `tests/test_feature_lane_retirement.py`, `tests/test_execution_overview_guidance.py`, `tests/test_execution_control_plane_guidance.py`, `README.md`, and `PROJECT-HANDBOOK.md`

- `sp-do` and `spx-do` repeatable project operations
  - Templates: `templates/commands/do.md`, `templates/command-partials/do/**`, `templates/command-references/do/**`, `templates/advanced-skills/spx-do/**`, and `templates/artifacts/{do-*,playbook-*}.json`
  - Runtime/code: `tools/specify-runtime/do*.go`, `tools/specify-runtime/playbook*.go`, `tools/specify-runtime/learning_do.go`, shared Work/cognition closeout owners, `src/specify_cli/launcher.py`, and Claude/Gemini native hook dispatchers
  - Contract: native tools execute commands; the runtime freezes definitions, binds observations and current evidence, and publishes immutable verified method revisions. Recover every interruption, including optional or superseded attempts. Knowledge retry does not rerun passed execution. Retained source changes require exact session/epoch-bound canonical `sp-do` cognition closeout; preserve Do-before-Learning/cognition lock ordering and Work ownership through writes.
  - State: `.specify/do/sessions/<id>/**` and `.specify/playbooks/**` are specialized runtime-owned artifacts preserved by additive installation and repair. Do adds no formal stage or Activity.
  - Tests/docs: `tools/specify-runtime/do*_test.go`, `tools/specify-runtime/playbook*_test.go`, `tools/specify-runtime/learning_do*_test.go`, `tests/integrations/test_do_installation.py`, `tests/test_do_{hooks,launcher,operation_probe}.py`, and `docs/sp-do.md`

- `sp-teams` and `sp-implement-teams` (Codex-only durable execution surfaces)
  - Templates: `templates/commands/{team,implement-teams}.md`, `templates/command-partials/{team,implement-teams}/shell.md`, and `src/specify_cli/integrations/claude/templates/implement-teams.md`
  - Runtime/code: `src/specify_cli/codex_team/**`, `src/specify_cli/mcp/**`, `src/specify_cli/__init__.py` `teams_app`, and `extensions/agent-teams/engine/**`
  - Scripts/config: `scripts/bash/sync-ecc-to-codex.sh`, `scripts/powershell/sync-ecc-to-codex.ps1`, `.codex/config.toml` assumptions, and runtime state under `.specify/teams/`
  - Tests/docs: `tests/codex_team/**`, `tests/contract/test_codex_team_*`, `tests/test_teams_mcp_server.py`, `README.md`, and `PROJECT-HANDBOOK.md`

### Per-Change Checklist

- Update the workflow command template and every referenced partial or included prompt.
- Check whether `src/specify_cli/__init__.py` CLI routing, aliases, or help text now disagree with the template behavior.
- Check whether `src/specify_cli/agents.py` invocation rewriting or skills-backed syntax needs to change.
- Check whether `src/specify_cli/integrations/base.py` or a specific integration override injects workflow-specific guidance that now drifted.
- Check whether hook dispatch maps, shared hook logic, or generated wrapper scripts encode the workflow name or assumptions.
- Check whether packaged assets in `pyproject.toml` still include every new template/script/prompt you introduced.
- Check whether `README.md`, `PROJECT-HANDBOOK.md`, or `templates/project-handbook-template.md` teach outdated behavior.
- Run or update the narrowest relevant test families before treating the workflow change as complete.
