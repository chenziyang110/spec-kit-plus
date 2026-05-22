# Spec Kit Plus

`spec-kit-plus` is a maintained fork of Spec Kit focused on practical Spec-Driven Development workflow support for local AI coding agents.

`specify` is the public entrypoint for requirement discovery. Internally it runs
the brainstorming lock flow, persists facts, route, and intent truth, and hands
structured handoff context to `sp-implement` and later workflow stages.

This repository contains:

- the `specify` CLI
- built-in spec, plan, tasks, and implement templates
- agent integrations for tools such as Codex, Claude, Gemini, Copilot, Cursor, Windsurf, Kimi, Forge, and others
- the bundled scripts and assets used by `specify init`

## Install

### Persistent install from this fork

Install the CLI from this repository:

```bash
uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

Upgrade to the latest version from this fork. If a machine previously installed
`specify-cli` through `pip`, Conda, or another `uv tool` location, remove the old
entry first so a stale `specify.exe` does not shadow the new one:

```powershell
python -m pip uninstall -y specify-cli
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
Get-Command specify -All
specify --help
```

`specify version` reports the package version, but development installs can share
the same `0.5.1.dev0` version string across commits. Use `specify --help` to
confirm newly added commands such as `testing` are present, and use
`Get-Command specify -All` on Windows to detect duplicate old entrypoints.
Feature creation follows `sp-specify` plus the generated create-feature script
at `.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`; do not assume a separate
`specify create-feature` command family exists.

### One-time use without installing

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init my-project --ai codex
```

Initialize the current directory with the latest fork version, without relying on whatever `specify` is currently on your `PATH`:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init . --ai codex
```

### Local editable install for development

```bash
git clone https://github.com/chenziyang110/spec-kit-plus.git
cd spec-kit-plus
uv pip install -e .
```

## Prerequisites

- Python 3.11+
- `uv`
- `git`
- your target AI agent CLI or IDE integration

## Quick Start

Create a new project:

```bash
specify init my-project --ai codex
```

Use a non-default built-in constitution profile when the repo needs a different
governance default:

```bash
specify init my-project --ai claude --constitution-profile library
```

Initialize the current directory:

```bash
specify init --here --ai codex
```

If the current directory is not empty:

```bash
specify init --here --force --ai codex
```

Generated projects may also persist a trusted project launcher in
`.specify/config.json` under `specify_launcher`. When that launcher exists,
first-party runtime helper instructions should follow it instead of assuming the
first `specify` executable on PATH is the correct one.

Validate generated-project runtime health and repair stale generated assets:

```bash
specify check
specify integration repair
```

`specify check` now reports:

- missing or broken persisted project launchers
- stale generated PowerShell workflow scripts that still rely on exact branch-to-feature-dir matching
- stale Claude hook commands that still use shell-parsed direct Python, POSIX, cmd, or PowerShell-style launchers instead of the shell-free Node launcher

`specify integration repair` refreshes shared/runtime-managed generated assets in place
without overwriting user-edited workflow or skill content.

Validate the installation:

```bash
specify --help
specify check
```

## Common Agent Examples

Codex:

```bash
specify init my-project --ai codex
```

Claude:

```bash
specify init my-project --ai claude
```

Claude project-local installs now write `.claude/skills/` as before and also
install thin native hook adapters under `.claude/hooks/`. When
`.claude/settings.json` is absent, it is created; when it already exists and is
valid JSON, managed hook registrations are merged without overwriting unrelated
user settings.

If a generated Claude project on Windows still has stale hook commands, run:

```bash
specify integration repair --script ps
```

Gemini:

```bash
specify init my-project --ai gemini
```

Copilot:

```bash
specify init my-project --ai copilot
```

Cursor:

```bash
specify init my-project --ai cursor-agent
```

If you want templates without checking whether the agent tool is installed:

```bash
specify init my-project --ai codex --ignore-agent-tools
```

## Workflow

After `specify init`, use the generated workflow commands in your agent:

1. `constitution` to establish or revise project principles when the seeded default constitution needs project-specific changes
2. `specify` to produce a planning-ready, analysis-first feature spec
3. `plan` to define implementation design
4. `tasks` to break work into executable tasks
5. `implement` to execute the task plan
6. `auto` to resume the recommended next workflow step from current repository state when you do not want to name the exact command yourself
7. `integrate` to close out completed independent feature lanes before mainline merge

Use `discussion` before `specify` when the idea is exploratory, has product trade-offs, or has unclear context boundaries. `discussion` classifies each turn, answers repository-discoverable facts from live evidence, uses project cognition only as advisory navigation toward minimal live reads, appends compact ordinary-turn events, and refreshes structured artifacts only at semantic checkpoints. It runs a Context Boundary Gate before technicalizing unclear target/reference/external/evidence boundaries, drafts one unified handoff pair only after explicit handoff request and boundary lock, and marks that pair handoff-ready only after self-review and user confirmation.

Generated workflows preserve the user's confirmed product scope. Scope reduction requires user confirmation: agents should not steer a requirement toward an MVP, pilot, prototype, first-story release, or smaller validation build unless the user asked for that shape, the request already defines that boundary, or a named constraint makes reduced scope a decision the user confirms.

For cross-project work, current project cognition cannot prove another project's files. Lock the target project root and record whether target evidence comes from target cognition, minimal live reads, user confirmation, external source, or explicit assumptions.

For an existing repository that needs product documentation rather than a new
change spec, use `prd-scan -> prd-build` as the canonical heavy reconstruction
PRD lane. It extracts repository-first current-state PRD evidence from
implementation reality and compiles a reconstruction archive with two reader
entry layers: `exports/README.md` as the package navigation entry and
`exports/prd.md` as the primary reader-facing PRD. It is a peer workflow path
to `specify` and does not automatically hand off to `plan`.
`prd` remains as a deprecated compatibility entrypoint only.

Built-in constitution profiles:

- `product` (default) for application and service repos
- `minimal` for lean, low-ceremony repos
- `library` for packages, SDKs, and CLIs with compatibility concerns
- `regulated` for security, privacy, or audit-heavy repos

Profile details and selection guidance live in [docs/constitution-profiles.md](docs/constitution-profiles.md).

Mainline pre-planning flow:

```text
specify -> plan
```

Feature creation is driven by the `specify` workflow itself. `sp-specify` now
uses a collaborative reviewed specification flow: explore project context,
ask one question at a time, decompose semantic terms, present two or three
approaches, write the artifact package, self-review it, and ask for user review
before planning. Use `sp-specify` with the generated create-feature script at
`.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`, plus the lane/runtime
helpers that it invokes; do not look for or teach a separate branch-creation
CLI family.

`specify` remains the public entry shell and writes `spec.md`, `alignment.md`,
`context.md`, `workflow-state.md`, `checklists/requirements.md`, and a minimal
compatibility `brainstorming/handoff-to-specify.json`. When a feature starts
from `sp-discussion`, `sp-specify` reads the discussion source files, including
`discussion-log.md`, `requirements.md`, and `open-questions.md`, not only the
handoff summary. Capability-like upstream signals must appear in
`source_signal_disposition`. `alignment.md` records `Semantic Term Decisions`,
`Upstream Intent Disposition`, and `Out-Of-Scope Conflicts`; ambiguous product terms such as "real",
"capability", "usable", fetch, probe, model, endpoint, `能力`, `真实`, and
`可用` must be decomposed before scope is narrowed.

The normal next step remains exactly one of `/sp.plan`, `/sp.clarify`, or
`/sp.deep-research`. `/sp.plan` is valid only after the written artifacts pass
self-review and user review has been requested.

Treat the live `specify --help` output as the only authoritative CLI command
surface. Before suggesting or running a `specify <subcommand>` invocation,
verify it exists in `specify --help` or `specify <subcommand> --help`, and do
not invent unsupported names such as `specify create-feature`.

Optional feasibility branch when `sp-specify` finds an unproven implementation chain:

```text
specify -> deep-research -> plan
```

### Workflow invocation syntax

Canonical workflow names are integration-neutral: `constitution`, `specify`,
`plan`, `tasks`, `implement`, `analyze`, and the other workflow names below are
the stable concepts used in docs, workflow state, and generated artifacts. The
text a user types in their AI agent depends on the integration.

Invocation syntax depends on the integration:

| Integration surface | Example: specify | Example: prd-scan -> prd-build | Example: plan | Notes |
| --- | --- | --- | --- | --- |
| Codex skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Skills-backed Codex projects use `$sp-*`. |
| Antigravity skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Antigravity projects install workflow skills under `.agents/skills`. |
| Kimi Code skills | `/skill:sp-specify` | `/skill:sp-prd-scan -> /skill:sp-prd-build` | `/skill:sp-plan` | Kimi exposes generated skills through `/skill:sp-*`. |
| Claude skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Claude keeps slash-style skill commands. |
| Cursor skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Cursor projects install workflow skills under `.cursor/skills` and keep `.cursor/rules/` for context files. |
| Trae skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Trae projects install workflow skills under `.trae/skills` and keep `.trae/rules/project_rules.md` as context. |
| Mistral Vibe skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Vibe projects install workflow skills under `.vibe/skills`. |
| Slash-dot command integrations | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | Gemini, Copilot, Windsurf, Forge, and similar command/prompt integrations use slash-dot examples unless their native UI documents a different launcher. |

`/sp-*` is not universal for skills-backed integrations. When these docs say to
run the canonical workflow `plan`, use the invocation form generated for your
selected integration, for example `$sp-plan` in Codex or `/skill:sp-plan` in
Kimi.

Skill map after `specify init`:

- Core workflow skills: `constitution`, `specify`, `plan`, `tasks`, `implement`
- Support skills: `map-scan`, `map-build`, `map-update`, `auto`, `discussion`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `clarify`, `deep-research` (`research` alias), `checklist`, `analyze`, `debug`, `explain`
- Codex-only runtime: `sp-teams`

Conditional gates and follow-up commands:

- Generated projects use `.specify/project-cognition/status.json` plus the agent-planned task-local project cognition query bundle as the advisory project cognition index. `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries, not evidence by itself.
- New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, `project-cognition lexicon`, and `project-cognition query --query-plan` as advisory navigation inputs. `templates/project-map/**` remains a historical compatibility/export surface for handbook generation, but new workflows should not read or require `.specify/project-map/**`.
- Releases publish prebuilt `project-cognition` binaries for Windows, Linux, and macOS. `specify init` best-effort downloads and pins the matching binary in `.specify/config.json`; if that cannot happen, install via `tools/project-cognition/install.sh` or `tools/project-cognition/install.ps1`, or set `PROJECT_COGNITION_BIN` to a custom binary path.
- Use `map-update` for localized stale cognition refresh recommendations, ordinary changed-path map maintenance, and ordinary existing-baseline gaps; use `map-scan` followed by `map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is map-maintenance complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`.
- Recorded refresh and ready refresh are different outcomes: refresh commands may write update metadata, then still report `partial_refresh` when the shared freshness contract says runtime readiness remains blocked.
- Readiness diagnostics such as `recommended_next_action`, `needs_update`, and `needs_rebuild` remain available to explain map quality and suggested map-maintenance follow-up, but ordinary workflows must treat them as advisory and apply the map-update-first routing policy.
- Project cognition respects `.cognitionignore` at the repository root and `.specify/project-cognition/.cognitionignore`. The syntax is gitignore-compatible and applies to `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`.
- When using another local directory as a reference, check whether that directory
  or its children contain `.specify/` before broad source reads. Run
  `project-cognition discover --root <path> --format json`; use reference cognition only
  when `.specify/project-cognition/status.json` and
  `.specify/project-cognition/project-cognition.db` exist,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true. If the reference is blocked, stale, or incomplete, do not treat legacy
  `.specify/project-map/**` outputs as current truth; fall back to minimal live
  reads and recommend `map-update` for localized stale or weak reference
  coverage after a usable baseline. If the reference baseline is missing or
  unusable, recommend `map-scan -> map-build` only for first/missing/unusable
  baseline, schema failure, zero active-generation `path_index` rows,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Support drift is not runtime-truth staleness. When `freshness` is `support_drift`, resolve or ignore the support-surface change instead of reflexively routing to `map-update`.
- Map points, code proves: technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
- `specify`, `clarify`, `deep-research`, `plan`, and `tasks` do not directly rewrite project cognition content; when they discover the current cognition runtime is too weak or likely outdated for the touched area, they should use `map-update` for changed-path refresh. Uncertain closure is recorded by `map-update` as partial/low-confidence facts when needed. Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- `auto` to resume the recommended next workflow step from current repository state; it reads canonical state surfaces such as `workflow-state.md`, `implement-tracker.md`, quick-task `STATUS.md`, and debug session files, then continues under the routed workflow's contract without rewriting downstream `next_command` to `sp-auto`
- when concurrent feature lanes exist, `auto` should prefer lane registry plus reconcile over branch-only recency and should only auto-resume when exactly one safe candidate remains
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It classifies each turn, answers repository-discoverable facts from live evidence, uses project cognition only as advisory navigation toward minimal live reads, appends compact ordinary-turn events, and refreshes structured artifacts only at semantic checkpoints. It writes `.specify/discussions/<slug>/` artifacts, runs the Context Boundary Gate before technicalizing unclear target/reference/external/evidence boundaries, and creates exactly one draft unified handoff pair: `handoff-to-specify.md` plus `handoff-to-specify.json` only after explicit handoff request and boundary lock. The pair becomes handoff-ready only after self-review and user confirmation. The handoff includes `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger. It does not automatically invoke `specify`.
- `prd-scan` followed by `prd-build` to reverse-extract a repository-first current-state PRD reconstruction archive from an existing project. Substantive `prd-scan` runs are subagent-mandatory and read implementation reality, docs, tests, routes, UI/API surfaces, project cognition evidence, and memory files into `.specify/prd-runs/<run-id>/`; critical reconstruction claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. `prd-build` compiles from the scan package into the expanded archive, including config/protocol/state/error/verification/risk exports. The exported suite includes `exports/README.md` as the package navigation entry and `exports/prd.md` as the main reader-facing PRD, and `prd-build` must not perform a second repository scan. `prd` remains a deprecated compatibility entrypoint that should route into the same pair.
- `clarify` to deepen an existing spec before planning when analysis, references, or gaps need more work
- `deep-research` to coordinate focused feasibility research, optional multi-agent evidence gathering, and disposable demos before planning when requirements are clear but a capability still lacks a credible implementation chain; it writes a traceable `Planning Handoff` with evidence IDs for `plan` and should be skipped for minor tweaks to already-proven project behavior. `research` is a compatibility alias for this same gate and must not create separate workflow artifacts
- `checklist` to generate requirement-quality checklists after planning so the written requirements can be audited before implementation
- `analyze` is an optional read-only diagnostic and legacy revalidation pass once `tasks.md` exists; run the cross-artifact consistency pass across `spec.md`, `context.md`, `plan.md`, and `tasks.md` only when explicitly requested or recorded by existing state
- `debug` to investigate blocked implementation work, regressions, or execution-time defects without reopening upstream planning artifacts unless drift is discovered. It now defaults to project-cognition-backed minimum intake; the heavier Stage 1A/1B observer-contract flow is reserved for missing/ambiguous/stale map coverage, competing truth owners, or failed verification loops.
- `explain` to describe the current spec, plan, task, implement, project cognition, or compatibility/export artifact in plain language
- `integrate` to discover implementation-complete lanes, run closeout prechecks, and prepare them for mainline merge without folding closeout back into `implement`
- `integration repair` to refresh generated shared/runtime-managed assets after CLI upgrades or when `specify check` reports stale launcher, script, or hook surfaces
- when you run `analyze` and it finds upstream issues, it becomes a workflow gate, not a dead-end audit: reopen the highest invalid stage and regenerate downstream artifacts before continuing implementation
- `analyze` now also detects boundary guardrail drift through stable issue codes: `BG1` (missing `Implementation Constitution`), `BG2` (missing task guardrails), and `BG3` (missing implementation-time boundary confirmation)
- `analyze` should also surface delegated-execution packet gaps through `DP1` (missing compiled hard rules), `DP2` (missing required references or forbidden drift), and `DP3` (missing subagent validation evidence)

Already have code? Resolve `.specify/project-cognition/status.json` and the agent-planned task-local project cognition query bundle first. The workflow asks the runtime for a lexicon, the agent expands the user's natural-language request into a `query_plan`, and the runtime executes that plan. For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build`, and require `project-cognition validate-scan --format json` plus `project-cognition validate-build --format json` to pass before downstream work proceeds. Use `map-update` for changed-path and localized stale cognition runtime refresh after that. Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, zero active-generation path_index rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
Generated projects track cognition freshness in `.specify/project-cognition/status.json`, so brownfield workflows can decide whether the current cognition baseline is `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, or `possibly_stale` before proceeding. Ordinary `sp-*` workflows treat cognition freshness as advisory navigation, continue with live repository evidence, and apply the map-update-first routing policy while using `recommended_next_action` for public state guidance.

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

Routing guide for lightweight work:

- `sp-fast` is only for trivial local fixes. Stay on that path only when the change is obvious, touches at most 3 files, and does not touch a shared surface.
- Move from `sp-fast` to `sp-quick` as soon as the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `sp-quick` is for small but non-trivial work that still fits one bounded quick-task workspace.
- Both `sp-fast` and `sp-quick` still pass the project cognition gate first: run `project-cognition lexicon --intent implement --query="$ARGUMENTS" --format json`, have the agent translate the raw request into a `query_plan` using returned map terms, then run `project-cognition query --intent implement --query-plan "<query_plan_json>" --format json`. Generated projects require `PROJECT_COGNITION_BIN` or `project-cognition` on PATH for these helpers; helper scripts prefer `PROJECT_COGNITION_BIN` when set and otherwise call `project-cognition` from PATH. Continue from the returned readiness, task-local bundle, and `minimal_live_reads` before source reads continue.
- On shells or native command launchers that strip nested JSON quotes, write the planned object to a file and call `project-cognition query --intent <intent> --query-plan-file <path> --format json`; `path_hints`/`reason` are accepted aliases for `paths`/`selection_reason`.
- If the work is a bug fix or regression and the root cause is still unknown, use `sp-debug` instead of treating `sp-quick` as a symptom-fix lane.
- Behavior-changing work across `sp-fast`, `sp-quick`, `sp-implement`, and `sp-debug` follows a failing test first rule. Capture a RED state before production edits; if the touched area lacks a viable automated test surface, add the smallest safe bootstrap in the owning workflow or escalate to `sp-quick`/`sp-specify`.
- Quick workspaces now live under `.planning/quick/<id>-<slug>/`, with `STATUS.md` as the task source of truth and `.planning/quick/index.json` as a derived management index.
- Invoking `sp-quick` with no arguments should resume unfinished quick work when possible. If only one unfinished quick task exists, continue it automatically. `blocked` quick tasks still count as resumable unfinished work.
- Use `specify quick list` to inspect unfinished quick tasks by default.
- Quick-task helper command shapes:
  - Command shape: `specify quick status <id>`
  - Command shape: `specify quick resume <id>`
  - Command shape: `specify quick close <id> --status resolved|blocked`
  - Command shape: `specify quick archive <id>`
- Move from `sp-quick` to `sp-specify` when the request spans multiple independent capabilities, carries compatibility or rollout risk, or needs explicit acceptance criteria before implementation.

Required action markers:

- `[AGENT]` marks a required AI action and is independent from `[P]`.
- `[P]` still means parallel-safe work; `[AGENT]` does not imply parallelism, subagent dispatch, or runtime routing by itself.
- Existing `AGENTS.md` files are extended through a managed `SPEC-KIT` block instead of full-file append or replacement.
- First-wave `[AGENT]` coverage started with `sp-fast`, `sp-quick`, `sp-map-scan`, and `sp-map-build`; the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows now use the same marker for hard gates and required state updates.

Passive project learning layer:

- Generated projects include `.specify/memory/learnings/INDEX.md` as the thin first-read learning layer.
- Each reusable lesson may link to one detail markdown document per lesson under `.specify/memory/learnings/`.
- `project-learnings.md` remains a compatibility summary; new captures write index/detail memory first.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work.
- This shared project memory is available across later work in the repository, not just when a `sp-*` workflow is active.
- The major workflow templates now read the passive project learning layer before deeper command-local context so recurring pitfalls, constraints, and user defaults can influence later runs.
- Low-level helper commands exist for the passive learning lifecycle:
- `specify learning ensure --format json`
- `specify learning status --format json`
- `specify learning start`
  - Command shape: `specify learning start --command <workflow> --format json`
- `specify learning capture`
  - Required options: `--command`, `--type`, `--summary`, `--evidence`
- `specify learning capture-auto`
  - Command shape: `specify learning capture-auto --command <workflow> --format json`
- `specify implement closeout`
  - Command shape: `specify implement closeout --feature-dir <feature-dir> --format json`
- `specify learning aggregate --format json`
- `specify learning promote`
  - Command shape: `specify learning promote --recurrence-key <key> --target learning|rule`
- Use `specify learning aggregate` when you want a grouped, promotion-oriented summary of candidate, confirmed, and promoted learning patterns before deciding what should become a shared learning or rule.
- This is an internal/runtime helper surface, not a new daily `sp-` workflow. The intent is passive reuse across every `sp-*` workflow, with direct learning-memory commands preserving structured path-learning fields such as pain score, false starts, decisive signal, root-cause family, injection target, and promotion hint.
- Durable eval helpers turn promoted rules into local regression checks:
  - `specify eval create`
    - Command shape: `specify eval create --recurrence-key <key> --summary "<summary>"`
  - `specify eval status --format json`
  - `specify eval run --format json`
- Use `specify eval create` after a rule or learning becomes stable enough that the repository should keep proving it, not just remember it.

First-party hook runtime:

- `specify hook ...` is a compatibility, diagnostic, and native-adapter surface. Normal `sp-*` workflow steps should not call `specify hook ...`; generated workflows express quality requirements through durable state, artifact, packet, result, verification, learning, and project cognition contracts instead.
- Keep using hook commands when debugging a generated project, preserving compatibility with older generated assets, or running a native adapter that translates host hook events into shared checks.
- Important diagnostic command shapes:
  - `specify hook validate-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-session-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-packet --packet-file <path>`
  - `specify hook validate-result --packet-file <packet> --result-file <result>`
  - `specify hook validate-read-path --target-path <path>`
  - `specify hook validate-prompt --prompt-text "<text>"`
- Project cognition freshness should use the public project-cognition commands:
  - Command shape: `project-cognition complete-refresh`
  - Command shape: `project-cognition mark-dirty --reason "<reason>" [--origin-command <workflow>] [--origin-feature-dir <dir>] [--origin-lane-id <lane-id>] [--packet-file <packet-json>]`
  - Historical compatibility/export surface: legacy project-map artifacts may still exist in old projects, but there is no Python runtime alias and new generated workflow guidance should not call them.

Claude Code integration note:

- `specify init --ai claude` installs thin native adapters in `.claude/hooks/` and merges project-local `.claude/settings.json`.
- Managed Claude hook entries use a single shell-free `node -e ... claude <route>` command. The inline launcher walks upward from the hook working directory to find `.specify/bin/specify-hook.mjs`, so hooks still work when Claude runs from a monorepo subdirectory such as `apps/web`, then the shared Node launcher resolves project-local runtime details from the hook payload and project files.
- The current managed Claude native hook set covers:
  - `SessionStart` statusline/orientation context plus bounded compaction-backed resume cues
  - `UserPromptSubmit` prompt-guard checks plus shared workflow-policy enforcement
  - `PreToolUse` shared workflow-policy checks, read-boundary checks, and inline commit-message validation
  - `PostToolUse` session-state drift warnings for active implement/quick/debug flows, plus soft learning-signal warnings and compaction refresh guidance when workflow state records reusable friction
  - `Stop` context-monitor checkpoint blocking or advisory output before stop, plus compaction-backed resume cues and soft learning-signal warnings when active workflow state crosses the pain threshold
- These adapters are intentionally thin: they call back into the shared `specify hook ...` command surface instead of re-implementing workflow truth inside standalone Claude scripts.

Codex/OMX integration note:

- The OMX runtime manages Codex native hooks through `.codex/hooks.json` and `codex-native-hook.js`.
- The managed Codex native hook set covers `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- `SessionStart` and `Stop` can append bounded compaction-backed resume cues from the shared hook surface.
- `UserPromptSubmit` can bridge shared workflow-policy blocking when the active workflow is being asked to jump phases unsafely.
- `PostToolUse` and `Stop` bridge shared learning-signal warnings when active workflow state records reusable friction.
- Learning capture and terminal learning review remain direct learning-memory responsibilities; native hooks may surface soft signals, but normal `sp-*` workflow steps should not call hook learning commands.

Gemini integration note:

- `specify init --ai gemini` installs thin native adapters in `.gemini/hooks/` and merges project-local `.gemini/settings.json`.
- The managed Gemini native hook set covers `SessionStart`, `BeforeAgent`, and `BeforeTool`.
- `SessionStart` can append bounded compaction-backed resume cues from the shared hook surface.
- `BeforeAgent` applies shared prompt guards, targeted workflow-policy checks for explicit phase jumps, and soft learning-signal warnings when active workflow state records reusable friction.
- `BeforeTool` applies shared read-boundary and inline commit-message validation.
- As with Claude and Codex, learning capture and terminal learning review remain direct learning-memory responsibilities; native hooks may surface soft signals, but normal `sp-*` workflow steps should not call hook learning commands.

Native hook coverage matrix:

| Surface | Shared `specify hook ...` | Native adapter/runtime | Learning signal bridge | Native terminal review gate |
| --- | --- | --- | --- | --- |
| Claude | Yes | Yes | Yes | No |
| Codex/OMX | Yes | Yes | Yes | No |
| Gemini | Yes | Yes | Yes | No |
| Other integrations | Yes | No | No | No |

After planning, continue with:

```text
specify -> plan -> tasks -> implement
```

`plan` and `tasks` use adaptive execution: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`. Light, low-risk single-lane planning or task generation runs leader-inline. Standard work uses native subagents when available; if native subagents are unavailable and no high-risk trigger is present, it may continue leader-inline with `capability_degraded: true`. Standard work that has no safe subagent lane or cannot be packetized safely records `dispatch_shape: subagent-blocked` and stops. Heavy or safety-critical work also blocks when native subagents are unavailable or the work is unpacketizable. Managed-team fallback is not part of adaptive plan/tasks dispatch.

Closed-loop remediation after `tasks`:

- If the defect is in `spec.md` or `context.md`, go back to `clarify`, then rerun `plan`, `tasks`, and `implement` after the upstream artifacts are repaired.
- If the defect is in `plan.md`, go back to `plan`, then rerun `tasks` and `implement`.
- If the defect is only in `tasks.md`, rerun `tasks`, then resume `implement`.
- `tasks` should run an implementation-readiness self-audit before final handoff, covering task coverage, locked decision preservation, task guardrails, DP1/DP2/DP3 readiness, reference fidelity mapping, unmapped tasks, and write-set conflicts.
- If `analyze` is run, it should finish a complete blocker bundle before selecting the single recommended next command; do not treat one discovered blocker as permission to stop the rest of the analysis pass.
- repeated `tasks -> analyze -> tasks` loops are abnormal. only use `analyze` again when explicitly required by legacy or diagnostic state; if revalidation finds new task-layer blockers that were detectable before remediation, diagnose a previous analyze miss or a tasks self-audit failure.
- If `tasks` discovers missing upstream truth during remediation, route directly to `plan`, `clarify`, or `deep-research`; run `analyze` again only when explicitly required by legacy or diagnostic state after upstream artifacts are repaired and tasks are regenerated.
- If the defect is execution-only with no upstream artifact drift, continue in `implement` or route into `debug`.
- If `analyze` is run after `implement` has already started or finished, treat the current implementation as provisional until the highest invalid stage has been repaired and downstream artifacts have been regenerated.

Boundary-sensitive implementation rule:

- If the feature touches an established boundary pattern in the target project, `plan` should write an `Implementation Constitution` section instead of leaving that rule buried in technical background.
- Use `Implementation Constitution` for architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus.
- Typical triggers include existing framework-owned boundaries, native/plugin bridges, protocol seams, generated API surfaces, or any area where "generic implementation instinct" would likely drift from the repository's established pattern.
- A good heuristic is: if an implementer should be forced to inspect specific existing boundary files before coding safely, the feature likely needs `Implementation Constitution`.
- `tasks` should convert those rules into explicit implementation guardrails before setup or feature work begins.
- `tasks` should also preserve a `Task Guardrail Index` or equivalent task-to-guardrail mapping when subagent execution needs task-local rule inheritance.
- `implement` should treat those guardrails as binding execution constraints and confirm the touched boundary's owning framework, defining reference files, and forbidden drift before dispatching code-writing work.
- Delegated execution should no longer rely on raw task text when architecture or quality rules matter.
- `plan` should provide `Dispatch Compilation Hints`.
- `implement` should compile and validate a `WorkerTaskPacket` before dispatching subagents.
- Subagent packets should carry platform guardrails when a lane depends on supported-platform constraints, conditional compilation, or environment-sensitive runtime assumptions.

Current `sp-implement` runtime model in this fork:

- `sp-implement` acts as a milestone-level orchestration leader rather than the direct executor
- concrete implementation uses `subagents-first` execution when the packet is ready, with `one-subagent` for one safe delegated lane and `parallel-subagents` for independent safe lanes
- `leader-inline-fallback` is allowed only after recording why delegation is unavailable, unsafe, or not packetized
- durable teams/runtime execution is the `managed-team` surface (`sp-implement-teams` / `sp-teams`) for durable state or lifecycle needs, not an internal fallback hidden inside `sp-implement`
- subagents should execute from compiled `WorkerTaskPacket` contracts rather than rediscovering rules from background context
- subagent result handoff should use the runtime-managed result channel when one exists; otherwise subagents should write normalized result envelopes to the declared filesystem handoff path for the current workflow
- implementation lanes without a runtime-managed channel should use `FEATURE_DIR/worker-results/<task-id>.json`
- quick-task lanes without a runtime-managed channel should use `.planning/quick/<id>-<slug>/worker-results/<lane-id>.json`
- debug evidence lanes without a runtime-managed channel should use `.planning/debug/results/<session-slug>/<lane-id>.json`
- when the local CLI is available and no runtime-managed result channel exists, prefer `specify result path` to compute the canonical handoff target and `specify result submit` to normalize and write the subagent result envelope
- when subagent language is normalized into canonical orchestration state, preserve the raw `reported_status`
- top-level `tasks.md` items should stay bounded to one coffee-break-sized implementation slice, usually roughly 10-20 minutes, while subagents may still execute them through smaller 2-5 minute atomic steps
- task decomposition should stay progressive: refine only the current executable window after each join point instead of pre-expanding later batches that still depend on upstream evidence
- parallel work is coordinated through explicit join points before dependent work continues
- every join point that gates downstream work should name a validation target, a validation command or check, and a pass condition
- grouped parallelism is the default when ready tasks have isolated write sets; use a pipeline shape only when outputs must flow stage-by-stage and keep explicit checkpoints between stages
- high-risk batches touching shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces should add a review gate before crossing the join point
- if a read-only verification lane is available, use one peer-review lane only for those high-risk batches rather than for every batch
- runtime surfaces can report retry-pending work and blockers instead of hiding those states in chat-only narration
- blocked subagent results should carry the blocker, the failed assumption, and the smallest safe recovery step so the leader can fail fast instead of guessing
- if a subagent lane reports `completed` or drifts into `idle` before the promised handoff arrives, treat it as a stale lane and recover explicitly instead of assuming success
- established boundary patterns should be preserved through `Implementation Constitution` and implementation guardrails, not rediscovered ad hoc during coding

Shared runtime-facing guidance across integrations:

- `sp-implement`, `sp-debug`, and `sp-quick` now all carry a shared leader contract, subagent-dispatch contract, and subagent-result contract across Markdown, TOML, and skills-based integrations.
- The shared contract is integration-neutral: leader role, join-point discipline, structured handoff expectations, and `reported_status` preservation are common across CLIs. Workflow-specific fallback semantics stay explicit in the command guidance.
- Only the concrete dispatch command remains integration-specific. For example, Codex names `spawn_agent` and uses `sp-teams` only when durable team state is needed.

For Codex and other skills-based integrations, the generated commands are installed in skills form. Codex now uses the dedicated `.codex/skills/` directory for generated skills.

Skills-based projects now install two layers into the same skills directory:

- explicit workflow skills: `sp-*`
- passive bundled skills: keep the directory names from `templates/passive-skills/` (for example `spec-kit-*`, `tdd-workflow`, `frontend-design`)

`sp-*` remains the primary user-facing workflow surface. Passive skills keep their template names and exist to improve automatic routing, guardrails, and bundled capabilities inside Spec Kit Plus repositories, not to replace the explicit workflow commands.

## Multi-CLI Orchestration

Current orchestration status in this fork:

- generic orchestration core exists under `src/specify_cli/orchestration/`
- `sp-plan` and `sp-tasks` are adaptive: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`.
- Adaptive `sp-plan`/`sp-tasks` use leader-inline for light work, native subagents for standard work when available, leader-inline degradation with `capability_degraded: true` only for standard native-unavailable work without high-risk triggers, and `subagent-blocked` for standard no-safe-lane or unpacketizable work plus heavy/safety-critical unavailable or unpacketizable work; managed-team fallback is not part of adaptive plan/tasks dispatch.
- Workflows that remain mandatory-subagent, such as `sp-implement`, `sp-debug`, `sp-map-scan`, `sp-map-build`, `sp-prd-scan`, and `sp-prd-build`, still use `execution_model: subagent-mandatory`.
- in execution-oriented workflows, use subagent execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality
- `specify`, `plan`, `tasks`, and `explain` now document workflow-specific lanes and join points while keeping shared workflow templates integration-neutral
- `sp-teams` remains the Codex `managed-team` execution surface for durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst
- Claude, Gemini, and Copilot ship first-release adapter skeletons (alongside Codex) for native-first capability reporting
- durable runtime maturity for `implement` and `debug`, plus wider integration rollout, remain future work

This repository is no longer only a Milestone 1 slice, but the full execution/runtime maturity roadmap is still not complete.

## Codex Team Runtime

This fork now exposes a Codex-only first-release team/runtime surface through:

```bash
sp-teams
```

### The `sp-teams` surface

`sp-teams` is the official CLI surface for the runtime. All operations start from this command, so avoid advertising legacy aliases or alternate entry points.

- `sp-teams watch` opens a full-screen observer over members and flow, with lightweight terminal interaction for focus switching, detail expansion, and view cycling.
- `sp-teams status` dumps the latest JSON snapshot of the team phase, worker roster, task queue, and mailbox state.
- `sp-teams await` blocks until the runtime reaches a terminal phase so operators can wait for batch completion.
- `sp-teams resume` re-attaches to an existing runtime session by replaying the metadata in `.specify/teams/` and restarting the tmux backend.
- `sp-teams shutdown` requests a graceful stop, letting workers finish or fail their in-flight tasks before tearing down.
- `sp-teams cleanup` removes `.specify/teams/` state after shutdown succeeds; run it only once shutdown has settled to avoid corrupting the state folder.
- `sp-teams submit-result --request-id <id> --result-file <path>` validates and records a structured subagent result for an existing dispatch. Use `sp-teams result-template --request-id <id>` only to generate the canonical `pending` placeholder; do not submit that template unchanged.
- `sp-teams api <operation>` proxies structured JSON operations (task claims, worker heartbeats, events) into the runtime; use it when automation needs a predictable channel.

For agents and automation, prefer the optional MCP supplement instead of having the model compose CLI invocations directly:

- `specify-teams-mcp` exposes an agent-facing MCP facade for the structured control plane
- install the optional facade with `pip install "specify-cli[mcp]"`; Codex config can register it only when that extra is available
- if you install the MCP extra after project init, refresh the generated Codex config with `scripts/sync-ecc-to-codex.sh` or `scripts/powershell/sync-ecc-to-codex.ps1`
- the MCP layer is intended for agent/tool consumers
- `sp-teams` remains the human/operator CLI and parity fallback surface

This command suite powers both the `sp-teams` skill and the runtime APIs that downstream tooling relies on, which is why the command is restricted to Codex-initiated projects.

### Runtime state location and lifecycle

All runtime state lives under `.specify/teams/`:

- `runtime.json` contains the active session metadata and canonical root paths.
- `state/` holds per-object JSON files (`tasks/*.json`, `workers/*.json`, `mailboxes/*.json`, `dispatch/*.json`) along with `phase.json` and `events.log` for the lifecycle stream.
- Heartbeats, claims, approvals, and monitor snapshots append to the files under `state/`, helping the CLI restart from the latest saved facts.

Lifecycle notes:

- Tasks run through `pending -> in_progress -> completed|failed` and emit events that `sp-teams status` surfaces.
- Workers claim tasks with identity records, write heartbeats under `state/workers`, and consume mailbox messages from `state/mailboxes`.
- Structured subagent results live under `state/results/` and are submitted through `sp-teams submit-result` / `sp-teams api submit-result` before `complete-batch` should mark a structured-result batch done.
- Shutdown requests append a terminal event, and cleanup removes the `.specify/teams/` directory once all JSON files have been archived.

Operators should treat this directory as the single source of truth for resumes, restarts, and audits, and not attempt to recreate state outside the official CLI surface.

### Operator guidance and backend requirements

- The runtime currently requires a tmux-capable backend (`tmux` on Unix/WSL or a Windows-compatible alternative) to host worker panes; the CLI validates the backend before bootstrapping a session.
- `sp-teams watch` is the operator-facing live board: use it when you need a continuous view of members and flow instead of one-shot diagnostics.
- Use `sp-teams resume` whenever a previously-running session still holds worker heartbeats or task claims to prevent duplicate boots.
- Issue `sp-teams shutdown` before terminating the tmux backend so the runtime can flush claims and notify join points, then run `sp-teams cleanup` once the CLI reports the phase is `shutdown`/`cleaned`.
- `sp-teams await` is useful for scripts that need to pause until the team exits the `dispatch` phase without polling `state/` files directly.

### Release isolation guidance

Current release scope:

- Codex-only for first release
- requires a tmux-capable environment
- installs the Codex team skill as `sp-teams`
- keeps non-Codex integrations free of the team/runtime surface by default
- installs runtime helper assets only under `.specify/teams/` for Codex projects

Existing Codex projects may use an optional upgrade path, but that upgrade remains optional, non-blocking release support rather than a first-release requirement.

Release isolation guidance:

- `specify init --ai codex` may generate `sp-teams` and `.specify/teams/*`
- non-Codex init flows must not generate `sp-teams`, `.specify/teams/*`, or advertise `sp-teams`
- `omx` and `$team` are not the supported product surface for this repository

Maintainer note:

- keep Codex team assets and messaging behind Codex-only install and help paths unless the release boundary is intentionally widened

## Key Commands

- `specify init`
  - Command shape: `specify init <project> --ai <agent>`
- `specify check`
- `specify extension list`
- `specify preset list`

Result helper command shapes:

- Command shape: `specify result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>`
- Command shape: `specify result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id> --result-file <path>`

For the full CLI surface:

```bash
specify --help
specify init --help
```

## Supported Agents

Commonly used integrations in this fork include:

- `codex`
- `claude`
- `gemini`
- `copilot`
- `cursor-agent`
- `qwen`
- `opencode`
- `windsurf`
- `junie`
- `kilocode`
- `auggie`
- `roo`
- `codebuddy`
- `amp`
- `shai`
- `kiro-cli`
- `agy`
- `bob`
- `qodercli`
- `vibe`
- `kimi`
- `iflow`
- `pi`
- `forge`
- `generic`

The exact up-to-date list is available from the CLI:

```bash
specify init --help
```

## Repository Layout

Important directories:

- `src/specify_cli/` - CLI implementation and integrations
- `templates/` - built-in templates bundled into generated projects
- `scripts/` - shell and PowerShell support scripts
- `tests/` - regression and integration test suite
- `docs/` - installation, upgrade, and development notes

## Project Cognition Runtime

Navigation and technical truth are now cognition-first:

- Generated projects use `.specify/project-cognition/status.json` plus the agent-planned task-local project cognition query bundle as the advisory project cognition index. `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries, not evidence by itself.
- Ordinary brownfield workflows should read the cognition status and the task-local project cognition query bundle before broader repository analysis.
- `fresh` means the last handbook refresh completed against a known git baseline, and `.specify/project-cognition/status.json` records that git-baseline freshness truth source.
- `support_drift` means support/tool-managed surfaces changed without proving runtime-truth staleness; resolve or ignore those support surfaces instead of treating them as a localized runtime refresh.
- `partial_refresh` means refresh data was recorded but the ready refresh check still failed; do not report refresh completion until readiness passes.
- `sp-map-scan` still performs diff-based scope selection when entered, but the refresh workbench remains internal to `map-scan` / `map-build`.
- Ordinary runtime consumption should prefer `debug-handbook.md` or `build-handbook.md` plus the workflow's fixed chapter set only as compatibility/export views.
- New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, `project-cognition lexicon`, and `project-cognition query --query-plan` as advisory navigation inputs. `templates/project-map/**` remains a historical compatibility/export surface for handbook generation, but new workflows should not read or require `.specify/project-map/**`.
- Releases publish prebuilt `project-cognition` binaries for Windows, Linux, and macOS. `specify init` best-effort downloads and pins the matching binary in `.specify/config.json`; if that cannot happen, install via `tools/project-cognition/install.sh` or `tools/project-cognition/install.ps1`, or set `PROJECT_COGNITION_BIN` to a custom binary path.
- Use `map-update` for localized stale cognition refresh recommendations, ordinary changed-path map maintenance, and ordinary existing-baseline gaps; use `map-scan` followed by `map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is map-maintenance complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`.
- Project cognition ignore rules live in root `.cognitionignore` or `.specify/project-cognition/.cognitionignore`. They use gitignore-compatible patterns and are honored by `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`.
- For cross-project references, run `project-cognition discover --root <path> --format json`
  before broad inspection. Use another project's cognition only when
  `.specify/project-cognition/status.json` and
  `.specify/project-cognition/project-cognition.db` exist,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true; do not treat legacy `.specify/project-map/**` outputs as current truth
  when the reference is stale, blocked, or incomplete.
- Generated projects require the `specify init` pinned `project_cognition_launcher`, `PROJECT_COGNITION_BIN`, or `project-cognition` on PATH before any of these helpers run; helper scripts prefer `PROJECT_COGNITION_BIN` when set and otherwise call `project-cognition` from PATH.
- If a full refresh can be completed now, run `project-cognition validate-build --format json`, then `project-cognition complete-refresh --format json` only when build acceptance passes; otherwise run `project-cognition mark-dirty --reason "<reason>" --format json` as the manual override/fallback.
- Map points, code proves: technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
- This repository does not treat its own root `.specify/` directory as committed source-of-truth content; repo-local `.specify/` state is disposable and may be regenerated.
- After a successful refresh, record the new fresh cognition baseline. Use dirty fallback metadata only when the required refresh cannot be completed now, so same-feature resume can warn instead of self-blocking while upstream brownfield entrypoints and other features still require refresh.
- Any code change that alters project cognition meaning must update the cognition runtime.

## Documentation

- [Installation Guide](docs/installation.md)
- [Upgrade Guide](docs/upgrade.md)
- [Local Development](docs/local-development.md)
- [Spec-Driven Walkthrough](spec-driven.md)

## Notes For This Fork

- install from `chenziyang110/spec-kit-plus`, not the upstream `github/spec-kit`, if you want this fork's behavior
- Codex integration in this fork defaults to skills-mode behavior; `--ai-skills` is usually unnecessary
- template and workflow behavior may differ from upstream Spec Kit

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
