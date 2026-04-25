# Native Windows Specify Team Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the first native Windows Codex team-runtime milestone real by standardizing on `psmux`, routing `sp-implement-teams` through `specify team`, preferring tracker-driven recovery over stale `tasks.md`, and fixing Windows-native runtime bootstrap artifacts.

**Architecture:** Keep the existing `specify team` product surface and refine its internals instead of extending the legacy `agent-teams` bridge. First lock the new contract in tests and generated-skill expectations. Then fix Windows-native runtime detection and build logic. Next add a state-first implementation batch materializer that can recover from `implement-tracker.md` before falling back to `tasks.md`. Finally reroute the Codex `sp-implement-teams` skill and `team auto-dispatch` help surface onto the canonical runtime wording and verify the end-to-end path.

**Tech Stack:** Python, Typer CLI, Markdown skill templates, pytest, PowerShell/bash helper scripts, vendored TypeScript runtime bridge metadata

---

## File Structure

- Modify: `templates/commands/implement-teams.md`
  - Replace legacy extension/`tasks.md` language with native Windows + `psmux` + `specify team` guidance.
- Modify: `src/specify_cli/integrations/codex/__init__.py`
  - Keep Codex generated skill augmentation aligned with the new `sp-implement-teams` contract.
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
  - Tighten Windows readiness checks, prefer `psmux`, and surface native-toolchain expectations.
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
  - Add state-first batch materialization from `implement-tracker.md` and phase-plan fallbacks before `tasks.md`.
- Modify: `src/specify_cli/execution/packet_compiler.py`
  - Stop assuming delegated packets can only be compiled from `tasks.md`.
- Modify: `src/specify_cli/__init__.py`
  - Update `team auto-dispatch` help text and any runtime/API wording that still hardcodes `tasks.md`.
- Modify: `extensions/agent-teams/scripts/build-engine.sh`
  - Accept `omx-runtime.exe` as a built Windows artifact.
- Modify: `extensions/agent-teams/engine/src/runtime/bridge.ts`
  - Accept Windows `.exe` runtime binary discovery.
- Modify: `tests/codex_team/test_runtime_bridge.py`
  - Cover Windows native readiness details and `.exe`-aware runtime bootstrap detection.
- Modify: `tests/codex_team/test_auto_dispatch.py`
  - Cover tracker-first batch recovery and fallback ordering.
- Modify: `tests/codex_team/test_implement_runtime_routing.py`
  - Lock the shared workflow contract wording around tracker/state-first execution.
- Modify: `tests/integrations/test_integration_codex.py`
  - Lock the generated Codex `sp-implement-teams` skill wording and remove extension-plumbing expectations.

---

### Task 1: Lock the new native Windows runtime contract in tests first

**Files:**
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/codex_team/test_runtime_bridge.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`

- [ ] **Step 1: Add failing skill-generation assertions for the new `sp-implement-teams` contract**

```python
def test_codex_generated_sp_implement_teams_skill_exists_and_is_codex_only(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-implement-teams"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-implement-teams" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert "native windows + psmux" in content
    assert "specify team" in content
    assert "implement-tracker.md" in content
    assert "state-first" in content or "execution-state source of truth" in content
    assert "sp.agent-teams.run" not in content
    assert "specify extension add agent-teams" not in content
```

- [ ] **Step 2: Add failing runtime-bridge assertions for native Windows toolchain guidance**

```python
def test_runtime_status_reports_native_windows_toolchain_requirements(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\\psmux.exe" if name == "psmux" else None,
    )

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["runtime_backend"] == "psmux"
    assert status["native_windows"] is True
    assert "single native shell" in " ".join(status["next_steps"]).lower() or status["teams_ready"] is True
```

- [ ] **Step 3: Add failing auto-dispatch assertions for tracker-first recovery**

```python
def test_route_ready_parallel_batch_prefers_tracker_state_over_stale_tasks(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\\psmux.exe" if name == "psmux" else None,
    )

    feature_dir = codex_team_project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Old foundational task\n", encoding="utf-8")
    (feature_dir / "implement-tracker.md").write_text(
        \"\"\"---
status: executing
feature: 001-test-feature
created: 2026-04-25T00:00:00+00:00
updated: 2026-04-25T00:00:00+00:00
resume_decision: resume-here
---

## Current Focus
current_batch: phase3-bll-aria2
goal: Resume the active refactor batch
next_action: Dispatch BLL and Aria2 lanes

## Execution State
completed_tasks:
  - T001
in_progress_tasks:
  - BLL-lane
failed_tasks:
retry_attempts: 0
\"\"\",
        encoding="utf-8",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    assert result.batch_name == "phase3-bll-aria2"
    assert result.dispatched_task_ids != ["T001"]
```

- [ ] **Step 4: Run the targeted tests to verify they fail for the expected reasons**

Run:

```bash
python -m pytest tests/integrations/test_integration_codex.py -k implement_teams
python -m pytest tests/codex_team/test_runtime_bridge.py -k native_windows_toolchain
python -m pytest tests/codex_team/test_auto_dispatch.py -k tracker_state_over_stale_tasks
```

Expected:

- the generated-skill test fails because the current template still mentions `tasks.md`, `sp.agent-teams.run`, and extension install guidance
- the runtime-bridge test fails because no native-shell/toolchain guidance is surfaced yet
- the auto-dispatch test fails because dispatch still reads `tasks.md` directly

### Task 2: Fix Windows-native runtime binary and readiness behavior

**Files:**
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `extensions/agent-teams/scripts/build-engine.sh`
- Modify: `extensions/agent-teams/engine/src/runtime/bridge.ts`
- Modify: `tests/codex_team/test_runtime_bridge.py`

- [ ] **Step 1: Add failing tests for `.exe` runtime artifact detection**

```python
def test_runtime_bridge_accepts_windows_runtime_exe(monkeypatch, tmp_path: Path):
    from specify_cli.codex_team.runtime_bridge import resolve_agent_teams_runtime_binary

    engine_root = tmp_path / "engine"
    release_dir = engine_root / "target" / "release"
    release_dir.mkdir(parents=True)
    runtime_exe = release_dir / "omx-runtime.exe"
    runtime_exe.write_text("", encoding="utf-8")

    resolved = resolve_agent_teams_runtime_binary(engine_root)

    assert resolved == runtime_exe
```

- [ ] **Step 2: Run the runtime-bridge test to watch it fail**

Run:

```bash
python -m pytest tests/codex_team/test_runtime_bridge.py -k runtime_exe
```

Expected:

- fail with missing helper or unresolved bare `omx-runtime` path behavior

- [ ] **Step 3: Implement minimal `.exe`-aware runtime discovery and Windows-native readiness messaging**

```python
def _candidate_runtime_paths(engine_root: Path) -> list[Path]:
    release_dir = engine_root / "target" / "release"
    debug_dir = engine_root / "target" / "debug"
    candidates = [
        release_dir / "omx-runtime",
        release_dir / "omx-runtime.exe",
        debug_dir / "omx-runtime",
        debug_dir / "omx-runtime.exe",
    ]
    return candidates


def resolve_agent_teams_runtime_binary(engine_root: Path) -> Path | None:
    for candidate in _candidate_runtime_paths(engine_root):
        if candidate.is_file():
            return candidate
    return None
```

```bash
#!/usr/bin/env bash
set -e

EXT_DIR=".specify/extensions/agent-teams/engine"
RUST_TARGET="$EXT_DIR/target/release/omx-runtime"
RUST_TARGET_EXE="$EXT_DIR/target/release/omx-runtime.exe"
RUNTIME_CLI="$EXT_DIR/dist/team/runtime-cli.js"

if { [ -f "$RUST_TARGET" ] || [ -f "$RUST_TARGET_EXE" ]; } && [ -f "$RUNTIME_CLI" ] && [ -d "$EXT_DIR/node_modules" ]; then
    exit 0
fi
```

```ts
export function resolveRuntimeBinaryPath(options: RuntimeBinaryDiscoveryOptions = {}): string {
  const exists = options.exists ?? existsSync;
  const envOverride = process.env.OMX_RUNTIME_BINARY?.trim();
  if (envOverride) return envOverride;

  const workspaceDebug = options.debugPath ?? resolve(__bridge_dirname, '../../target/debug/omx-runtime');
  const workspaceDebugExe = `${workspaceDebug}.exe`;
  if (exists(workspaceDebug)) return workspaceDebug;
  if (exists(workspaceDebugExe)) return workspaceDebugExe;

  const workspaceRelease = options.releasePath ?? resolve(__bridge_dirname, '../../target/release/omx-runtime');
  const workspaceReleaseExe = `${workspaceRelease}.exe`;
  if (exists(workspaceRelease)) return workspaceRelease;
  if (exists(workspaceReleaseExe)) return workspaceReleaseExe;

  return options.fallbackBinary ?? 'omx-runtime';
}
```

- [ ] **Step 4: Re-run the runtime tests and build-script assertions**

Run:

```bash
python -m pytest tests/codex_team/test_runtime_bridge.py -k "runtime_exe or native_windows"
```

Expected:

- all new runtime detection and native Windows readiness tests pass

### Task 3: Add state-first implementation batch materialization

**Files:**
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`

- [ ] **Step 1: Add failing materialization tests before touching production code**

```python
def test_compile_worker_task_packet_accepts_materialized_task_input(tmp_path: Path):
    from specify_cli.execution.packet_compiler import compile_worker_task_packet

    project_root = tmp_path
    feature_dir = tmp_path / "specs" / "001-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text("- MUST preserve runtime contract\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("## Required Implementation References\n- `src/contracts.py`\n", encoding="utf-8")

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="BLL-lane",
        task_body="[US1] Refactor BLL lane in src/bll_manager.py",
    )

    assert packet.task_id == "BLL-lane"
    assert "src/bll_manager.py" in packet.scope.write_scope
```

```python
def test_materialize_runtime_batch_from_tracker_uses_current_batch_metadata(codex_team_project_root: Path):
    from specify_cli.codex_team.auto_dispatch import materialize_runtime_batch

    feature_dir = codex_team_project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        \"\"\"---
status: executing
feature: 001-test-feature
created: 2026-04-25T00:00:00+00:00
updated: 2026-04-25T00:00:00+00:00
resume_decision: resume-here
---

## Current Focus
current_batch: phase3-bll-aria2
goal: Resume the active refactor batch
next_action: Dispatch BLL and Aria2 lanes

## Execution State
completed_tasks:
  - T001
in_progress_tasks:
failed_tasks:
retry_attempts: 0

## User Execution Notes
- note: BLL lane touches JZDownloader/BLLDownloadManager.cpp
  source: sp-implement arguments
  priority: high
  applies_to: current feature execution
\"\"\",
        encoding="utf-8",
    )
    (feature_dir / "phase3-refactor-plan.md").write_text(
        \"\"\"## Batch phase3-bll-aria2
- BLL-lane Refactor BLLDownloadManager in JZDownloader/BLLDownloadManager.cpp
- Aria2-lane Continue the Aria2 split in JZDownloader/Aria2Adapter.cpp
\"\"\",
        encoding="utf-8",
    )

    batch = materialize_runtime_batch(feature_dir)

    assert batch.batch_name == "phase3-bll-aria2"
    assert [task.task_id for task in batch.tasks] == ["BLL-lane", "Aria2-lane"]
```

- [ ] **Step 2: Run the materialization tests to verify they fail**

Run:

```bash
python -m pytest tests/codex_team/test_auto_dispatch.py -k "materialize_runtime_batch or materialized_task_input"
```

Expected:

- fail because no materializer exists and packet compilation still requires `tasks.md`

- [ ] **Step 3: Implement a minimal tracker/phase-plan-first materialization path**

```python
@dataclass(slots=True)
class MaterializedTask:
    task_id: str
    summary: str
    task_body: str
    completed: bool = False
    parallel: bool = True
    agent_required: bool = True


@dataclass(slots=True)
class MaterializedBatch:
    batch_name: str
    join_point_name: str
    tasks: list[MaterializedTask]


def materialize_runtime_batch(feature_dir: Path) -> MaterializedBatch:
    tracker_path = feature_dir / "implement-tracker.md"
    if tracker_path.exists():
        tracker_text = tracker_path.read_text(encoding="utf-8")
        current_batch = _extract_tracker_scalar(tracker_text, "current_batch")
        if current_batch:
            phase_plan = _find_phase_plan(feature_dir)
            tasks = _extract_batch_tasks_from_phase_plan(phase_plan, current_batch) if phase_plan else []
            if tasks:
                return MaterializedBatch(
                    batch_name=current_batch,
                    join_point_name=f"{current_batch}-join",
                    tasks=tasks,
                )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")
    batch = find_next_ready_parallel_batch(parsed)
    if batch is None:
        raise AutoDispatchError("no ready implementation batch found")
    tasks_by_id = {task.task_id: task for task in parsed.tasks}
    return MaterializedBatch(
        batch_name=batch.batch_name,
        join_point_name=batch.join_point_name,
        tasks=[
            MaterializedTask(
                task_id=task_id,
                summary=tasks_by_id[task_id].summary,
                task_body=tasks_by_id[task_id].summary,
                completed=tasks_by_id[task_id].completed,
                parallel=tasks_by_id[task_id].parallel,
                agent_required=tasks_by_id[task_id].agent_required,
            )
            for task_id in batch.task_ids
        ],
    )
```

```python
def compile_worker_task_packet(
    *,
    project_root: Path,
    feature_dir: Path,
    task_id: str,
    task_body: str | None = None,
) -> WorkerTaskPacket:
    constitution_text = _read(project_root / ".specify" / "memory" / "constitution.md")
    plan_text = _read(feature_dir / "plan.md")
    tasks_text = _read(feature_dir / "tasks.md")

    resolved_task_body = task_body if task_body is not None else _task_body(tasks_text, task_id)
```

- [ ] **Step 4: Rewire `route_ready_parallel_batch` to use materialized batches instead of direct `tasks.md` dispatch**

```python
materialized = materialize_runtime_batch(feature_dir)
batch_name = materialized.batch_name
join_point_name = materialized.join_point_name

for materialized_task in materialized.tasks:
    if materialized_task.completed:
        continue
    request_id = _request_id_for(session_id, batch_name, materialized_task.task_id)
    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id=materialized_task.task_id,
        task_body=materialized_task.task_body,
    )
```

- [ ] **Step 5: Re-run the auto-dispatch tests**

Run:

```bash
python -m pytest tests/codex_team/test_auto_dispatch.py -k "parse_tasks_markdown or materialize_runtime_batch or route_ready_parallel_batch"
```

Expected:

- tracker-first materialization tests pass
- existing `tasks.md` parsing tests still pass as fallback coverage

### Task 4: Reroute the Codex `sp-implement-teams` skill and command wording

**Files:**
- Modify: `templates/commands/implement-teams.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/codex_team/test_implement_runtime_routing.py`

- [ ] **Step 1: Add failing wording assertions for the new product-surface contract**

```python
def test_codex_generated_sp_implement_teams_skill_points_to_specify_team_runtime(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-implement-teams"
    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0
    content = (target / ".codex" / "skills" / "sp-implement-teams" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "specify team" in content
    assert "sp.agent-teams.run" not in content
    assert "native windows + psmux" in content
    assert "implementation-state source of truth" in content or "implement-tracker.md" in content
```

- [ ] **Step 2: Run the integration assertion and confirm it fails**

Run:

```bash
python -m pytest tests/integrations/test_integration_codex.py -k implement_teams
```

Expected:

- fail because the shared template still mentions extension plumbing and `tasks.md` readiness

- [ ] **Step 3: Replace the legacy template contract with the native runtime contract**

```md
## Boundary

1. Codex-only
2. Implementation-phase entry point only; use it after the active implementation batch is known
3. On Windows, this workflow supports only `native Windows + psmux`
4. Use `specify team` as the official runtime surface; do not teach `sp.agent-teams.run`

## Execution Contract

1. Confirm the current project is using the Codex integration.
2. Confirm `FEATURE_DIR/implement-tracker.md` exists or create it, then recover the current execution batch from tracker state before trusting `tasks.md`.
3. Confirm the native runtime backend is ready through `specify team` status checks.
4. Route durable execution through `specify team` and its runtime/API surfaces.
5. Treat `tasks.md` as planning input only; prefer tracker and phase-plan recovery state when they are more current.
```

- [ ] **Step 4: Re-run the Codex integration and runtime-routing tests**

Run:

```bash
python -m pytest tests/integrations/test_integration_codex.py -k implement_teams
python -m pytest tests/codex_team/test_implement_runtime_routing.py
```

Expected:

- all `sp-implement-teams` wording assertions pass
- no regression in the canonical `sp-implement` routing contract

### Task 5: Run the milestone verification sweep

**Files:**
- Modify only if verification reveals drift

- [ ] **Step 1: Run the full targeted regression suite for this milestone**

Run:

```bash
python -m pytest tests/codex_team/test_runtime_bridge.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_implement_runtime_routing.py tests/integrations/test_integration_codex.py
```

Expected:

- all targeted tests pass with no new failures

- [ ] **Step 2: Run a focused diff review for the changed runtime/template surfaces**

Run:

```bash
git diff -- templates/commands/implement-teams.md src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/auto_dispatch.py src/specify_cli/execution/packet_compiler.py src/specify_cli/__init__.py extensions/agent-teams/scripts/build-engine.sh extensions/agent-teams/engine/src/runtime/bridge.ts tests/codex_team/test_runtime_bridge.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_implement_runtime_routing.py tests/integrations/test_integration_codex.py
```

Expected:

- only the first-milestone contract changes appear
- no unrelated user changes are reverted or overwritten

- [ ] **Step 3: Commit the milestone changes**

```bash
git add templates/commands/implement-teams.md src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/auto_dispatch.py src/specify_cli/execution/packet_compiler.py src/specify_cli/__init__.py extensions/agent-teams/scripts/build-engine.sh extensions/agent-teams/engine/src/runtime/bridge.ts tests/codex_team/test_runtime_bridge.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_implement_runtime_routing.py tests/integrations/test_integration_codex.py
git commit -m "feat: align codex teams with native Windows runtime"
```

---

## Self-Review

- Spec coverage:
  - native Windows + `psmux` contract: Tasks 1, 2, 4, 5
  - `specify team` as the real backend: Tasks 1, 4, 5
  - state-first batch materialization: Task 3
  - `.exe` runtime artifact support: Task 2
  - verification and release hardening: Task 5
- Placeholder scan:
  - no `TODO`, `TBD`, or deferred implementation markers remain
  - every task names concrete files and commands
- Type and surface consistency:
  - packet compilation remains centered on `compile_worker_task_packet(...)`
  - batch materialization is introduced as a distinct layer instead of overloading `parse_tasks_markdown(...)`
  - `sp-implement-teams` is documented as a `specify team` runtime workflow instead of extension plumbing
