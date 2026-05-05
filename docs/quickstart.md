# Quick Start Guide

This guide will help you get started with Spec-Driven Development using Spec Kit Plus.

> [!NOTE]
> All automation scripts now provide both Bash (`.sh`) and PowerShell (`.ps1`) variants. The `specify` CLI auto-selects based on OS unless you pass `--script sh|ps`.

## The 5-Step Process

> [!TIP]
> **Context Awareness**: In single-feature workflows, Spec Kit commands can infer the active feature from the current Git branch (for example `001-feature-name`). Once concurrent feature lanes exist, root-level `sp-*` commands should prefer lane registry plus reconcile over branch-only guessing, and `sp-auto` should resume only when there is one uniquely safe candidate.

### Step 1: Install Specify

**In your terminal**, run the `specify` CLI command to initialize your project:

```bash
# Create a new project directory
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME>

# OR initialize in the current directory
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init .
```

Pick script type explicitly (optional):

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME> --script ps  # Force PowerShell
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME> --script sh  # Force POSIX shell
```

When `specify init` comes from a trusted source-bound launcher such as the
`uvx --refresh --from ... specify` form above, generated projects can persist
that launcher in `.specify/config.json` as `specify_launcher`. Runtime helper
instructions inside generated workflows should follow the project launcher when
it exists instead of blindly trusting whichever `specify` happens to be first on
PATH.

### Invocation Syntax

Canonical workflow names are integration-neutral: `constitution`, `specify`,
`plan`, `tasks`, `implement`, `analyze`, and the other workflow names in this
guide are the stable names used by Spec Kit Plus.

Invocation syntax depends on the integration:

| Integration surface | Constitution | Specify | PRD | Plan | Tasks |
| --- | --- | --- | --- | --- | --- |
| Codex skills | `$sp-constitution` | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | `$sp-tasks` |
| Kimi Code skills | `/skill:sp-constitution` | `/skill:sp-specify` | `/skill:sp-prd-scan -> /skill:sp-prd-build` | `/skill:sp-plan` | `/skill:sp-tasks` |
| Claude skills | `/sp-constitution` | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | `/sp-tasks` |
| Slash-dot command integrations | `/sp.constitution` | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | `/sp.tasks` |

`/sp-*` is not universal for skills-backed integrations. Use the syntax
generated for the integration selected during `specify init`; for example, run
`$sp-specify` in Codex, `/skill:sp-specify` in Kimi, `/sp-specify` in Claude, or
`/sp.specify` in slash-dot command integrations. For existing-project PRD
extraction, use the same mapping for the canonical `prd-scan -> prd-build`
workflow pair, such as `$sp-prd-scan -> $sp-prd-build`, `/skill:sp-prd-scan ->
/skill:sp-prd-build`, `/sp-prd-scan -> /sp-prd-build`, or `/sp.prd-scan ->
/sp.prd-build`. `prd` remains deprecated compatibility-only.

The concrete chat snippets below use Claude-style `/sp-*` examples for
readability. Translate them through the matrix above when you are using Codex,
Kimi, or a slash-dot command integration.

### Step 2: Define Your Constitution

`specify init` seeds a default constitution into `.specify/memory/constitution.md`. In your AI agent's chat interface, run the `constitution` workflow when that default constitution needs project-specific changes or when you need to establish or revise project principles before downstream planning work continues.

If the repository needs a different built-in baseline, pick a constitution
profile during init:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME> --constitution-profile library
```

Built-in profiles:

- `product` (default) for application and service repositories
- `minimal` for lean, low-ceremony repositories
- `library` for packages, SDKs, and CLIs with compatibility expectations
- `regulated` for security, privacy, or audit-heavy repositories

```markdown
/sp-constitution This project follows a "Library-First" approach. All features must be implemented as standalone libraries first. We use TDD strictly. We prefer functional programming patterns.
```

### Step 3: Create the Spec

**In the chat**, run the `specify` workflow to describe what you want to build. Focus on the **what** and **why**, not the tech stack.

Treat `sp-specify` plus the generated create-feature script as the supported
feature-creation path. Do not look for or teach a separate branch-creation
command family.

```markdown
/sp-specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page. Albums are never in other nested albums. Within each album, photos are previewed in a tile-like interface.
```

For an existing repository that needs a current-state product requirements
document instead of a new feature spec, run the peer `prd-scan -> prd-build`
workflow pair. It is the heavy reconstruction PRD lane: substantive
`prd-scan` runs are subagent-mandatory, critical claims target
`L4 Reconstruction-Ready`, `config-contracts.json` is part of the scan
contract surface, and `prd-build` compiles the expanded reconstruction archive
from the scan package without performing a second repository scan. The workflow
writes `.specify/prd-runs/<run-id>/` and does not automatically hand off to
`plan`. `prd` remains a deprecated compatibility entrypoint only.

```markdown
/sp-prd-scan Extract the heavy reconstruction PRD scan package for this repository.
/sp-prd-build Compile the expanded reconstruction archive from the validated scan package without a second repository scan.
```

### Step 4: Plan the Implementation

**In the chat**, move directly from `specify` to `plan` once the spec is planning-ready. This is the mainline workflow:

```bash
/sp-plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.
```

Use `clarify` only when an existing spec needs deeper analysis before planning.
Use `deep-research` only when the requirements are clear but feasibility still needs proof before planning, for example an unproven API, library, integration, algorithm, performance envelope, or platform behavior. It can coordinate parallel research tracks and disposable demo spikes, then writes a traceable `Planning Handoff` with evidence IDs that `plan` must consume. Skip it for minor changes to an existing capability that already has a clear implementation path.
Use `research` only as a compatibility alias for `deep-research`; it should route into the same gate and must not create separate workflow artifacts.
When `specify` records an unproven implementation chain, the recommended pre-planning branch is `specify` -> `deep-research` -> `plan`.

### Step 5: Break Down and Implement

**In the chat**, run the `tasks` workflow to create an actionable task list.

```markdown
/sp-tasks
```

Before implementation, run `analyze`. Treat it as the required gate before implementation once `tasks.md` exists. If it flags upstream issues, resolve them through the re-entry path below before proceeding:

```markdown
/sp-analyze
```

Then, run the `implement` workflow to execute the plan.

```markdown
/sp-implement
```

When you want one state-driven resume lane instead of naming the next workflow manually, use the `auto` workflow. It reads the current repository state and resumes the recommended next step under that workflow's existing contract.

If generated workflow assets or helper surfaces seem stale after a CLI upgrade,
run `specify check` first. Treat any reported workflow-contract drift as a hard
incompatibility, then run `specify integration repair` before continuing with
`sp-*` workflows.

When the feature touches an established boundary pattern in the target project, make that constraint explicit before coding starts:

- `plan` should write an `Implementation Constitution` section instead of leaving the rule as background context only.
- Use `Implementation Constitution` for architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus.
- `tasks` should turn those rules into explicit implementation guardrails before setup or feature work begins.
- `tasks` should also preserve a `Task Guardrail Index` or equivalent task-to-guardrail mapping when subagent work needs task-local rule inheritance.
- `implement` should treat those guardrails as binding execution constraints and confirm the owning framework, defining reference files, and forbidden drift before dispatching code-writing work.
- Delegated execution should not rely on raw task text when architecture or quality rules matter.
- `plan` should provide `Dispatch Compilation Hints`.
- `implement` should compile and validate a `WorkerTaskPacket` before dispatching subagents; if delegation is unavailable, unsafe, or not packetized, it should use `leader-inline-fallback` with an explicit recorded reason.
- Subagent packets should carry platform guardrails when the lane depends on supported-platform constraints, conditional compilation, or environment-sensitive runtime assumptions.
- If the active integration exposes a runtime-managed result channel, subagents should use it. Otherwise they should write normalized result envelopes to the workflow-specific worker-results path.
- When the local `specify` CLI is available and no runtime-managed result channel exists, subagents should prefer `specify result path` and `specify result submit` instead of inventing ad-hoc result locations or payload shapes.
- Preserve the raw `reported_status` when subagent language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` is normalized into canonical orchestration state.
- Top-level `tasks.md` items should usually fit one coffee-break-sized implementation slice, roughly 10-20 minutes, while subagents may still break them into smaller 2-5 minute atomic steps internally.
- Keep decomposition progressive: refine only the current executable window after each join point instead of over-specifying later batches too early.
- Every join point that gates downstream work should name a validation target, a validation command or check, and a pass condition.
- Grouped parallelism is the default when ready tasks have isolated write sets; use a pipeline shape only when outputs flow stage-by-stage and keep explicit checkpoints between stages.
- For high-risk batches touching shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces, add a review gate before crossing the join point.
- If a read-only verification lane is available, use one peer-review lane only for those high-risk batches rather than for every batch.
- If subagent work returns `blocked`, require the blocker, the failed assumption, and the smallest safe recovery step before accepting the result.
- If a subagent lane reports `completed` or slips into `idle` before the promised handoff arrives, treat it as a stale lane and recover explicitly instead of assuming success.

> [!TIP]
> **Phased Implementation**: For complex projects, implement in phases to avoid overwhelming the agent's context. Start with core functionality, validate it works, then add features incrementally.

## Skill Map

After initialization, treat the generated commands as three groups:

- **Core workflow skills**: `constitution`, `specify`, `plan`, `tasks`, `implement`
- **Support skills**: `map-scan`, `map-build`, `test-scan`, `test-build`, `auto`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `clarify`, `deep-research` (`research` alias), `checklist`, `analyze`, `debug`, `explain`, `integrate`
- **Codex-only runtime**: `sp-teams` and `sp-teams` skill surface when the project was initialized for Codex

For Codex team-mode execution, use the runtime surface deliberately:

- Run `sp-teams doctor` before the first coordinated batch so backend readiness, executor availability, baseline build state, and the latest transcript are visible up front.
- Run `sp-teams live-probe` when the runtime was just installed, recently repaired, or still looks suspect after `doctor`.
- If agent automation should use the optional MCP facade, install it with `pip install "specify-cli[mcp]"` and refresh the generated Codex config with `scripts/sync-ecc-to-codex.sh` or `scripts/powershell/sync-ecc-to-codex.ps1`.
- Use `sp-teams result-template --request-id <id>` and `sp-teams submit-result --print-schema` instead of inventing handoff JSON by guesswork. The generated result template is a `pending placeholder` and must be replaced with a real success, blocked, or failed result before submission.
- Use `sp-teams sync-back` after managed team execution when the canonical code changes landed under `.specify/teams/worktrees/<session>/...` and need to be promoted back to the main workspace.
- In execution-oriented workflows, use the leader + subagents model: `subagents-first` execution, `one-subagent` or `parallel-subagents` dispatch, and `leader-inline-fallback` only when delegation is unavailable, unsafe, or not packetized.
- Use `native-subagents` when the active integration supports in-session subagents, `managed-team` only when durable state or lifecycle control is needed, and `leader-inline` only as the recorded fallback surface.
- Prefer subagent execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality.
- Interpret `DONE_WITH_CONCERNS` as lane-local completion with follow-up concerns, not silent success.
- Treat lane-local completion and repo-global verification separately: a batch can be complete while `doctor` still reports repo verification blocked by baseline debt.
- Keep join point validation explicit in team-mode runs, and do not accept `idle` without the promised result handoff as completed work.

Generated project navigation now follows the handbook system:

- Generated projects include `PROJECT-HANDBOOK.md` as the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Treat the combined handbook/project-map surface as an atlas-style technical encyclopedia for dependency graph, runtime flows, state lifecycle, and change-impact view.
- `.specify/project-map/index/status.json` records the current handbook freshness baseline and dirty state.
- After a successful `map-build` run, use `project-map complete-refresh` as the standard completion hook to record the fresh baseline.
- Any code change that alters navigation meaning must update the handbook system.

Use support skills when they solve a specific gap:

- `map-scan` followed by `map-build` as the required brownfield gate when you are working in an existing codebase; generate the complete scan package first, then refresh the handbook/project-map navigation system before deeper workflow steps
- `auto` when the repository already records the recommended next step and you want a single state-driven continue entrypoint instead of naming the exact workflow yourself
- `prd-scan` followed by `prd-build` as the existing-project reverse PRD lane when you need repository-first current-state product documentation; it is the heavy reconstruction workflow, substantive scans are subagent-mandatory, critical claims target `L4 Reconstruction-Ready`, `config-contracts.json` is part of the scan contract surface, `prd-build` must not perform a second repository scan, it writes `.specify/prd-runs/<run-id>/`, and it does not automatically hand off to `plan`. `prd` remains a deprecated compatibility entrypoint that should route into the same pair
- Treat the handbook system as an atlas-style technical encyclopedia that gives agents a dependency graph, runtime flows, state lifecycle, and change-impact view before deeper brownfield work starts.
- `specify`, `clarify`, `deep-research`, `plan`, and `tasks` should not directly rewrite atlas content; when they discover the current atlas is too weak or likely outdated for the touched area, they should mark `.specify/project-map/index/status.json` dirty and run `map-scan` followed by `map-build` as the follow-up refresh workflow
- `clarify` when an existing spec still needs deeper analysis before planning
- `deep-research` when a planning-ready spec still needs feasibility evidence or a disposable demo before `plan`; `research` is only its compatibility alias
- `checklist` when you want to audit requirement quality after planning
- `analyze` as the required gate before implementation once `tasks.md` exists
- `debug` when you need to investigate blocked implementation work, regressions, or execution-time defects without reopening upstream planning artifacts unless drift is discovered
- When you run `analyze` and it finds upstream issues, it becomes a workflow gate, not a dead-end audit: reopen the highest invalid stage and regenerate downstream artifacts before continuing implementation
- `analyze` also flags boundary guardrail drift through `BG1`, `BG2`, and `BG3` when boundary-sensitive work was not preserved cleanly from plan to tasks to implementation guidance
- `analyze` should also flag subagent packet failures through `DP1`, `DP2`, and `DP3` when task packets or subagent results lose required rule-carrying evidence
- `explain` when you want the current spec, plan, task, implement, or handbook/project-map atlas artifact restated in plain language

If you're starting from an existing codebase, `map-scan` followed by `map-build` is the required brownfield gate before requirement, planning, task generation, or implementation work continues. Downstream workflows use `.specify/project-map/index/status.json` to decide whether the existing map is fresh, possibly stale, or stale.

Use the lightweight routing rules consistently:

- `fast` is only for trivial local fixes. Stay there only when the change is obvious, touches at most 3 files, and does not touch a shared surface.
- Upgrade to `quick` when the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `quick` is for small but non-trivial work that still fits one bounded quick-task workspace.
- If the work is a bug fix or regression and the root cause is still unknown, route to `debug` instead of using `quick` for a symptom-only patch.
- Quick workspaces live under `.planning/quick/<id>-<slug>/`, with `STATUS.md` as the source of truth and `.planning/quick/index.json` as a derived management index.
- Invoking `quick` with no arguments should resume unfinished quick work when possible. If exactly one unfinished quick task exists, continue it automatically. `blocked` quick tasks remain resumable.
- Use `specify quick list`, `specify quick status <id>`, `specify quick resume <id>`, `specify quick close <id> --status resolved|blocked`, and `specify quick archive <id>` to inspect and manage quick tasks. `specify quick list` defaults to unfinished quick tasks.
- Upgrade to `specify` when the request spans multiple independent capabilities, carries compatibility or rollout risk, or needs explicit acceptance criteria before implementation.

Required action markers:

- `[AGENT]` marks a required AI action and is independent from `[P]`.
- `[P]` still means parallel-safe work; `[AGENT]` does not imply parallelism or delegation by itself.
- Existing `AGENTS.md` files are extended through a managed `SPEC-KIT` block instead of full-file replacement.
- `fast`, `quick`, `map-scan`, and `map-build` are the first-wave `[AGENT]` workflows, and the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows now use the same marker for hard gates.

Passive project learning layer:

- Generated projects now include `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md` as stable shared project memory below the constitution.
- This shared project memory is available across later work in the repository, not just when a `sp-*` workflow is active.
- Runtime candidate learnings live under `.planning/learnings/candidates.md`, with `.planning/learnings/review.md` tracking passive promotion notes.
- The major workflow templates read this passive project learning layer before deeper command-local context so recurring pitfalls, constraints, and user defaults can influence later runs.
- The passive start step can auto-promote repeated candidates into shared learnings before the command does deeper local analysis, including repeated high-signal candidates that should no longer stay stuck in the candidate layer.
- Low-level helper commands exist for the passive lifecycle:
  - `specify learning ensure --format json`
  - `specify learning status --format json`
  - `specify learning start`
    - Command shape: `specify learning start --command <workflow> --format json`
  - `specify learning capture`
    - Required options: `--command`, `--type`, `--summary`, `--evidence`
  - `specify learning capture-auto`
    - Command shape: `specify learning capture-auto --command <workflow> --format json`
  - `specify implement closeout --feature-dir <feature-dir> --format json`
  - `specify learning aggregate --format json`
  - `specify learning promote`
    - Command shape: `specify learning promote --recurrence-key <key> --target learning|rule`
  - `specify hook signal-learning`
    - Command shape: `specify hook signal-learning --command <workflow> --retry-attempts <n> --hypothesis-changes <n>`
  - `specify hook review-learning`
    - Command shape: `specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"`
  - `specify hook capture-learning`
    - Required options: `--command`, `--type`, `--summary`, `--evidence`
  - `specify hook inject-learning`
    - Command shape: `specify hook inject-learning --command <workflow> --type <type> --summary "<summary>"`
- `specify learning aggregate --format json` groups repeated patterns so operators can decide what to promote into shared learnings or rules.
- Treat this as an internal/runtime helper surface, not as a separate daily slash workflow. `review-learning` is the terminal learning gate, and `capture-learning` preserves structured path-learning fields such as pain score, false starts, decisive signal, root-cause family, injection target, and promotion hint.
- Durable eval helpers exist once a rule should become executable proof instead of only remembered guidance:
  - `specify eval create --recurrence-key <key> ...`
  - `specify eval status --format json`
  - `specify eval run --format json`

First-party workflow quality hooks:

- Use `specify hook preflight --command <workflow> ...` when you want the product-level gate result rather than relying only on prompt wording.
- Use `specify hook validate-state --command <workflow> ...` and `specify hook validate-session-state --command <workflow> ...` to inspect or enforce the current source-of-truth workflow state.
- Use `specify hook validate-artifacts --command <workflow> --feature-dir <dir>` to check that the promised artifact set really exists.
- Use `specify hook checkpoint --command <workflow> ...` to build a resume-safe checkpoint from the active workflow state file.
- Use `specify hook monitor-context --command <workflow> ...` to trigger proactive checkpointing before compaction or a risky transition.
- Use `specify hook validate-packet --packet-file <path>` and `specify hook validate-result --packet-file <packet> --result-file <result>` for subagent integrity.
- Use `specify hook validate-read-path --target-path <path>` and `specify hook validate-prompt --prompt-text "<text>"` when path safety or workflow-bypass language is in doubt.
- Use `specify hook validate-boundary`, `validate-phase-boundary`, and `validate-commit` to enforce workflow transitions and commit-time integrity.
- Use `specify hook signal-learning`, `review-learning`, `capture-learning`, and `inject-learning` to turn passive project learning into a cross-workflow closeout gate instead of relying only on agent memory.

Claude Code project-local integration:

- `specify init --ai claude` installs `.claude/hooks/claude-hook-dispatch.py`, installs the shared launcher assets under `.specify/bin/`, and merges project-local `.claude/settings.json` when it is valid JSON.
- Generated Claude native hook registrations now call `.specify/bin/specify-hook` (or `.specify/bin/specify-hook.cmd` on Windows) instead of embedding `python` or `python3` directly.
- The shared launcher resolves Python at hook execution time, then delegates to the existing project-local Claude dispatch script.
- The current managed Claude native hooks bridge:
  - `SessionStart` into `specify hook render-statusline`
  - `UserPromptSubmit` into `specify hook validate-prompt`
  - `PreToolUse` into `specify hook validate-read-path` / `specify hook validate-commit`
  - `PostToolUse` into `specify hook validate-session-state` for active resumable workflows and soft `specify hook signal-learning` warnings when workflow state records reusable friction
  - `Stop` into `specify hook monitor-context --trigger before_stop` and soft `specify hook signal-learning` warnings when active workflow state crosses the pain threshold
- If an existing `.claude/settings.json` cannot be parsed, it is preserved and hook registration is skipped rather than overwritten.

Codex/OMX native integration:

- OMX manages Codex native hooks through `.codex/hooks.json` and `codex-native-hook.js`.
- The managed Codex native hooks cover `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- `PostToolUse` and `Stop` also surface soft `specify hook signal-learning` warnings when active workflow state records reusable friction.
- Learning capture and terminal learning review remain shared `specify hook capture-learning` / `review-learning` responsibilities rather than native-hook decisions.

Gemini native integration:

- `specify init --ai gemini` installs `.gemini/hooks/gemini-hook-dispatch.py`, installs the shared launcher assets under `.specify/bin/`, and merges project-local `.gemini/settings.json` when it is valid JSON.
- Generated Gemini native hook registrations now call `.specify/bin/specify-hook` (or `.specify/bin/specify-hook.cmd` on Windows) instead of embedding `python` or `python3` directly.
- The shared launcher resolves Python at hook execution time, then delegates to the existing project-local Gemini dispatch script.
- The managed Gemini native hooks bridge:
  - `SessionStart` into `specify hook render-statusline`
  - `BeforeAgent` into `specify hook validate-prompt` and soft `specify hook signal-learning` warnings when active workflow state records reusable friction
  - `BeforeTool` into `specify hook validate-read-path` / `specify hook validate-commit`
- Learning capture and terminal learning review remain shared `specify hook capture-learning` / `review-learning` responsibilities rather than native-hook decisions.

Native hook coverage matrix:

| Surface | Shared `specify hook ...` | Native adapter/runtime | Learning signal bridge | Native terminal review gate |
| --- | --- | --- | --- | --- |
| Claude | Yes | Yes | Yes | No |
| Codex/OMX | Yes | Yes | Yes | No |
| Gemini | Yes | Yes | Yes | No |
| Other integrations | Yes | No | No | No |

Active `sp-*` workflows now surface a structured recovery summary on resume. Prompt-entry policy uses redirect-first enforcement for phase drift, then hard-blocks repeated or explicit phase jumps so agents return to the recorded workflow state before coding or fix loops.

## Detailed Example: Building Taskify

Here's a complete example of building a team productivity platform:

### Step 1: Define Constitution

Initialize the project's constitution to set ground rules:

```markdown
/sp-constitution Taskify is a "Security-First" application. All user inputs must be validated. We use a microservices architecture. Code must be fully documented.
```

The following Taskify snippets use Claude-style `/sp-*` invocation syntax. If
your project was initialized for Codex, Kimi, or a slash-dot command
integration, translate each literal command through the invocation matrix above.

### Step 2: Define Requirements with `specify`

```text
Develop Taskify, a team productivity platform. It should allow users to create projects, add team members,
assign tasks, comment and move tasks between boards in Kanban style. In this initial phase for this feature,
let's call it "Create Taskify," let's have multiple users but the users will be declared ahead of time, predefined.
I want five users in two different categories, one product manager and four engineers. Let's create three
different sample projects. Let's have the standard Kanban columns for the status of each task, such as "To Do,"
"In Progress," "In Review," and "Done." There will be no login for this application as this is just the very
first testing thing to ensure that our basic features are set up.
```

### Step 3: Define the Plan

Once `specify` reaches planning-ready alignment, move directly to `plan`.

```bash
/sp-plan We are going to generate this using .NET Aspire, using Postgres as the database. The frontend should use Blazor server with drag-and-drop task boards, real-time updates. There should be a REST API created with a projects API, tasks API, and a notifications API.
```

If an existing spec needs deeper analysis first, use `clarify`.

```bash
/sp-clarify Add sharper reporting requirements and cross-team notification expectations before planning.
```

If the spec is clear but feasibility is still uncertain, use `deep-research`
before planning so research findings, demo evidence, rejected options, and
constraints become plan inputs.

```bash
/sp-deep-research Prove whether the notification provider can support the required retry and audit trail behavior with a small disposable spike, and produce a Planning Handoff for plan.
```

`research` is accepted only as a compatibility alias for the same workflow.

### Step 4: Validate the Spec

Validate the specification checklist using the `checklist` workflow:

```bash
/sp-checklist
```

### Step 5: Define Tasks

Generate an actionable task list using the `tasks` workflow:

```bash
/sp-tasks
```

### Step 6: Validate and Implement

Have your AI agent audit the implementation plan using `analyze`:

```bash
/sp-analyze
```

If `analyze` finds issues, do not treat the report as informational only:

- If the problem is in `spec.md` or `context.md`, return to `clarify`, then rerun `plan`, `tasks`, and `analyze`.
- If the problem is in `plan.md`, return to `plan`, then rerun `tasks` and `analyze`.
- If the problem is only in `tasks.md`, rerun `tasks`, then `analyze`.
- If the problem is execution-only with no upstream artifact drift, continue in `implement` or route into `debug`.
- If analysis happens after implementation has already started or finished, treat the current implementation as provisional until the highest invalid stage has been repaired and downstream artifacts have been regenerated.

Finally, implement the solution:

```bash
/sp-implement
```

> [!TIP]
> **Phased Implementation**: For large projects like Taskify, consider implementing in phases (e.g., Phase 1: Basic project/task structure, Phase 2: Kanban functionality, Phase 3: Comments and assignments). This prevents context saturation and allows for validation at each stage.

## Key Principles

- **Be explicit** about what you're building and why
- **Don't focus on tech stack** during specification phase
- **Use `specify -> plan` as the default path**
- **Use `clarify` only when an existing spec needs deeper analysis before planning**
- **Use `deep-research` only when feasibility or the implementation chain must be proven before planning, and preserve its Planning Handoff as plan input; treat `research` as a compatibility alias, not a separate workflow**
- **Use failing test first** for `sp-fast`, `sp-quick`, `sp-implement`, and `sp-debug`; if the touched behavior has no viable automated test surface yet, run `sp-test-scan` first for deep evidence gathering, then use `sp-test-build` when scan-approved lanes can bootstrap the bundled language testing skills, establish a coverage baseline, leave manual validation evidence behind, and emit `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` for any brownfield testing-system program or coverage uplift program that needs follow-on routing.
- **Validate** the plan before coding begins
- **Let the AI agent handle** the implementation details

## Next Steps

- Read the [complete methodology](https://github.com/chenziyang110/spec-kit-plus/blob/main/spec-driven.md) for in-depth guidance
- Check out [more examples](https://github.com/chenziyang110/spec-kit-plus/tree/main/templates) in the repository
- Explore the [source code on GitHub](https://github.com/chenziyang110/spec-kit-plus)
