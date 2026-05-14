# Claude Node Hook Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate Claude Code managed hook settings that use a shell-free Node launcher instead of `.sh` or `.cmd` hook command strings.

**Architecture:** Keep the existing Python hook dispatcher as the source of hook behavior. Add one thin Node launcher under shared hook assets, then teach the Claude integration to emit Claude Code `command` + `args` hook entries that call that launcher through `${CLAUDE_PROJECT_DIR}`. Existing shell, cmd, and Python launchers remain installed for compatibility and non-Claude integrations.

**Tech Stack:** Python 3.11, pytest, Typer integration tests, Node.js ESM launcher, Claude Code native hook settings JSON.

---

## File Structure

- Create `src/specify_cli/shared_hooks/specify-hook.mjs`
  - Cross-platform outer hook launcher.
  - Resolves project root and Python runtime.
  - Spawns existing `.specify/bin/specify-hook.py`.

- Modify `src/specify_cli/launcher.py`
  - Add `HOOK_LAUNCHER_NODE = "specify-hook.mjs"`.
  - Add a renderer for Claude Code argv-style hook objects.
  - Keep `render_hook_launcher_command()` for Gemini and backwards compatibility.
  - Update diagnostics wording and stale-command detection for old Claude shell/cmd commands.

- Modify `src/specify_cli/integrations/claude/__init__.py`
  - Generate hook dictionaries with `"command": "node"` and `"args": [...]`.
  - Compare managed hook entries by both command and args.
  - Strip stale managed hooks that use legacy direct Python, shell launcher, cmd launcher, or old PowerShell env syntax.
  - Keep user hook entries untouched.

- Modify `tests/test_launcher.py`
  - Add renderer expectations for the Node hook entry.
  - Update shared asset inventory to include `.mjs`.
  - Update diagnostics expectations.

- Modify `tests/integrations/test_integration_claude.py`
  - Update generated settings assertions to inspect hook objects, not only command strings.
  - Confirm both `--script sh` and `--script ps` generate the same Node launcher shape.
  - Confirm manifest/inventory includes `.specify/bin/specify-hook.mjs`.
  - Confirm merge/uninstall behavior still preserves user hooks.

- Modify `tests/integrations/test_integration_subcommand.py`
  - Update repair tests to expect Node hook entries.

- Modify `tests/test_packaging_assets.py`
  - Add `.mjs` to shared hook asset fixture and assertions.

- Modify `README.md`
  - Update the stale hook diagnostic wording only where it currently says bash-style `$CLAUDE_PROJECT_DIR`.

- Modify `docs/superpowers/specs/2026-05-14-claude-node-hook-launcher-design.md`
  - Commit the already-approved example correction from relative path to `${CLAUDE_PROJECT_DIR}`.

---

### Task 1: Lock Shared Launcher Rendering And Asset Expectations

**Files:**
- Modify: `tests/test_launcher.py`
- Modify: `tests/test_packaging_assets.py`

- [ ] **Step 1: Add failing launcher renderer test**

Add this import in `tests/test_launcher.py`:

```python
from specify_cli.launcher import render_claude_hook_launcher
```

If the existing import block already imports from `specify_cli.launcher`, add `render_claude_hook_launcher` to that block instead of adding a duplicate import.

Add this test after `test_render_hook_launcher_command_can_target_powershell_surface_from_posix`:

```python
def test_render_claude_hook_launcher_uses_node_exec_form():
    hook = render_claude_hook_launcher("session-start")

    assert hook == {
        "type": "command",
        "command": "node",
        "args": [
            "${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs",
            "claude",
            "session-start",
        ],
    }
```

- [ ] **Step 2: Update shared asset inventory test to expect `.mjs`**

In `tests/test_launcher.py`, update `test_install_shared_hook_launcher_assets_writes_all_runtime_files` so `relpaths` expectation becomes:

```python
    assert relpaths == [
        ".specify/bin/specify-hook",
        ".specify/bin/specify-hook.cmd",
        ".specify/bin/specify-hook.mjs",
        ".specify/bin/specify-hook.py",
    ]
```

- [ ] **Step 3: Update packaging fixture to include `.mjs`**

In `tests/test_packaging_assets.py`, inside `test_install_shared_infra_copies_split_core_pack_template_dirs`, add this line after the fake `.cmd` asset is written:

```python
    (core_pack / "shared_hooks" / "specify-hook.mjs").write_text("console.log('hook')\n", encoding="utf-8")
```

No assertion is needed in that test because `_install_shared_infra()` intentionally does not install hook assets.

- [ ] **Step 4: Run focused tests and verify failure**

Run:

```bash
pytest tests/test_launcher.py::test_render_claude_hook_launcher_uses_node_exec_form tests/test_launcher.py::test_install_shared_hook_launcher_assets_writes_all_runtime_files tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs -q
```

Expected: FAIL because `render_claude_hook_launcher` and `specify-hook.mjs` do not exist yet.

---

### Task 2: Add The Thin Node Launcher Asset

**Files:**
- Create: `src/specify_cli/shared_hooks/specify-hook.mjs`

- [ ] **Step 1: Create the Node launcher**

Create `src/specify_cli/shared_hooks/specify-hook.mjs` with this content:

```javascript
#!/usr/bin/env node
import { accessSync, constants } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

function exists(path) {
  try {
    accessSync(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function projectRoot() {
  for (const key of ["CLAUDE_PROJECT_DIR", "GEMINI_PROJECT_DIR", "SPECIFY_PROJECT_DIR"]) {
    const value = (process.env[key] || "").trim();
    if (value) {
      return resolve(value);
    }
  }

  const scriptDir = dirname(fileURLToPath(import.meta.url));
  return resolve(scriptDir, "..", "..");
}

function pythonCandidates(root) {
  if (process.platform === "win32") {
    return [
      [resolve(root, ".venv", "Scripts", "python.exe")],
      ["py"],
      ["python"],
    ];
  }

  return [
    [resolve(root, ".venv", "bin", "python")],
    ["python3"],
    ["python"],
  ];
}

function runnable(command) {
  if (command.includes("/") || command.includes("\\")) {
    return exists(command);
  }

  const probe = process.platform === "win32"
    ? spawnSync("where", [command], { stdio: "ignore", shell: false })
    : spawnSync("command", ["-v", command], { stdio: "ignore", shell: true });

  return probe.status === 0;
}

function resolvePython(root) {
  for (const candidate of pythonCandidates(root)) {
    if (runnable(candidate[0])) {
      return candidate;
    }
  }
  return null;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.error("Usage: specify-hook.mjs <integration> <route>");
    return 2;
  }

  const root = projectRoot();
  const launcher = resolve(root, ".specify", "bin", "specify-hook.py");
  if (!exists(launcher)) {
    console.error("Missing .specify/bin/specify-hook.py. Run 'specify integration repair'.");
    return 2;
  }

  const python = resolvePython(root);
  if (!python) {
    console.error("No usable Python runtime found for native hook launcher. Run 'specify integration repair' or install Python.");
    return 2;
  }

  const child = spawnSync(python[0], [...python.slice(1), launcher, ...args], {
    cwd: root,
    env: process.env,
    stdio: "inherit",
    shell: false,
  });

  if (child.error) {
    console.error(`Failed to start native hook launcher: ${child.error.message}`);
    return 2;
  }

  return child.status ?? 2;
}

process.exitCode = main();
```

- [ ] **Step 2: Run focused asset test and verify remaining failure**

Run:

```bash
pytest tests/test_launcher.py::test_install_shared_hook_launcher_assets_writes_all_runtime_files -q
```

Expected: PASS for asset installation once the file exists.

Run:

```bash
pytest tests/test_launcher.py::test_render_claude_hook_launcher_uses_node_exec_form -q
```

Expected: FAIL because the Python renderer is not implemented yet.

---

### Task 3: Add Python Renderer For Claude Exec-Form Hooks

**Files:**
- Modify: `src/specify_cli/launcher.py`

- [ ] **Step 1: Add launcher constant**

Near the existing hook launcher constants, add:

```python
HOOK_LAUNCHER_NODE = "specify-hook.mjs"
```

The constants should read:

```python
HOOK_LAUNCHER_POSIX = "specify-hook"
HOOK_LAUNCHER_WINDOWS = "specify-hook.cmd"
HOOK_LAUNCHER_NODE = "specify-hook.mjs"
HOOK_LAUNCHER_PYTHON = "specify-hook.py"
```

- [ ] **Step 2: Add renderer function**

Add this function immediately after `render_hook_launcher_command()`:

```python
def render_claude_hook_launcher(route: str) -> dict[str, Any]:
    """Render a shell-free Claude Code native-hook launcher entry."""

    return {
        "type": "command",
        "command": "node",
        "args": [
            f"${{CLAUDE_PROJECT_DIR}}/.specify/bin/{HOOK_LAUNCHER_NODE}",
            "claude",
            route,
        ],
    }
```

- [ ] **Step 3: Run renderer and asset tests**

Run:

```bash
pytest tests/test_launcher.py::test_render_claude_hook_launcher_uses_node_exec_form tests/test_launcher.py::test_install_shared_hook_launcher_assets_writes_all_runtime_files -q
```

Expected: PASS.

---

### Task 4: Generate Claude Settings With Node Hook Entries

**Files:**
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Update Claude integration import**

Change the launcher import at the top of `src/specify_cli/integrations/claude/__init__.py` from:

```python
from ...launcher import install_shared_hook_launcher_assets, render_hook_launcher_command
```

to:

```python
from ...launcher import install_shared_hook_launcher_assets, render_claude_hook_launcher
```

- [ ] **Step 2: Replace `_hook_dispatch_command()` with `_hook_dispatch_hook()`**

Replace the current `_hook_dispatch_command()` method with:

```python
    @staticmethod
    def _hook_dispatch_hook(route: str, *, script_type: str = "sh") -> dict[str, Any]:
        del script_type
        return render_claude_hook_launcher(route)
```

The `script_type` argument stays to avoid widening this change through call sites.

- [ ] **Step 3: Update managed hook construction**

In `_build_managed_hook_events()`, replace every hook object like:

```python
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("session-start", script_type=script_type),
                        }
```

with:

```python
                        cls._hook_dispatch_hook("session-start", script_type=script_type)
```

Apply the same replacement for:

```text
user-prompt-submit
post-tool-session-state
stop-monitor
pre-tool-read
pre-tool-bash
```

- [ ] **Step 4: Update Claude test import helper**

In `tests/integrations/test_integration_claude.py`, replace:

```python
from specify_cli.launcher import render_hook_launcher_command
```

with:

```python
from specify_cli.launcher import render_claude_hook_launcher
```

Replace `_expected_launcher_command()` with:

```python
    @staticmethod
    def _expected_launcher_hook(route: str, *, script_type: str = "sh") -> dict[str, object]:
        del script_type
        return render_claude_hook_launcher(route)
```

- [ ] **Step 5: Update settings assertion helper inline**

Where tests currently build a `commands = [...]` list from `hook["command"]`, add or replace with:

```python
        managed_hooks = [
            hook
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
```

Then assert expected hooks with:

```python
        assert self._expected_launcher_hook("user-prompt-submit", script_type="sh") in managed_hooks
        assert self._expected_launcher_hook("pre-tool-read", script_type="sh") in managed_hooks
        assert self._expected_launcher_hook("pre-tool-bash", script_type="sh") in managed_hooks
        assert self._expected_launcher_hook("session-start", script_type="sh") in managed_hooks
        assert self._expected_launcher_hook("post-tool-session-state", script_type="sh") in managed_hooks
        assert self._expected_launcher_hook("stop-monitor", script_type="sh") in managed_hooks
```

- [ ] **Step 6: Update Windows-safe settings test**

Rename `test_setup_writes_windows_safe_hook_commands` to:

```python
    def test_setup_writes_shell_free_hook_entries_for_powershell_script_variant(self, tmp_path):
```

Replace its command-string loop with:

```python
        managed_hooks = [
            hook
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]

        assert managed_hooks
        for hook in managed_hooks:
            assert hook["command"] == "node"
            assert hook["args"][0] == "${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs"
            assert "specify-hook.cmd" not in json.dumps(hook)
            assert "$env:CLAUDE_PROJECT_DIR" not in json.dumps(hook)
```

- [ ] **Step 7: Update manifest inventory expectation**

In `_expected_inventory()`, add:

```python
                ".specify/bin/specify-hook.mjs",
```

between `.specify/bin/specify-hook.cmd` and `.specify/bin/specify-hook.py`.

- [ ] **Step 8: Run focused Claude generation tests and verify failures**

Run:

```bash
pytest tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_installs_hook_assets_and_settings_json tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_writes_shell_free_hook_entries_for_powershell_script_variant -q
```

Expected before stale-merge updates: one or more failures where merge helpers still compare only command strings.

---

### Task 5: Make Hook Merge, Stale Detection, And Uninstall Args-Aware

**Files:**
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Add normalized hook signature helper**

Add this static method after `_normalize_hook_command()`:

```python
    @staticmethod
    def _normalize_hook_signature(hook: Any) -> tuple[str, tuple[str, ...]]:
        if not isinstance(hook, dict):
            return ("", ())
        command = str(hook.get("command") or "").strip()
        args = hook.get("args", [])
        if not isinstance(args, list):
            args = []
        normalized_args = tuple(str(arg) for arg in args if isinstance(arg, str))
        return (command, normalized_args)
```

- [ ] **Step 2: Update `_has_managed_hook_entry()` signature**

Change the method signature from:

```python
        command: str,
```

to:

```python
        expected_hook: dict[str, Any],
```

Replace the method body with:

```python
        expected_signature = self._normalize_hook_signature(expected_hook)
        for entry in existing_entries:
            if not isinstance(entry, dict):
                continue
            if matcher is not None and entry.get("matcher") != matcher:
                continue
            hooks = entry.get("hooks", [])
            if not isinstance(hooks, list):
                continue
            for hook in hooks:
                if self._normalize_hook_signature(hook) == expected_signature:
                    return True
        return False
```

- [ ] **Step 3: Update merge caller**

Inside `_merge_managed_hook_settings()`, replace the current extraction of `command = ...` and the `if not command` check with:

```python
                expected_hook = next(
                    (hook for hook in hooks_list if isinstance(hook, dict)),
                    None,
                )
                if expected_hook is None:
                    continue
```

Then update the `_has_managed_hook_entry()` call to pass:

```python
                    expected_hook=expected_hook,
```

- [ ] **Step 4: Update stale command detection for old launcher commands**

Replace `_is_stale_managed_hook_command()` with:

```python
    @staticmethod
    def _is_stale_managed_hook_command(command: str, managed_suffixes: tuple[str, ...]) -> bool:
        normalized = str(command or "")
        if any(suffix in normalized for suffix in managed_suffixes):
            return True
        if ".specify/bin/specify-hook" in normalized:
            return True
        if '"$env:CLAUDE_PROJECT_DIR"' in normalized or "$env:CLAUDE_PROJECT_DIR" in normalized:
            return True
        return False
```

This strips old `.sh`, `.cmd`, and direct Python managed hook command strings. User hooks that do not contain these managed launcher markers are preserved.

- [ ] **Step 5: Update merge test expected hook comparison**

In `test_setup_merges_existing_settings_json_without_overwriting_user_values`, replace the command equality check:

```python
                and self._expected_launcher_command("pre-tool-read", script_type="sh") == str(hook.get("command", ""))
```

with:

```python
                and self._expected_launcher_hook("pre-tool-read", script_type="sh") == hook
```

- [ ] **Step 6: Update duplicate managed hook test**

In the later duplicate-check test around the `suffixes = (` block, replace it with:

```python
        expected_hooks = (
            self._expected_launcher_hook("session-start", script_type="sh"),
            self._expected_launcher_hook("user-prompt-submit", script_type="sh"),
            self._expected_launcher_hook("pre-tool-read", script_type="sh"),
            self._expected_launcher_hook("pre-tool-bash", script_type="sh"),
            self._expected_launcher_hook("post-tool-session-state", script_type="sh"),
            self._expected_launcher_hook("stop-monitor", script_type="sh"),
        )
        for expected_hook in expected_hooks:
            assert sum(hook == expected_hook for hook in managed_hooks) == 1
```

If that test does not already define `managed_hooks`, add:

```python
        managed_hooks = [
            hook
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
```

- [ ] **Step 7: Run focused Claude integration tests**

Run:

```bash
pytest tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_installs_hook_assets_and_settings_json tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_writes_shell_free_hook_entries_for_powershell_script_variant tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_merges_existing_settings_json_without_overwriting_user_values -q
```

Expected: PASS.

---

### Task 6: Update Repair And Diagnostics Tests

**Files:**
- Modify: `tests/test_launcher.py`
- Modify: `tests/integrations/test_integration_subcommand.py`
- Modify: `src/specify_cli/launcher.py`

- [ ] **Step 1: Update diagnostics wording in tests**

In `tests/test_launcher.py`, rename:

```python
def test_diagnose_project_runtime_compatibility_reports_stale_claude_windows_hook_commands(tmp_path):
```

to:

```python
def test_diagnose_project_runtime_compatibility_reports_stale_claude_shell_hook_commands(tmp_path):
```

Keep the direct Python fixture as-is.

Add this test after it:

```python
def test_diagnose_project_runtime_compatibility_reports_stale_claude_cmd_launcher_commands(tmp_path):
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
                                    "command": '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude session-start',
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

    assert any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues)
```

- [ ] **Step 2: Update diagnostics implementation code and text**

In `src/specify_cli/launcher.py`, in the Claude settings scan, replace the stale Claude condition:

```python
                        if (
                            ".specify/bin/specify-hook" in command
                            and "claude" in command
                            and '"$env:CLAUDE_PROJECT_DIR"' in command
                        ):
                            stale_claude_hook = True
```

with:

```python
                        if ".specify/bin/specify-hook" in command and "claude" in command:
                            stale_claude_hook = True
```

Change the issue block code and summary to:

```python
                    "code": "stale-claude-managed-hook-command",
                    "summary": "Claude managed hook commands still use shell-parsed direct Python, POSIX, cmd, or PowerShell-style launcher commands instead of the shell-free Node launcher.",
```

- [ ] **Step 3: Update direct Python diagnostic test expectation**

In `test_diagnose_project_runtime_compatibility_reports_stale_claude_shell_hook_commands`, update the assertion to:

```python
    assert any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues)
```

Leave `test_diagnose_project_runtime_compatibility_reports_stale_direct_hook_launcher_command` unchanged; direct Python still also reports the generic direct-launcher issue.

- [ ] **Step 4: Update repair tests to inspect hook dicts**

In `tests/integrations/test_integration_subcommand.py`, add:

```python
def _expected_claude_hook(route: str) -> dict[str, object]:
    return {
        "type": "command",
        "command": "node",
        "args": [
            "${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs",
            "claude",
            route,
        ],
    }
```

Place it near `_init_project()`.

- [ ] **Step 5: Update `test_repair_upgrades_direct_claude_hook_commands_to_shared_launcher`**

Replace the final `commands = [...]` block and assertion with:

```python
        hooks = [
            hook
            for entries in repaired_settings["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
        assert _expected_claude_hook("session-start") in hooks
        assert not any(
            isinstance(hook.get("command"), str) and "claude-hook-dispatch.py" in hook["command"]
            for hook in hooks
        )
```

- [ ] **Step 6: Update `test_repair_refreshes_missing_project_launcher_and_stale_claude_hook_commands`**

Replace the final `commands = [...]` block and `assert all(...)` with:

```python
        hooks = [
            hook
            for entries in repaired_settings["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
        assert hooks
        assert _expected_claude_hook("session-start") in hooks
        assert all(hook.get("command") == "node" for hook in hooks)
        assert all("specify-hook.cmd" not in json.dumps(hook) for hook in hooks)
        assert all("$env:CLAUDE_PROJECT_DIR" not in json.dumps(hook) for hook in hooks)
```

- [ ] **Step 7: Run diagnostics and repair tests**

Run:

```bash
pytest tests/test_launcher.py::test_diagnose_project_runtime_compatibility_reports_stale_claude_shell_hook_commands tests/test_launcher.py::test_diagnose_project_runtime_compatibility_reports_stale_claude_cmd_launcher_commands tests/integrations/test_integration_subcommand.py::TestIntegrationRepair::test_repair_upgrades_direct_claude_hook_commands_to_shared_launcher tests/integrations/test_integration_subcommand.py::TestIntegrationRepair::test_repair_refreshes_missing_project_launcher_and_stale_claude_hook_commands -q
```

Expected: PASS.

---

### Task 7: Update User-Facing Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-14-claude-node-hook-launcher-design.md`

- [ ] **Step 1: Update repair diagnostic bullet**

In `README.md`, replace:

```markdown
- stale Claude Windows hook commands that still use PowerShell-style `$env:CLAUDE_PROJECT_DIR` (or legacy `claude-hook-dispatch.py`) instead of bash-style `$CLAUDE_PROJECT_DIR`
```

with:

```markdown
- stale Claude hook commands that still use shell-parsed direct Python, POSIX, cmd, or PowerShell-style launchers instead of the shell-free Node launcher
```

- [ ] **Step 2: Add one sentence to native hook docs**

Under the Claude native hook section after:

```markdown
- `specify init --ai claude` installs thin native adapters in `.claude/hooks/` and merges project-local `.claude/settings.json`.
```

add:

```markdown
- Managed Claude hook entries use Claude Code's `command` + `args` form with `node` and `${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs` to avoid shell-specific path and environment parsing on Windows.
```

- [ ] **Step 3: Stage the approved design doc correction**

The design doc already has the corrected `${CLAUDE_PROJECT_DIR}` example. Include it in the implementation commit:

```bash
git add docs/superpowers/specs/2026-05-14-claude-node-hook-launcher-design.md
```

- [ ] **Step 4: Run README-sensitive tests if present**

Run:

```bash
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS. If this file does not exist in the local checkout, run:

```bash
pytest tests/test_launcher.py -q
```

Expected: PASS.

---

### Task 8: Final Verification And Commit

**Files:**
- Verify all modified files from Tasks 1-7.

- [ ] **Step 1: Run focused test set**

Run:

```bash
pytest tests/test_launcher.py tests/test_packaging_assets.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_subcommand.py -q
```

Expected: PASS.

- [ ] **Step 2: Inspect generated hook JSON manually**

Run:

```bash
python -m pytest tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_setup_installs_hook_assets_and_settings_json -q
```

Expected: PASS.

Then inspect a generated settings file only if a focused test leaves a temporary debug path. Do not add debug prints to tests.

- [ ] **Step 3: Review git diff**

Run:

```bash
git diff -- src/specify_cli/shared_hooks/specify-hook.mjs src/specify_cli/launcher.py src/specify_cli/integrations/claude/__init__.py tests/test_launcher.py tests/test_packaging_assets.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_subcommand.py README.md docs/superpowers/specs/2026-05-14-claude-node-hook-launcher-design.md
```

Check:

- Claude generated managed hooks use `"command": "node"`.
- Claude managed hooks include `"args"` with `${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs`.
- No test still expects `.specify/bin/specify-hook.cmd claude`.
- Gemini behavior is not changed.
- Python hook dispatch behavior is not changed.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add src/specify_cli/shared_hooks/specify-hook.mjs src/specify_cli/launcher.py src/specify_cli/integrations/claude/__init__.py tests/test_launcher.py tests/test_packaging_assets.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_subcommand.py README.md docs/superpowers/specs/2026-05-14-claude-node-hook-launcher-design.md
git commit -m "fix: use node launcher for claude hooks"
```

Expected: commit succeeds.

---

## Self-Review

- Spec coverage: The plan covers the Node launcher asset, Claude settings exec-form generation, repair behavior, diagnostics, packaging assets, compatibility, docs, and focused tests. It does not rewrite Python hook logic or workflow templates, matching the non-goals.
- Placeholder scan: No unresolved placeholder markers remain. Each code-changing task includes exact file paths and concrete code or exact replacement text.
- Type consistency: The planned renderer returns a `dict[str, Any]`, Claude merge code compares normalized `(command, args)` signatures, and tests compare full hook dictionaries.
