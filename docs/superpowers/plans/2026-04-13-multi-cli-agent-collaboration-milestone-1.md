# Multi-CLI Agent Collaboration Milestone 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a generic orchestration core for multi-agent collaboration, refactor the existing Codex runtime primitives onto that core, add adapter skeletons for Codex, Claude, Gemini, and Copilot, and make `implement` the first workflow that uses unified strategy selection.

**Architecture:** Extract the current `codex_team` state, backend, and lifecycle concepts into a generic `src/specify_cli/orchestration/` package built around sessions, batches, lanes, events, and backends. Preserve the existing Codex-facing `specify team` surface as a compatibility layer that delegates to the new core. Add native-first adapter skeletons for the first four integrations and a shared policy engine that can choose `single-agent`, `native-multi-agent`, or `sidecar-runtime`, then wire that decision into `templates/commands/implement.md` plus Codex-specific guidance.

**Status update (2026-04-13):** Milestone 1 release-slice deliverables are now implemented in-repo: the generic orchestration core exists under `src/specify_cli/orchestration/`, `implement` is the first workflow on unified strategy selection, `specify team` remains the Codex compatibility surface, and Claude/Gemini/Copilot adapter skeletons are present for first-release routing. This remains a Milestone 1 artifact; full workflow migration is not claimed here.

**Tech Stack:** Python 3.11+, Typer CLI, JSON file-backed state, dataclasses, pytest, tmux/psmux detection, portable subprocess backend

---

## File Structure

- `src/specify_cli/orchestration/__init__.py`: Public exports for the generic orchestration package.
- `src/specify_cli/orchestration/models.py`: Canonical dataclasses for capability snapshots, execution decisions, sessions, batches, lanes, and artifact results.
- `src/specify_cli/orchestration/state_store.py`: Canonical state-root and JSON persistence helpers under `.specify/orchestration/`.
- `src/specify_cli/orchestration/events.py`: Append-only event writing and replay helpers.
- `src/specify_cli/orchestration/backends/base.py`: Backend protocol and backend descriptor types.
- `src/specify_cli/orchestration/backends/detect.py`: Cross-platform backend detection and backend registry.
- `src/specify_cli/orchestration/backends/process_backend.py`: Portable managed-process backend for sidecar fallback.
- `src/specify_cli/orchestration/adapters.py`: Adapter protocol and registration helpers shared by integrations.
- `src/specify_cli/orchestration/policy.py`: Strategy selection rules for collaboration-aware workflows.
- `src/specify_cli/integrations/codex/multi_agent.py`: Codex adapter using the orchestration core plus Codex-specific compatibility facts.
- `src/specify_cli/integrations/claude/multi_agent.py`: Claude adapter skeleton with native-first capability reporting.
- `src/specify_cli/integrations/gemini/multi_agent.py`: Gemini adapter skeleton with native-first capability reporting.
- `src/specify_cli/integrations/copilot/multi_agent.py`: Copilot adapter skeleton with conservative native-first capability reporting.
- `src/specify_cli/codex_team/*.py`: Compatibility-layer modules updated to consume orchestration-core state and backend helpers.
- `templates/commands/implement.md`: First workflow template that routes through the unified strategy model.
- `tests/orchestration/*.py`: New regression coverage for models, store, events, backends, adapters, and policy.
- `tests/codex_team/*.py`: Compatibility regression coverage proving the Codex surface still works on the new core.
- `tests/integrations/test_integration_codex.py`, `tests/integrations/test_cli.py`, `tests/test_alignment_templates.py`: Integration and template coverage for new routing language.

### Task 1: Create the generic orchestration core models and state store

**Files:**
- Create: `src/specify_cli/orchestration/__init__.py`
- Create: `src/specify_cli/orchestration/models.py`
- Create: `src/specify_cli/orchestration/state_store.py`
- Create: `src/specify_cli/orchestration/events.py`
- Create: `tests/orchestration/test_models.py`
- Create: `tests/orchestration/test_state_store.py`
- Create: `tests/orchestration/test_events.py`

- [ ] **Step 1: Write failing tests for canonical orchestration models and `.specify/orchestration/` paths**

Create tests that assert:

```python
from pathlib import Path

from specify_cli.orchestration.models import CapabilitySnapshot, ExecutionDecision, Session
from specify_cli.orchestration.state_store import (
    orchestration_root,
    session_path,
    batch_path,
    lane_path,
    task_path,
)


def test_orchestration_root_uses_generic_state_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    assert orchestration_root(project_root) == project_root / ".specify" / "orchestration"


def test_capability_snapshot_defaults_are_explicit() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude")
    assert snapshot.integration_key == "claude"
    assert snapshot.native_multi_agent is False
    assert snapshot.sidecar_runtime_supported is False


def test_execution_decision_records_strategy_and_reason() -> None:
    decision = ExecutionDecision(
        command_name="implement",
        strategy="single-agent",
        reason="default",
    )
    assert decision.strategy == "single-agent"
    assert decision.reason == "default"
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/orchestration/test_models.py tests/orchestration/test_state_store.py tests/orchestration/test_events.py -q
```

Expected: FAIL because the orchestration package and its state helpers do not exist yet.

- [ ] **Step 3: Implement the canonical models and JSON persistence helpers**

Create the orchestration core with explicit, reusable dataclasses and state helpers:

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ExecutionStrategy = Literal["single-agent", "native-multi-agent", "sidecar-runtime"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CapabilitySnapshot:
    integration_key: str
    native_multi_agent: bool = False
    sidecar_runtime_supported: bool = False
    structured_results: bool = False
    durable_coordination: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    command_name: str
    strategy: ExecutionStrategy
    reason: str
    fallback_from: ExecutionStrategy | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Session:
    session_id: str
    integration_key: str
    command_name: str
    status: str = "created"
    created_at: str = field(default_factory=utc_now)
```

And implement state helpers that write generic records to `.specify/orchestration/`:

```python
import json
from pathlib import Path


def orchestration_root(project_root: Path) -> Path:
    return project_root / ".specify" / "orchestration"


def session_path(project_root: Path, session_id: str) -> Path:
    return orchestration_root(project_root) / "sessions" / f"{session_id}.json"


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/orchestration/test_models.py tests/orchestration/test_state_store.py tests/orchestration/test_events.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/orchestration/__init__.py src/specify_cli/orchestration/models.py src/specify_cli/orchestration/state_store.py src/specify_cli/orchestration/events.py tests/orchestration/test_models.py tests/orchestration/test_state_store.py tests/orchestration/test_events.py
git commit -m "feat: add orchestration core models and state store"
```

### Task 2: Add backend registry and portable process backend

**Files:**
- Create: `src/specify_cli/orchestration/backends/__init__.py`
- Create: `src/specify_cli/orchestration/backends/base.py`
- Create: `src/specify_cli/orchestration/backends/detect.py`
- Create: `src/specify_cli/orchestration/backends/process_backend.py`
- Create: `tests/orchestration/test_backends.py`
- Create: `tests/orchestration/test_process_backend.py`

- [ ] **Step 1: Write failing tests for backend detection and portable fallback**

Add tests that cover:

```python
from specify_cli.orchestration.backends.detect import detect_available_backends
from specify_cli.orchestration.backends.process_backend import ProcessBackend


def test_detect_available_backends_includes_process_backend() -> None:
    backends = detect_available_backends()
    assert "process" in backends
    assert backends["process"].available is True


def test_process_backend_descriptor_is_portable() -> None:
    backend = ProcessBackend()
    descriptor = backend.describe()
    assert descriptor.name == "process"
    assert descriptor.available is True
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/orchestration/test_backends.py tests/orchestration/test_process_backend.py -q
```

Expected: FAIL because backend registry and the process backend do not exist yet.

- [ ] **Step 3: Implement backend descriptors, detection, and process backend**

Add an explicit backend protocol:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True, frozen=True)
class BackendDescriptor:
    name: str
    available: bool
    interactive: bool
    binary: str | None = None
    reason: str = ""


class RuntimeBackend(Protocol):
    def describe(self) -> BackendDescriptor:
        pass

    def launch(self, *, command: str, cwd: Path, env: dict[str, str]) -> object:
        pass
```

Implement detection that returns `tmux`, `psmux`, and `process` descriptors:

```python
import shutil


def detect_available_backends() -> dict[str, BackendDescriptor]:
    tmux = shutil.which("tmux")
    psmux = shutil.which("psmux")
    return {
        "tmux": BackendDescriptor("tmux", tmux is not None, True, tmux),
        "psmux": BackendDescriptor("psmux", psmux is not None, True, psmux),
        "process": BackendDescriptor("process", True, False, None),
    }
```

And implement the portable backend as a subprocess wrapper that returns structured launch metadata instead of pane-specific assumptions:

```python
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class ProcessHandle:
    pid: int
    command: str


class ProcessBackend:
    def describe(self) -> BackendDescriptor:
        return BackendDescriptor(name="process", available=True, interactive=False)

    def launch(self, *, command: str, cwd: Path, env: dict[str, str]) -> ProcessHandle:
        proc = subprocess.Popen(command, cwd=str(cwd), env=env, shell=True)
        return ProcessHandle(pid=proc.pid, command=command)
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/orchestration/test_backends.py tests/orchestration/test_process_backend.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/orchestration/backends/__init__.py src/specify_cli/orchestration/backends/base.py src/specify_cli/orchestration/backends/detect.py src/specify_cli/orchestration/backends/process_backend.py tests/orchestration/test_backends.py tests/orchestration/test_process_backend.py
git commit -m "feat: add orchestration backend registry"
```

### Task 3: Define the adapter protocol and add the first four integration adapters

**Files:**
- Create: `src/specify_cli/orchestration/adapters.py`
- Create: `src/specify_cli/integrations/codex/multi_agent.py`
- Create: `src/specify_cli/integrations/claude/multi_agent.py`
- Create: `src/specify_cli/integrations/gemini/multi_agent.py`
- Create: `src/specify_cli/integrations/copilot/multi_agent.py`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `src/specify_cli/integrations/gemini/__init__.py`
- Modify: `src/specify_cli/integrations/copilot/__init__.py`
- Create: `tests/orchestration/test_adapters.py`

- [ ] **Step 1: Write failing tests for adapter capability snapshots**

Add adapter tests such as:

```python
from specify_cli.integrations.claude.multi_agent import ClaudeMultiAgentAdapter
from specify_cli.integrations.codex.multi_agent import CodexMultiAgentAdapter


def test_claude_adapter_reports_native_first_capabilities() -> None:
    snapshot = ClaudeMultiAgentAdapter().detect_capabilities()
    assert snapshot.integration_key == "claude"
    assert snapshot.native_multi_agent is True


def test_codex_adapter_reports_sidecar_support() -> None:
    snapshot = CodexMultiAgentAdapter().detect_capabilities()
    assert snapshot.integration_key == "codex"
    assert snapshot.sidecar_runtime_supported is True
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/orchestration/test_adapters.py -q
```

Expected: FAIL because the adapter protocol and adapter modules do not exist yet.

- [ ] **Step 3: Implement the adapter protocol and per-integration capability detection**

Create a small protocol module:

```python
from dataclasses import dataclass
from typing import Protocol

from .models import CapabilitySnapshot


class MultiAgentAdapter(Protocol):
    def detect_capabilities(self) -> CapabilitySnapshot:
        pass

    def supports_command(self, command_name: str) -> bool:
        pass
```

And implement explicit first-release adapters:

```python
from specify_cli.orchestration.models import CapabilitySnapshot


class ClaudeMultiAgentAdapter:
    def detect_capabilities(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key="claude",
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=True,
        )


class CodexMultiAgentAdapter:
    def detect_capabilities(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key="codex",
            native_multi_agent=False,
            sidecar_runtime_supported=True,
            durable_coordination=True,
        )
```

Expose the adapters from each integration package so later policy wiring can import them without hard-coded file paths.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/orchestration/test_adapters.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/orchestration/adapters.py src/specify_cli/integrations/codex/multi_agent.py src/specify_cli/integrations/claude/multi_agent.py src/specify_cli/integrations/gemini/multi_agent.py src/specify_cli/integrations/copilot/multi_agent.py src/specify_cli/integrations/codex/__init__.py src/specify_cli/integrations/claude/__init__.py src/specify_cli/integrations/gemini/__init__.py src/specify_cli/integrations/copilot/__init__.py tests/orchestration/test_adapters.py
git commit -m "feat: add multi-agent adapter skeletons"
```

### Task 4: Refactor `codex_team` into a compatibility layer over the orchestration core

**Files:**
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `src/specify_cli/codex_team/tmux_backend.py`
- Modify: `src/specify_cli/codex_team/runtime_state.py`
- Modify: `src/specify_cli/codex_team/state_paths.py`
- Modify: `src/specify_cli/codex_team/session_ops.py`
- Modify: `src/specify_cli/codex_team/__init__.py`
- Modify: `tests/codex_team/test_runtime_state.py`
- Modify: `tests/codex_team/test_state_paths.py`
- Modify: `tests/codex_team/test_session_ops.py`
- Modify: `tests/codex_team/test_tmux_backend.py`

- [ ] **Step 1: Write failing compatibility tests that prove `codex_team` delegates to the new core**

Add or update tests so they assert:

```python
from specify_cli.codex_team.state_paths import codex_team_state_root
from specify_cli.orchestration.state_store import orchestration_root


def test_codex_team_and_orchestration_roots_share_specify_namespace(tmp_path):
    project_root = tmp_path / "project"
    assert codex_team_state_root(project_root).parent.parent == orchestration_root(project_root).parent
```

Also assert Codex backend detection now comes from the orchestration backend registry rather than directly from `runtime_bridge`.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/codex_team/test_runtime_state.py tests/codex_team/test_state_paths.py tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_backend.py -q
```

Expected: FAIL because `codex_team` still owns its own state and backend logic.

- [ ] **Step 3: Move Codex runtime helpers onto orchestration-core primitives**

Refactor the compatibility layer so Codex-specific modules import generic helpers instead of duplicating them:

```python
from specify_cli.orchestration.backends.detect import detect_available_backends
from specify_cli.orchestration.state_store import orchestration_root


def codex_team_state_root(project_root: Path) -> Path:
    return project_root / ".specify" / "codex-team" / "state"


def detect_team_runtime_backend() -> dict[str, object]:
    backends = detect_available_backends()
    if backends["tmux"].available:
        return {"available": True, "name": "tmux", "binary": backends["tmux"].binary}
    if backends["psmux"].available:
        return {"available": True, "name": "psmux", "binary": backends["psmux"].binary}
    return {"available": False, "name": None, "binary": None}
```

Keep the Codex public API intact while reusing the new canonical models and persistence helpers underneath.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/codex_team/test_runtime_state.py tests/codex_team/test_state_paths.py tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_backend.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/tmux_backend.py src/specify_cli/codex_team/runtime_state.py src/specify_cli/codex_team/state_paths.py src/specify_cli/codex_team/session_ops.py src/specify_cli/codex_team/__init__.py tests/codex_team/test_runtime_state.py tests/codex_team/test_state_paths.py tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_backend.py
git commit -m "refactor: move codex team onto orchestration core"
```

### Task 5: Add unified strategy selection and route `implement` through it

**Files:**
- Create: `src/specify_cli/orchestration/policy.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `templates/commands/implement.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Create: `tests/orchestration/test_policy.py`
- Create: `tests/orchestration/test_implement_strategy_routing.py`
- Modify: `tests/codex_team/test_implement_runtime_routing.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write failing tests for `single-agent`, `native-multi-agent`, and `sidecar-runtime` selection**

Add policy tests like:

```python
from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import choose_execution_strategy


def test_policy_prefers_native_multi_agent_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )
    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={"parallel_batches": 1, "overlapping_write_sets": False},
    )
    assert decision.strategy == "native-multi-agent"


def test_policy_falls_back_to_sidecar_when_native_is_missing() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_multi_agent=False,
        sidecar_runtime_supported=True,
    )
    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={"parallel_batches": 2, "overlapping_write_sets": False},
    )
    assert decision.strategy == "sidecar-runtime"
```

Add template assertions that `implement.md` describes the same three strategy names and the same decision order.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py -q
```

Expected: FAIL because there is no generic policy module and `implement` still carries Codex-specific routing language only.

- [ ] **Step 3: Implement the policy engine and wire `implement` to the unified model**

Add a shared policy function:

```python
from specify_cli.orchestration.models import ExecutionDecision


def choose_execution_strategy(*, command_name: str, snapshot, workload_shape: dict[str, object]) -> ExecutionDecision:
    parallel_batches = int(workload_shape.get("parallel_batches", 0))
    overlapping = bool(workload_shape.get("overlapping_write_sets", False))
    if parallel_batches <= 0 or overlapping:
        return ExecutionDecision(command_name=command_name, strategy="single-agent", reason="no-safe-batch")
    if snapshot.native_multi_agent:
        return ExecutionDecision(command_name=command_name, strategy="native-multi-agent", reason="native-supported")
    if snapshot.sidecar_runtime_supported:
        return ExecutionDecision(command_name=command_name, strategy="sidecar-runtime", reason="native-missing")
    return ExecutionDecision(command_name=command_name, strategy="single-agent", reason="fallback")
```

Update `templates/commands/implement.md` so it refers to the canonical strategy names and decision order rather than only the Codex runtime wording. Keep the Codex-specific addendum in the Codex integration layer.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/orchestration/policy.py src/specify_cli/__init__.py templates/commands/implement.md src/specify_cli/integrations/codex/__init__.py tests/orchestration/test_policy.py tests/orchestration/test_implement_strategy_routing.py tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py
git commit -m "feat: add unified implement strategy selection"
```

### Task 6: Harden the release slice with integration and documentation updates

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-04-13-multi-cli-agent-collaboration-design.md`
- Modify: `docs/superpowers/plans/2026-04-13-multi-cli-agent-collaboration-milestone-1.md`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add failing integration tests for the new orchestration language**

Extend integration coverage to assert:

```python
import os

from typer.testing import CliRunner

from specify_cli import app


def test_codex_init_still_advertises_specify_team_surface(tmp_path):
    runner = CliRunner()
    project = tmp_path / "codex-init"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["init", "--here", "--ai", "codex", "--script", "sh", "--no-git", "--ignore-agent-tools"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)
    assert result.exit_code == 0
    assert "specify team" in result.output


def test_non_codex_init_does_not_advertise_specify_team_as_primary_surface(tmp_path):
    runner = CliRunner()
    project = tmp_path / "claude-init"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["init", "--here", "--ai", "claude", "--script", "sh", "--no-git", "--ignore-agent-tools"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)
    assert result.exit_code == 0
    assert "specify team" not in result.output


def test_codex_implement_skill_mentions_single_native_sidecar_order(tmp_path):
    runner = CliRunner()
    project = tmp_path / "codex-skill"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["init", "--here", "--ai", "codex", "--script", "sh", "--no-git", "--ignore-agent-tools"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)
    assert result.exit_code == 0
    content = (project / ".agents" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
```

Also add an assertion that non-Codex integrations do not leak `specify team` as their main entrypoint.

- [ ] **Step 2: Run the release-slice regression suite and verify it fails**

Run:

```powershell
pytest tests/orchestration tests/codex_team tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/test_alignment_templates.py -q
```

Expected: FAIL until the integration copy and docs are aligned with the new orchestration model.

- [ ] **Step 3: Update docs and integration messaging**

Update user-facing docs to describe milestone-1 reality accurately:

```markdown
- generic orchestration core now exists under `src/specify_cli/orchestration/`
- `implement` is the first workflow routed through unified strategy selection
- `specify team` remains the Codex compatibility surface
- Claude, Gemini, and Copilot now have first-release adapter skeletons
```

Do not claim that all workflows are fully migrated yet.

- [ ] **Step 4: Run the release-slice regression suite and verify it passes**

Run:

```powershell
pytest tests/orchestration tests/codex_team tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-04-13-multi-cli-agent-collaboration-design.md docs/superpowers/plans/2026-04-13-multi-cli-agent-collaboration-milestone-1.md tests/integrations/test_cli.py tests/integrations/test_integration_codex.py
git commit -m "docs: describe milestone 1 multi-agent orchestration rollout"
```

## Self-Review

- Spec coverage:
  - generic orchestration core: covered by Tasks 1 and 2
  - Codex compatibility migration: covered by Task 4
  - first four integration adapters: covered by Task 3
  - unified strategy model and `implement` integration: covered by Task 5
  - release-slice documentation and integration hardening: covered by Task 6
- Placeholder scan:
  - no `TBD`, `TODO`, `implement later`, or unresolved placeholder markers remain
  - every task has exact file paths, test commands, and commit commands
- Type consistency:
  - the plan consistently uses `CapabilitySnapshot`, `ExecutionDecision`, `Session`, `Batch`, `Lane`, and `ProcessBackend`
  - the strategy names remain `single-agent`, `native-multi-agent`, and `sidecar-runtime` throughout
