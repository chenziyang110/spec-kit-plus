# Spec Kit Plus

`spec-kit-plus` is a maintained fork of Spec Kit focused on practical Spec-Driven Development workflow support for local AI coding agents.

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

Upgrade to the latest version from this fork:

```bash
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

### One-time use without installing

```bash
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init my-project --ai codex
```

Initialize the current directory with the latest fork version, without relying on whatever `specify` is currently on your `PATH`:

```bash
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init . --ai codex
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
5. `implement` to execute the task plan (supports autonomous loop via `/sp-autonomous`)

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

Skill map after `specify init`:

- Core workflow skills: `constitution`, `specify`, `plan`, `tasks`, `implement`
- Support skills: `map-codebase`, `test`, `spec-extend`, `checklist`, `analyze`, `debug`, `explain`
- Codex-only runtime: `specify team` and `sp-team`

Conditional gates and follow-up commands:

- `map-codebase` is the required brownfield gate for an existing codebase; generate or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` before specification, planning, task generation, or implementation continues
- Treat the handbook system as an atlas-style technical encyclopedia that gives agents a dependency graph, runtime flows, state lifecycle, and change-impact view before deeper brownfield work starts.
- `test` to bootstrap or refresh a durable project-wide unit testing system, testing contract, and standard test/coverage playbook
- `spec-extend` to deepen an existing spec before planning when analysis, references, or gaps need more work
- `checklist` to generate requirement-quality checklists after planning so the written requirements can be audited before implementation
- `analyze` is the default pre-implementation gate once `tasks.md` exists; run the cross-artifact consistency pass across `spec.md`, `context.md`, `plan.md`, and `tasks.md` before implementation starts
- `debug` to investigate blocked implementation work, regressions, or execution-time defects without reopening upstream planning artifacts unless drift is discovered
- `explain` to describe the current spec, plan, task, implement, or handbook/project-map atlas artifact in plain language
- when you run `analyze` and it finds upstream issues, it becomes a workflow gate, not a dead-end audit: reopen the highest invalid stage and regenerate downstream artifacts before continuing implementation
- `analyze` now also detects boundary guardrail drift through stable issue codes: `BG1` (missing `Implementation Constitution`), `BG2` (missing task guardrails), and `BG3` (missing implementation-time boundary confirmation)
- `analyze` should also surface delegated-execution packet gaps through `DP1` (missing compiled hard rules), `DP2` (missing required references or forbidden drift), and `DP3` (missing worker validation evidence)

Already have code? Run `map-codebase` first and treat it as the required brownfield gate before deeper specification, planning, task generation, or implementation work.
Generated projects also track handbook freshness in `.specify/project-map/status.json`, so brownfield workflows can decide whether the current atlas baseline is fresh, possibly stale, or stale before proceeding.

Routing guide for lightweight work:

- `sp-fast` is only for trivial local fixes. Stay on that path only when the change is obvious, touches at most 3 files, and does not touch a shared surface.
- Move from `sp-fast` to `sp-quick` as soon as the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `sp-quick` is for small but non-trivial work that still fits one bounded quick-task workspace.
- If the work is a bug fix or regression and the root cause is still unknown, use `sp-debug` instead of treating `sp-quick` as a symptom-fix lane.
- Behavior-changing work across `sp-fast`, `sp-quick`, `sp-implement`, and `sp-debug` now follows a failing test first rule. Capture a RED state before production edits; if the touched area lacks a viable automated test surface, bootstrap it through `sp-test` before continuing.
- Quick workspaces now live under `.planning/quick/<id>-<slug>/`, with `STATUS.md` as the task source of truth and `.planning/quick/index.json` as a derived management index.
- Invoking `sp-quick` with no arguments should resume unfinished quick work when possible. If only one unfinished quick task exists, continue it automatically. `blocked` quick tasks still count as resumable unfinished work.
- Use `specify quick list`, `specify quick status <id>`, `specify quick resume <id>`, `specify quick close <id> --status resolved|blocked`, and `specify quick archive <id>` to inspect and manage tracked quick tasks. `specify quick list` defaults to unfinished quick tasks.
- Move from `sp-quick` to `sp-specify` when the request spans multiple independent capabilities, carries compatibility or rollout risk, or needs explicit acceptance criteria before implementation.

Required action markers:

- `[AGENT]` marks a required AI action and is independent from `[P]`.
- `[P]` still means parallel-safe work; `[AGENT]` does not imply parallelism, delegation, or worker routing by itself.
- Existing `AGENTS.md` files are extended through a managed `SPEC-KIT` block instead of full-file append or replacement.
- First-wave `[AGENT]` coverage started with `sp-fast`, `sp-quick`, and `sp-map-codebase`; the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows now use the same marker for hard gates and required state updates.

Passive project learning layer:

- Generated projects now include `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md` as stable shared project memory below the constitution.
- Runtime candidate learnings live under `.planning/learnings/candidates.md`, with `.planning/learnings/review.md` tracking passive promotion notes.
- The major workflow templates now read the passive project learning layer before deeper command-local context so recurring pitfalls, constraints, and user defaults can influence later runs.
- The passive start step can auto-promote repeated non-high-signal candidates into shared learnings before the command does deeper local analysis.
- Low-level helper commands exist for the passive learning lifecycle:
- `specify learning ensure --format json`
- `specify learning status --format json`
- `specify learning start --command <workflow> --format json`
- `specify learning capture --command <workflow> ...`
- `specify learning capture-auto --command <workflow> ...`
- `specify implement closeout --feature-dir <feature-dir> --format json`
- `specify learning aggregate --format json`
- `specify learning promote --recurrence-key <key> --target learning|rule`
- `specify hook signal-learning --command <workflow> ...`
- `specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> ...`
- `specify hook capture-learning --command <workflow> --type <type> --summary "..." --evidence "..."`
- `specify hook inject-learning --command <workflow> --type <type> --summary "..."`
- Use `specify learning aggregate` when you want a grouped, promotion-oriented summary of candidate, confirmed, and promoted learning patterns before deciding what should become a shared learning or rule.
- This is an internal/runtime helper surface, not a new daily `sp-` workflow. The intent is passive reuse across every `sp-*` workflow, with `review-learning` acting as the terminal learning gate and `capture-learning` preserving structured path-learning fields such as pain score, false starts, decisive signal, root-cause family, injection target, and promotion hint.

First-party workflow quality hooks:

- `specify hook preflight --command <workflow> ...` runs the shared product gate before a workflow continues.
- `specify hook validate-state --command <workflow> ...` checks workflow state truth such as `workflow-state.md`, `implement-tracker.md`, or quick-task `STATUS.md`.
- `specify hook validate-artifacts --command <workflow> --feature-dir <dir>` machine-checks the minimum artifact set instead of trusting chat progress.
- `specify hook checkpoint --command <workflow> ...` emits a resume-safe checkpoint payload from the active source-of-truth state file.
- `specify hook monitor-context --command <workflow> ...` recommends proactive checkpointing when context pressure or a risky structural transition appears.
- `specify hook validate-session-state --command <workflow> ...` reconciles resume-critical state across the active workflow surfaces.
- `specify hook render-statusline --command <workflow> ...` returns a compact operator-facing status summary.
- `specify hook validate-packet --packet-file <path>` and `specify hook validate-result --packet-file <packet> --result-file <result>` enforce the shared delegated execution contract.
- `specify hook validate-read-path --target-path <path>` and `specify hook validate-prompt --prompt-text "<text>"` provide shared read-boundary and prompt-bypass guards.
- `specify hook validate-boundary`, `validate-phase-boundary`, and `validate-commit` cover workflow transitions and last-mile commit integrity.
- `specify hook signal-learning`, `review-learning`, `capture-learning`, and `inject-learning` turn passive project learning into a cross-workflow closeout gate instead of relying only on agent memory.
- `specify hook mark-dirty --reason "<reason>"` and `specify hook complete-refresh` are the shared product paths for project-map freshness updates.

Claude Code integration note:

- `specify init --ai claude` installs thin native adapters in `.claude/hooks/` and merges project-local `.claude/settings.json`.
- The current managed Claude native hook set covers:
  - `SessionStart` statusline/orientation context derived from active workflow state
  - `UserPromptSubmit` prompt-guard checks
  - `PreToolUse` read-boundary and inline commit-message validation
  - `PostToolUse` session-state drift warnings for active implement/quick/debug flows, plus soft `signal-learning` warnings when workflow state records reusable friction
  - `Stop` context-monitor checkpoint blocking or advisory output before stop, plus soft `signal-learning` warnings when active workflow state crosses the pain threshold
- These adapters are intentionally thin: they call back into the shared `specify hook ...` command surface instead of re-implementing workflow truth inside standalone Claude scripts.

Codex/OMX integration note:

- The OMX runtime manages Codex native hooks through `.codex/hooks.json` and `codex-native-hook.js`.
- The managed Codex native hook set covers `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- `PostToolUse` and `Stop` bridge shared `specify hook signal-learning` warnings when active workflow state records reusable friction.
- Learning capture and terminal learning review still stay in the shared `specify hook capture-learning` / `review-learning` surfaces; native Codex hooks only surface the signal.

Gemini integration note:

- `specify init --ai gemini` installs thin native adapters in `.gemini/hooks/` and merges project-local `.gemini/settings.json`.
- The managed Gemini native hook set covers `SessionStart`, `BeforeAgent`, and `BeforeTool`.
- `BeforeAgent` applies shared prompt guards and soft `signal-learning` warnings when active workflow state records reusable friction.
- `BeforeTool` applies shared read-boundary and inline commit-message validation.
- As with Claude and Codex, learning capture and terminal review remain shared `specify hook capture-learning` / `review-learning` responsibilities.

Native hook coverage matrix:

| Surface | Shared `specify hook ...` | Native adapter/runtime | Learning signal bridge | Native terminal review gate |
| --- | --- | --- | --- | --- |
| Claude | Yes | Yes | Yes | No |
| Codex/OMX | Yes | Yes | Yes | No |
| Gemini | Yes | Yes | Yes | No |
| Other integrations | Yes | No | No | No |

After planning, continue with:

```text
tasks -> analyze -> implement
```

Closed-loop remediation after `analyze`:

- If the defect is in `spec.md` or `context.md`, go back to `spec-extend`, then rerun `plan`, `tasks`, and `analyze` before resuming `implement`.
- If the defect is in `plan.md`, go back to `plan`, then rerun `tasks` and `analyze` before resuming `implement`.
- If the defect is only in `tasks.md`, rerun `tasks`, then `analyze`, then resume `implement`.
- If the defect is execution-only with no upstream artifact drift, continue in `implement` or route into `debug`.
- If `analyze` is run after `implement` has already started or finished, treat the current implementation as provisional until the highest invalid stage has been repaired and downstream artifacts have been regenerated.

Boundary-sensitive implementation rule:

- If the feature touches an established boundary pattern in the target project, `plan` should write an `Implementation Constitution` section instead of leaving that rule buried in technical background.
- Use `Implementation Constitution` for architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus.
- Typical triggers include existing framework-owned boundaries, native/plugin bridges, protocol seams, generated API surfaces, or any area where "generic implementation instinct" would likely drift from the repository's established pattern.
- A good heuristic is: if an implementer should be forced to inspect specific existing boundary files before coding safely, the feature likely needs `Implementation Constitution`.
- `tasks` should convert those rules into explicit implementation guardrails before setup or feature work begins.
- `tasks` should also preserve a `Task Guardrail Index` or equivalent task-to-guardrail mapping when delegated execution needs task-local rule inheritance.
- `implement` should treat those guardrails as binding execution constraints and confirm the touched boundary's owning framework, defining reference files, and forbidden drift before dispatching code-writing work.
- Delegated execution should no longer rely on raw task text when architecture or quality rules matter.
- `plan` should provide `Dispatch Compilation Hints`.
- `implement` should compile and validate a `WorkerTaskPacket` before dispatching native workers or sidecar workers.
- Delegated packets should carry platform guardrails when a lane depends on supported-platform constraints, conditional compilation, or environment-sensitive runtime assumptions.

Current `sp-implement` runtime model in this fork:

- `sp-implement` acts as a milestone-level orchestration leader rather than the direct executor
- concrete implementation runs through delegated execution paths (`single-lane`, `native-multi-agent`, or `sidecar-runtime`)
- delegated workers should execute from compiled `WorkerTaskPacket` contracts rather than rediscovering rules from background context
- delegated result handoff should use the runtime-managed result channel when one exists; otherwise workers should write normalized result envelopes to the declared filesystem handoff path for the current workflow
- implementation lanes without a runtime-managed channel should use `FEATURE_DIR/worker-results/<task-id>.json`
- quick-task lanes without a runtime-managed channel should use `.planning/quick/<id>-<slug>/worker-results/<lane-id>.json`
- debug evidence lanes without a runtime-managed channel should use `.planning/debug/results/<session-slug>/<lane-id>.json`
- when the local CLI is available and no runtime-managed result channel exists, prefer `specify result path` to compute the canonical handoff target and `specify result submit` to normalize and write the delegated result envelope
- when worker language is normalized into canonical orchestration state, preserve the raw `reported_status`
- top-level `tasks.md` items should stay bounded to one coffee-break-sized implementation slice, usually roughly 10-20 minutes, while delegated workers may still execute them through smaller 2-5 minute atomic steps
- task decomposition should stay progressive: refine only the current executable window after each join point instead of pre-expanding later batches that still depend on upstream evidence
- parallel work is coordinated through explicit join points before dependent work continues
- every join point that gates downstream work should name a validation target, a validation command or check, and a pass condition
- grouped parallelism is the default when ready tasks have isolated write sets; use a pipeline shape only when outputs must flow stage-by-stage and keep explicit checkpoints between stages
- high-risk batches touching shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces should add a review gate before crossing the join point
- if a read-only verification lane is available, use one peer-review lane only for those high-risk batches rather than for every batch
- runtime surfaces can report retry-pending work and blockers instead of hiding those states in chat-only narration
- blocked delegated worker results should carry the blocker, the failed assumption, and the smallest safe recovery step so the leader can fail fast instead of guessing
- if a delegated lane reports `completed` or drifts into `idle` before the promised handoff arrives, treat it as a stale lane and recover explicitly instead of assuming success
- established boundary patterns should be preserved through `Implementation Constitution` and implementation guardrails, not rediscovered ad hoc during coding

Shared runtime-facing guidance across integrations:

- `sp-implement`, `sp-debug`, and `sp-quick` now all carry a shared leader contract, delegation-surface contract, and worker-result contract across Markdown, TOML, and skills-based integrations.
- The shared contract is integration-neutral: leader role, join-point discipline, structured handoff expectations, `reported_status` preservation, and sidecar fallback semantics are common across CLIs.
- Only the concrete native dispatch surface remains integration-specific. For example, Codex may name `spawn_agent` and `specify team`, while another CLI may expose only a generic native delegated worker surface or no sidecar runtime at all.

For Codex and other skills-based integrations, the generated commands are installed in skills form. Codex now uses the dedicated `.codex/skills/` directory for generated skills.

Skills-based projects now install two layers into the same skills directory:

- explicit workflow skills: `sp-*`
- passive bundled skills: keep the directory names from `templates/passive-skills/` (for example `spec-kit-*`, `tdd-workflow`, `frontend-design`)

`sp-*` remains the primary user-facing workflow surface. Passive skills keep their template names and exist to improve automatic routing, guardrails, and bundled capabilities inside Spec Kit Plus repositories, not to replace the explicit workflow commands.

## Multi-CLI Orchestration (Milestones 1-2)

Current orchestration status in this fork:

- generic orchestration core exists under `src/specify_cli/orchestration/`
- `specify`, `plan`, `tasks`, `test`, `map-codebase`, `explain`, `debug`, `implement`, and `quick` now surface `single-lane`, `native-multi-agent`, and `sidecar-runtime` in user-facing workflow guidance
- `single-lane` is the topology label for one safe execution lane, not a synonym for either worker-only or leader-only execution
- in execution-oriented workflows, prefer delegated worker execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality
- `specify`, `plan`, `tasks`, and `explain` now document workflow-specific lanes and join points while keeping shared workflow templates integration-neutral
- `specify team` remains the Codex compatibility surface for runtime-heavy execution
- Claude, Gemini, and Copilot ship first-release adapter skeletons (alongside Codex) for native-first capability reporting
- durable runtime maturity for `implement` and `debug`, plus wider integration rollout, remain future work

This repository is no longer only a Milestone 1 slice, but the full execution/runtime maturity roadmap is still not complete.

## Codex Team Runtime

This fork now exposes a Codex-only first-release team/runtime surface through:

```bash
specify team
```

### The `specify team` surface

`specify team` is the official CLI surface for the runtime. All operations start from this command, so avoid advertising other entry points such as `omx` or `$team`.

- `specify team watch` opens a full-screen observer over members and flow, with lightweight terminal interaction for focus switching, detail expansion, and view cycling.
- `specify team status` dumps the latest JSON snapshot of the team phase, worker roster, task queue, and mailbox state.
- `specify team await` blocks until the runtime reaches a terminal phase so operators can wait for batch completion.
- `specify team resume` re-attaches to an existing runtime session by replaying the metadata in `.specify/codex-team/` and restarting the tmux backend.
- `specify team shutdown` requests a graceful stop, letting workers finish or fail their in-flight tasks before tearing down.
- `specify team cleanup` removes `.specify/codex-team/` state after shutdown succeeds; run it only once shutdown has settled to avoid corrupting the state folder.
- `specify team submit-result --request-id <id> --result-file <path>` validates and records a structured worker result for an existing dispatch. Use `specify team result-template --request-id <id>` only to generate the canonical `pending` placeholder; do not submit that template unchanged.
- `specify team api <operation>` proxies structured JSON operations (task claims, worker heartbeats, events) into the runtime; use it when automation needs a predictable channel.

For agents and automation, prefer the optional MCP supplement instead of having the model compose CLI invocations directly:

- `specify-teams-mcp` exposes an agent-facing MCP facade for the structured control plane
- install the optional facade with `pip install "specify-cli[mcp]"`; Codex config can register it only when that extra is available
- if you install the MCP extra after project init, refresh the generated Codex config with `scripts/sync-ecc-to-codex.sh` or `scripts/powershell/sync-ecc-to-codex.ps1`
- the MCP layer is intended for agent/tool consumers
- `specify team` remains the human/operator CLI and parity fallback surface

This command suite powers both the `sp-team` skill and the runtime APIs that downstream tooling relies on, which is why the command is restricted to Codex-initiated projects.

### Runtime state location and lifecycle

All runtime state lives under `.specify/codex-team/`:

- `runtime.json` contains the active session metadata and canonical root paths.
- `state/` holds per-object JSON files (`tasks/*.json`, `workers/*.json`, `mailboxes/*.json`, `dispatch/*.json`) along with `phase.json` and `events.log` for the lifecycle stream.
- Heartbeats, claims, approvals, and monitor snapshots append to the files under `state/`, helping the CLI restart from the latest saved facts.

Lifecycle notes:

- Tasks run through `pending -> in_progress -> completed|failed` and emit events that `specify team status` surfaces.
- Workers claim tasks with identity records, write heartbeats under `state/workers`, and consume mailbox messages from `state/mailboxes`.
- Structured worker results live under `state/results/` and are submitted through `specify team submit-result` / `specify team api submit-result` before `complete-batch` should mark a structured-result batch done.
- Shutdown requests append a terminal event, and cleanup removes the `.specify/codex-team/` directory once all JSON files have been archived.

Operators should treat this directory as the single source of truth for resumes, restarts, and audits, and not attempt to recreate state outside the official CLI surface.

### Operator guidance and backend requirements

- The runtime currently requires a tmux-capable backend (`tmux` on Unix/WSL or a Windows-compatible alternative) to host worker panes; the CLI validates the backend before bootstrapping a session.
- `specify team watch` is the operator-facing live board: use it when you need a continuous view of members and flow instead of one-shot diagnostics.
- Use `specify team resume` whenever a previously-running session still holds worker heartbeats or task claims to prevent duplicate boots.
- Issue `specify team shutdown` before terminating the tmux backend so the runtime can flush claims and notify join points, then run `specify team cleanup` once the CLI reports the phase is `shutdown`/`cleaned`.
- `specify team await` is useful for scripts that need to pause until the team exits the `dispatch` phase without polling `state/` files directly.

### Release isolation guidance

Current release scope:

- Codex-only for first release
- requires a tmux-capable environment
- installs the Codex team skill as `sp-team`
- keeps non-Codex integrations free of the team/runtime surface by default
- installs runtime helper assets only under `.specify/codex-team/` for Codex projects

Existing Codex projects may use an optional upgrade path, but that upgrade remains optional, non-blocking release support rather than a first-release requirement.

Release isolation guidance:

- `specify init --ai codex` may generate `sp-team` and `.specify/codex-team/*`
- non-Codex init flows must not generate `sp-team`, `.specify/codex-team/*`, or advertise `specify team`
- `omx` and `$team` are not the supported product surface for this repository

Maintainer note:

- keep Codex team assets and messaging behind Codex-only install and help paths unless the release boundary is intentionally widened

## Key Commands

```bash
specify init <project> --ai <agent>
specify check
specify result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>
specify result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id> --result-file <path>
specify extension list
specify preset list
```

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

## Project Handbook System

Navigation and technical truth are now handbook-first:

- Generated projects include `PROJECT-HANDBOOK.md` as the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Treat the combined handbook/project-map surface as an atlas-style technical encyclopedia for dependency graph, runtime flows, state lifecycle, and change-impact view.
- `.specify/project-map/status.json` records the last successful map refresh and dirty state for freshness checks.
- After a successful `map-codebase` refresh, use `project-map complete-refresh` as the standard completion hook to record the new fresh baseline.
- Any code change that alters navigation meaning must update the handbook system.

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
