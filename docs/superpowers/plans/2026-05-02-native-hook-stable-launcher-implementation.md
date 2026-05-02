# Native Hook Stable Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace interpreter-specific Claude and Gemini native hook registrations with a shared project-local stable launcher that resolves Python at runtime and preserves the existing shared `specify hook ...` core.

**Architecture:** Add a shared launcher asset family under `.specify/bin/`, backed by Python helpers in `src/specify_cli/launcher.py`, and rewire Claude and Gemini managed hook commands to target that launcher instead of hardcoded `python` or `python3` command strings. Keep the existing `claude-hook-dispatch.py` and `gemini-hook-dispatch.py` scripts in place so host payload parsing and shared-hook response translation remain unchanged.

**Tech Stack:** Python 3.11+, Typer CLI, hatchling force-include packaging, Claude/Gemini integration installers, pytest

---

## File Structure

### Shared launcher runtime and generated assets

- Modify: `src/specify_cli/launcher.py`
  - Add the shared native-hook launcher runtime helpers, startup-runtime resolution, generated launcher asset rendering, and compatibility diagnostics for stale direct-dispatch hook commands.
- Create: `src/specify_cli/shared_hooks/specify-hook`
  - POSIX launcher template that resolves Python at runtime and then invokes `.specify/bin/specify-hook.py`.
- Create: `src/specify_cli/shared_hooks/specify-hook.cmd`
  - Windows launcher template that resolves Python at runtime and then invokes `.specify/bin/specify-hook.py`.
- Create: `src/specify_cli/shared_hooks/specify-hook.py`
  - Shared Python launcher implementation that validates arguments and delegates to `.claude/hooks/claude-hook-dispatch.py` or `.gemini/hooks/gemini-hook-dispatch.py`.

### Integration wiring

- Modify: `src/specify_cli/integrations/claude/__init__.py`
  - Stop generating direct `python ...claude-hook-dispatch.py` commands, install the shared launcher assets, and point managed hooks at `.specify/bin/specify-hook claude <route>`.
- Modify: `src/specify_cli/integrations/gemini/__init__.py`
  - Stop generating direct `python ...gemini-hook-dispatch.py` commands, install the shared launcher assets, and point managed hooks at `.specify/bin/specify-hook gemini <route>`.

### Packaging and wheel asset coverage

- Modify: `pyproject.toml`
  - Force-include the new shared hook launcher assets so wheel installs can generate them offline.
- Modify: `tests/test_packaging_assets.py`
  - Verify the new shared hook launcher assets are bundled into `specify_cli/core_pack/`.

### Tests

- Modify: `tests/test_launcher.py`
  - Add focused launcher helper tests for startup-runtime resolution, generated launcher asset installation, and stale native hook diagnostics.
- Modify: `tests/integrations/test_integration_claude.py`
  - Update Claude install, inventory, and hook command assertions to expect the shared launcher.
- Modify: `tests/integrations/test_integration_gemini.py`
  - Update Gemini install, inventory, and hook command assertions to expect the shared launcher.
- Modify: `tests/integrations/test_integration_subcommand.py`
  - Verify `integration repair` upgrades stale direct-dispatch managed hooks to shared launcher commands.

### Documentation follow-through

- Modify: `docs/quickstart.md`
  - Explain that generated Claude and Gemini native hooks now target `.specify/bin/specify-hook`.
- Modify: `docs/upgrade.md`
  - Document repair and compatibility behavior for stale direct-dispatch hook commands.

## Task 1: Add Shared Launcher Helper Tests First

**Files:**
- Modify: `tests/test_launcher.py`
- Test: `tests/test_launcher.py`

- [ ] **Step 1: Write the failing startup-runtime resolution tests**

```python
import json
import os
from pathlib import Path

from specify_cli.launcher import (
    HookRuntimeSpec,
    render_hook_launcher_command,
    resolve_hook_runtime_spec,
)


def test_resolve_hook_runtime_spec_prefers_runtime_env_argv(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SPECIFY_HOOK_RUNTIME_ARGV",
        json.dumps(["python-custom", "-X", "utf8"]),
    )
    resolved = resolve_hook_runtime_spec(tmp_path)
    assert resolved == HookRuntimeSpec(
        command="python-custom -X utf8",
        argv=("python-custom", "-X", "utf8"),
        source="env:SPECIFY_HOOK_RUNTIME_ARGV",
    )


def test_render_hook_launcher_command_targets_shared_launcher_posix(monkeypatch):
    monkeypatch.setattr(os, "name", "posix", raising=False)
    command = render_hook_launcher_command("claude", "session-start")
    assert command == '.specify/bin/specify-hook claude session-start'


def test_render_hook_launcher_command_targets_shared_launcher_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "nt", raising=False)
    command = render_hook_launcher_command("gemini", "before-tool")
    assert command == '.specify/bin/specify-hook.cmd gemini before-tool'
```

- [ ] **Step 2: Run the focused launcher tests to verify they fail**

Run: `pytest tests/test_launcher.py -q`
Expected: FAIL because `HookRuntimeSpec`, `resolve_hook_runtime_spec`, and `render_hook_launcher_command` do not exist yet

- [ ] **Step 3: Add the new runtime-spec dataclass and launcher command rendering helpers**

```python
@dataclass(frozen=True)
class HookRuntimeSpec:
    command: str
    argv: tuple[str, ...]
    source: str


def render_hook_launcher_command(integration_key: str, route: str) -> str:
    launcher = ".specify/bin/specify-hook.cmd" if os.name == "nt" else ".specify/bin/specify-hook"
    return f"{launcher} {integration_key} {route}"
```

Add `resolve_hook_runtime_spec(project_root: Path) -> HookRuntimeSpec | None` with runtime override support for:

- `SPECIFY_HOOK_RUNTIME_ARGV`
- `SPECIFY_HOOK_RUNTIME_COMMAND`

Normalize the env-provided `argv` through `render_command(...)` so the `command` string stays human-readable.

- [ ] **Step 4: Re-run the focused launcher tests**

Run: `pytest tests/test_launcher.py -q`
Expected: PASS for the newly added tests

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/launcher.py tests/test_launcher.py
git commit -m "test: add shared hook launcher helpers"
```

## Task 2: Implement Startup Runtime Resolution and Shared Launcher Asset Installation

**Files:**
- Modify: `src/specify_cli/launcher.py`
- Create: `src/specify_cli/shared_hooks/specify-hook`
- Create: `src/specify_cli/shared_hooks/specify-hook.cmd`
- Create: `src/specify_cli/shared_hooks/specify-hook.py`
- Modify: `tests/test_launcher.py`
- Test: `tests/test_launcher.py`

- [ ] **Step 1: Write failing tests for `.venv`, system fallback, and generated launcher assets**

```python
def test_resolve_hook_runtime_spec_prefers_project_venv_python(tmp_path):
    python_bin = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("", encoding="utf-8")

    resolved = resolve_hook_runtime_spec(tmp_path)

    assert resolved is not None
    assert resolved.argv[0] == str(python_bin)
    assert resolved.source == "project-venv"


def test_install_shared_hook_launcher_assets_writes_all_runtime_files(tmp_path):
    created = install_shared_hook_launcher_assets(tmp_path)
    relpaths = sorted(path.relative_to(tmp_path).as_posix() for path in created)
    assert ".specify/bin/specify-hook.py" in relpaths
    if os.name == "nt":
        assert ".specify/bin/specify-hook.cmd" in relpaths
    else:
        assert ".specify/bin/specify-hook" in relpaths
```

- [ ] **Step 2: Run the focused launcher tests to verify they fail**

Run: `pytest tests/test_launcher.py -q`
Expected: FAIL because project `.venv` resolution and shared launcher asset installation do not exist yet

- [ ] **Step 3: Implement runtime resolution precedence and asset installation**

Add these helpers to `src/specify_cli/launcher.py`:

```python
def _project_hook_python_candidates(project_root: Path) -> list[Path]:
    return [
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
    ]


def install_shared_hook_launcher_assets(
    project_root: Path,
    *,
    manifest: IntegrationManifest | None = None,
) -> list[Path]:
    ...
```

Implementation rules:

- prefer `.venv/Scripts/python.exe` and `.venv/bin/python` when present
- otherwise try system candidates:
  - Windows: `py`, then `python`
  - POSIX: `/usr/bin/env python3`, then `/usr/bin/env python`
- write generated assets to `.specify/bin/`
- mark POSIX launcher scripts executable
- record files in `manifest` when one is provided

For `specify-hook.py`, implement a minimal CLI contract:

```python
def main() -> int:
    # argv: <integration> <route>
    # dispatch to .claude/hooks/claude-hook-dispatch.py or .gemini/hooks/gemini-hook-dispatch.py
```

Do not invoke `specify hook ...` directly from `specify-hook.py`; delegate to the existing integration dispatch scripts.

- [ ] **Step 4: Re-run the focused launcher tests**

Run: `pytest tests/test_launcher.py -q`
Expected: PASS, including `.venv` preference and shared asset installation coverage

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/launcher.py src/specify_cli/shared_hooks/specify-hook src/specify_cli/shared_hooks/specify-hook.cmd src/specify_cli/shared_hooks/specify-hook.py tests/test_launcher.py
git commit -m "feat: add shared native hook launcher assets"
```

## Task 3: Rewire Claude Managed Hooks to the Shared Launcher

**Files:**
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Write failing Claude integration assertions for shared launcher commands**

```python
def test_setup_installs_shared_launcher_assets_for_claude(self, tmp_path):
    integration = get_integration("claude")
    manifest = IntegrationManifest("claude", tmp_path)
    created = integration.setup(tmp_path, manifest, script_type="sh")

    tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
    assert ".specify/bin/specify-hook.py" in tracked
    assert ".specify/bin/specify-hook" in tracked


def test_setup_installs_claude_hook_commands_via_shared_launcher(self, tmp_path):
    integration = get_integration("claude")
    manifest = IntegrationManifest("claude", tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")

    settings_path = tmp_path / ".claude" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entries in payload["hooks"].values()
        for entry in entries
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict) and isinstance(hook.get("command"), str)
    ]

    assert any(command == ".specify/bin/specify-hook claude session-start" for command in commands)
    assert any(command == ".specify/bin/specify-hook claude user-prompt-submit" for command in commands)
    assert not any("python3" in command or "python " in command for command in commands)
```

- [ ] **Step 2: Run the focused Claude integration tests to verify they fail**

Run: `pytest tests/integrations/test_integration_claude.py -q`
Expected: FAIL because Claude still generates direct interpreter-backed hook commands and does not install shared launcher assets

- [ ] **Step 3: Replace direct command generation with shared launcher command rendering**

In `src/specify_cli/integrations/claude/__init__.py`:

- delete `_detect_python_command(...)`
- replace `_hook_dispatch_command(...)` with a shared-launcher form
- install shared launcher assets during `setup(...)` and `repair_runtime_assets(...)`

Use code shaped like:

```python
from ...launcher import install_shared_hook_launcher_assets, render_hook_launcher_command


@staticmethod
def _hook_dispatch_command(route: str) -> str:
    return render_hook_launcher_command("claude", route)
```

When building managed hook events, stop threading a `python_cmd` argument. The launcher command should be identical across POSIX installs, with only `render_hook_launcher_command(...)` deciding whether the output is `.cmd` on Windows.

- [ ] **Step 4: Re-run the focused Claude integration tests**

Run: `pytest tests/integrations/test_integration_claude.py -q`
Expected: PASS, including shared launcher file creation and direct-command removal

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/integrations/claude/__init__.py tests/integrations/test_integration_claude.py
git commit -m "feat: route claude hooks through shared launcher"
```

## Task 4: Rewire Gemini Managed Hooks to the Shared Launcher

**Files:**
- Modify: `src/specify_cli/integrations/gemini/__init__.py`
- Modify: `tests/integrations/test_integration_gemini.py`
- Test: `tests/integrations/test_integration_gemini.py`

- [ ] **Step 1: Write failing Gemini integration assertions for shared launcher commands**

```python
def test_setup_installs_shared_launcher_assets_for_gemini(self, tmp_path):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")

    assert ".specify/bin/specify-hook.py" in manifest.files


def test_setup_installs_gemini_hook_commands_via_shared_launcher(self, tmp_path):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")

    settings_path = tmp_path / ".gemini" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entries in payload["hooks"].values()
        for entry in entries
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict) and isinstance(hook.get("command"), str)
    ]

    assert any(command == ".specify/bin/specify-hook gemini session-start" for command in commands)
    assert any(command == ".specify/bin/specify-hook gemini before-agent" for command in commands)
    assert any(command == ".specify/bin/specify-hook gemini before-tool" for command in commands)
    assert not any("python3" in command or "python " in command for command in commands)
```

- [ ] **Step 2: Run the focused Gemini integration tests to verify they fail**

Run: `pytest tests/integrations/test_integration_gemini.py -q`
Expected: FAIL because Gemini still generates direct interpreter-backed hook commands and does not install shared launcher assets

- [ ] **Step 3: Replace Gemini direct command generation with shared launcher command rendering**

In `src/specify_cli/integrations/gemini/__init__.py`:

- delete `_detect_python_command(...)`
- remove the `python_cmd` parameter from `_build_managed_hook_events(...)`
- install shared launcher assets during `setup(...)` and `repair_runtime_assets(...)`

Use code shaped like:

```python
from ...launcher import install_shared_hook_launcher_assets, render_hook_launcher_command


"command": render_hook_launcher_command("gemini", "session-start")
```

Keep the existing `.gemini/hooks/gemini-hook-dispatch.py` asset installation unchanged.

- [ ] **Step 4: Re-run the focused Gemini integration tests**

Run: `pytest tests/integrations/test_integration_gemini.py -q`
Expected: PASS, including shared launcher command coverage

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/integrations/gemini/__init__.py tests/integrations/test_integration_gemini.py
git commit -m "feat: route gemini hooks through shared launcher"
```

## Task 5: Add Stale Runtime Diagnostics and Repair Coverage

**Files:**
- Modify: `src/specify_cli/launcher.py`
- Modify: `tests/test_launcher.py`
- Modify: `tests/integrations/test_integration_subcommand.py`
- Test: `tests/test_launcher.py`
- Test: `tests/integrations/test_integration_subcommand.py`

- [ ] **Step 1: Write failing stale-command diagnostic and repair tests**

```python
def test_diagnose_project_runtime_compatibility_reports_stale_direct_claude_hook_launcher(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py session-start',
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)
    assert any(issue["code"] == "stale-direct-hook-launcher-command" for issue in issues)
```

```python
def test_repair_upgrades_direct_claude_hook_commands_to_shared_launcher(self, tmp_path):
    project = _init_project(tmp_path, "claude")
    settings_path = project / ".claude" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    for entries in payload.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    hook["command"] = hook["command"].replace(
                        ".specify/bin/specify-hook claude",
                        'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py',
                    )
    settings_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    ...
    repaired = json.loads(settings_path.read_text(encoding="utf-8"))
    commands = [...]
    assert any(command == ".specify/bin/specify-hook claude session-start" for command in commands)
```

- [ ] **Step 2: Run the focused diagnostic and repair tests to verify they fail**

Run: `pytest tests/test_launcher.py tests/integrations/test_integration_subcommand.py -q`
Expected: FAIL because stale direct-dispatch commands are not diagnosed as their own compatibility issue and repair does not normalize them to shared launcher commands

- [ ] **Step 3: Extend diagnostics and ensure repair normalizes stale commands**

In `src/specify_cli/launcher.py`:

- add a new diagnostic code:

```python
"code": "stale-direct-hook-launcher-command"
```

- detect direct `python`, `python3`, or `py -m` command forms that point straight at:
  - `claude-hook-dispatch.py`
  - `gemini-hook-dispatch.py`

In the Claude and Gemini integration setup/repair merge paths, treat any of those direct forms as stale managed hooks so they are stripped and replaced with the shared launcher command.

- [ ] **Step 4: Re-run the focused diagnostic and repair tests**

Run: `pytest tests/test_launcher.py tests/integrations/test_integration_subcommand.py -q`
Expected: PASS, including direct-command stale detection and repair rewriting

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/launcher.py tests/test_launcher.py tests/integrations/test_integration_subcommand.py src/specify_cli/integrations/claude/__init__.py src/specify_cli/integrations/gemini/__init__.py
git commit -m "feat: diagnose and repair stale direct hook launcher commands"
```

## Task 6: Bundle Shared Launcher Assets into Wheel Packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_packaging_assets.py`
- Test: `tests/test_packaging_assets.py`

- [ ] **Step 1: Write failing packaging assertions for shared hook launcher assets**

```python
def test_pyproject_force_includes_shared_hook_launcher_assets():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"src/specify_cli/shared_hooks/specify-hook" = "specify_cli/core_pack/shared_hooks/specify-hook"' in pyproject
    assert '"src/specify_cli/shared_hooks/specify-hook.cmd" = "specify_cli/core_pack/shared_hooks/specify-hook.cmd"' in pyproject
    assert '"src/specify_cli/shared_hooks/specify-hook.py" = "specify_cli/core_pack/shared_hooks/specify-hook.py"' in pyproject
```

Add a split-core-pack install test that expects `.specify/bin/specify-hook.py` to be generated from bundled assets when `_locate_core_pack()` is monkeypatched.

- [ ] **Step 2: Run the packaging tests to verify they fail**

Run: `pytest tests/test_packaging_assets.py -q`
Expected: FAIL because the new shared launcher assets are not bundled yet

- [ ] **Step 3: Add the shared launcher assets to hatch force-include and asset-copy coverage**

In `pyproject.toml`, add entries shaped like:

```toml
"src/specify_cli/shared_hooks" = "specify_cli/core_pack/shared_hooks"
```

If the existing bundling tests require more explicit file-by-file assertions, add those exact expectations to `tests/test_packaging_assets.py`.

- [ ] **Step 4: Re-run the packaging tests**

Run: `pytest tests/test_packaging_assets.py -q`
Expected: PASS, including wheel-bundle coverage for shared launcher assets

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_packaging_assets.py
git commit -m "build: bundle shared native hook launcher assets"
```

## Task 7: Update Documentation and Run End-to-End Verification

**Files:**
- Modify: `docs/quickstart.md`
- Modify: `docs/upgrade.md`
- Test: `tests/test_launcher.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_gemini.py`
- Test: `tests/integrations/test_integration_subcommand.py`
- Test: `tests/test_packaging_assets.py`

- [ ] **Step 1: Write the documentation updates**

Add exact guidance to `docs/quickstart.md`:

```md
- Generated Claude and Gemini native hook registrations now call `.specify/bin/specify-hook` instead of embedding `python` or `python3` directly.
- The shared launcher resolves the Python runtime at hook execution time, then delegates to the existing project-local dispatch scripts.
```

Add exact upgrade guidance to `docs/upgrade.md`:

```md
If a project still has direct `python ...claude-hook-dispatch.py` or `python ...gemini-hook-dispatch.py` managed commands, run:

`specify integration repair`

This refresh installs the shared launcher assets under `.specify/bin/` and rewrites managed hook commands to use the stable launcher contract.
```

- [ ] **Step 2: Run the focused verification suite**

Run: `pytest tests/test_launcher.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_subcommand.py tests/test_packaging_assets.py -q`
Expected: PASS

- [ ] **Step 3: Run the broader integration safety suite**

Run: `pytest tests/integrations -q`
Expected: PASS

- [ ] **Step 4: Review the final diff before commit**

Run: `git diff -- src/specify_cli/launcher.py src/specify_cli/shared_hooks/specify-hook src/specify_cli/shared_hooks/specify-hook.cmd src/specify_cli/shared_hooks/specify-hook.py src/specify_cli/integrations/claude/__init__.py src/specify_cli/integrations/gemini/__init__.py pyproject.toml docs/quickstart.md docs/upgrade.md tests/test_launcher.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_subcommand.py tests/test_packaging_assets.py`
Expected: only shared launcher runtime, Claude/Gemini hook command rewiring, packaging updates, docs updates, and matching test changes

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/launcher.py src/specify_cli/shared_hooks/specify-hook src/specify_cli/shared_hooks/specify-hook.cmd src/specify_cli/shared_hooks/specify-hook.py src/specify_cli/integrations/claude/__init__.py src/specify_cli/integrations/gemini/__init__.py pyproject.toml docs/quickstart.md docs/upgrade.md tests/test_launcher.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_subcommand.py tests/test_packaging_assets.py
git commit -m "feat: add stable launcher for native hook entrypoints"
```

## Self-Review

### Spec Coverage

- Stable launcher surface under `.specify/bin/`: covered by Tasks 1, 2, 3, and 4.
- Keep Claude and Gemini dispatch scripts intact: enforced by Tasks 2, 3, 4, and 7.
- Distinguish startup-runtime resolution from shared `specify hook ...` resolution: covered by Tasks 1, 2, and 5.
- Repair and diagnostics for stale direct-dispatch hook commands: covered by Task 5.
- Wheel/offline bundling coverage: covered by Task 6.
- Documentation and upgrade path: covered by Task 7.

### Placeholder Scan

- No `TBD`, `TODO`, or “similar to previous task” placeholders remain.
- Every code-writing task includes concrete code snippets or exact helper shapes.
- Every verification step includes an exact command and expected outcome.

### Type and Naming Consistency

- Shared launcher entrypoint names are consistently `specify-hook`, `specify-hook.cmd`, and `specify-hook.py`.
- Shared runtime override names are consistently `SPECIFY_HOOK_RUNTIME_ARGV` and `SPECIFY_HOOK_RUNTIME_COMMAND`.
- Shared-hook second-hop override names remain `SPECIFY_HOOK_ARGV` and `SPECIFY_HOOK_COMMAND`.
- Diagnostic code name is consistently `stale-direct-hook-launcher-command`.

