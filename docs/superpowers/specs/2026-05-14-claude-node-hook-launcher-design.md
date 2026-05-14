# Claude Node Hook Launcher Design

## Goal

Replace the generated Claude managed native-hook command string with a shell-free Node launcher so Windows projects do not depend on whether Claude Code executes hook commands through bash, PowerShell, or cmd.

The change is intentionally limited to the hook entry layer. Existing hook policy, routing, and output behavior remain in the Python hook dispatch scripts.

## Problem

Claude managed hooks currently render commands such as:

```json
"\"$CLAUDE_PROJECT_DIR\"/.specify/bin/specify-hook.cmd claude session-start"
```

That command shape mixes a bash-style environment variable with a Windows `.cmd` launcher. It avoids one stale PowerShell form, but it still depends on shell parsing semantics. On Windows, Claude Code may run in environments where bash, PowerShell, or cmd behavior differs, especially around variable expansion, path quoting, and executable suffix handling.

## Recommended Approach

Add a small project-local Node launcher:

```text
.specify/bin/specify-hook.mjs
```

Claude managed hooks should invoke this launcher with Claude Code's argv-style command configuration:

```json
{
  "type": "command",
  "command": "node",
  "args": [
    ".specify/bin/specify-hook.mjs",
    "claude",
    "session-start"
  ]
}
```

The Node launcher should:

1. Resolve the project root from `CLAUDE_PROJECT_DIR`, then `GEMINI_PROJECT_DIR`, then `SPECIFY_PROJECT_DIR`, then the launcher's own path.
2. Resolve the Python runtime using the current project-first behavior:
   - `.venv/Scripts/python.exe`
   - `.venv/bin/python`
   - `py` / `python` on Windows
   - `python3` / `python` on POSIX
3. Spawn the existing `.specify/bin/specify-hook.py` with the original integration and route arguments.
4. Forward stdin, stdout, stderr, cwd, and environment.
5. Return the child process exit code.
6. Print a clear stderr message when Node starts successfully but no usable Python runtime can be found.

## Non-Goals

- Do not rewrite `claude-hook-dispatch.py`.
- Do not change hook event behavior for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, or `Stop`.
- Do not change the generated `sp-*` workflow templates.
- Do not remove the existing `specify-hook`, `specify-hook.cmd`, or `specify-hook.py` assets in this change.
- Do not make Gemini depend on the new launcher unless its current hook command surface is intentionally updated in a separate pass.

## Compatibility

Existing generated projects keep working because the current shell and cmd launchers remain installed. New and repaired Claude integrations should prefer the Node launcher.

Node becomes the required outer hook runtime for newly generated or repaired Claude hook settings. This is acceptable because it removes the cross-shell ambiguity from the managed hook command itself, while Python remains the inner runtime for the existing hook implementation.

`specify integration repair` should remove stale managed Claude hook commands that target direct Python dispatch, `.specify/bin/specify-hook`, or `.specify/bin/specify-hook.cmd`, then insert the Node launcher command.

Diagnostics should treat old Claude managed hook commands as refreshable runtime drift.

## Files Expected To Change

- `src/specify_cli/shared_hooks/specify-hook.mjs`
- `src/specify_cli/launcher.py`
- `src/specify_cli/integrations/claude/__init__.py`
- `tests/test_launcher.py`
- `tests/integrations/test_integration_claude.py`
- `tests/integrations/test_integration_subcommand.py`
- `tests/test_packaging_assets.py`
- README or upgrade notes only if test-driven wording updates show user-facing drift

## Testing

Focused tests should verify:

- Shared hook assets include `specify-hook.mjs`.
- Claude settings generated for `--script sh` use the Node launcher.
- Claude settings generated for `--script ps` also use the Node launcher and no longer emit `.cmd` hook commands.
- Repair replaces stale managed hook commands with the Node launcher.
- Diagnostics identify old Claude shell/cmd/direct-Python managed hook commands as stale.
- Existing Python hook dispatch tests continue to pass unchanged.
